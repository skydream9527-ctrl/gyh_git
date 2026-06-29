"""Auto-extracted from tool_runner.py — DO NOT edit tool_runner.py for these functions."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ....core.config import get_settings
from ....core.errors import ErrorCode


async def _tool_todo_write(args: dict, ctx: dict | None = None) -> Any:
    """Replace-all write of the task-level todo list. Sends a WS `todos_updated`
    event to the caller when a send_event callback is present in ctx."""
    from ....core.storage import file_transaction, get_paths

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "todo_write needs a task context"}

    raw_items = args.get("items")
    # Compatibility for older prompts / model slips that send
    # {"todos": "[...]"} or {"todos": [...]} even though the schema says
    # `items`. Keeping this here makes the progress panel resilient without
    # broadening the advertised contract.
    if raw_items is None and "todos" in args:
        raw_items = args.get("todos")
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except json.JSONDecodeError:
                return {"error_code": "VALIDATION_ERROR", "message": "todos must be valid JSON array"}
    if not isinstance(raw_items, list):
        return {"error_code": "VALIDATION_ERROR", "message": "items must be an array"}

    normalized: list[dict] = []
    seen_in_progress = 0
    for idx, it in enumerate(raw_items):
        if not isinstance(it, dict):
            return {"error_code": "VALIDATION_ERROR", "message": f"items[{idx}] must be an object"}
        content = (it.get("content") or "").strip()
        active = (it.get("activeForm") or "").strip()
        status = (it.get("status") or "pending").strip()
        if not content:
            return {"error_code": "VALIDATION_ERROR", "message": f"items[{idx}].content required"}
        if status not in ("pending", "in_progress", "completed"):
            return {"error_code": "VALIDATION_ERROR", "message": f"items[{idx}].status invalid"}
        if status == "in_progress":
            seen_in_progress += 1
        normalized.append(
            {
                "id": it.get("id") or f"t{idx + 1}",
                "content": content,
                "activeForm": active or content,
                "status": status,
            }
        )

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    payload = {
        "task_id": task_id,
        "updated_at": now_iso,
        "updated_by_conv_id": (ctx or {}).get("conversation_id"),
        "items": normalized,
    }
    paths = get_paths()
    todo_path = paths.task_todos(task_id)
    todo_path.parent.mkdir(parents=True, exist_ok=True)
    with file_transaction([todo_path]) as tx:
        tx.write_json(todo_path, payload)

    # Notify the WS if the handler wired an emit callback into ctx.
    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit(
                {
                    "type": "todos_updated",
                    "task_id": task_id,
                    "items": normalized,
                    "updated_at": now_iso,
                }
            )
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass

    return {
        "updated": True,
        "count": len(normalized),
        "in_progress": seen_in_progress,
        "updated_at": now_iso,
    }


async def _tool_exit_plan_mode(args: dict, ctx: dict | None = None) -> Any:
    """Emit the proposed plan and flag the current round for termination.

    The actual plan_mode → live-mode transition happens in ws.py when the user
    approves via the frontend modal; here we just persist the plan_id and emit
    a `plan_proposed` event. The outer round loop checks a flag set on ctx to
    break without re-invoking the LLM.
    """
    import uuid

    plan = (args.get("plan") or "").strip()
    if not plan:
        return {"error_code": "VALIDATION_ERROR", "message": "plan is required"}

    task_id = (ctx or {}).get("task_id")
    conv_id = (ctx or {}).get("conversation_id")
    if not task_id or not conv_id:
        return {"error_code": "VALIDATION_ERROR", "message": "exit_plan_mode needs a conv context"}

    plan_id = f"p_{uuid.uuid4().hex[:12]}"

    # Persist plan_id onto the conversation meta via conversation_svc (lazy import).
    try:
        from app.services.task import conversation_svc

        await conversation_svc.set_pending_plan(task_id=task_id, conv_id=conv_id, plan_id=plan_id, plan_text=plan)
    except Exception as exc:
        return {"error_code": "PLAN_PERSIST_FAILED", "message": str(exc)[:300]}

    # Ask the round loop to break (the ws.py handler checks this key).
    if ctx is not None:
        ctx["_plan_proposed"] = {"plan_id": plan_id, "plan_text": plan}

    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit(
                {
                    "type": "plan_proposed",
                    "plan_id": plan_id,
                    "plan_text": plan,
                }
            )
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass

    return {"waiting_for_approval": True, "plan_id": plan_id}


async def _tool_request_human_input(args: dict, ctx: dict | None = None) -> Any:
    from app.services.notification import hitl_svc

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "request_human_input needs a task context"}
    title = (args.get("title") or "").strip()
    message = (args.get("message") or "").strip()
    if not title or not message:
        return {"error_code": "VALIDATION_ERROR", "message": "title and message are required"}

    req = await hitl_svc.create_request(
        task_id=task_id,
        conv_id=(ctx or {}).get("conversation_id"),
        created_by=(ctx or {}).get("user_id"),
        title=title,
        message=message,
        fields=args.get("fields") if isinstance(args.get("fields"), list) else None,
        table=args.get("table") if isinstance(args.get("table"), dict) else None,
        actions=args.get("actions") if isinstance(args.get("actions"), list) else None,
        resume_prompt=args.get("resume_prompt"),
        source="tool",
    )

    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit({"type": "hitl_requested", "request": req})
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass
    return {"waiting_for_human": True, "request": req}


async def _tool_create_scheduled_task(args: dict, ctx: dict | None = None) -> Any:
    from app.services.storage import scheduler_svc

    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {"error_code": "VALIDATION_ERROR", "message": "create_scheduled_task needs task + user"}

    name = (args.get("name") or "").strip()
    cron = (args.get("cron") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    if not name or not cron or not prompt:
        return {"error_code": "VALIDATION_ERROR", "message": "name, cron and prompt are required"}

    body = {
        "name": name,
        "cron": cron,
        "prompt": prompt,
        "enabled": args.get("enabled", True),
        "model": args.get("model") or None,
        "todo_list": args.get("todo_list") if isinstance(args.get("todo_list"), list) else [],
        "channels": args.get("channels") if isinstance(args.get("channels"), list) else ["in_app"],
    }
    try:
        rec = scheduler_svc.create(task_id=task_id, owner_id=user_id, body=body)
    except Exception as exc:
        return {"error_code": "SCHEDULE_CREATE_FAILED", "message": str(exc)[:300]}

    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit({"type": "scheduled_task_created", "schedule": rec})
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass
    return {"scheduled_task": rec}


async def _tool_spawn_subagent(args: dict, ctx: dict | None = None) -> Any:
    """Run a bounded sub-agent and return only its final text."""
    import uuid

    from app.services.admin import experience_card_svc
    from app.services.agent import agent_runtime, agents_svc

    from ....core.storage import append_jsonl, get_paths

    agent_id = (args.get("agent_id") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    if not agent_id or not prompt:
        return {"error_code": "VALIDATION_ERROR", "message": "agent_id and prompt are required"}

    s = get_settings()
    if not s.ICE_SUBAGENT_ENABLED:
        return {"error_code": "SUBAGENT_DISABLED", "message": "sub-agent delegation is not enabled"}

    parent_ctx = ctx or {}
    depth = int(parent_ctx.get("subagent_depth") or 0)
    if depth >= s.ICE_SUBAGENT_MAX_DEPTH:
        return {
            "error_code": "SUBAGENT_DEPTH_EXCEEDED",
            "message": f"sub-agent depth limit is {s.ICE_SUBAGENT_MAX_DEPTH}",
        }

    task_id = parent_ctx.get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "spawn_subagent needs a task context"}

    # Verify the target agent exists. (get_agent is sync — earlier code awaited
    # it and the resulting TypeError got swallowed, so the check was dead.)
    if not agents_svc.get_agent(agent_id):
        return {"error_code": "AGENT_NOT_FOUND", "message": f"agent '{agent_id}' not found"}
    parent_agent_id = (parent_ctx.get("agent_id") or "").strip()
    if parent_agent_id:
        allowed_targets = agents_svc.list_spawnable_agent_ids(parent_agent_id)
        if agent_id not in allowed_targets:
            return {
                "error_code": "AGENT_NOT_ALLOWED",
                "message": f"agent '{agent_id}' is not an allowed spawn target for '{parent_agent_id}'",
                "allowed_targets": allowed_targets,
            }

    run_id = f"sub_{uuid.uuid4().hex[:12]}"
    paths = get_paths()
    transcript_path = paths.task_subagent_run(task_id, run_id)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    async def _emit_subagent_event(
        *,
        label: str,
        status: str = "running",
        detail: str | None = None,
    ) -> None:
        emit = parent_ctx.get("emit_event")
        if not callable(emit):
            return
        try:
            maybe = emit(
                {
                    "type": "run_event",
                    "run_id": run_id,
                    "stage": "subagent",
                    "label": label,
                    "status": status,
                    "detail": detail,
                    "payload": {"agent_id": agent_id},
                    "created_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            )
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass

    from ....core.storage import read_json as _read_json
    parent_meta = _read_json(paths.task_meta(task_id)) or {}
    parent_skill_ids = list(parent_meta.get("skill_ids") or [])
    # Effective tool whitelist for the child = intersection of:
    #   1. the child agent's own `agent.json.tools` (None if unrestricted)
    #   2. parent-passed `allowed_tools` arg (LLM's runtime choice)
    # Both None ⇒ no whitelist (the child gets every subagent-exposable tool).
    child_whitelist = agents_svc.get_agent_tools(agent_id)
    parent_allowed = args.get("allowed_tools") if isinstance(args.get("allowed_tools"), list) else None
    if child_whitelist is not None and parent_allowed is not None:
        effective_whitelist = [t for t in child_whitelist if t in parent_allowed]
    else:
        effective_whitelist = child_whitelist if child_whitelist is not None else parent_allowed
    tools = get_anthropic_tools(
        in_subagent=True,
        tool_whitelist=effective_whitelist,
        disallowed_tools=agents_svc.get_agent_disallowed_tools(agent_id),
        task_skill_ids=parent_skill_ids,
    )
    system_prompt = experience_card_svc.merged_system_prompt(
        agent_id,
        task_skill_ids=parent_skill_ids,
        callable_tool_names=[t["name"] for t in tools],
        user_id=parent_ctx.get("user_id"),
        task_id=task_id,
        query=prompt,
    )
    initial_prompt = agents_svc.get_agent_initial_prompt(agent_id)
    child_user_prompt = f"{initial_prompt}\n\n{prompt}" if initial_prompt else prompt

    child_ctx = {
        "user_id": parent_ctx.get("user_id"),
        "agent_id": agent_id,
        "task_id": task_id,
        "conversation_id": f"{parent_ctx.get('conversation_id', 'main')}::{run_id}",
        "subagent_depth": depth + 1,
        "plan_mode": False,
    }

    append_jsonl(
        transcript_path,
        {
            "event": "spawn",
            "run_id": run_id,
            "parent_conv": parent_ctx.get("conversation_id"),
            "parent_agent": parent_ctx.get("agent_id"),
            "agent_id": agent_id,
            "prompt": prompt,
            "at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )

    started = datetime.now(tz=timezone.utc)
    # Per-message arg > child agent's agent.json.model > runtime default.
    child_model = args.get("model") or agents_svc.get_agent_model(agent_id)
    try:
        await _emit_subagent_event(label=f"子 Agent {agent_id} 开始执行")
        result = await asyncio.wait_for(
            agent_runtime.run_agent_turn(
                system_prompt=system_prompt,
                initial_messages=[{"role": "user", "content": child_user_prompt}],
                tools=tools,
                ctx=child_ctx,
                max_rounds=min(
                    s.ICE_SUBAGENT_MAX_TOOL_ROUNDS,
                    agents_svc.get_agent_max_turns(agent_id) or s.ICE_SUBAGENT_MAX_TOOL_ROUNDS,
                ),
                model=child_model,
                max_tokens=int(args.get("max_tokens") or 2048),
                transcript_sink=transcript_path,
            ),
            timeout=s.ICE_SUBAGENT_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        append_jsonl(transcript_path, {"event": "timeout", "at": datetime.now(tz=timezone.utc).isoformat()})
        await _emit_subagent_event(
            label=f"子 Agent {agent_id} 执行超时",
            status="error",
            detail=f"{s.ICE_SUBAGENT_TIMEOUT_SEC}s",
        )
        return {
            "error_code": "SUBAGENT_TIMEOUT",
            "message": f"sub-agent exceeded {s.ICE_SUBAGENT_TIMEOUT_SEC}s",
            "run_id": run_id,
        }
    except Exception as exc:
        append_jsonl(transcript_path, {"event": "error", "message": str(exc)[:500]})
        await _emit_subagent_event(
            label=f"子 Agent {agent_id} 执行失败",
            status="error",
            detail=str(exc)[:160],
        )
        return {"error_code": "SUBAGENT_FAILED", "message": str(exc)[:300], "run_id": run_id}

    duration_ms = int((datetime.now(tz=timezone.utc) - started).total_seconds() * 1000)
    append_jsonl(
        transcript_path,
        {
            "event": "done",
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "tool_count": len(result.get("tool_uses_log") or []),
        },
    )
    await _emit_subagent_event(
        label=f"子 Agent {agent_id} 执行完成",
        status="done",
        detail=f"{len(result.get('tool_uses_log') or [])} 个工具 · {duration_ms}ms",
    )

    # P3: Sub-agent feedback loop — extract reusable insights and save as Agent Memory
    try:
        from app.services.task.subagent_feedback import extract_and_save_insights
        user_id = parent_ctx.get("user_id")
        if user_id and result.get("final_text"):
            extract_and_save_insights(
                sub_agent_id=agent_id,
                result_text=result["final_text"],
                task_description=prompt[:200],
                user_id=user_id,
                parent_agent_id=parent_agent_id or "general",
            )
    except Exception:
        pass  # best-effort; never block the spawn return path

    return {
        "final_text": result.get("final_text", ""),
        "run_id": run_id,
        "tool_count": len(result.get("tool_uses_log") or []),
        "duration_ms": duration_ms,
    }


async def _tool_spawn_parallel(args: dict, ctx: dict | None = None) -> Any:
    """Run multiple sub-agents in parallel and return aggregated results."""
    tasks_list = args.get("tasks")
    if not isinstance(tasks_list, list) or not tasks_list:
        return {"error_code": "VALIDATION_ERROR", "message": "tasks must be a non-empty array"}
    if len(tasks_list) > 5:
        return {"error_code": "VALIDATION_ERROR", "message": "max 5 parallel sub-agents"}

    s = get_settings()
    if not s.ICE_SUBAGENT_ENABLED:
        return {"error_code": "SUBAGENT_DISABLED", "message": "sub-agent delegation is not enabled"}

    parent_ctx = ctx or {}
    task_id = parent_ctx.get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "spawn_parallel needs a task context"}

    # Validate all entries first
    for i, entry in enumerate(tasks_list):
        if not isinstance(entry, dict):
            return {"error_code": "VALIDATION_ERROR", "message": f"tasks[{i}] must be an object"}
        if not (entry.get("agent_id") or "").strip():
            return {"error_code": "VALIDATION_ERROR", "message": f"tasks[{i}].agent_id required"}
        if not (entry.get("prompt") or "").strip():
            return {"error_code": "VALIDATION_ERROR", "message": f"tasks[{i}].prompt required"}

    # Run each as a standard spawn_subagent call in parallel
    async def _run_one(entry: dict) -> dict:
        sub_args = {
            "agent_id": entry["agent_id"].strip(),
            "prompt": entry["prompt"].strip(),
        }
        try:
            result = await _tool_spawn_subagent(sub_args, ctx)
            return {"agent_id": sub_args["agent_id"], "success": True, **result}
        except Exception as exc:
            return {
                "agent_id": sub_args["agent_id"],
                "success": False,
                "error_code": "SUBAGENT_FAILED",
                "message": str(exc)[:300],
            }

    started = time.time()
    results = await asyncio.gather(*[_run_one(entry) for entry in tasks_list])
    total_ms = int((time.time() - started) * 1000)

    # Separate successes and failures
    successes = [r for r in results if r.get("success") and not r.get("error_code")]
    failures = [r for r in results if not r.get("success") or r.get("error_code")]

    return {
        "results": list(results),
        "total_count": len(results),
        "success_count": len(successes),
        "failure_count": len(failures),
        "total_duration_ms": total_ms,
    }


async def _tool_run_background(args: dict, ctx: dict | None = None) -> Any:
    """Enqueue a background job. Returns immediately; completion fires a
    notification to the user and drops any produced files into the task
    workspace."""
    from app.services.task import bg_task_svc

    s = get_settings()
    if not s.ICE_BG_TASK_ENABLED:
        return {"error_code": "BG_TASK_DISABLED", "message": "background tasks are not enabled"}

    agent_id = (args.get("agent_id") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    title = (args.get("title") or "").strip()
    if not (agent_id and prompt and title):
        return {"error_code": "VALIDATION_ERROR", "message": "agent_id, prompt, title all required"}

    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {"error_code": "VALIDATION_ERROR", "message": "run_background needs task + user"}

    try:
        job = await bg_task_svc.enqueue(
            task_id=task_id,
            user_id=user_id,
            agent_id=agent_id,
            title=title,
            prompt=prompt,
            source_conv_id=(ctx or {}).get("conversation_id"),
        )
    except Exception as exc:
        return {"error_code": "BG_TASK_ENQUEUE_FAILED", "message": str(exc)[:300]}
    return {"job_id": job["id"], "status": job["status"], "title": title}


_DATA_PLATFORM_MCP_URL = os.getenv(
    "DATA_PLATFORM_MCP_URL",
    "https://data-platform-mcp.mib.miui.com/mcp",
)

_DATA_PLATFORM_MCP_REQ_ID = 0


async def _tool_data_platform_call(args: dict, ctx: dict | None = None) -> Any:
    import httpx

    global _DATA_PLATFORM_MCP_REQ_ID

    tool_name = (args.get("tool_name") or "").strip()
    if not tool_name:
        return {"error_code": "VALIDATION_ERROR", "message": "tool_name is required"}

    mcp_args = args.get("arguments") or {}

    _DATA_PLATFORM_MCP_REQ_ID += 1
    payload = {
        "jsonrpc": "2.0",
        "id": _DATA_PLATFORM_MCP_REQ_ID,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": mcp_args},
    }

    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            resp = await cli.post(
                _DATA_PLATFORM_MCP_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPStatusError as exc:
        return {
            "error_code": "DATA_PLATFORM_HTTP_ERROR",
            "message": f"MCP HTTP {exc.response.status_code}",
            "detail": exc.response.text[:500],
        }
    except httpx.RequestError as exc:
        return {
            "error_code": "DATA_PLATFORM_UNREACHABLE",
            "message": f"Cannot reach data-platform-mcp: {exc}",
        }
    except Exception as exc:
        return {
            "error_code": "DATA_PLATFORM_ERROR",
            "message": str(exc)[:500],
        }

    if "error" in body:
        err = body["error"]
        return {
            "error_code": "DATA_PLATFORM_MCP_ERROR",
            "message": err.get("message", str(err)),
            "mcp_error_code": err.get("code"),
        }

    result = body.get("result", {})
    content_items = result.get("content", [])
    texts = []
    for item in content_items:
        if isinstance(item, dict) and item.get("type") == "text":
            texts.append(item["text"])
        elif isinstance(item, dict) and item.get("type") == "resource":
            texts.append(json.dumps(item.get("resource", {}), ensure_ascii=False))
    merged = "\n".join(texts)
    try:
        parsed = json.loads(merged)
        return {"tool_name": tool_name, "result": parsed}
    except (json.JSONDecodeError, TypeError):
        return {"tool_name": tool_name, "result": merged}


