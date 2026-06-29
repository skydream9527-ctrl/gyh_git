"""Human-in-the-loop requests for task execution.

Source of truth: tasks/{tid}/hitl_requests.json.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.task import task_svc

from ...core.errors import APIError, ErrorCode
from ...core.storage import append_jsonl, file_transaction, get_paths, read_json
from . import notification_svc


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"hitl_{uuid.uuid4().hex[:12]}"


def _load(task_id: str) -> list[dict]:
    return read_json(get_paths().task_hitl_requests(task_id), default=[]) or []


async def list_requests(task_id: str, *, status: str | None = None) -> list[dict]:
    items = _load(task_id)
    if status:
        items = [it for it in items if it.get("status") == status]
    return sorted(items, key=lambda it: it.get("created_at") or "", reverse=True)


async def create_request(
    *,
    task_id: str,
    conv_id: str | None,
    created_by: str | None,
    title: str,
    message: str,
    fields: list[dict] | None = None,
    table: dict | None = None,
    actions: list[dict] | None = None,
    resume_prompt: str | None = None,
    source: str = "api",
) -> dict:
    meta = read_json(get_paths().task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    req = {
        "id": _new_id(),
        "task_id": task_id,
        "conversation_id": conv_id,
        "status": "pending",
        "title": (title or "需要人工确认").strip()[:120],
        "message": (message or "").strip(),
        "fields": fields or [],
        "table": table or None,
        "actions": actions or [],
        "resume_prompt": resume_prompt or None,
        "source": source,
        "created_by": created_by,
        "created_at": _now(),
        "resolved_by": None,
        "resolved_at": None,
        "resolution": None,
    }
    if not req["message"]:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "message 不能为空")

    path = get_paths().task_hitl_requests(task_id)
    with file_transaction([path]) as tx:
        items = tx.read_json(path, default=[]) or []
        items.append(req)
        tx.write_json(path, items)
    await task_svc.set_task_status(task_id, "paused")

    owner_id = meta.get("owner_id")
    if owner_id:
        await notification_svc.add_notification(
            owner_id,
            kind="system",
            title="任务等待人工确认",
            body=req["title"],
            action_url=f"/workspace/{task_id}",
        )
    return req


async def resolve_request(
    *,
    task_id: str,
    request_id: str,
    user_id: str,
    decision: str,
    payload: dict[str, Any] | None = None,
    note: str | None = None,
) -> dict:
    path = get_paths().task_hitl_requests(task_id)
    with file_transaction([path]) as tx:
        items = tx.read_json(path, default=[]) or []
        target = None
        for it in items:
            if it.get("id") == request_id:
                target = it
                break
        if not target:
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "人工干预请求不存在")
        if target.get("status") != "pending":
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "该请求已处理")
        target["status"] = "resolved"
        target["resolved_by"] = user_id
        target["resolved_at"] = _now()
        target["resolution"] = {
            "decision": (decision or "continue").strip() or "continue",
            "payload": payload or {},
            "note": note or "",
        }
        tx.write_json(path, items)

    if target.get("conversation_id"):
        append_jsonl(
            get_paths().task_conversation(task_id, target["conversation_id"]),
            {
                "id": f"hitl_resolution_{uuid.uuid4().hex[:12]}",
                "role": "user",
                "content": _resolution_message(target),
                "user_id": user_id,
                "created_at": _now(),
                "meta": {"hitl_request_id": request_id, "kind": "hitl_resolution"},
            },
        )

    pending_left = [it for it in _load(task_id) if it.get("status") == "pending"]
    if not pending_left:
        await task_svc.set_task_status(task_id, "active", only_if={"paused"})
    return target


def _resolution_message(req: dict) -> str:
    res = req.get("resolution") or {}
    payload = res.get("payload") or {}
    lines = [
        f"人工干预已处理：{req.get('title') or req.get('id')}",
        f"处理动作：{res.get('decision') or 'continue'}",
    ]
    note = (res.get("note") or "").strip()
    if note:
        lines.append(f"说明：{note}")
    if payload:
        lines.append(f"结构化结果：{payload}")
    resume = (req.get("resume_prompt") or "").strip()
    if resume:
        lines.append(f"后续要求：{resume}")
    return "\n".join(lines)
