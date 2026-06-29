"""API endpoints for data monitor rules (anomaly detection jobs)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.deps import get_current_user
from ...core.errors import APIError, ErrorCode, ok
from ...services.task import monitor_svc

router = APIRouter()


@router.get("/tasks/{task_id}/monitors")
async def list_monitors(task_id: str, user: dict = Depends(get_current_user)):
    items = monitor_svc.list_monitors(task_id)
    return ok({"items": items, "total": len(items)})


@router.post("/tasks/{task_id}/monitors")
async def create_monitor(task_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Create a new data anomaly monitor.

    Body:
        name: str - monitor name
        sql: str - SQL query to execute
        cron: str - 5-field cron expression
        threshold: dict - {type, value, direction, upper_bound, lower_bound, periods}
        channels: list[str] - ["in_app", "feishu"]
        feishu_chat_id: str - optional feishu chat for alerts
        description: str - optional description
    """
    name = (body.get("name") or "").strip()
    sql = (body.get("sql") or "").strip()
    cron = (body.get("cron") or "").strip()
    threshold = body.get("threshold")

    if not name:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "name 不能为空")
    if not sql:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "sql 不能为空")
    if not cron:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "cron 不能为空")
    if not isinstance(threshold, dict) or "type" not in threshold:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "threshold 必须包含 type 字段")

    monitor = monitor_svc.create_monitor(
        task_id=task_id,
        owner_id=user["id"],
        name=name,
        sql=sql,
        cron=cron,
        threshold=threshold,
        channels=body.get("channels"),
        feishu_chat_id=body.get("feishu_chat_id"),
        description=body.get("description"),
    )
    return ok(monitor)


@router.patch("/tasks/{task_id}/monitors/{monitor_id}")
async def update_monitor(
    task_id: str, monitor_id: str, body: dict, user: dict = Depends(get_current_user)
):
    monitor = monitor_svc.update_monitor(task_id, monitor_id, user["id"], body)
    return ok(monitor)


@router.delete("/tasks/{task_id}/monitors/{monitor_id}")
async def delete_monitor(
    task_id: str, monitor_id: str, user: dict = Depends(get_current_user)
):
    monitor_svc.delete_monitor(task_id, monitor_id, user["id"])
    return ok({"deleted": True})
