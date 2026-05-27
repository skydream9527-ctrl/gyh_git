"""Owner-initiated collaboration invitations.

`/tasks/{task_id}/invitations` — owner / admin send & cancel.
`/me/invitations` — invitee inbox + accept / decline.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from ...core.deps import TaskRole, get_current_user, require_task_role
from ...core.errors import APIError, ErrorCode, ok
from ...services import invitation_svc

# Two routers because they live under different prefixes (mounted in __init__.py).
task_router = APIRouter()
me_router = APIRouter()


# ---- task scope (owner / admin) ----


@task_router.get("/{task_id}/invitations")
async def list_invites(
    task_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
):
    items = await invitation_svc.list_for_task(task_id=task_id)
    return ok({"items": items, "total": len(items)})


@task_router.post("/{task_id}/invitations")
async def create_invites(
    task_id: str,
    body: dict[str, Any] = Body(...),
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    invitee_ids = body.get("invitee_ids") or []
    if not isinstance(invitee_ids, list) or not invitee_ids:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "至少选择一个被邀请人")
    invite_role = body.get("role", "editor")
    message = body.get("message") or ""
    result = await invitation_svc.invite(
        task_id=task_id,
        inviter_id=user["id"],
        invitee_ids=[str(x) for x in invitee_ids],
        role=str(invite_role),
        message=str(message),
    )
    return ok(result)


@task_router.delete("/{task_id}/invitations/{invite_id}")
async def cancel_invite(
    task_id: str,
    invite_id: str,
    role: TaskRole = Depends(require_task_role(TaskRole.OWNER, TaskRole.ADMIN)),
    user: dict = Depends(get_current_user),
):
    result = await invitation_svc.cancel(
        task_id=task_id, invite_id=invite_id, operator_id=user["id"]
    )
    return ok(result)


# ---- invitee scope ----


@me_router.get("/invitations")
async def my_invites(user: dict = Depends(get_current_user)):
    items = await invitation_svc.list_for_user(user_id=user["id"])
    return ok({"items": items, "total": len(items)})


@me_router.post("/invitations/{invite_id}/accept")
async def accept_invite(invite_id: str, user: dict = Depends(get_current_user)):
    result = await invitation_svc.respond(
        invite_id=invite_id, invitee_id=user["id"], action="accept"
    )
    return ok(result)


@me_router.post("/invitations/{invite_id}/decline")
async def decline_invite(
    invite_id: str,
    body: dict[str, Any] | None = Body(default=None),
    user: dict = Depends(get_current_user),
):
    reason = (body or {}).get("reason")
    result = await invitation_svc.respond(
        invite_id=invite_id,
        invitee_id=user["id"],
        action="decline",
        decline_reason=str(reason) if reason else None,
    )
    return ok(result)
