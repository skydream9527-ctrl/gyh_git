"""Skill 服务（D-13）：候选 → 个人草稿（立即可用）→ 版本化。

数据落点（沿用 D-06 隔离/复用）：
    候选       tasks/{tid}/skill_candidates.jsonl（追加型，状态后写覆盖）
    个人草稿   users/{uid}/skills/{sid}/skill.json + versions/{n}/{code.txt,meta.json}
               （by-user，立即可用，仅本人可见）
    团队 Skill skills/{sid}/skill.json + versions/{n}/...
               （by-team，需沙盒 test-run 通过 + 审核双门，见 skill_evolve_svc）

Skill 版本化：每次更新写新版本快照，可回滚（回滚=写新版本，不删历史）。
入参 schema 决定 Skill 能否被复用：Python 从 params["k"]/params.get("k") 抽取；SQL 从 :param 抽取。
"""
from __future__ import annotations

import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import append_jsonl, read_json, read_jsonl, write_json, write_text
from app.core.storage.transaction import file_transaction

RUNTIME_PYTHON = "python"
RUNTIME_SQL = "sql"
VALID_RUNTIMES = {RUNTIME_PYTHON, RUNTIME_SQL}

SCOPE_BY_USER = "by_user"  # 个人草稿，立即可用，仅本人
SCOPE_BY_TEAM = "by_team"  # 贡献给团队，需 test-run + 审核
VALID_SKILL_SCOPES = {SCOPE_BY_USER, SCOPE_BY_TEAM}

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


# ─────────────────── 入参 schema 抽取 ───────────────────

_PY_PARAM_RE = re.compile(r"""params\s*(?:\[\s*['"]([A-Za-z_]\w*)['"]\s*\]|\.\s*get\(\s*['"]([A-Za-z_]\w*)['"])""")
_SQL_PARAM_RE = re.compile(r":([A-Za-z_]\w*)")


def extract_schema(code: str, runtime: str) -> list[dict]:
    """从代码抽取入参（决定 Skill 可复用性）。返回 [{name,type,required,default}]，去重保序。"""
    names: list[str] = []
    seen: set[str] = set()
    pattern = _SQL_PARAM_RE if runtime == RUNTIME_SQL else _PY_PARAM_RE
    for m in pattern.finditer(code or ""):
        name = m.group(1) if runtime == RUNTIME_SQL else (m.group(1) or m.group(2))
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return [{"name": n, "type": "string", "required": True, "default": None} for n in names]


def _schema_defaults(schema: list[dict] | None) -> dict:
    return {p["name"]: p.get("default") for p in (schema or []) if p.get("name")}


# ─────────────────── 候选（SkillCandidate）───────────────────

def propose_skill_candidate(
    task_id: str, *, name: str, description: str, runtime: str, code: str,
    proposer: str = "", scope: str = SCOPE_BY_USER, agent_id: str = "",
    knowledge: str = "", input_schema: list[dict] | None = None,
) -> dict:
    """run_user_code 跑通后提议沉淀为 Skill（写候选，待用户在表单确认范围）。"""
    if runtime not in VALID_RUNTIMES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效运行时: {runtime}")
    if scope not in VALID_SKILL_SCOPES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效 Skill scope: {scope}")
    if not (name or "").strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "Skill 名称不能为空")
    if not (code or "").strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "Skill 代码不能为空")

    schema = input_schema if input_schema is not None else extract_schema(code, runtime)
    cand = {
        "id": f"skc_{uuid.uuid4().hex[:8]}", "ts": _now_iso(),
        "name": name.strip(), "description": (description or "").strip(),
        "runtime": runtime, "code": code,
        "input_schema": schema, "knowledge": (knowledge or "").strip(),
        "agent_id": agent_id, "proposed_scope": scope,
        "source": {"task": task_id, "proposer": proposer},
        "status": STATUS_PENDING, "needs_review": scope == SCOPE_BY_TEAM,
        "test_passed": False, "skill_id": None,
    }
    append_jsonl(paths.task_skill_candidates(task_id), cand)
    return cand


