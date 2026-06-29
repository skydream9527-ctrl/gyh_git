from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends

from ...core.deps import get_current_user
from ...core.errors import APIError, ErrorCode, ok
from ...services import llm_gateway, scheduler_svc, task_svc

router = APIRouter()
log = logging.getLogger("scheduled")


_PLAN_SYS = """你是一个定时任务规划助手。根据用户的自然语言需求产出两样东西：
1) cron — 标准 5 段 cron 表达式（分 时 日 月 周）。若需求里有「每天上午 9 点」这种明确节奏就照给；模糊的就给一个合理默认，例如「每日」= 0 9 * * *，「每小时」= 0 * * * *，「每周一早上」= 0 9 * * 1。
2) todo_list — 一个可执行的简短 todo 数组（字符串数组），每条 8-30 字，描述这个任务每次被触发后 AI 要执行的动作。3-6 条足够。

严格输出 JSON，形如：
{"cron": "0 9 * * *", "todo_list": ["拉取指标A","对比昨日","高亮异常","生成报告"]}
不要有任何其他文字、markdown 围栏或注释。
"""


@router.post("/plan")
async def plan(body: dict, user: dict = Depends(get_current_user)):
    """Use the LLM to turn a free-text prompt into a cron expression + todo list.

    Body: { prompt: str, model?: str }
    Returns: { cron: str, todo_list: list[str], model: str }
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "prompt 不能为空")
    model = body.get("model") or None
    try:
        resp = await llm_gateway.complete_once(
            system_prompt=_PLAN_SYS,
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=512,
        )
    except APIError:
        raise
    except Exception as e:
        log.exception("plan LLM failed")
        raise APIError(500, ErrorCode.INTERNAL_ERROR, f"生成失败：{e}") from e

    raw = (resp.get("text") or "").strip()
    # 模型有时候还是会套 ```json ... ```；兜底扒 JSON
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise APIError(502, ErrorCode.INTERNAL_ERROR, f"LLM 未返回 JSON：{raw[:200]}")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise APIError(502, ErrorCode.INTERNAL_ERROR, f"LLM JSON 解析失败：{e}") from e
    cron = str(data.get("cron") or "").strip()
    if not cron or len(cron.split()) != 5:
        raise APIError(502, ErrorCode.INTERNAL_ERROR, f"LLM 返回的 cron 非法：{cron!r}")
    todos = data.get("todo_list") or []
    if not isinstance(todos, list):
        todos = []
    todos = [str(x).strip() for x in todos if str(x).strip()][:10]
    return ok({"cron": cron, "todo_list": todos, "model": resp.get("model")})


@router.get("")
async def list_my(user: dict = Depends(get_current_user)):
    items = scheduler_svc.list_for_user(user["id"])
    return ok({"items": items, "total": len(items)})


@router.get("/summary")
async def summary(user: dict = Depends(get_current_user)):
    return ok(scheduler_svc.summary_for_user(user["id"]))


@router.get("/by-task/{task_id}")
async def list_by_task(task_id: str, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    items = scheduler_svc.list_for_task(task_id)
    return ok({"items": items, "total": len(items)})


@router.post("/by-task/{task_id}")
async def create(task_id: str, body: dict, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    return ok(scheduler_svc.create(task_id=task_id, owner_id=user["id"], body=body))


@router.patch("/by-task/{task_id}/{sid}")
async def update(task_id: str, sid: str, body: dict, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    return ok(scheduler_svc.update(task_id, sid, user["id"], body))


@router.delete("/by-task/{task_id}/{sid}")
async def remove(task_id: str, sid: str, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    scheduler_svc.remove(task_id, sid, user["id"])
    return ok({"deleted": True})


@router.post("/by-task/{task_id}/{sid}/run-now")
async def run_now(task_id: str, sid: str, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    return ok(await scheduler_svc.run_now(task_id, sid, user["id"]))


@router.get("/by-task/{task_id}/{sid}/runs")
async def list_runs(task_id: str, sid: str, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    return ok({"items": scheduler_svc.list_runs(task_id, sid)})


@router.get("/by-task/{task_id}/{sid}/runs/{run_id}")
async def get_run_detail(task_id: str, sid: str, run_id: str, user: dict = Depends(get_current_user)):
    await task_svc.get_task(task_id, user["id"])
    detail = scheduler_svc.get_run_detail(task_id, sid, run_id)
    if not detail:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "执行记录不存在")
    return ok(detail)
