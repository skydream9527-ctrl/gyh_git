"""任务服务：任务模型 + 6 态状态机 + 参与者管理（D-14）+ 目标/DoD 门控（M7-T08）。

状态机（6 态）：
    todo（待办）→ doing（执行中）→ await（待确认）→ done（已完成）
    doing/await → error（报错）  ·  任意活跃态 → paused（已暂停）

任务必须归属项目（project_id，缺省落用户个人项目，D-11）。
参与者 participants[]：user / twin / agent，一等 assignee。
目标/完成判据（M7-T08）：goal + definition_of_done；置 done 时若 DoD 非空，
    需"计划步骤全完成"或"显式确认"才放行（DoD 不满足不许完成）。
存储：tasks/{tid}/task.json（G3 文件优先）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json, write_json

# ─── 状态机 ───

STATUS_TODO = "todo"
STATUS_DOING = "doing"
STATUS_AWAIT = "await"
STATUS_DONE = "done"
STATUS_ERROR = "error"
STATUS_PAUSED = "paused"

ALL_STATUSES = {STATUS_TODO, STATUS_DOING, STATUS_AWAIT, STATUS_DONE, STATUS_ERROR, STATUS_PAUSED}

# 合法状态流转（from -> {to...}）
_TRANSITIONS: dict[str, set[str]] = {
    STATUS_TODO: {STATUS_DOING, STATUS_PAUSED},
    STATUS_DOING: {STATUS_AWAIT, STATUS_DONE, STATUS_ERROR, STATUS_PAUSED, STATUS_TODO},
    STATUS_AWAIT: {STATUS_DOING, STATUS_DONE, STATUS_ERROR, STATUS_PAUSED},
    STATUS_ERROR: {STATUS_DOING, STATUS_PAUSED, STATUS_TODO},
    STATUS_PAUSED: {STATUS_DOING, STATUS_TODO},
    STATUS_DONE: {STATUS_DOING},  # 重新打开
}

VALID_PARTICIPANT_TYPES = {"user", "twin", "agent"}
VALID_PARTICIPANT_ROLES = {"owner", "collaborator", "tool"}


def can_transition(from_status: str, to_status: str) -> bool:
    if to_status not in ALL_STATUSES:
        return False
    return to_status in _TRANSITIONS.get(from_status, set())


# ─── 查询 ───

def get_task(task_id: str) -> dict:
    meta = read_json(paths.task_json(task_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"任务不存在: {task_id}")
    return meta


def list_tasks(
    *,
    project_id: str | None = None,
    user_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """列出任务，可按 project / 参与用户 / 状态过滤。"""
    out: list[dict] = []
    for d in iter_dirs(paths.root() / "tasks"):
        meta = read_json(d / "task.json")
        if meta is None:
            continue
        if meta.get("deleted_at"):
            continue
        if project_id and meta.get("project_id") != project_id:
            continue
        if status and meta.get("status") != status:
            continue
        if user_id and not _is_participant(meta, user_id):
            continue
        out.append(_task_summary(meta))
    # 按更新时间倒序
    out.sort(key=lambda t: t.get("updated_at") or t.get("created_at") or "", reverse=True)
    return out


# ─── 创建 / 更新 ───

def create_task(
    *,
    title: str,
    project_id: str,
    created_by: str,
    task_type: str = "general",
    participants: list[dict] | None = None,
    assignee: dict | None = None,
    goal: str = "",
    definition_of_done: str = "",
) -> dict:
    """创建任务。created_by 自动作为 owner 参与者。"""
    if not title.strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "任务标题不能为空")
    if task_type not in ("data", "general"):
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效任务类型: {task_type}")

    task_id = f"t_{uuid.uuid4().hex[:12]}"

    # 参与者：创建者必为 owner
    parts = [{"ref_type": "user", "ref_id": created_by, "role": "owner",
              "permission_level": "L3", "joined_at": _now_iso()}]
    for p in participants or []:
        _validate_participant(p)
        if not any(x["ref_id"] == p["ref_id"] and x["ref_type"] == p["ref_type"] for x in parts):
            parts.append({**p, "joined_at": _now_iso()})

    meta = {
        "id": task_id,
        "project_id": project_id,
        "title": title.strip(),
        "type": task_type,
        "status": STATUS_TODO,
        "goal": goal.strip(),
        "definition_of_done": definition_of_done.strip(),
        "assignee": assignee,
        "participants": parts,
        "artifacts": [],
        "created_by": created_by,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    paths.ensure(paths.task_json(task_id))
    write_json(paths.task_json(task_id), meta)
    return meta


def update_task(
    task_id: str, *, title: str | None = None, assignee: dict | None = None,
    goal: str | None = None, definition_of_done: str | None = None,
) -> dict:
    meta = get_task(task_id)
    if title is not None:
        if not title.strip():
            raise APIError(400, ErrorCode.BAD_REQUEST, "任务标题不能为空")
        meta["title"] = title.strip()
    if assignee is not None:
        meta["assignee"] = assignee
    if goal is not None:
        meta["goal"] = goal.strip()
    if definition_of_done is not None:
        meta["definition_of_done"] = definition_of_done.strip()
    meta["updated_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)
    return meta


def set_status(task_id: str, new_status: str, *, reason: str = "", confirm: bool = False) -> dict:
    """状态流转（校验合法性 + DoD 门控）。

    DoD 门控（M7-T08）：置 done 且 definition_of_done 非空时，需"计划全部完成"或 confirm=True；
    否则拒绝（DoD 不满足不许完成）。DoD 为空时行为与 v1 一致（自由置 done）。
    """
    meta = get_task(task_id)
    current = meta.get("status", STATUS_TODO)

    if current == new_status:
        return meta  # 幂等

    if not can_transition(current, new_status):
        raise APIError(
            400, ErrorCode.BAD_REQUEST,
            f"非法状态流转: {current} → {new_status}",
        )

    if new_status == STATUS_DONE and (meta.get("definition_of_done") or "").strip():
        if not (confirm or _plan_complete(task_id)):
            raise APIError(
                400, ErrorCode.BAD_REQUEST,
                "完成判据（DoD）未满足：需完成全部计划步骤，或由用户显式确认完成",
            )

    meta["status"] = new_status
    meta["updated_at"] = _now_iso()
    if new_status == STATUS_ERROR and reason:
        meta["error_reason"] = reason
    if new_status == STATUS_PAUSED:
        meta["paused_from"] = current
    if new_status == STATUS_DONE:
        meta["completed_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)
    return meta


def delete_task(task_id: str) -> None:
    """标记删除任务。"""
    meta = get_task(task_id)
    meta["deleted_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)


# ─── 参与者管理 ───

def add_participant(task_id: str, ref_type: str, ref_id: str, *,
                    role: str = "collaborator", permission_level: str = "L2") -> dict:
    """邀请参与者（agent / twin / user）。"""
    participant = {
        "ref_type": ref_type, "ref_id": ref_id,
        "role": role, "permission_level": permission_level,
    }
    _validate_participant(participant)

    meta = get_task(task_id)
    parts = meta.get("participants", [])
    if any(p["ref_id"] == ref_id and p["ref_type"] == ref_type for p in parts):
        raise APIError(409, ErrorCode.CONFLICT, f"{ref_type}:{ref_id} 已是参与者")

    participant["joined_at"] = _now_iso()
    parts.append(participant)
    meta["participants"] = parts
    meta["updated_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)

    # 建参与者任务级笔记
    notes = paths.task_participant_notes(task_id, ref_id)
    if not notes.exists():
        paths.ensure(notes)
        notes.write_text(f"# {ref_type}:{ref_id} 在任务 {task_id} 的笔记\n\n", encoding="utf-8")

    return meta


def remove_participant(task_id: str, ref_type: str, ref_id: str) -> dict:
    meta = get_task(task_id)
    parts = meta.get("participants", [])
    entry = next((p for p in parts if p["ref_id"] == ref_id and p["ref_type"] == ref_type), None)
    if entry is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"{ref_type}:{ref_id} 不是参与者")
    if entry.get("role") == "owner":
        raise APIError(400, ErrorCode.BAD_REQUEST, "不能移除任务 owner")

    meta["participants"] = [p for p in parts
                            if not (p["ref_id"] == ref_id and p["ref_type"] == ref_type)]
    meta["updated_at"] = _now_iso()
    write_json(paths.task_json(task_id), meta)
    return meta


def list_participants(task_id: str) -> list[dict]:
    return get_task(task_id).get("participants", [])


# ─── 内部 ───

def _plan_complete(task_id: str) -> bool:
    """计划是否全部完成（供 DoD 门控）；无计划返回 False。"""
    try:
        from app.services import plan_svc
        return plan_svc.is_plan_complete(task_id)
    except Exception:
        return False


def _is_participant(meta: dict, user_id: str) -> bool:
    return any(
        p.get("ref_type") == "user" and p.get("ref_id") == user_id
        for p in meta.get("participants", [])
    )


def _task_summary(meta: dict) -> dict:
    return {
        "id": meta.get("id"),
        "project_id": meta.get("project_id"),
        "title": meta.get("title"),
        "type": meta.get("type"),
        "status": meta.get("status"),
        "goal": meta.get("goal", ""),
        "definition_of_done": meta.get("definition_of_done", ""),
        "has_dod": bool((meta.get("definition_of_done") or "").strip()),
        "assignee": meta.get("assignee"),
        "participant_count": len(meta.get("participants", [])),
        "artifact_count": len(meta.get("artifacts", [])),
        "created_at": meta.get("created_at"),
        "updated_at": meta.get("updated_at"),
        "error_reason": meta.get("error_reason"),
    }


def _validate_participant(p: dict) -> None:
    if p.get("ref_type") not in VALID_PARTICIPANT_TYPES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效参与者类型: {p.get('ref_type')}")
    if not p.get("ref_id"):
        raise APIError(400, ErrorCode.BAD_REQUEST, "参与者 ref_id 不能为空")
    if p.get("role") and p["role"] not in VALID_PARTICIPANT_ROLES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效参与者角色: {p.get('role')}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