def list_skill_candidates(task_id: str, *, status: str | None = None) -> list[dict]:
    """读取候选，合并同 id 的状态更新（后写覆盖字段）。"""
    records = read_jsonl(paths.task_skill_candidates(task_id))
    latest: dict[str, dict] = {}
    for r in records:
        cid = r.get("id")
        if cid in latest and r.get("_status_update"):
            latest[cid] = {**latest[cid], **{k: v for k, v in r.items() if k != "_status_update"}}
        else:
            latest[cid] = r
    out = list(latest.values())
    if status:
        out = [c for c in out if c.get("status") == status]
    out.sort(key=lambda c: c.get("ts", ""), reverse=True)
    return out


def get_skill_candidate(task_id: str, candidate_id: str) -> dict:
    cand = next((c for c in list_skill_candidates(task_id) if c["id"] == candidate_id), None)
    if cand is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"Skill 候选不存在: {candidate_id}")
    return cand


def append_candidate_update(task_id: str, candidate_id: str, fields: dict) -> None:
    """追加候选状态更新（供 skill_evolve_svc 物化/晋升时调用）。"""
    append_jsonl(paths.task_skill_candidates(task_id), {
        "id": candidate_id, "_status_update": True, "ts": _now_iso(), **fields,
    })


# ─────────────────── 个人草稿 Skill（by-user，立即可用）───────────────────

def create_user_skill(
    uid: str, *, name: str, description: str, runtime: str, code: str,
    input_schema: list[dict] | None = None, knowledge: str = "", source_task: str = "",
) -> dict:
    """创建用户草稿 Skill（v1，立即可用，仅本人可见）。"""
    if runtime not in VALID_RUNTIMES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效运行时: {runtime}")
    if not (name or "").strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "Skill 名称不能为空")
    if not (code or "").strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "Skill 代码不能为空")

    sid = f"sk_{uuid.uuid4().hex[:8]}"
    schema = input_schema if input_schema is not None else extract_schema(code, runtime)
    now = _now_iso()
    skill = {
        "id": sid, "name": name.strip(), "description": (description or "").strip(),
        "runtime": runtime, "scope": SCOPE_BY_USER, "owner": {"uid": uid},
        "input_schema": schema, "knowledge": (knowledge or "").strip(),
        "version": 1, "source_task": source_task,
        "created_at": now, "updated_at": now, "test_passed": False,
    }
    root = paths.user_skill_dir(uid, sid)
    sjp = root / "skill.json"
    with file_transaction([sjp, root / "versions" / "1" / "code.txt", root / "versions" / "1" / "meta.json"]):
        _write_version(root, 1, code, runtime, schema, note="initial")
        write_json(sjp, skill)
    return skill


# ─────────────────── 读取 ───────────────────

def get_skill(sid: str, *, uid: str = "") -> dict:
    """按 id 读 Skill：团队 Skill 优先，其次当前用户的草稿。"""
    team_jp = paths.skill_json(sid)
    if team_jp.exists():
        return read_json(team_jp)
    if uid:
        user_jp = _user_skill_json(uid, sid)
        if user_jp.exists():
            return read_json(user_jp)
    raise APIError(404, ErrorCode.NOT_FOUND, f"Skill 不存在: {sid}")


def read_skill_code(skill: dict, *, version: int | None = None) -> str:
    n = int(version if version is not None else skill["version"])
    code_path = skill_root(skill) / "versions" / str(n) / "code.txt"
    return code_path.read_text(encoding="utf-8") if code_path.exists() else ""


def list_user_skills(uid: str) -> list[dict]:
    """列出用户的草稿 Skill。"""
    from app.core.storage.jsonio import iter_dirs
    out: list[dict] = []
    for d in iter_dirs(paths.user_dir(uid) / "skills"):
        meta = read_json(d / "skill.json")
        if meta:
            out.append(meta)
    out.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return out


def list_team_skills(tid: str = "") -> list[dict]:
    """列出团队共享 Skill（可按 tid 过滤）。"""
    from app.core.storage.jsonio import iter_dirs
    out: list[dict] = []
    for d in iter_dirs(paths.root() / "skills"):
        meta = read_json(d / "skill.json")
        if not meta or meta.get("scope") != SCOPE_BY_TEAM:
            continue
        if tid and meta.get("owner", {}).get("tid") != tid:
            continue
        out.append(meta)
    out.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return out


