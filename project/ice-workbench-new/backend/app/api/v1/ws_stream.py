"""WebSocket streaming handler — LLM stream + tool calling loop.

Extracted from ws.py. Contains _handle_user_message (the main turn processor)
and _handle_retry_tool_call.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from ...core.config import get_settings
from ...core.errors import ErrorCode
from ...core.storage import append_jsonl, get_paths, read_jsonl
from ...services import (
    agent_kernel,
    agents_svc,
    compaction_svc,
    conversation_svc,
    event_log,
    experience_card_svc,
    inflight_svc,
    llm_gateway,
    sysconfig_svc,
    task_intent_svc,
    task_svc,
    tool_runner,
    usage_svc,
)
from .ws_helpers import _new_id, _now, _rebuild_content_blocks, _send, _send_error, _to_api_messages

log = logging.getLogger("ws")
async def _handle_user_message(
    ws: WebSocket,
    msg: dict,
    user: dict,
    task_id: str,
    conversation_id: str,
    conv_path,
    tool_path,
    cancel_event: asyncio.Event,
):
    s = get_settings()
    user_msg_id = _new_id()
    run_id = _new_id()
    content = (msg.get("content") or "").strip()

    async def _send_run_event(
        stage: str,
        label: str,
        *,
        status: str = "running",
        detail: str | None = None,
        payload: dict | None = None,
    ) -> None:
        await _send(
            ws,
            {
                "type": "run_event",
                "run_id": run_id,
                "stage": stage,
                "label": label,
                "status": status,
                "detail": detail,
                "payload": payload or {},
                "created_at": _now(),
            },
        )
        task_svc.append_run_event(
            task_id,
            conversation_id,
            {
                "type": "run_event",
                "run_id": run_id,
                "stage": stage,
                "label": label,
                "status": status,
                "detail": detail,
                "payload": payload or {},
                "created_at": _now(),
            },
        )

    if not content:
        await _send_error(ws, ErrorCode.VALIDATION_ERROR, "empty message")
        return
    event_log.emit(
        task_id=task_id,
        conv_id=conversation_id,
        run_id=run_id,
        source="ws",
        event_type="turn_start",
        user_id=user.get("id"),
        message=f"len={len(content)}",
        payload={"content_preview": content[:80]},
    )
    await task_svc.set_task_status(task_id, "running", only_if={"active", "failed"})
    await _send_run_event("received", "收到用户消息", detail=content[:80])

    user_record = {
        "id": user_msg_id,
        "role": "user",
        "content": content,
        "user_id": user["id"],
        "created_at": _now(),
    }
    # 同步 IO 全部走线程池——多 session 并行时不能让一个会话的 jsonl 写阻塞
    # 整个 worker 的 event loop（否则其它会话的 ws ping 会超时被误关）。
    await asyncio.to_thread(append_jsonl, conv_path, user_record)
    await conversation_svc.touch_last_message(task_id=task_id, conv_id=conversation_id)
    await _send(ws, {"type": "user_message_ack", "message_id": user_msg_id})

    # FTS index: fire-and-forget for the user message
    async def _fts_user():
        try:
            from ...services.task import fts_svc
            await fts_svc.ensure_fts_table()
            await fts_svc.index_message(
                task_id=task_id,
                conversation_id=conversation_id,
                message_id=user_msg_id,
                role="user",
                content=content,
                created_at=user_record["created_at"],
            )
        except Exception:
            pass
    asyncio.create_task(_fts_user())
    await task_svc.touch_task(task_id, last_message_preview=content)

    if not s.llm_enabled:
        await _send_run_event("failed", "模型服务未配置", status="error")
        await _send(
            ws,
            {
                "type": "error",
                "code": 400,
                "message": "LLM API Key 未配置，请联系 @gongyunhe",
                "error_code": ErrorCode.LLM_KEY_MISSING,
                "data": None,
            },
        )
        return

    # NOTE: budget ceiling is notification-only. The monthly cap surfaces as
    # a banner on /admin/overview when month_summary().budget_state is
    # "warning" or "exceeded"; we intentionally do NOT block chat here.

    # load_conversation_messages 读 jsonl 是 sync IO，长会话能耗几十毫秒到几秒。
    # _to_api_messages 内部还会读 tool_calls.jsonl 一次。两个一起 to_thread。
    await _send_run_event("context", "整理对话上下文")
    history = await asyncio.to_thread(
        task_svc.load_conversation_messages, task_id, conversation_id
    )
    api_messages = await asyncio.to_thread(
        _to_api_messages, history, task_id=task_id, conversation_id=conversation_id
    )
    await _send_run_event("context", "上下文已就绪", status="done", detail=f"{len(api_messages)} 条模型消息")
    if s.ICE_COMPACTION_ENABLED:
        try:
            await _send_run_event("compaction", "检查长对话压缩")
            api_messages = await compaction_svc.maybe_compact(
                task_id=task_id, conv_id=conversation_id, api_messages=api_messages
            )
            await _send_run_event("compaction", "上下文压缩检查完成", status="done")
        except Exception as exc:
            log.warning("compaction failed, falling back: %s", exc)
            await _send_run_event("compaction", "上下文压缩失败，已回退原历史", status="warning", detail=str(exc)[:160])
    task = await task_svc.get_task(task_id, user["id"])
    agent_id = task.get("agent_id") or "biz-insight"
    plan_state = await conversation_svc.get_plan_mode(task_id=task_id, conv_id=conversation_id)
    plan_mode = bool(plan_state.get("plan_mode"))
    # Resolve per-agent overrides on top of global env flags. agent.json
    # `features.<name>` (true/false) wins; missing → falls back to env.
    feature_flags = {
        "todo_write": agents_svc.get_agent_feature(agent_id, "todo_write", s.ICE_TODO_ENABLED),
        "exit_plan_mode": agents_svc.get_agent_feature(agent_id, "exit_plan_mode", s.ICE_PLAN_MODE_ENABLED),
        "spawn_subagent": agents_svc.get_agent_feature(agent_id, "spawn_subagent", s.ICE_SUBAGENT_ENABLED),
        "run_background": agents_svc.get_agent_feature(agent_id, "run_background", s.ICE_BG_TASK_ENABLED),
    }
    tools = tool_runner.get_anthropic_tools(
        plan_mode=plan_mode,
        feature_flags=feature_flags,
        tool_whitelist=agents_svc.get_agent_tools(agent_id),
        disallowed_tools=agents_svc.get_agent_disallowed_tools(agent_id),
        task_skill_ids=list(task.get("skill_ids") or []),
        spawn_targets=agents_svc.list_spawnable_agent_ids(agent_id),
    )
    system_prompt = experience_card_svc.merged_system_prompt(
        agent_id,
        plan_mode=plan_mode,
        task_skill_ids=list(task.get("skill_ids") or []),
        callable_tool_names=[t["name"] for t in tools],
        user_id=user["id"],
        task_id=task_id,
        query=content,
    )
    runtime_hint = task_intent_svc.build_runtime_hint(
        content, task_name=task.get("name")
    )
    if runtime_hint:
        system_prompt = f"{system_prompt}\n\n---\n\n{runtime_hint}"
    # Per-message > task workspace > agent.json.model > settings default
    model_id = (
        msg.get("model")
        or (task.get("workspace") or {}).get("model")
        or agents_svc.get_agent_model(agent_id)
        or llm_gateway.resolve_model(None)
    )

    async def _emit_event(evt: dict) -> None:
        await _send(ws, evt)

    tool_ctx = {
        "user_id": user["id"],
        "agent_id": agent_id,
        "task_id": task_id,
        "conversation_id": conversation_id,
        "plan_mode": plan_mode,
        "subagent_depth": 0,
        "emit_event": _emit_event,
    }

    await _send(ws, {"type": "agent_typing", "status": "start"})

    # Read the round limit from sysconfig (admin-tunable). Clamp into
    # [1, MAX_TOOL_ROUNDS] so a misconfigured value can't kill the loop or
    # let it run unbounded.
    sys_params = sysconfig_svc.get_system_params()
    max_rounds = max(
        1,
        min(
            llm_gateway.MAX_TOOL_ROUNDS,
            int(sys_params.get("tool_call_max_rounds") or 20),
        ),
    )
    agent_max_turns = agents_svc.get_agent_max_turns(agent_id)
    if agent_max_turns is not None:
        max_rounds = min(max_rounds, agent_max_turns)

    final_text = ""
    files_created: list[dict] = []
    tool_attempt_count = 0
    tool_success_count = 0
    tool_failure_count = 0
    # keepalive sidecar：每 _WS_KEEPALIVE_SEC 秒发一帧 {"type":"keepalive"}，给反代和底层 ws
    # 协议一个非 idle 信号。多会话并行时——某个会话在压缩/工具/慢 LLM
    # 期间没有自然下行字节，原本会让 ws ping 超时被误关。
    keepalive_task = asyncio.create_task(_ws_keepalive_loop(ws))
    try:
        if s.ICE_AGENT_KERNEL_ENABLED:
            # ── Unified-kernel path (Plan A) ──────────────────────────────
            # Runs the SAME bounded ReAct loop the sub-agent runtime uses
            # (agent_kernel.run), with a WebSocketEventSink reproducing every
            # frame / run_event / persistence the legacy inline loop below
            # emits. Gated by ICE_AGENT_KERNEL_ENABLED so the legacy loop stays
            # the default until this path passes staging QA; once validated the
            # legacy branch can be deleted. The shared `finally` (agent_typing
            # stop, task-status reset, keepalive cancel) still runs on return.
            sink = WebSocketEventSink(
                ws=ws,
                send=_send,
                send_run_event=_send_run_event,
                conv_path=conv_path,
                tool_path=tool_path,
                agent_id=agent_id,
                run_id=run_id,
                model_id=model_id,
                user=user,
                task_id=task_id,
                conversation_id=conversation_id,
            )
            try:
                state = await agent_kernel.run(
                    system_prompt=system_prompt,
                    messages=api_messages,
                    tools=tools,
                    ctx=tool_ctx,
                    max_rounds=max_rounds,
                    sink=sink,
                    model=model_id,
                    max_tokens=None,  # parity: legacy loop never forwarded it
                    parallel_tools=True,  # kernel still gates on ICE_PARALLEL_TOOLS_ENABLED
                    cancel=cancel_event,
                    halt_on_plan=True,
                    halt_on_human_input=True,
                    raise_on_llm_error=True,
                )
            except APIError:
                raise
            except Exception as e:  # noqa: BLE001 - mirror legacy GATEWAY_ERROR wrap
                raise APIError(502, "GATEWAY_ERROR", str(e)[:500]) from e

            files_created = sink.files_created
            final_text = state.final_text

            if state.aborted:
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(ws, {"type": "agent_message_done", "files_created": files_created, "aborted": True})
                return
            if state.human_intervention is not None:
                await _send_run_event("waiting_user", "等待人工确认", status="waiting")
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(
                    ws,
                    {
                        "type": "agent_message_done",
                        "files_created": files_created,
                        "human_intervention": state.human_intervention,
                        "stop_reason": "human_intervention",
                    },
                )
                return
            if state.plan_proposed is not None:
                await _send_run_event("waiting_user", "等待用户审批方案", status="waiting")
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(
                    ws,
                    {
                        "type": "agent_message_done",
                        "files_created": files_created,
                        "plan_proposed": state.plan_proposed,
                        "stop_reason": "plan_proposed",
                    },
                )
                return

            if not final_text and state.tool_attempt_count:
                fallback_msg_id = _new_id()
                fallback_text = (
                    "这轮执行已经结束，但模型没有生成最终说明。\n\n"
                    f"已执行工具 {state.tool_attempt_count} 步，其中成功 {state.tool_success_count} 步、"
                    f"失败 {state.tool_failure_count} 步，生成文件 {len(files_created)} 个。"
                    "请查看上方工具执行记录；你也可以直接追问“继续整理结果”或“失败项原因”。"
                )
                await _send_run_event(
                    "completed",
                    "执行结束但缺少最终回复，已补充状态说明",
                    status="warning",
                    detail=f"工具 {state.tool_attempt_count} 步 · 失败 {state.tool_failure_count} 步",
                )
                await _send(ws, {"type": "agent_message", "message_id": fallback_msg_id, "content": fallback_text})
                await asyncio.to_thread(
                    append_jsonl,
                    conv_path,
                    {
                        "id": fallback_msg_id,
                        "role": "assistant",
                        "content": fallback_text,
                        "tool_uses": [],
                        "agent_id": agent_id,
                        "run_id": run_id,
                        "stop_reason": "empty_final_fallback",
                        "usage": {},
                        "created_at": _now(),
                    },
                )
                await conversation_svc.touch_last_message(task_id=task_id, conv_id=conversation_id)
                final_text = fallback_text

            await _send_run_event("completed", "执行完成", status="done", detail=f"生成 {len(files_created)} 个文件")
            await _send(ws, {"type": "agent_message_done", "files_created": files_created})

            # Auto-memory extraction (fire-and-forget): analyze the completed
            # turn for reusable insights and save to agent memory.
            if final_text and state.tool_attempt_count >= 2:
                from ...services.task import auto_memory_svc

                async def _auto_memory():
                    try:
                        task_meta = await task_svc.get_task(task_id, user["id"], is_admin=True)
                        await auto_memory_svc.maybe_extract_and_save(
                            user_id=user["id"],
                            agent_id=agent_id,
                            task_id=task_id,
                            final_text=final_text,
                            tool_attempt_count=state.tool_attempt_count,
                            tool_success_count=state.tool_success_count,
                            task_name=task_meta.get("name"),
                        )
                    except Exception:
                        pass  # best-effort, never fail the main flow

                asyncio.create_task(_auto_memory())

            return

        for round_idx in range(max_rounds + 1):
            if cancel_event.is_set():
                await _send_run_event("aborted", "用户已中断执行", status="aborted")
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(ws, {"type": "agent_message_done", "files_created": files_created, "aborted": True})
                return
            assistant_msg_id = _new_id()
            text_buf = []
            tool_uses: list[dict] = []
            done_event = None
            await _send_run_event(
                "llm",
                "模型生成中",
                detail=f"第 {round_idx + 1} 轮 · {model_id}",
                payload={"round": round_idx + 1, "model": model_id},
            )
            try:
                async for ev in llm_gateway.stream_chat(
                    system_prompt=system_prompt,
                    messages=api_messages,
                    tools=tools,
                    model=model_id,
                ):
                    if cancel_event.is_set():
                        break
                    if ev["type"] == "text":
                        text_buf.append(ev["delta"])
                        await _send(
                            ws,
                            {
                                "type": "agent_message",
                                "message_id": assistant_msg_id,
                                "content": ev["delta"],
                            },
                        )
                    elif ev["type"] == "tool_use_delta":
                        # OpenAI streams tool calls incrementally; surface for
                        # frontend to show "正在准备参数…" before tool_call_start.
                        await _send(
                            ws,
                            {
                                "type": "tool_call_preview",
                                "message_id": assistant_msg_id,
                                "index": ev.get("index"),
                                "id": ev.get("id"),
                                "name": ev.get("name"),
                                "args_chunk": ev.get("args_chunk", ""),
                            },
                        )
                    elif ev["type"] == "message_done":
                        done_event = ev
                        for block in ev.get("content") or []:
                            if block.get("type") == "tool_use":
                                tool_uses.append(block)
            except Exception as e:
                log.exception("gateway stream failed")
                event_log.emit(
                    task_id=task_id,
                    conv_id=conversation_id,
                    run_id=run_id,
                    source="llm_gateway",
                    event_type="gateway_error",
                    level="ERROR",
                    code="GATEWAY_ERROR",
                    message=f"{type(e).__name__}: {str(e)[:300]}",
                    payload={"model": model_id, "round": round_idx},
                )
                from ...core.errors import APIError as _APIError
                if isinstance(e, _APIError):
                    raise
                raise _APIError(502, "GATEWAY_ERROR", str(e)[:500]) from e
            if cancel_event.is_set():
                # 保留已经生成的部分到对话历史，便于用户接着追问。
                await _send_run_event("aborted", "用户已中断执行", status="aborted")
                partial_text = "".join(text_buf)
                if partial_text or tool_uses:
                    await asyncio.to_thread(
                        append_jsonl,
                        conv_path,
                        {
                            "id": assistant_msg_id,
                            "role": "assistant",
                            "content": partial_text,
                            "tool_uses": tool_uses,
                            "agent_id": agent_id,
                            "stop_reason": "user_aborted",
                            "usage": (done_event or {}).get("usage") or {},
                            "created_at": _now(),
                        },
                    )
                    await conversation_svc.touch_last_message(task_id=task_id, conv_id=conversation_id)
                    final_text = partial_text or final_text
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(ws, {"type": "agent_message_done", "files_created": files_created, "aborted": True})
                return
            assistant_text = "".join(text_buf)
            usage = (done_event or {}).get("usage") or {}
            await _send_run_event(
                "llm",
                "模型生成完成",
                status="done",
                detail=f"{len(assistant_text)} 字 · {len(tool_uses)} 个工具",
                payload={"round": round_idx + 1, "tool_count": len(tool_uses)},
            )
            assistant_record = {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": assistant_text,
                "tool_uses": tool_uses,
                "agent_id": agent_id,
                "run_id": run_id,
                "stop_reason": (done_event or {}).get("stop_reason"),
                "usage": usage,
                "created_at": _now(),
            }
            await asyncio.to_thread(append_jsonl, conv_path, assistant_record)
            await conversation_svc.touch_last_message(task_id=task_id, conv_id=conversation_id)
            try:
                await usage_svc.record_usage(
                    user_id=user["id"],
                    agent_id=agent_id,
                    task_id=task_id,
                    conversation_id=conversation_id,
                    model=model_id,
                    input_tokens=int(usage.get("input_tokens") or 0),
                    output_tokens=int(usage.get("output_tokens") or 0),
                    success=True,
                )
            except Exception as exc:
                log.warning("record_usage failed: %s", exc)
            api_messages.append(
                {
                    "role": "assistant",
                    "content": _rebuild_content_blocks(assistant_text, tool_uses),
                }
            )
            final_text = assistant_text or final_text

            if not tool_uses or round_idx == max_rounds:
                break

            # Partition: parallel-safe reads can fan out via gather; anything
            # flagged parallel_safe=False runs serially in original order.
            parallel_enabled = s.ICE_PARALLEL_TOOLS_ENABLED
            parallel_idx: list[int] = []
            serial_idx: list[int] = []
            for i, tu in enumerate(tool_uses):
                meta = tool_runner.get_tool_meta(tu.get("name") or "")
                if parallel_enabled and meta.get("parallel_safe"):
                    parallel_idx.append(i)
                else:
                    serial_idx.append(i)

            # Emit start events for the parallel group first so the UI shows
            # them all spinning simultaneously.
            started_at: list[str] = [""] * len(tool_uses)
            for i in parallel_idx:
                tu = tool_uses[i]
                await _send_run_event(
                    "tool",
                    f"开始执行 {tool_runner.get_display_name(tu.get('name'))}",
                    detail="并行执行",
                    payload={"tool_call_id": tu.get("id"), "tool_name": tu.get("name")},
                )
                await _send(
                    ws,
                    {
                        "type": "tool_call_start",
                        "tool_call_id": tu.get("id"),
                        "tool_name": tu.get("name"),
                        "display_name": tool_runner.get_display_name(tu.get("name")),
                        "arguments": tu.get("input") or {},
                    },
                )
                started_at[i] = _now()

            async def _run_one(i: int) -> dict:
                tu = tool_uses[i]
                tu_name = tu.get("name")
                tu_input = tu.get("input") or {}

                async def _runner():
                    return await tool_runner.execute_tool(tu_name, tu_input, ctx=tool_ctx)

                timeout = llm_gateway.tool_timeout_for(tu_name, sys_params)
                return await llm_gateway.run_tool_with_retry(
                    _runner,
                    timeout=timeout,
                    settings=s,
                    audit_ctx={"task_id": task_id, "conversation_id": conversation_id},
                )

            outcomes: list[dict] = [None] * len(tool_uses)  # type: ignore
            if parallel_idx:
                gathered = await asyncio.gather(
                    *[_run_one(i) for i in parallel_idx], return_exceptions=True
                )
                for idx, res in zip(parallel_idx, gathered):
                    if isinstance(res, Exception):
                        outcomes[idx] = {
                            "status": "error",
                            "success": False,
                            "error": {"error_code": "TOOL_EXCEPTION", "message": str(res)[:300]},
                        }
                    else:
                        outcomes[idx] = res

            # Serial group: emit start+run+done one at a time.
            for i in serial_idx:
                tu = tool_uses[i]
                await _send_run_event(
                    "tool",
                    f"开始执行 {tool_runner.get_display_name(tu.get('name'))}",
                    payload={"tool_call_id": tu.get("id"), "tool_name": tu.get("name")},
                )
                await _send(
                    ws,
                    {
                        "type": "tool_call_start",
                        "tool_call_id": tu.get("id"),
                        "tool_name": tu.get("name"),
                        "display_name": tool_runner.get_display_name(tu.get("name")),
                        "arguments": tu.get("input") or {},
                    },
                )
                started_at[i] = _now()
                outcomes[i] = await _run_one(i)

            # Emit done events + persist tool_calls + build tool_results in the
            # ORIGINAL tool_uses order (Anthropic doesn't require order in the
            # tool_result array but keeping it simplifies debugging).
            tool_results: list[dict] = []
            plan_proposed_payload: dict | None = None
            human_intervention_payload: dict | None = None
            for i, tu in enumerate(tool_uses):
                tu_id = tu.get("id")
                tu_name = tu.get("name")
                tu_input = tu.get("input") or {}
                outcome = outcomes[i] or {"status": "error", "success": False, "error": {}}
                tool_attempt_count += 1
                if outcome.get("success"):
                    tool_success_count += 1
                else:
                    tool_failure_count += 1
                await _send_run_event(
                    "tool",
                    f"{tool_runner.get_display_name(tu_name)} 执行结束",
                    status="done" if outcome.get("success") else "error",
                    detail=str(outcome.get("status") or ""),
                    payload={"tool_call_id": tu_id, "tool_name": tu_name},
                )
                await _send(
                    ws,
                    {
                        "type": "tool_call_done",
                        "tool_call_id": tu_id,
                        "tool_name": tu_name,
                        "status": outcome.get("status"),
                        "success": outcome.get("success"),
                        "result": outcome.get("result"),
                        "error": outcome.get("error"),
                    },
                )
                # 工具调用失败入 events（成功的不记，避免噪音；完整调用流仍在
                # tool_calls.jsonl 里，诊断页时间轴可合并展示）。
                if not outcome.get("success"):
                    err = outcome.get("error") or {}
                    err_code = (
                        err.get("error_code")
                        if isinstance(err, dict)
                        else None
                    ) or "TOOL_ERROR"
                    err_msg = (
                        err.get("message")
                        if isinstance(err, dict)
                        else str(err)
                    ) or "tool failed"
                    event_log.emit(
                        task_id=task_id,
                        conv_id=conversation_id,
                        run_id=run_id,
                        source="tool_runner",
                        event_type="tool_error",
                        level="WARN",
                        code=err_code,
                        message=f"{tu_name}: {err_msg}",
                        payload={"tool_call_id": tu_id, "status": outcome.get("status")},
                    )
                if (
                    tu_name == "write_file"
                    and outcome.get("success")
                    and isinstance(outcome.get("result"), dict)
                    and outcome["result"].get("file_id")
                ):
                    res = outcome["result"]
                    file_meta = {
                        "id": res["file_id"],
                        "name": res.get("name"),
                        "size_bytes": res.get("size_bytes"),
                        "scope": res.get("scope", "output"),
                        "path": res.get("path"),
                    }
                    files_created.append(file_meta)
                    await _send(ws, {"type": "file_created", "file": file_meta})
                await asyncio.to_thread(
                    append_jsonl,
                    tool_path,
                    {
                        "id": tu_id,
                        "tool_name": tu_name,
                        "arguments": tu_input,
                        "status": outcome.get("status"),
                        "success": outcome.get("success"),
                        "result": outcome.get("result"),
                        "error": outcome.get("error"),
                        "started_at": started_at[i],
                        "ended_at": _now(),
                    },
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": json.dumps(
                            outcome.get("result") or outcome.get("error") or {}, ensure_ascii=False
                        ),
                        "is_error": not outcome.get("success"),
                    }
                )
                # exit_plan_mode success → terminate the round loop AFTER
                # finishing all tool_call_done / tool_call audit records.
                if (
                    tu_name == "exit_plan_mode"
                    and outcome.get("success")
                    and isinstance(outcome.get("result"), dict)
                    and outcome["result"].get("plan_id")
                ):
                    plan_proposed_payload = outcome["result"]
                if (
                    tu_name == "request_human_input"
                    and outcome.get("success")
                    and isinstance(outcome.get("result"), dict)
                    and outcome["result"].get("waiting_for_human")
                ):
                    human_intervention_payload = outcome["result"]
            api_messages.append({"role": "user", "content": tool_results})

            if human_intervention_payload is not None:
                await _send_run_event("waiting_user", "等待人工确认", status="waiting")
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(
                    ws,
                    {
                        "type": "agent_message_done",
                        "files_created": files_created,
                        "human_intervention": human_intervention_payload,
                        "stop_reason": "human_intervention",
                    },
                )
                return

            # If a plan was proposed this round, stop the outer loop without
            # feeding tool_results back to the LLM — the user must approve.
            if plan_proposed_payload is not None:
                await _send_run_event("waiting_user", "等待用户审批方案", status="waiting")
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(
                    ws,
                    {
                        "type": "agent_message_done",
                        "files_created": files_created,
                        "plan_proposed": plan_proposed_payload,
                        "stop_reason": "plan_proposed",
                    },
                )
                return

        if not final_text and tool_attempt_count:
            fallback_msg_id = _new_id()
            fallback_text = (
                "这轮执行已经结束，但模型没有生成最终说明。\n\n"
                f"已执行工具 {tool_attempt_count} 步，其中成功 {tool_success_count} 步、"
                f"失败 {tool_failure_count} 步，生成文件 {len(files_created)} 个。"
                "请查看上方工具执行记录；你也可以直接追问“继续整理结果”或“失败项原因”。"
            )
            await _send_run_event(
                "completed",
                "执行结束但缺少最终回复，已补充状态说明",
                status="warning",
                detail=f"工具 {tool_attempt_count} 步 · 失败 {tool_failure_count} 步",
            )
            await _send(ws, {"type": "agent_message", "message_id": fallback_msg_id, "content": fallback_text})
            await asyncio.to_thread(
                append_jsonl,
                conv_path,
                {
                    "id": fallback_msg_id,
                    "role": "assistant",
                    "content": fallback_text,
                    "tool_uses": [],
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "stop_reason": "empty_final_fallback",
                    "usage": {},
                    "created_at": _now(),
                },
            )
            await conversation_svc.touch_last_message(task_id=task_id, conv_id=conversation_id)
            final_text = fallback_text

        await _send_run_event("completed", "执行完成", status="done", detail=f"生成 {len(files_created)} 个文件")
        await _send(ws, {"type": "agent_message_done", "files_created": files_created})
    except APIError as e:
        await _send_run_event("failed", "执行失败", status="error", detail=e.message)
        await _send(ws, {"type": "error", "error_code": e.error_code, "message": e.message})
        event_log.emit(
            task_id=task_id,
            conv_id=conversation_id,
            run_id=run_id,
            source="ws",
            event_type="turn_error",
            level="ERROR",
            code=e.error_code,
            message=e.message,
        )
    except Exception as e:
        log.exception("ws stream error")
        await _send_run_event("failed", "执行异常", status="error", detail=str(e)[:200])
        await _send(ws, {"type": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})
        event_log.emit(
            task_id=task_id,
            conv_id=conversation_id,
            run_id=run_id,
            source="ws",
            event_type="turn_error",
            level="ERROR",
            code="INTERNAL_ERROR",
            message=f"{type(e).__name__}: {str(e)[:300]}",
        )
    finally:
        await _send(ws, {"type": "agent_typing", "status": "stop"})
        if final_text:
            await task_svc.touch_task(task_id, last_message_preview=final_text)
        event_log.emit(
            task_id=task_id,
            conv_id=conversation_id,
            run_id=run_id,
            source="ws",
            event_type="turn_end",
            user_id=user.get("id"),
            message=f"final_len={len(final_text)} files={len(files_created)}",
        )
        # Auto-memory extraction for the legacy loop path (kernel path
        # handles it above before returning). Fire-and-forget.
        if (
            final_text
            and len(final_text) > 120
            and tool_attempt_count >= 2
            and tool_success_count >= 1
            and not s.ICE_AGENT_KERNEL_ENABLED
        ):
            from ...services.task import auto_memory_svc

            async def _auto_memory_legacy():
                try:
                    task_meta = await task_svc.get_task(task_id, user["id"], is_admin=True)
                    await auto_memory_svc.maybe_extract_and_save(
                        user_id=user["id"],
                        agent_id=agent_id,
                        task_id=task_id,
                        final_text=final_text,
                        tool_attempt_count=tool_attempt_count,
                        tool_success_count=tool_success_count,
                        task_name=task_meta.get("name"),
                    )
                except Exception:
                    pass

            asyncio.create_task(_auto_memory_legacy())

        keepalive_task.cancel()
        try:
            await keepalive_task
        except BaseException:
            pass
        await task_svc.set_task_status(task_id, "active", only_if={"running"})


def _latest_tool_call(tool_path, tool_call_id: str) -> dict | None:
    found = None
    for rec in read_jsonl(tool_path):
        if rec.get("id") == tool_call_id:
            found = rec
    return found


def _normalize_tool_outcome(outcome: dict) -> dict:
    return llm_gateway.normalize_tool_outcome(outcome)


async def _handle_retry_tool_call(
    ws: WebSocket,
    user: dict,
    task_id: str,
    conversation_id: str,
    tool_path,
    tool_call_id: str,
) -> None:
    run_id = _new_id()
    rec = _latest_tool_call(tool_path, tool_call_id)
    if not rec:
        await _send_error(ws, ErrorCode.RESOURCE_NOT_FOUND, "未找到该工具调用记录")
        return
    tool_name = str(rec.get("tool_name") or "")
    tool_args = rec.get("arguments") or {}
    meta = tool_runner.get_tool_meta(tool_name or "")
    display_name = tool_runner.get_display_name(tool_name or "")
    if rec.get("success"):
        await _send_error(ws, ErrorCode.VALIDATION_ERROR, "该工具已成功，无需重试")
        return
    if meta.get("side_effect") != "read":
        await _send_error(
            ws,
            ErrorCode.PERMISSION_DENIED,
            "写入类工具暂不支持一键重试，请让 Agent 重新执行该步骤",
        )
        return

    async def _send_run_event(stage: str, label: str, *, status: str = "running", detail: str | None = None):
        await _send(
            ws,
            {
                "type": "run_event",
                "run_id": run_id,
                "stage": stage,
                "label": label,
                "status": status,
                "detail": detail,
                "payload": {"tool_call_id": tool_call_id, "tool_name": tool_name},
                "created_at": _now(),
            },
        )

    task = await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    agent_id = task.get("agent_id") or "biz-insight"
    plan_state = await conversation_svc.get_plan_mode(task_id=task_id, conv_id=conversation_id)
    tool_ctx = {
        "user_id": user["id"],
        "agent_id": agent_id,
        "task_id": task_id,
        "conversation_id": conversation_id,
        "plan_mode": bool(plan_state.get("plan_mode")),
        "subagent_depth": 0,
    }

    await _send_run_event("tool_retry", f"重试 {display_name}")
    await _send(
        ws,
        {
            "type": "tool_call_start",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "display_name": display_name,
            "arguments": tool_args,
            "retry": True,
        },
    )
    started_at = _now()

    async def _runner():
        return await tool_runner.execute_tool(tool_name, tool_args, ctx=tool_ctx)

    sys_params = sysconfig_svc.get_system_params()
    timeout = llm_gateway.tool_timeout_for(tool_name, sys_params)
    outcome = _normalize_tool_outcome(await llm_gateway.run_tool_with_timeout(_runner, timeout=timeout))
    ended_at = _now()
    await asyncio.to_thread(
        append_jsonl,
        tool_path,
        {
            "id": tool_call_id,
            "tool_name": tool_name,
            "arguments": tool_args,
            "status": outcome.get("status"),
            "success": outcome.get("success"),
            "result": outcome.get("result"),
            "error": outcome.get("error"),
            "started_at": started_at,
            "ended_at": ended_at,
            "retry_of": tool_call_id,
            "retried_by": user.get("id"),
            "retried_at": ended_at,
        },
    )
    await _send(
        ws,
        {
            "type": "tool_call_done",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "status": outcome.get("status"),
            "success": outcome.get("success"),
            "result": outcome.get("result"),
            "error": outcome.get("error"),
            "retry": True,
        },
    )
    await _send_run_event(
        "tool_retry",
        f"{display_name} 重试完成",
        status="done" if outcome.get("success") else "error",
        detail=str(outcome.get("status") or ""),
    )
    event_log.emit(
        task_id=task_id,
        conv_id=conversation_id,
        run_id=run_id,
        source="tool_runner",
        event_type="tool_retry",
        level="INFO" if outcome.get("success") else "WARN",
        code=None if outcome.get("success") else "TOOL_RETRY_FAILED",
        message=f"{tool_name} retry status={outcome.get('status')}",
        payload={"tool_call_id": tool_call_id},
    )


def _latest_tool_call(tool_path, tool_call_id: str) -> dict | None:
    found = None
    for rec in read_jsonl(tool_path):
        if rec.get("id") == tool_call_id:
            found = rec
    return found


def _normalize_tool_outcome(outcome: dict) -> dict:
    return llm_gateway.normalize_tool_outcome(outcome)


async def _handle_retry_tool_call(
    ws: WebSocket,
    user: dict,
    task_id: str,
    conversation_id: str,
    tool_path,
    tool_call_id: str,
) -> None:
    run_id = _new_id()
    rec = _latest_tool_call(tool_path, tool_call_id)
    if not rec:
        await _send_error(ws, ErrorCode.RESOURCE_NOT_FOUND, "未找到该工具调用记录")
        return
    tool_name = str(rec.get("tool_name") or "")
    tool_args = rec.get("arguments") or {}
    meta = tool_runner.get_tool_meta(tool_name or "")
    display_name = tool_runner.get_display_name(tool_name or "")
    if rec.get("success"):
        await _send_error(ws, ErrorCode.VALIDATION_ERROR, "该工具已成功，无需重试")
        return
    if meta.get("side_effect") != "read":
        await _send_error(
            ws,
            ErrorCode.PERMISSION_DENIED,
            "写入类工具暂不支持一键重试，请让 Agent 重新执行该步骤",
        )
        return

    async def _send_run_event(stage: str, label: str, *, status: str = "running", detail: str | None = None):
        await _send(
            ws,
            {
                "type": "run_event",
                "run_id": run_id,
                "stage": stage,
                "label": label,
                "status": status,
                "detail": detail,
                "payload": {"tool_call_id": tool_call_id, "tool_name": tool_name},
                "created_at": _now(),
            },
        )

    task = await task_svc.get_task(task_id, user["id"], is_admin=bool(user.get("is_admin")))
    agent_id = task.get("agent_id") or "biz-insight"
    plan_state = await conversation_svc.get_plan_mode(task_id=task_id, conv_id=conversation_id)
    tool_ctx = {
        "user_id": user["id"],
        "agent_id": agent_id,
        "task_id": task_id,
        "conversation_id": conversation_id,
        "plan_mode": bool(plan_state.get("plan_mode")),
        "subagent_depth": 0,
    }

    await _send_run_event("tool_retry", f"重试 {display_name}")
    await _send(
        ws,
        {
            "type": "tool_call_start",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "display_name": display_name,
            "arguments": tool_args,
            "retry": True,
        },
    )
    started_at = _now()

    async def _runner():
        return await tool_runner.execute_tool(tool_name, tool_args, ctx=tool_ctx)

    sys_params = sysconfig_svc.get_system_params()
    timeout = llm_gateway.tool_timeout_for(tool_name, sys_params)
    outcome = _normalize_tool_outcome(await llm_gateway.run_tool_with_timeout(_runner, timeout=timeout))
    ended_at = _now()
    await asyncio.to_thread(
        append_jsonl,
        tool_path,
        {
            "id": tool_call_id,
            "tool_name": tool_name,
            "arguments": tool_args,
            "status": outcome.get("status"),
            "success": outcome.get("success"),
            "result": outcome.get("result"),
            "error": outcome.get("error"),
            "started_at": started_at,
            "ended_at": ended_at,
            "retry_of": tool_call_id,
            "retried_by": user.get("id"),
            "retried_at": ended_at,
        },
    )
    await _send(
        ws,
        {
            "type": "tool_call_done",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "status": outcome.get("status"),
            "success": outcome.get("success"),
            "result": outcome.get("result"),
            "error": outcome.get("error"),
            "retry": True,
        },
    )
    await _send_run_event(
        "tool_retry",
        f"{display_name} 重试完成",
        status="done" if outcome.get("success") else "error",
        detail=str(outcome.get("status") or ""),
    )
    event_log.emit(
        task_id=task_id,
        conv_id=conversation_id,
        run_id=run_id,
        source="tool_runner",
        event_type="tool_retry",
        level="INFO" if outcome.get("success") else "WARN",
        code=None if outcome.get("success") else "TOOL_RETRY_FAILED",
        message=f"{tool_name} retry status={outcome.get('status')}",
        payload={"tool_call_id": tool_call_id},
    )


