"""Experience cards. Source of truth: tasks/{tid}/experience_cards.json.

Approved cards are merged into agents/{aid}/prompt/cards.md and injected
into the Agent's system prompt (D66 / D118).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..core.errors import APIError, ErrorCode
from ..core.storage import get_index_db, get_paths, read_json, write_json


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


# ---- cache index ----

CARDS_INDEX_DDL = """
CREATE TABLE IF NOT EXISTS experience_cards_index (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL,
    agent_id    TEXT,
    author_id   TEXT,
    status      TEXT NOT NULL DEFAULT 'draft',
    title       TEXT,
    created_at  TEXT
);
CREATE INDEX IF NOT EXISTS ix_cards_status ON experience_cards_index(status);
CREATE INDEX IF NOT EXISTS ix_cards_agent ON experience_cards_index(agent_id);
"""


async def ensure_index() -> None:
    await get_index_db().executescript(CARDS_INDEX_DDL)


# ---- per-task storage ----


def _cards_path(task_id: str) -> Path:
    return get_paths().task_experience_cards(task_id)


def _read_task_cards(task_id: str) -> list[dict]:
    return read_json(_cards_path(task_id), default=[]) or []


def _write_task_cards(task_id: str, cards: list[dict]) -> None:
    write_json(_cards_path(task_id), cards)


# ---- public CRUD ----


async def create_draft(
    *,
    task_id: str,
    author_id: str,
    agent_id: str | None,
    title: str,
    rule: str,
    reason: str | None = None,
    source_message_id: str | None = None,
) -> dict:
    await ensure_index()
    cards = _read_task_cards(task_id)
    card = {
        "id": _new_id(),
        "task_id": task_id,
        "agent_id": agent_id,
        "author_id": author_id,
        "title": title.strip()[:120],
        "rule": rule.strip(),
        "reason": (reason or "").strip(),
        "source_message_id": source_message_id,
        "status": "draft",
        "reject_reason": None,
        "approved_by": None,
        "approved_at": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    cards.append(card)
    _write_task_cards(task_id, cards)
    db = get_index_db()
    await db.upsert(
        "experience_cards_index",
        {
            "id": card["id"],
            "task_id": task_id,
            "agent_id": agent_id,
            "author_id": author_id,
            "status": "draft",
            "title": card["title"],
            "created_at": card["created_at"],
        },
    )
    return card


async def list_for_task(task_id: str, *, status: str | None = None) -> list[dict]:
    cards = _read_task_cards(task_id)
    if status:
        cards = [c for c in cards if c.get("status") == status]
    cards.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    return cards


async def list_admin(
    *,
    status: str | None = None,
    agent_id: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Cross-task list for admin review center."""
    await ensure_index()
    db = get_index_db()
    where: list[str] = []
    params: list = []
    if status:
        where.append("status = ?")
        params.append(status)
    if agent_id:
        where.append("agent_id = ?")
        params.append(agent_id)
    sql = "SELECT * FROM experience_cards_index"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = await db.fetchall(sql, params)
    out: list[dict] = []
    for r in rows:
        for c in _read_task_cards(r["task_id"]):
            if c["id"] == r["id"]:
                out.append(c)
                break
    return out


async def list_public(*, agent_id: str, limit: int = 50) -> list[dict]:
    """Approved-only cards for an agent (Agent detail page user view)."""
    await ensure_index()
    db = get_index_db()
    rows = await db.fetchall(
        "SELECT * FROM experience_cards_index WHERE agent_id = ? AND status = 'approved' ORDER BY created_at DESC LIMIT ?",
        [agent_id, limit],
    )
    out: list[dict] = []
    for r in rows:
        for c in _read_task_cards(r["task_id"]):
            if c["id"] == r["id"]:
                out.append(c)
                break
    return out


