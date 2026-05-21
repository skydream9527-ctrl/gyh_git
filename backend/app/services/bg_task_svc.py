"""Background long-running tasks.

The main agent can call `run_background(agent_id, prompt, title)` to enqueue
work that runs without blocking the chat. The job is persisted to
`tasks/{tid}/bg_jobs.jsonl` (append-only history) and executed by an in-process
asyncio task; on completion, a notification is written to the user's
notifications stream and any files produced by the agent land in the parent
task's workspace.

Kept intentionally simple — no external queue, no retries, no cancel API for
Stage 3 MVP. The scheduler (scheduler_svc.scheduler_loop) is a natural place
to move this if we outgrow in-process execution.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from ..core.storage import append_jsonl, get_paths, read_json
from . import (
    agent_runtime,
    agents_svc,
    experience_card_svc,
    llm_gateway,
    notification_svc,
    sysconfig_svc,
    tool_runner,
)

log = logging.getLogger("bg_task")


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def enqueue(
    *,
    task_id: str,
    user_id: str,
    agent_id: str,
    title: str,
    prompt: str,
    source_conv_id: str | None = None,
) -> dict:
    """Record a new background job and start its coroutine. Returns the job
    descriptor (with status='running')."""
    try:
        await agents_svc.get_agent(agent_id)
    except Exception as exc:
        raise ValueError(f"agent '{agent_id}' not found") from exc

    job_id = f"bg_{uuid.uuid4().hex[:12]}"
    paths = get_paths()
    job_record = {
        "id": job_id,
        "task_id": task_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "title": title,
        "prompt": prompt,
        "source_conv_id": source_conv_id,
        "status": "running",
        "created_at": _now(),
    }
    append_jsonl(paths.task_bg_jobs(task_id), job_record)
    # Fire-and-forget the worker. We keep a reference on the module so the
    # event loop won't GC the task before it runs to completion.
    asyncio.create_task(_run(job_id, task_id, user_id, agent_id, title, prompt))
    return job_record


async def _run(
    job_id: str, task_id: str, user_id: str, agent_id: str, title: str, prompt: str
) -> None:
    paths = get_paths()
    started = _now()
    try:
        meta = read_json(paths.task_meta(task_id)) or {}
        skill_ids = list(meta.get("skill_ids") or [])
        system_prompt = experience_card_svc.merged_system_prompt(
            agent_id, task_skill_ids=skill_ids
        )
        tools = tool_runner.get_anthropic_tools(
            feature_flags={
                # Background jobs can use normal tools but can't recurse or re-enqueue.
                "spawn_subagent": False,
                "run_background": False,
                "exit_plan_mode": False,
            },
            task_skill_ids=skill_ids,
        )
        ctx = {
            "user_id": user_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "conversation_id": f"bg::{job_id}",
            "plan_mode": False,
            "subagent_depth": 0,
        }
        # Mirror the WS path: read admin-tunable round limit from sysconfig,
        # clamp into [1, MAX_TOOL_ROUNDS]. Background tasks (定时任务 / 后台
        # 续跑) run the same agent loop and used to be hardcoded to 5 rounds.
        sys_params = sysconfig_svc.get_system_params()
        max_rounds = max(
            1,
            min(
                llm_gateway.MAX_TOOL_ROUNDS,
                int(sys_params.get("tool_call_max_rounds") or 20),
            ),
        )
        result = await agent_runtime.run_agent_turn(
            system_prompt=system_prompt,
            initial_messages=[{"role": "user", "content": prompt}],
            tools=tools,
            ctx=ctx,
            max_rounds=max_rounds,
            max_tokens=2048,
        )
        append_jsonl(
            paths.task_bg_jobs(task_id),
            {
                "event": "done",
                "id": job_id,
                "status": "succeeded",
                "started_at": started,
                "finished_at": _now(),
                "rounds": result.get("rounds"),
                "final_text_excerpt": (result.get("final_text") or "")[:500],
            },
        )
        await notification_svc.add_notification(
            user_id,
            kind="bg_task_done",
            title=f"后台任务完成：{title}",
            body=(result.get("final_text") or "")[:400],
            action_url=f"/workspace/{task_id}",
        )
    except Exception as exc:
        log.exception("bg task failed id=%s", job_id)
        append_jsonl(
            paths.task_bg_jobs(task_id),
            {
                "event": "failed",
                "id": job_id,
                "status": "failed",
                "started_at": started,
                "finished_at": _now(),
                "error": str(exc)[:500],
            },
        )
        try:
            await notification_svc.add_notification(
                user_id,
                kind="bg_task_failed",
                title=f"后台任务失败：{title}",
                body=str(exc)[:400],
                action_url=f"/workspace/{task_id}",
            )
        except Exception:
            pass
