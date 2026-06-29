from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from ...core.deps import TaskRole, get_current_user, require_task_role
from ...core.errors import APIError, ErrorCode, ok
from ...core.storage import file_transaction, get_paths, read_json
from ...schemas.task import TaskCreate, TaskUpdate
from ...services import agent_snapshot_svc, conversation_svc, hitl_svc, join_request_svc, task_svc

router = APIRouter()


@router.post("/quick-create")
async def quick_create(body: dict, user: dict = Depends(get_current_user)):
    """Quick Chat: create a task from a single message, auto-select agent,
    and return everything needed to jump straight into the workspace."""
    message = (body.get("message") or "").strip()
    if not message:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "message 不能为空")
    agent_id = body.get("agent_id") or "general"

    # Auto-generate a concise task name from the message
    from datetime import datetime
    now = datetime.now()
    ts = f"{now.month}/{now.day} {now.hour:02d}:{now.minute:02d}"
    name = message[:40].rstrip() + ("…" if len(message) > 40 else "")
    name = f"{name} · {ts}"

    task = await task_svc.create_task(
        name=name,
        paradigm="open",
        owner_id=user["id"],
        agent_id=agent_id,
        description=None,
        initial_prompt=message,
        skill_ids=[],
        visibility="private",
    )
    # Read the conversation_id from the workspace file
    paths = get_paths()
    workspace = read_json(paths.task_workspace(task["id"]), default={})
    return ok({
        "task_id": task["id"],
        "agent_id": task.get("agent_id"),
        "conversation_id": workspace.get("current_conversation_id"),
        "name": task.get("name"),
    })


@router.get("")
async def list_tasks(user: dict = Depends(get_current_user)):
    items = await task_svc.list_user_tasks(user["id"])
    return ok({"items": items, "total": len(items)})


@router.get("/public")
async def list_public(user: dict = Depends(get_current_user)):
    items = await task_svc.list_public_tasks()
    return ok({"items": items, "total": len(items)})


@router.post("")
async def create_task(body: TaskCreate, user: dict = Depends(get_current_user)):
    task = await task_svc.create_task(
        name=body.name,
        paradigm=body.paradigm,
        owner_id=user["id"],
        agent_id=body.agent_id,
        description=body.description,
        initial_prompt=body.initial_prompt,
        skill_ids=body.skill_ids,
        visibility=body.visibility,
    )
    return ok(task)


@router.get("/{task_id}")
async def get_task(task_id: str, user: dict = Depends(get_current_user)):
    return ok(
        await task_svc.get_task(
            task_id, user["id"], is_admin=bool(user.get("is_admin"))
        )
    )


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    body: TaskUpdate,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    return ok(
        await task_svc.update_task(
            task_id,
            user["id"],
            body.model_dump(exclude_unset=True),
            is_admin=role == TaskRole.ADMIN or bool(user.get("is_admin")),
            allow_visibility=role in (TaskRole.OWNER, TaskRole.ADMIN),
        )
    )


@router.get("/{task_id}/conversation")
async def task_conversation(
    task_id: str,
    user: dict = Depends(get_current_user),
    limit: int = Query(80, ge=1, le=200),
    before: int | None = Query(default=None, ge=0),
):
    await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    cid = await task_svc.get_or_create_default_conversation(task_id)
    page = await asyncio.to_thread(
        task_svc.load_conversation_messages_page,
        task_id,
        cid,
        limit=limit,
        before=before,
    )
    return ok({"conversation_id": cid, **page})


@router.delete("/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    await task_svc.delete_task(
        task_id, user["id"], is_admin=bool(user.get("is_admin"))
    )
    return ok({"deleted": True, "task_id": task_id})


@router.patch("/{task_id}/skills")
async def update_task_skills(
    task_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Update the task's bound skill_ids. Body: {skill_ids: [...]}."""
    skill_ids = body.get("skill_ids")
    if not isinstance(skill_ids, list):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "skill_ids 必须是数组")
    return ok(await task_svc.update_skills(task_id, user["id"], skill_ids))