async def update_status(
    *,
    card_id: str,
    new_status: str,
    operator_id: str,
    reject_reason: str | None = None,
) -> dict:
    if new_status not in {"approved", "rejected", "draft"}:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "status 非法")
    await ensure_index()
    db = get_index_db()
    row = await db.fetchone("SELECT task_id FROM experience_cards_index WHERE id = ?", [card_id])
    if not row:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "卡片不存在")
    task_id = row["task_id"]
    cards = _read_task_cards(task_id)
    target = next((c for c in cards if c["id"] == card_id), None)
    if not target:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "卡片不存在")
    # Spec 4.9: approved is terminal
    if target.get("status") == "approved" and new_status == "rejected":
        raise APIError(409, ErrorCode.CARD_STATUS_IMMUTABLE, "已审批通过的卡片不可回滚")
    target["status"] = new_status
    target["reject_reason"] = reject_reason if new_status == "rejected" else None
    target["approved_by"] = operator_id if new_status == "approved" else None
    target["approved_at"] = _now() if new_status == "approved" else None
    target["updated_at"] = _now()
    _write_task_cards(task_id, cards)
    await db.execute(
        "UPDATE experience_cards_index SET status = ? WHERE id = ?", [new_status, card_id]
    )
    if target.get("agent_id"):
        rebuild_agent_cards(target["agent_id"])
    return target


async def batch_review(
    *,
    card_ids: Iterable[str],
    new_status: str,
    operator_id: str,
    reject_reason: str | None = None,
) -> list[dict]:
    out = []
    for cid in card_ids:
        try:
            out.append(
                await update_status(
                    card_id=cid,
                    new_status=new_status,
                    operator_id=operator_id,
                    reject_reason=reject_reason,
                )
            )
        except APIError:
            continue
    return out


# ---- Agent prompt injection ----


def rebuild_agent_cards(agent_id: str) -> None:
    """Rebuild agents/{aid}/prompt/cards.md from all approved cards."""
    paths = get_paths()
    if not paths.tasks.exists():
        return
    approved: list[dict] = []
    for d in paths.tasks.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        for c in read_json(d / "experience_cards.json", default=[]) or []:
            if c.get("agent_id") == agent_id and c.get("status") == "approved":
                approved.append(c)
    approved.sort(key=lambda c: c.get("approved_at") or "", reverse=False)
    cards_path = paths.agents / agent_id / "prompt" / "cards.md"
    cards_path.parent.mkdir(parents=True, exist_ok=True)
    if not approved:
        if cards_path.exists():
            cards_path.unlink()
        return
    lines = ["# 经验规则（自动注入）", ""]
    for i, c in enumerate(approved, 1):
        lines.append(f"## {i}. {c.get('title') or '(无标题)'}")
        if c.get("rule"):
            lines.append(c["rule"])
        if c.get("reason"):
            lines.append(f"\n> 依据：{c['reason']}")
        lines.append("")
    cards_path.write_text("\n".join(lines), encoding="utf-8")


_TODO_INSTRUCTIONS = (
    "# 待办跟踪（todo_write）\n"
    "当用户请求包含 **3 个及以上明显步骤** 时，立即调用 `todo_write` 写一份完整 todo 列表。"
    "每次调用传**全量列表**（replace-all 语义）。"
    "开始动手**之前**把该项置 `in_progress`；完成**立刻**置 `completed`，不要批量。"
    "同一时刻**仅允许一条** `in_progress`。"
    "若被卡住，保持该项 `in_progress` 并新增一项 `pending` 描述阻塞原因。"
    "前端会实时渲染这份列表让用户看到进度。"
)

_PLAN_MODE_BANNER = (
    "# 当前处于 Plan Mode（计划模式）\n"
    "**禁止**任何有副作用的工具：`write_file` / `feishu_publish` / `spawn_subagent` / `run_background` 都被后端闸门拦截。\n"
    "允许工具以当前 function tools 列表为准，通常只包括只读工具、`todo_write` 和 `exit_plan_mode`；"
    "如果某个工具没有出现在当前工具列表中，不要承诺或调用。\n"
    "工作流：用只读工具充分调研 → 产出**完整、可执行**的方案 → 调用 `exit_plan_mode(plan=<markdown>)` 并**立刻停止生成**。"
    "不要在调用 `exit_plan_mode` 后继续说话——用户会审批，批准后你会自动被重新唤起执行。"
)


