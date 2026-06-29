"""治理路由：审计日志 / 一键暂停 / 用量导出。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.core.deps import get_current_user, require_role
from app.core.errors import ok
from app.core.permissions import PlatformRole
from app.services import audit_svc, control_svc, task_svc, usage_svc

router = APIRouter(tags=["governance"])


# ─── 审计 ───

@router.get("/audit")
def my_audit(user: dict = Depends(get_current_user)) -> dict:
    """当前用户参与任务的近期审计聚合。"""
    return ok(audit_svc.list_recent_for_user(user["id"]))


@router.get("/audit/tasks/{task_id}")
def task_audit(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(task_id)
    return ok(audit_svc.list_task_audit(task_id))


# ─── 一键暂停 ───

@router.get("/control")
def control_state(user: dict = Depends(get_current_user)) -> dict:
    return ok(control_svc.get_state())


@router.post("/control/pause")
def pause(user: dict = Depends(get_current_user)) -> dict:
    """一键暂停全部执行。"""
    return ok(control_svc.pause_all(user["id"]), message="已暂停全部执行")


@router.post("/control/resume")
def resume(user: dict = Depends(get_current_user)) -> dict:
    return ok(control_svc.resume_all(user["id"]), message="已恢复执行")


# ─── 用量 CSV 导出 ───

@router.get("/usage/export")
def export_usage(
    month: str | None = None,
    user: dict = Depends(require_role(PlatformRole.SUPER_ADMIN, PlatformRole.ADMIN)),
) -> PlainTextResponse:
    csv_text = usage_svc.export_csv(month=month)
    return PlainTextResponse(
        csv_text,
        headers={"Content-Disposition": f"attachment; filename=usage_{month or 'all'}.csv"},
    )
