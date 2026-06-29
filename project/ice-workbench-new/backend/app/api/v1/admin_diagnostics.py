"""管理端日志/诊断查询 — 任务 + 会话粒度的运维事件查看。

任意 admin 可读，super_admin 也可读（同 require_admin）。读取直接走文件系统，
不入 SQLite——events 是冷查询，按需扫描即可，避免污染主索引（G3）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.deps import require_admin
from ...core.errors import ok
from ...services import agent_inspection_svc, event_log

router = APIRouter()


@router.get("/tasks-with-events")
async def tasks_with_events(
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_admin),
):
    """列出最近有事件写入的任务，按最近事件时间倒序。诊断页空状态时的入口。"""
    return ok({"items": event_log.list_tasks_with_events(limit=limit)})


@router.get("/tasks/{task_id}/events")
async def task_events(
    task_id: str,
    conv_id: str | None = Query(None),
    request_id: str | None = Query(None),
    level: str | None = Query(None, pattern="^(INFO|WARN|ERROR)$"),
    source: str | None = Query(None),
    event_type: str | None = Query(None),
    since_ym: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(500, ge=1, le=2000),
    _: dict = Depends(require_admin),
):
    """读取某任务的事件流，支持按会话/请求 ID/级别/来源/事件类型过滤。"""
    items = event_log.read_task_events(
        task_id,
        conv_id=conv_id,
        request_id=request_id,
        level=level,
        source=source,
        event_type=event_type,
        since_ym=since_ym,
        limit=limit,
    )
    return ok({"items": items, "total": len(items)})


@router.get("/tasks/{task_id}/timeline")
async def task_timeline(
    task_id: str,
    conv_id: str = Query(...),
    limit: int = Query(500, ge=1, le=2000),
    _: dict = Depends(require_admin),
):
    """会话级时间轴：events + conversation 消息 + 工具调用合并成一条时间序列。"""
    items = event_log.merge_with_other_streams(task_id, conv_id, limit=limit)
    return ok({"items": items, "total": len(items)})


@router.get("/by-request/{request_id}")
async def by_request(
    request_id: str,
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(require_admin),
):
    """跨任务按 request_id 反查——用户只贴了一个错误请求 ID 时用。"""
    items = event_log.merge_for_request(request_id, limit=limit)
    return ok({"items": items, "total": len(items)})


@router.get("/tasks/{task_id}/agent-context")
async def agent_context(
    task_id: str,
    agent_id: str = Query(...),
    user_id: str | None = Query(None),
    query: str | None = Query(None),
    _: dict = Depends(require_admin),
):
    """Inspect the runtime context that would be injected for an Agent."""
    return ok(
        agent_inspection_svc.inspect_context(
            task_id=task_id,
            agent_id=agent_id,
            user_id=user_id,
            query=query,
        )
    )


@router.get("/tasks/{task_id}/subagent-runs")
async def subagent_runs(
    task_id: str,
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_admin),
):
    """List sub-agent runs persisted under tasks/{tid}/subagent_runs."""
    items = agent_inspection_svc.list_subagent_runs(task_id, limit=limit)
    return ok({"items": items, "total": len(items)})
