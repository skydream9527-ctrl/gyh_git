"""记忆服务：候选生成 → 审批 → 晋升（5 种 scope），隔离/复用闭环（材料三 §4）。

记忆文件格式 `*.memory.md`：人类可读 + 机器可索引。
    ---
    scope: <scope>
    owner: <owner_ref>
    updated_at: <date>
    ---

    ## MEM-<id>  [confidence: high] [verified: <date>]
    <content>
    - tags: [...]
    - source: task:<tid> / proposer:<who>

5 种 scope 与落点（D-06/D-07）：
    user_preference → users/{uid}/twin/memory/preferences.memory.md   （用户本人确认）
    agent_user      → agents/{aid}/memory/by-user/{uid}/usage.memory.md（低风险，本人分区，默认隔离）
    agent_team      → agents/{aid}/memory/by-team/{tid}/shared.memory.md（"贡献给团队"，需审核）
    project         → teams/{tid}/projects/{pid}/shared/memory/shared.memory.md（项目 owner/admin）
    team            → teams/{tid}/shared/memory/shared.memory.md       （团队 owner/admin）

晋升原子性（TDR-5）：file_transaction 内"读候选 → 写目标 .memory.md(分配 MEM-id) → 更新索引 → 候选标 approved"。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import append_jsonl, read_jsonl, write_text
from app.core.storage.transaction import file_transaction

SCOPE_USER_PREFERENCE = "user_preference"
SCOPE_AGENT_USER = "agent_user"
SCOPE_AGENT_TEAM = "agent_team"
SCOPE_PROJECT = "project"
SCOPE_TEAM = "team"

VALID_SCOPES = {
    SCOPE_USER_PREFERENCE, SCOPE_AGENT_USER, SCOPE_AGENT_TEAM, SCOPE_PROJECT, SCOPE_TEAM,
}

# 需审核（管理员/owner）的 scope —— 跨越到共享空间
SCOPES_NEED_REVIEW = {SCOPE_AGENT_TEAM, SCOPE_PROJECT, SCOPE_TEAM}

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


# ─────────────────── 候选 ───────────────────

def propose_candidate(
    task_id: str, *, content: str, scope: str, proposer: str = "",
    tags: list[str] | None = None,
) -> dict:
    """生成记忆候选，追加到 tasks/{tid}/memory/candidates.jsonl。"""
    if scope not in VALID_SCOPES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效记忆 scope: {scope}")
    if not content.strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "记忆内容不能为空")

    cand = {
        "id": f"cand_{uuid.uuid4().hex[:8]}",
        "ts": _now_iso(),
        "proposed_scope": scope,
        "content": content.strip(),
        "tags": tags or [],
        "source": {"task": task_id, "proposer": proposer},
        "status": STATUS_PENDING,
        "needs_review": scope in SCOPES_NEED_REVIEW,
    }
    append_jsonl(paths.task_candidates(task_id), cand)
    return cand


def list_candidates(task_id: str, *, status: str | None = None) -> list[dict]:
    """读取任务的记忆候选。candidates.jsonl 是追加型，取每个 id 的最新状态。"""
    records = read_jsonl(paths.task_candidates(task_id))
    # 合并同 id 的状态更新（后写覆盖）
    latest: dict[str, dict] = {}
    for r in records:
        cid = r.get("id")
        if cid in latest and r.get("_status_update"):
            latest[cid] = {**latest[cid], "status": r["status"], "decided_by": r.get("decided_by")}
        else:
            latest[cid] = r
    out = list(latest.values())
    if status:
        out = [c for c in out if c.get("status") == status]
    return out


def get_candidate(task_id: str, candidate_id: str) -> dict:
    cand = next((c for c in list_candidates(task_id) if c["id"] == candidate_id), None)
    if cand is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"记忆候选不存在: {candidate_id}")
    return cand


# ─────────────────── 晋升 / 拒绝 ───────────────────

def promote(
    task_id: str, candidate_id: str, *,
    decided_by: str,
    uid: str = "", aid: str = "", tid: str = "", pid: str = "",
    override_scope: str | None = None,
) -> dict:
    """晋升记忆候选到目标空间（原子）。

    根据 scope 需要不同的目标 id：
        user_preference → uid
        agent_user      → aid + uid
        agent_team      → aid + tid
        project         → tid + pid
        team            → tid
    """
    cand = get_candidate(task_id, candidate_id)
    if cand["status"] == STATUS_APPROVED:
        raise APIError(409, ErrorCode.CONFLICT, "该候选已晋升")

    scope = override_scope or cand["proposed_scope"]
    target = _resolve_target(scope, uid=uid, aid=aid, tid=tid, pid=pid)

    mem_id = f"MEM-{uuid.uuid4().hex[:6]}"
    entry = _format_entry(mem_id, cand, scope)

    # 原子：写目标 .memory.md + 候选状态更新（同事务）
    candidates_path = paths.task_candidates(task_id)
    with file_transaction([target, candidates_path]):
        _append_memory_entry(target, scope, entry)
        append_jsonl(candidates_path, {
            "id": candidate_id, "status": STATUS_APPROVED, "decided_by": decided_by,
            "mem_id": mem_id, "promoted_to": str(target), "ts": _now_iso(),
            "_status_update": True,
        })

    return {
        "candidate_id": candidate_id, "mem_id": mem_id, "scope": scope,
        "promoted_to": _relative_to_root(target),
    }


def reject(task_id: str, candidate_id: str, *, decided_by: str, reason: str = "") -> dict:
    """拒绝候选（保留痕迹，可复盘）。"""
    cand = get_candidate(task_id, candidate_id)
    if cand["status"] != STATUS_PENDING:
        raise APIError(409, ErrorCode.CONFLICT, f"候选状态非 pending: {cand['status']}")
    append_jsonl(paths.task_candidates(task_id), {
        "id": candidate_id, "status": STATUS_REJECTED, "decided_by": decided_by,
        "reason": reason, "ts": _now_iso(), "_status_update": True,
    })
    return {"candidate_id": candidate_id, "status": STATUS_REJECTED}


# ─────────────────── 读取记忆 ───────────────────

def read_memory_entries(memory_path) -> list[dict]:
    """解析 .memory.md，返回条目列表 [{mem_id, content, confidence, tags, source}]。"""
    if not memory_path.exists():
        return []
    text = memory_path.read_text(encoding="utf-8")
    return _parse_memory_md(text)


def list_scope_memory(scope: str, *, uid: str = "", aid: str = "", tid: str = "", pid: str = "") -> list[dict]:
    """读取某 scope 空间内的全部记忆条目。"""
    target = _resolve_target(scope, uid=uid, aid=aid, tid=tid, pid=pid)
    return read_memory_entries(target)


# ─────────────────── 内部：scope 路由 ───────────────────

def _resolve_target(scope: str, *, uid: str, aid: str, tid: str, pid: str):
    if scope == SCOPE_USER_PREFERENCE:
        if not uid:
            raise APIError(400, ErrorCode.BAD_REQUEST, "user_preference 需 uid")
        return paths.twin_dir(uid) / "memory" / "preferences.memory.md"
    if scope == SCOPE_AGENT_USER:
        if not (aid and uid):
            raise APIError(400, ErrorCode.BAD_REQUEST, "agent_user 需 aid + uid")
        return paths.agent_user_memory(aid, uid)
    if scope == SCOPE_AGENT_TEAM:
        if not (aid and tid):
            raise APIError(400, ErrorCode.BAD_REQUEST, "agent_team 需 aid + tid")
        return paths.agent_team_memory(aid, tid)
    if scope == SCOPE_PROJECT:
        if not (tid and pid):
            raise APIError(400, ErrorCode.BAD_REQUEST, "project 需 tid + pid")
        return paths.project_shared(tid, pid, "memory") / "shared.memory.md"
    if scope == SCOPE_TEAM:
        if not tid:
            raise APIError(400, ErrorCode.BAD_REQUEST, "team 需 tid")
        return paths.team_shared(tid, "memory") / "shared.memory.md"
    raise APIError(400, ErrorCode.BAD_REQUEST, f"无效 scope: {scope}")


# ─────────────────── 内部：memory.md 格式 ───────────────────

_MEM_HEADER_RE = re.compile(r"^##\s+(MEM-[A-Za-z0-9]+)\s*(.*)$")


def _format_entry(mem_id: str, cand: dict, scope: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags = cand.get("tags", [])
    src = cand.get("source", {})
    src_str = f"task:{src.get('task', '')} / proposer:{src.get('proposer', '')}"
    lines = [
        f"## {mem_id}  [confidence: medium] [verified: {today}]",
        cand["content"],
        f"- tags: [{', '.join(tags)}]",
        f"- source: {src_str}",
        "",
    ]
    return "\n".join(lines)


def _append_memory_entry(target, scope: str, entry: str) -> None:
    """追加条目到 .memory.md；文件不存在则先写 frontmatter 头。"""
    paths.ensure(target)
    if target.exists() and target.read_text(encoding="utf-8").strip():
        existing = target.read_text(encoding="utf-8").rstrip() + "\n\n"
        write_text(target, existing + entry)
    else:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        header = f"---\nscope: {scope}\nupdated_at: {today}\n---\n\n"
        write_text(target, header + entry)


def _parse_memory_md(text: str) -> list[dict]:
    """解析 .memory.md 为条目列表。"""
    entries: list[dict] = []
    # 跳过 frontmatter
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            body = parts[2]

    current: dict | None = None
    content_lines: list[str] = []
    for line in body.splitlines():
        m = _MEM_HEADER_RE.match(line.strip())
        if m:
            if current is not None:
                current["content"] = "\n".join(content_lines).strip()
                entries.append(current)
            mem_id = m.group(1)
            meta = m.group(2)
            conf = re.search(r"confidence:\s*(\w+)", meta)
            current = {"mem_id": mem_id, "confidence": conf.group(1) if conf else "medium",
                       "content": "", "tags": [], "source": ""}
            content_lines = []
        elif current is not None:
            stripped = line.strip()
            if stripped.startswith("- tags:"):
                tags_str = stripped[len("- tags:"):].strip().strip("[]")
                current["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
            elif stripped.startswith("- source:"):
                current["source"] = stripped[len("- source:"):].strip()
            else:
                content_lines.append(line)
    if current is not None:
        current["content"] = "\n".join(content_lines).strip()
        entries.append(current)
    return entries


def _relative_to_root(path) -> str:
    try:
        return str(path.relative_to(paths.root()))
    except ValueError:
        return str(path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
