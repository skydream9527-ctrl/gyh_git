"""WebSocket /ws/conversations/{cid} — streaming chat + tool calling 5-round loop.

Auth: dual — 米盾 (Aegis) `X-Proxy-UserDetail` header, OR bearer JWT via
subprotocol `["bearer", "<token>"]` / legacy `?token=`. Either is sufficient.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ...core.config import get_settings
from ...core.deps import resolve_user
from ...core.errors import APIError, ErrorCode
from ...core.storage import append_jsonl, get_paths
from ...services import (
    agents_svc,
    compaction_svc,
    conversation_svc,
    experience_card_svc,
    llm_gateway,
    task_svc,
    tool_runner,
    usage_svc,
)

router = APIRouter()
log = logging.getLogger("ws")


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


# Global registry: (task_id, conv_id) → (task, cancel_event).
# When the WS disconnects mid-turn we DO NOT cancel — the task keeps running so
# the agent can finish its work and persist assistant messages / tool calls to
# JSONL. The registry also serves as an inflight guard: if the user reopens the
# task and tries to send another message while the earlier turn is still going,
# we reject with CONVERSATION_INFLIGHT instead of racing two writers.
#
# Explicit `abort` messages from the client still flip the cancel event; only
# the implicit "user navigated away → WS closed" path stops cancelling.
_inflight_turns: dict[tuple[str, str], tuple[asyncio.Task, asyncio.Event]] = {}


@router.websocket("/ws/conversations/{conversation_id}")
async def ws_chat(
    websocket: WebSocket,
    conversation_id: str,
    task_id: str = Query(...),
    token: str | None = Query(default=None),
):
    """Auth — try Aegis header first, then bearer (subprotocol or `?token=`).

    For the subprotocol path: client requests `["bearer", "<access_token>"]`;
    server picks `"bearer"` so the upgrade succeeds with that subprotocol.
    """
    offered = (websocket.headers.get("sec-websocket-protocol") or "").split(",")
    offered = [p.strip() for p in offered if p.strip()]
    chosen_proto: str | None = None
    sub_token: str | None = None
    if "bearer" in offered:
        chosen_proto = "bearer"
        for p in offered:
            if p != "bearer":
                sub_token = p
                break
    bearer = sub_token or token
    auth_header = f"Bearer {bearer}" if bearer else None

    try:
        user = await resolve_user(websocket.headers.get("x-proxy-userdetail"), auth_header)
    except APIError as e:
        log.warning(
            "WS auth fail cid=%s task=%s offered=%r bearer_len=%s reason=%s",
            conversation_id, task_id, offered,
            (len(bearer) if bearer else 0),
            e.message,
        )
        await websocket.close(code=4401)
        return

    try:
        await task_svc.get_task(task_id, user["id"])
    except APIError as e:
        log.warning(
            "WS task-gate fail cid=%s task=%s user=%s reason=%s",
            conversation_id, task_id, user["id"], e.message,
        )
        await websocket.close(code=4403)
        return

    if chosen_proto:
        await websocket.accept(subprotocol=chosen_proto)
    else:
        await websocket.accept()
    paths = get_paths()
    conv_path = paths.task_conversation(task_id, conversation_id)
    tool_path = paths.task_tool_calls(task_id, conversation_id)

    # 回合执行放到后台任务里，主循环始终能读 `abort` / `set_plan_mode` 等控制消息。
    # `_inflight_turns` 是跨 WS 的共享注册表：用户退出 → WS close → 注册表里的 task
    # 不会被取消，继续跑到完成。同一 conv 同时只能有一个 turn。
    inflight_key = (task_id, conversation_id)

    async def _run_turn(msg: dict, cancel: asyncio.Event) -> None:
        try:
            await _handle_user_message(
                websocket, msg, user, task_id, conversation_id, conv_path, tool_path, cancel
            )
        except Exception:
            log.exception("turn task crashed")
        finally:
            entry = _inflight_turns.get(inflight_key)
            if entry is not None and entry[1] is cancel:
                _inflight_turns.pop(inflight_key, None)

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "INVALID_JSON", "invalid JSON payload")
                continue
            mtype = msg.get("type")
            if mtype == "abort":
                # 显式 abort 仍然取消当前回合（不管是本 WS 启动的还是别处复用的）
                entry = _inflight_turns.get(inflight_key)
                if entry is not None:
                    entry[1].set()
                continue
            if mtype == "set_plan_mode":
                try:
                    await conversation_svc.set_plan_mode(
                        task_id=task_id,
                        conv_id=conversation_id,
                        enabled=bool(msg.get("enabled")),
                    )
                    await _send(
                        websocket,
                        {"type": "plan_mode_changed", "enabled": bool(msg.get("enabled"))},
                    )
                except Exception as exc:
                    await _send_error(websocket, "PLAN_MODE_FAILED", str(exc)[:200])
                continue
            if mtype in ("approve_plan", "reject_plan"):
                decision = "approved" if mtype == "approve_plan" else "rejected"
                try:
                    state = await conversation_svc.get_plan_mode(
                        task_id=task_id, conv_id=conversation_id
                    )
                    plan_id = state.get("pending_plan_id")
                    plan_text = state.get("pending_plan_text") or ""
                    await conversation_svc.clear_pending_plan(
                        task_id=task_id, conv_id=conversation_id
                    )
                    await _send(
                        websocket,
                        {"type": "plan_resolved", "plan_id": plan_id, "decision": decision},
                    )
                    await _send(websocket, {"type": "plan_mode_changed", "enabled": False})
                except Exception as exc:
                    await _send_error(websocket, "PLAN_RESOLVE_FAILED", str(exc)[:200])
                    continue
                if decision == "approved" and plan_id:
                    # Inject a synthetic user message so the agent continues
                    # executing the plan without the user re-typing anything.
                    synthetic = (
                        "(系统) 用户已批准上述方案，请现在按方案执行。\n\n"
                        f"[approved plan {plan_id}]\n{plan_text}"
                    )
                    # Plan 批准是用户主动意愿，撞上 inflight 的话直接取消旧 turn 让新的上。
                    existing = _inflight_turns.get(inflight_key)
                    if existing is not None and not existing[0].done():
                        existing[1].set()
                        try:
                            await asyncio.wait_for(existing[0], timeout=5.0)
                        except asyncio.TimeoutError:
                            existing[0].cancel()
                            try:
                                await existing[0]
                            except (asyncio.CancelledError, Exception):
                                pass
                    new_cancel = asyncio.Event()
                    new_task = asyncio.create_task(
                        _run_turn({"type": "user_message", "content": synthetic}, new_cancel)
                    )
                    _inflight_turns[inflight_key] = (new_task, new_cancel)
                continue
            if mtype != "user_message":
                await _send_error(websocket, "UNKNOWN_TYPE", f"unknown type {mtype}")
                continue

            # 同一对话已经有在跑的 turn（可能是本 WS 启动的，也可能是上次退出后残留的），
            # 直接拒绝新消息。用户想中断的话走显式 `abort`。
            existing = _inflight_turns.get(inflight_key)
            if existing is not None and not existing[0].done():
                await _send_error(
                    websocket,
                    ErrorCode.CONVERSATION_INFLIGHT,
                    "该对话正在处理中，请稍候或点中断后再发新消息",
                )
                continue

            new_cancel = asyncio.Event()
            new_task = asyncio.create_task(_run_turn(msg, new_cancel))
            _inflight_turns[inflight_key] = (new_task, new_cancel)
    finally:
        # 关键行为：WS 断开不再取消 task。让它继续跑完、把结果写进 JSONL，
        # 用户返回任务页时能直接看到持久化后的完整历史。
        try:
            await websocket.close()
        except Exception:
            pass


async def _send(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


async def _send_error(ws: WebSocket, code: str, message: str) -> None:
    await _send(ws, {"type": "error", "error_code": code, "message": message})


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
    content = (msg.get("content") or "").strip()
    if not content:
        await _send_error(ws, ErrorCode.VALIDATION_ERROR, "empty message")
        return

    user_record = {
        "id": user_msg_id,
        "role": "user",
        "content": content,
        "user_id": user["id"],
        "created_at": _now(),
    }
    append_jsonl(conv_path, user_record)
    await conversation_svc.touch_last_message(task_id=task_id, conv_id=conversation_id)
    await _send(ws, {"type": "user_message_ack", "message_id": user_msg_id})
    await task_svc.touch_task(task_id, last_message_preview=content)

    if not s.llm_enabled:
        await _send(
            ws,
            {
                "type": "error",
                "error_code": ErrorCode.LLM_KEY_MISSING,
                "message": "LLM API Key 未配置，请联系 @gongyunhe",
            },
        )
        return

    # NOTE: budget ceiling is notification-only. The monthly cap surfaces as
    # a banner on /admin/overview when month_summary().budget_state is
    # "warning" or "exceeded"; we intentionally do NOT block chat here.

    history = task_svc.load_conversation_messages(task_id, conversation_id)
    api_messages = _to_api_messages(history, task_id=task_id, conversation_id=conversation_id)
    if s.ICE_COMPACTION_ENABLED:
        try:
            api_messages = await compaction_svc.maybe_compact(
                task_id=task_id, conv_id=conversation_id, api_messages=api_messages
            )
        except Exception as exc:
            log.warning("compaction failed, falling back: %s", exc)
    task = await task_svc.get_task(task_id, user["id"])
    agent_id = task.get("agent_id") or "biz-insight"
    plan_state = await conversation_svc.get_plan_mode(task_id=task_id, conv_id=conversation_id)
    plan_mode = bool(plan_state.get("plan_mode"))
    system_prompt = experience_card_svc.merged_system_prompt(
        agent_id,
        plan_mode=plan_mode,
        task_skill_ids=list(task.get("skill_ids") or []),
    )
    feature_flags = {
        "todo_write": s.ICE_TODO_ENABLED,
        "exit_plan_mode": s.ICE_PLAN_MODE_ENABLED,
        "spawn_subagent": s.ICE_SUBAGENT_ENABLED,
        "run_background": s.ICE_BG_TASK_ENABLED,
    }
    tools = tool_runner.get_anthropic_tools(
        plan_mode=plan_mode,
        feature_flags=feature_flags,
        task_skill_ids=list(task.get("skill_ids") or []),
    )
    # Per-message > task workspace > settings default
    model_id = (
        msg.get("model")
        or (task.get("workspace") or {}).get("model")
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

    final_text = ""
    files_created: list[dict] = []
    try:
        for round_idx in range(llm_gateway.MAX_TOOL_ROUNDS + 1):
            if cancel_event.is_set():
                await _send(ws, {"type": "agent_typing", "status": "stop"})
                await _send(ws, {"type": "agent_message_done", "files_created": files_created, "aborted": True})
                return
            assistant_msg_id = _new_id()
            text_buf = []
            tool_uses: list[dict] = []
            done_event = None
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
                from ...core.errors import APIError as _APIError
                if isinstance(e, _APIError):
                    raise
                raise _APIError(502, "GATEWAY_ERROR", str(e)[:500]) from e
            if cancel_event.is_set():
                # 保留已经生成的部分到对话历史，便于用户接着追问。
                partial_text = "".join(text_buf)
                if partial_text or tool_uses:
                    append_jsonl(
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
            assistant_record = {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": assistant_text,
                "tool_uses": tool_uses,
                "agent_id": agent_id,
                "stop_reason": (done_event or {}).get("stop_reason"),
                "usage": usage,
                "created_at": _now(),
            }
            append_jsonl(conv_path, assistant_record)
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

            if not tool_uses or round_idx == llm_gateway.MAX_TOOL_ROUNDS:
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

                return await llm_gateway.run_tool_with_timeout(_runner)

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
            for i, tu in enumerate(tool_uses):
                tu_id = tu.get("id")
                tu_name = tu.get("name")
                tu_input = tu.get("input") or {}
                outcome = outcomes[i] or {"status": "error", "success": False, "error": {}}
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
                append_jsonl(
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
            api_messages.append({"role": "user", "content": tool_results})

            # If a plan was proposed this round, stop the outer loop without
            # feeding tool_results back to the LLM — the user must approve.
            if plan_proposed_payload is not None:
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

        await _send(ws, {"type": "agent_message_done", "files_created": files_created})
    except APIError as e:
        await _send(ws, {"type": "error", "error_code": e.error_code, "message": e.message})
    except Exception as e:
        log.exception("ws stream error")
        await _send(ws, {"type": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})
    finally:
        await _send(ws, {"type": "agent_typing", "status": "stop"})
        if final_text:
            await task_svc.touch_task(task_id, last_message_preview=final_text)


def _to_api_messages(
    history: list[dict],
    *,
    task_id: str | None = None,
    conversation_id: str | None = None,
) -> list[dict]:
    """Rebuild Anthropic-shaped message list from persisted JSONL history.

    Critical invariant for the upstream model: every `tool_use` block in an
    assistant message MUST be followed by matching `tool_result` blocks in the
    next user message. We read the tool_calls jsonl for the conversation and
    splice synthetic `tool_result` user-messages in between assistant turns.

    Without this fix, recent history (e.g. after page refresh or multi-tool
    rounds) sends the model orphan tool_use ids → 400 GATEWAY_ERROR.
    """
    # Index tool outcomes by tool_call_id so we can answer every tool_use.
    tool_results_by_id: dict[str, dict] = {}
    if task_id and conversation_id:
        from ...core.storage import get_paths, read_jsonl

        path = get_paths().task_tool_calls(task_id, conversation_id)
        for rec in read_jsonl(path):
            tid = rec.get("id")
            if tid:
                tool_results_by_id[tid] = rec

    # Walk history in chronological order; truncate from the start while keeping
    # turn-pairs intact so we never split an assistant→tool_result pair.
    raw = history[-20:] if len(history) > 20 else list(history)
    # If the slice happens to start with a tool_result-only user message,
    # drop it (orphan from the prior turn).
    while raw and raw[0].get("role") == "user" and not (raw[0].get("content") or "").strip() and not raw[0].get("tool_uses"):
        raw = raw[1:]

    out: list[dict] = []
    for h in raw:
        role = h.get("role")
        if role == "user":
            out.append({"role": "user", "content": h.get("content", "")})
            continue
        if role != "assistant":
            continue

        content = h.get("content", "")
        tool_uses = h.get("tool_uses") or []

        if tool_uses:
            # Build assistant message with text + tool_use blocks.
            blocks: list[dict] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for tu in tool_uses:
                # Strip nullable upstream-extension fields (e.g. `caller`) so
                # the message survives Bedrock validation on round-trip.
                blocks.append({k: v for k, v in tu.items() if v is not None})
            out.append({"role": "assistant", "content": blocks})

            # Follow with synthetic user{tool_result} message — every tool_use
            # MUST be answered or the model rejects the conversation.
            results: list[dict] = []
            for tu in tool_uses:
                tid = tu.get("id")
                rec = tool_results_by_id.get(tid)
                if rec:
                    payload = rec.get("result") if rec.get("success") else rec.get("error")
                    body = (
                        payload
                        if isinstance(payload, str)
                        else __import__("json").dumps(payload or {}, ensure_ascii=False)
                    )
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "content": body,
                            **({"is_error": True} if not rec.get("success") else {}),
                        }
                    )
                else:
                    # No record found — emit a stub so the pairing constraint
                    # holds; mark as error so the model knows it's incomplete.
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "content": "(tool_result unavailable in history)",
                            "is_error": True,
                        }
                    )
            out.append({"role": "user", "content": results})
        else:
            out.append({"role": "assistant", "content": content})

    return out


def _rebuild_content_blocks(text: str, tool_uses: list[dict]) -> list[dict] | str:
    if not tool_uses:
        return text
    blocks: list[dict] = []
    if text:
        blocks.append({"type": "text", "text": text})
    blocks.extend(tool_uses)
    return blocks