@router.post("/{task_id}/agent/refresh")
async def refresh_agent_snapshot(
    task_id: str,
    body: dict | None = None,
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    expected = (body or {}).get("expected_agent_source_version")
    result = await agent_snapshot_svc.refresh_task_snapshot(
        task_id=task_id, user_id=user["id"], expected_version=expected,
    )
    return ok(result)


@router.post("/{task_id}/join-request")
async def submit_join(
    task_id: str,
    body: dict,
    role: TaskRole = Depends(require_task_role(TaskRole.VIEWER)),
    user: dict = Depends(get_current_user),
):
    req = await join_request_svc.submit(
        task_id=task_id, user_id=user["id"], message=body.get("message", ""),
    )
    return ok(req)


@router.get("/{task_id}/join-requests")
async def list_joins(
    task_id: str,
    status: str | None = None,
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
):
    items = await join_request_svc.list_requests(task_id=task_id, status=status)
    return ok({"items": items, "total": len(items)})


@router.post("/{task_id}/join-requests/{req_id}/review")
async def review_join(
    task_id: str,
    req_id: str,
    body: dict,
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    new_status = body.get("status", "approved")
    reason = body.get("reject_reason")
    req = await join_request_svc.review(
        task_id=task_id, req_id=req_id, new_status=new_status,
        operator_id=user["id"], reject_reason=reason,
    )
    return ok(req)


@router.delete("/{task_id}/collaborators/{user_id}")
async def remove_collaborator(
    task_id: str,
    user_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
):
    paths = get_paths()
    cpath = paths.task_collaborators(task_id)
    with file_transaction([cpath]) as tx:
        collabs = tx.read_json(cpath, default=[])
        target = next((c for c in collabs if c["user_id"] == user_id), None)
        if not target:
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "协作者不存在")
        if target.get("role") == "owner":
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "不能移除 owner")
        target["status"] = "removed"
        tx.write_json(cpath, collabs)
    return ok({"removed": True})


@router.get("/{task_id}/todos")
async def get_task_todos(task_id: str, user: dict = Depends(get_current_user)):
    """Agent v2 — return the latest todo list for this task (empty list for
    tasks that have never called todo_write)."""
    await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    payload = read_json(get_paths().task_todos(task_id), default=None)
    if not isinstance(payload, dict):
        return ok({"task_id": task_id, "items": [], "updated_at": None})
    return ok(payload)


@router.get("/{task_id}/run-events")
async def get_run_events(
    task_id: str,
    user: dict = Depends(get_current_user),
    conv_id: str | None = None,
    limit: int = Query(80, ge=1, le=200),
):
    await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    if not conv_id:
        conv_id = await task_svc.get_or_create_default_conversation(task_id)
    items = task_svc.list_run_events(task_id, conv_id, limit=limit)
    return ok({"task_id": task_id, "conversation_id": conv_id, "items": items, "total": len(items)})


@router.get("/{task_id}/hitl")
async def list_hitl(
    task_id: str,
    status: str | None = "pending",
    user: dict = Depends(get_current_user),
):
    await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    items = await hitl_svc.list_requests(task_id, status=status)
    return ok({"items": items, "total": len(items)})


@router.post("/{task_id}/hitl")
async def create_hitl(
    task_id: str,
    body: dict,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    req = await hitl_svc.create_request(
        task_id=task_id,
        conv_id=body.get("conversation_id"),
        created_by=user["id"],
        title=body.get("title") or "需要人工确认",
        message=body.get("message") or "",
        fields=body.get("fields") if isinstance(body.get("fields"), list) else None,
        table=body.get("table") if isinstance(body.get("table"), dict) else None,
        actions=body.get("actions") if isinstance(body.get("actions"), list) else None,
        resume_prompt=body.get("resume_prompt"),
        source="api",
    )
    return ok(req)


@router.post("/{task_id}/hitl/{request_id}/resolve")
async def resolve_hitl(
    task_id: str,
    request_id: str,
    body: dict,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    req = await hitl_svc.resolve_request(
        task_id=task_id,
        request_id=request_id,
        user_id=user["id"],
        decision=body.get("decision") or "continue",
        payload=body.get("payload") if isinstance(body.get("payload"), dict) else {},
        note=body.get("note"),
    )
    return ok(req)


@router.get("/{task_id}/conversations/{conv_id}/plan-state")
async def get_plan_state(
    task_id: str, conv_id: str, user: dict = Depends(get_current_user)
):
    """Agent v2 — return plan_mode + pending_plan for a conversation. Used by
    the frontend on page load to restore the banner / approval modal state."""
    await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    return ok(await conversation_svc.get_plan_mode(task_id=task_id, conv_id=conv_id))