def merged_system_prompt(
    agent_id: str,
    *,
    plan_mode: bool = False,
    task_skill_ids: list[str] | None = None,
    callable_tool_names: list[str] | None = None,
) -> str:
    """Agent base prompt + approved cards + skill catalog.

    The skill catalog section is task-scoped:
      - `task_skill_ids` is None → show every globally-callable function tool
        plus EVERY agentic skill (legacy behavior, used by admin sandbox /
        scheduler / pre-task contexts where there is no task to scope to).
      - `task_skill_ids` is a list → show globally-callable function tools
        plus ONLY the agentic skills bound to the task. Agentic skills not in
        the list are not enumerated to the LLM, so it doesn't even know they
        exist (preventing it from calling read_skill against unbound ones, or
        from regurgitating a "here are all the skills" table to the user).

    `plan_mode=True` appends the PLAN MODE banner so the LLM knows write-side
    tools are off-limits until `exit_plan_mode` is called.
    """
    from ..core.config import get_settings
    from .agent_prompt_builder import build_base_prompt

    base = build_base_prompt(agent_id)
    cards_path = get_paths().agents / agent_id / "prompt" / "cards.md"
    parts: list[str] = [base]
    if cards_path.exists():
        parts.append(cards_path.read_text(encoding="utf-8"))
    skill_section = _build_skill_catalog_section(
        task_skill_ids=task_skill_ids,
        callable_tool_names=callable_tool_names,
    )
    if skill_section:
        parts.append(skill_section)
    s = get_settings()
    if s.ICE_TODO_ENABLED:
        parts.append(_TODO_INSTRUCTIONS)
    if plan_mode and s.ICE_PLAN_MODE_ENABLED:
        parts.append(_PLAN_MODE_BANNER)
    return "\n\n---\n\n".join(parts)


def _build_skill_catalog_section(
    *,
    task_skill_ids: list[str] | None = None,
    callable_tool_names: list[str] | None = None,
) -> str:
    """Skill index for the system prompt.

    Strategy: list every skill's `id` + frontmatter `description` only (a few
    KB total). The full SKILL.md body is fetched on-demand via the `read_skill`
    function tool when the LLM decides a skill applies. This is the Claude
    Code progressive-disclosure pattern; it keeps the system prompt small
    enough to cache cheaply across rounds.

    When `task_skill_ids` is provided, agentic-skill enumeration is filtered
    to that allowlist so the LLM is unaware of unbound skills.
    """
    from .skill_svc import list_all

    try:
        skills = list_all()
    except Exception:
        return ""
    if not skills:
        return ""

    all_callable_names = {
        "now",
        "echo",
        "kyuubi_query",
        "execute_python",
        "volcano_abtest_analyze",
        "write_file",
        "list_files",
        "read_file",
        "feishu_publish",
        "feishu_upload_image",
        "read_skill",
        "read_agent_knowledge",
        "todo_write",
        "request_human_input",
        "exit_plan_mode",
        "spawn_subagent",
        "run_background",
    }
    callable_names = (
        all_callable_names
        if callable_tool_names is None
        else all_callable_names.intersection(callable_tool_names)
    )
    from .tool_runner import _read_skill_description_for_task

    callable_lines: list[str] = []
    agentic_lines: list[str] = []
    bound_set: set[str] | None = set(task_skill_ids) if task_skill_ids is not None else None

    for s in skills:
        sid = s.get("id") or s.get("name") or ""
        name = s.get("name") or sid
        desc = (s.get("description") or "").strip().replace("\n", " ")
        # `read_skill` 的官方描述硬编码了 kyuubi/nl-mapping-table-sql/docx/... 全集示例；
        # task 内必须用任务作用域的描述覆盖，否则 LLM 仍会从这条索引里读到全部
        # skill 名字并在回复里复述给用户。
        if sid == "read_skill" and bound_set is not None:
            desc = _read_skill_description_for_task(list(task_skill_ids or [])).replace("\n", " ")
        if len(desc) > 280:
            desc = desc[:280].rstrip() + "…"
        if sid in callable_names:
            callable_lines.append(f"- `{sid}` — {name}：{desc}")
            continue
        if s.get("category") == "agentic":
            if bound_set is not None and sid not in bound_set:
                continue
            agentic_lines.append(f"- `{sid}` — {name}：{desc}")

    if bound_set is None:
        header = "# 可用 Skill 全集（全局，所有 Agent 共享）"
        intro = "本平台对所有 Agent 暴露同一套 Skill。下面是索引，全文按需用 `read_skill` 拉取。"
    else:
        header = "# 本任务可用 Skill"
        intro = (
            "下面是**本任务**绑定的 Skill 索引（agentic skill 仅列任务里加过的；其他 skill "
            "对本任务不可见，禁止臆测、禁止调用 `read_skill` 索取未列出的 id）。"
            "agentic 全文按需用 `read_skill(skill_id=...)` 拉取。"
        )
    out: list[str] = [header, intro]
    if callable_lines:
        out.append(
            "## 直接调用的函数工具（function calling）\n"
            "下列工具已注册，按需 tool_use 即可：\n\n"
            + "\n".join(callable_lines)
        )
    if agentic_lines:
        out.append(
            "## Agentic Skills（说明书型）\n"
            "以下 Skill 没有独立函数工具，而是说明书。当用户请求命中其触发条件时，"
            "**先调用 `read_skill(skill_id=...)` 拉取完整说明，再严格按其步骤执行**；"
            "产出的最终内容请用 `write_file` 保存到工作区，必要时用 `feishu_publish` 发布。\n\n"
            + "\n".join(agentic_lines)
        )
    elif bound_set is not None:
        out.append(
            "## Agentic Skills（说明书型）\n"
            "本任务**未绑定任何 agentic skill**。如需 nl-mapping-table-sql / docx / pdf 之类，"
            "请提示用户去工作区右栏「🧰 本任务 Skills」点击 +添加。"
        )
    return "\n\n".join(out)


