from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from ...core.deps import TaskRole, get_current_user, require_task_role
from ...core.errors import APIError, ErrorCode, ok
from ...services import conversation_svc, inflight_svc

router = APIRouter()


@router.get("/tasks/{task_id}/conversations")
async def list_convs(
    task_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.VIEWER, TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
):
    items = await conversation_svc.list_conversations(task_id=task_id)
    # 注入 inflight：本 worker 内是否还有正在跑的回合。前端用这个角标 ⏳
    # 提示用户「这个对话后台还在生成」，避免切走后误以为任务停了。
    # 多 worker / reload 后补读 sidecar 状态文件，否则 UI 会误判为空闲。
    from . import ws as ws_module
    for c in items:
        c["inflight"] = ws_module.is_inflight(task_id, c["id"]) or (
            inflight_svc.read_state(task_id, c["id"]) is not None
        )
    return ok({"items": items, "total": len(items)})


@router.post("/tasks/{task_id}/conversations")
async def create_conv(
    task_id: str,
    body: dict | None = None,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    title = (body or {}).get("title")
    conv = await conversation_svc.create_conversation(
        task_id=task_id, created_by=user["id"], title=title,
    )
    return ok(conv)


@router.patch("/tasks/{task_id}/conversations/{conv_id}")
async def rename_conv(
    task_id: str,
    conv_id: str,
    body: dict,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    # Creator or owner only
    items = await conversation_svc.list_conversations(task_id=task_id)
    target = next((c for c in items if c["id"] == conv_id), None)
    if not target:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "对话不存在")
    if target["created_by"] != user["id"] and role not in (TaskRole.OWNER, TaskRole.ADMIN):
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "仅创建者或任务 owner 可改标题")
    title = body.get("title", "").strip()
    if not title:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "title 不能为空")
    return ok(await conversation_svc.rename_conversation(task_id=task_id, conv_id=conv_id, title=title))


@router.delete("/tasks/{task_id}/conversations/{conv_id}")
async def delete_conv(
    task_id: str,
    conv_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    items = await conversation_svc.list_conversations(task_id=task_id)
    target = next((c for c in items if c["id"] == conv_id), None)
    if not target:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "对话不存在")
    if target["created_by"] != user["id"] and role not in (TaskRole.OWNER, TaskRole.ADMIN):
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "仅创建者或任务 owner 可删除")
    from . import ws as ws_module
    if ws_module.is_inflight(task_id, conv_id) or inflight_svc.read_state(task_id, conv_id):
        raise APIError(409, ErrorCode.CONVERSATION_INFLIGHT, "对话正在生成中，请先中断或稍后再删除")
    await conversation_svc.delete_conversation(task_id=task_id, conv_id=conv_id)
    return ok({"deleted": True})


@router.get("/tasks/{task_id}/conversations/{conv_id}")
async def get_conv(
    task_id: str,
    conv_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.VIEWER, TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
    limit: int = Query(80, ge=1, le=200),
    before: int | None = Query(default=None, ge=0),
):
    from ...services import task_svc
    # Verify the conv belongs to this task
    items = await conversation_svc.list_conversations(task_id=task_id)
    if not any(c["id"] == conv_id for c in items):
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "对话不存在")
    page = await asyncio.to_thread(
        task_svc.load_conversation_messages_page,
        task_id,
        conv_id,
        limit=limit,
        before=before,
    )
    return ok({"conversation_id": conv_id, **page})


@router.post("/tasks/{task_id}/conversations/{conv_id}/abort")
async def abort_conv(
    task_id: str,
    conv_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN)),
):
    """HTTP-level 终止后台回合。

    用户在 WS 已断开（如 STREAM_INTERRUPTED）时仍能取消正在跑的 LLM 回合。
    单 worker 部署下 100% 生效；多 worker 部署仅本 worker 内回合可达。
    """
    from . import ws as ws_module
    cancelled = await ws_module.cancel_inflight_turn(task_id, conv_id)
    return ok({"cancelled": cancelled})
