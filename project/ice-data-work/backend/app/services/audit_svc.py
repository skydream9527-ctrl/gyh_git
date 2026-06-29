"""审计服务：所有工具调用 + 权限检查 + 跨空间读取写 audit.jsonl（材料二 §8）。

审计是治理的基础：可追溯、复盘、回滚、权限优化、成本控制。
落盘：tasks/{tid}/audit.jsonl（任务级）+ users/{uid}/audit.jsonl（用户级）。
事件类型：tool_call / permission_check / cross_space_read / status_change / memory_promote。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.storage import paths
from app.core.storage.jsonio import append_jsonl, iter_dirs, read_json, read_jsonl


def record(
    *,
    actor: str,
    action: str,
    task_id: str = "",
    tool: str = "",
    permission_level: str = "",
    result: str = "ok",
    summary: str = "",
    detail: dict | None = None,
) -> dict:
    """记录一条审计事件。同时写任务级与用户级（actor）审计。"""
    event = {
        "id": f"aud_{uuid.uuid4().hex[:10]}",
        "ts": _now_iso(),
        "actor": actor,
        "action": action,
        "tool": tool,
        "permission_level": permission_level,
        "result": result,  # ok | blocked | error | pending
        "summary": summary,
        "detail": detail or {},
        "task_id": task_id,
    }
    if task_id:
        append_jsonl(paths.task_audit(task_id), event)
    if actor and not actor.startswith(("agent:", "twin")):
        # 用户级审计（actor 为 user_id 时）
        try:
            append_jsonl(paths.user_audit(actor), event)
        except Exception:
            pass
    return event


def record_blocked_cross_space(actor: str, target: str, *, task_id: str = "") -> dict:
    """记录被拒的跨空间读取（治理高亮项）。"""
    return record(
        actor=actor, action="cross_space_read", task_id=task_id,
        result="blocked", summary=f"尝试读取 {target} · 已拦截",
        detail={"target": target},
    )


def list_task_audit(task_id: str) -> list[dict]:
    events = read_jsonl(paths.task_audit(task_id))
    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return events


def list_user_audit(uid: str, *, limit: int = 100) -> list[dict]:
    events = read_jsonl(paths.user_audit(uid))
    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return events[:limit]


def list_recent_for_user(user_id: str, *, limit: int = 50) -> list[dict]:
    """聚合用户参与任务的近期审计（治理页用）。"""
    out: list[dict] = []
    for d in iter_dirs(paths.root() / "tasks"):
        meta = read_json(d / "task.json")
        if meta is None or meta.get("deleted_at"):
            continue
        if not any(p.get("ref_type") == "user" and p.get("ref_id") == user_id
                   for p in meta.get("participants", [])):
            continue
        for e in read_jsonl(paths.task_audit(meta["id"])):
            out.append({**e, "task_title": meta.get("title")})
    out.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return out[:limit]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