def reindex_all() -> int:
    """Reload index from per-task files. Returns number of cards indexed."""
    paths = get_paths()
    if not paths.tasks.exists():
        return 0
    import asyncio

    async def _run():
        await ensure_index()
        db = get_index_db()
        count = 0
        for d in paths.tasks.iterdir():
            if not d.is_dir() or d.name.startswith("."):
                continue
            for c in read_json(d / "experience_cards.json", default=[]) or []:
                await db.upsert(
                    "experience_cards_index",
                    {
                        "id": c["id"],
                        "task_id": d.name,
                        "agent_id": c.get("agent_id"),
                        "author_id": c.get("author_id"),
                        "status": c.get("status", "draft"),
                        "title": c.get("title"),
                        "created_at": c.get("created_at"),
                    },
                )
                count += 1
        return count

    return asyncio.run(_run())


def build_system_prompt_for_task(task_id: str) -> str:
    """Mode-aware prompt build (spec 4.2).

    - system.md: always read from task snapshot
    - cards.md: live → source (with fallback); frozen → snapshot
    - skills catalog: from task's skills INDEX
    """
    paths = get_paths()
    snap = read_json(paths.task_snapshot(task_id)) or {"mode": "live"}
    meta = read_json(paths.task_meta(task_id)) or {}
    agent_id = meta.get("agent_id")

    system_md = ""
    sys_path = paths.task_agent_system_md(task_id)
    if sys_path.exists():
        system_md = sys_path.read_text()

    if snap.get("mode") == "frozen":
        cards_md = _safe_read(paths.task_agent_cards_md(task_id))
    else:
        src = paths.agent_prompt_cards_md(agent_id) if agent_id else None
        if src and src.exists():
            cards_md = src.read_text()
        else:
            cards_md = _safe_read(paths.task_agent_cards_md(task_id))

    skills_catalog = read_json(paths.task_skills_index(task_id), default=[]) or []
    skill_lines = "\n".join(
        f"- {s['id']}: {s.get('description', '')}" for s in skills_catalog
    )

    parts = [system_md]
    if cards_md.strip():
        parts.append("## Approved Experience Cards\n" + cards_md)
    if skill_lines:
        parts.append("## Available Skills\n" + skill_lines)
    return "\n\n".join(parts).strip()


def _safe_read(path) -> str:
    try:
        return path.read_text()
    except (FileNotFoundError, OSError):
        return ""