def list_versions(skill: dict) -> list[dict]:
    """列出 Skill 的历史版本元数据（用于回滚 UI）。"""
    vroot = skill_root(skill) / "versions"
    if not vroot.exists():
        return []
    metas: list[dict] = []
    for d in sorted(vroot.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        meta = read_json(d / "meta.json")
        if meta:
            metas.append(meta)
    return metas


# ─────────────────── 沙盒 test-run ───────────────────

def test_run(sid: str, *, uid: str = "", sample_params: dict | None = None) -> dict:
    """对 Skill 当前版本做一次沙盒 test-run。结果回写 test_passed（团队晋升前置门）。"""
    skill = get_skill(sid, uid=uid)
    code = read_skill_code(skill)
    runtime = skill["runtime"]
    params = sample_params if sample_params is not None else _schema_defaults(skill.get("input_schema"))

    if runtime == RUNTIME_SQL:
        if not get_settings().kyuubi_host:
            result = _degraded("KYUUBI_NOT_CONFIGURED", "Kyuubi 未配置，SQL Skill 无法 test-run", "sql")
        else:
            result = _degraded("KYUUBI_NOT_CONFIGURED", "Kyuubi SQL test-run 尚未接入（M6 stub）", "sql")
    else:
        from app.services import sandbox
        if not sandbox.is_enabled():
            result = _degraded("SANDBOX_NOT_ENABLED", "自演进/沙盒未启用", "python")
        else:
            wd = Path(tempfile.mkdtemp(prefix="idw_skilltest_"))
            try:
                result = sandbox.run_python(code, params=params, workdir=wd)
            finally:
                shutil.rmtree(wd, ignore_errors=True)

    _set_test_passed(skill, bool(result.get("ok")))
    return result


# ─────────────────── 版本写入 / 路径（供 skill_evolve_svc 复用）───────────────────

def skill_json_path(skill: dict) -> Path:
    if skill.get("scope") == SCOPE_BY_TEAM:
        return paths.skill_json(skill["id"])
    return _user_skill_json(skill["owner"]["uid"], skill["id"])


def skill_root(skill: dict) -> Path:
    if skill.get("scope") == SCOPE_BY_TEAM:
        return paths.skill_dir(skill["id"])
    return paths.user_skill_dir(skill["owner"]["uid"], skill["id"])


def save_new_version(skill: dict, code: str, *, note: str = "", input_schema: list[dict] | None = None) -> dict:
    """写入新版本快照并 bump 版本号（原子）。返回更新后的 skill。"""
    root = skill_root(skill)
    n = int(skill["version"]) + 1
    schema = input_schema if input_schema is not None else skill.get("input_schema", [])
    now = _now_iso()
    new_skill = {**skill, "version": n, "updated_at": now, "input_schema": schema}
    sjp = skill_json_path(skill)
    with file_transaction([sjp, root / "versions" / str(n) / "code.txt", root / "versions" / str(n) / "meta.json"]):
        _write_version(root, n, code, skill["runtime"], schema, note=note)
        write_json(sjp, new_skill)
    return new_skill


def write_skill_meta(skill: dict) -> None:
    """覆盖写 skill.json（用于绑定/状态变更等不涉及代码版本的更新）。"""
    write_json(skill_json_path(skill), skill)


# ─────────────────── 内部 ───────────────────

def _write_version(root: Path, n: int, code: str, runtime: str, schema: list[dict], *, note: str) -> None:
    vdir = root / "versions" / str(int(n))
    write_text(vdir / "code.txt", code)
    write_json(vdir / "meta.json", {
        "version": int(n), "runtime": runtime, "created_at": _now_iso(),
        "note": note, "input_schema": schema,
    })


def _user_skill_json(uid: str, sid: str) -> Path:
    return paths.user_skill_dir(uid, sid) / "skill.json"


def _set_test_passed(skill: dict, passed: bool) -> None:
    skill = {**skill, "test_passed": passed, "updated_at": _now_iso()}
    write_json(skill_json_path(skill), skill)


def _degraded(error_code: str, message: str, runtime: str) -> dict:
    return {
        "ok": False, "error_code": error_code, "message": message, "runtime": runtime,
        "stdout": "", "stderr": "", "exit_code": None, "timed_out": False, "duration_ms": 0,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
