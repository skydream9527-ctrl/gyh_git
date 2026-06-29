"""WebSocket /ws/conversations/{cid} — streaming chat + tool calling 5-round loop.

Auth: dual — 米盾 (Aegis) `X-Proxy-UserDetail` header, OR bearer JWT via
subprotocol `["bearer", "<token>"]` / legacy `?token=`. Either is sufficient.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import IO

import portalocker
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ...core.config import get_settings
from ...core.deps import resolve_user
from ...core.errors import APIError, ErrorCode
from ...core.storage import append_jsonl, get_paths, read_jsonl
from ...core.ws_auth import extract_bearer
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
from .ws_event_sink import WebSocketEventSink

router = APIRouter()
log = logging.getLogger("ws")


import re as _re


def _filter_plan_steps(plan_text: str, approved_indices: list[int]) -> str:
    """Filter a markdown plan to only include approved steps (1-indexed).

    Parses numbered list items (1. / 2. / - Step N) and markdown headings
    that look like steps, keeping only those whose index is in approved_indices.
    """
    lines = plan_text.split("\n")
    result_lines: list[str] = []
    current_step = 0
    step_pattern = _re.compile(r"^\s*(\d+)\s*[.)]\s")
    heading_step_pattern = _re.compile(r"^#{1,4}\s*(?:Step|步骤)?\s*(\d+)", _re.IGNORECASE)
    in_approved_step = False

    for line in lines:
        # Check if this line starts a new step
        m = step_pattern.match(line) or heading_step_pattern.match(line)
        if m:
            current_step = int(m.group(1))
            in_approved_step = current_step in approved_indices
        elif current_step == 0:
            # Preamble before any steps — always include
            result_lines.append(line)
            continue

        if in_approved_step:
            result_lines.append(line)

    # If parsing found no steps, return original text (fail-safe)
    if current_step == 0:
        return plan_text

    return "\n".join(result_lines)


from .ws_helpers import (
    _INFLIGHT_HEARTBEAT_SEC,
    _WS_KEEPALIVE_SEC,
    _broadcast_inflight,
    _inflight_heartbeat,
    _inflight_status_payload,
    _inflight_turns,
    _new_id,
    _now,
    _register_subscriber,
    _release_conv_inflight,
    _send,
    _send_error,
    _state_signature,
    _try_acquire_conv_inflight,
    _unregister_subscriber,
    _ws_keepalive_loop,
    cancel_inflight_turn,
    is_inflight,
)
from .ws_stream import _handle_retry_tool_call, _handle_user_message


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
    # Subprotocol-bearer negotiation contract (see core/ws_auth.extract_bearer):
    # client offers `Sec-WebSocket-Protocol: bearer, <jwt>`; the negotiated
    # subprotocol value is exactly "bearer" (never the token), and the
    # subprotocol token takes precedence over the legacy `?token=` query param.
    offered_header = websocket.headers.get("sec-websocket-protocol")
    chosen_proto, bearer = extract_bearer(offered_header, token)
    auth_header = f"Bearer {bearer}" if bearer else None

    # Accept the upgrade FIRST, then validate. A WebSocket close issued *before*
    # accept() rejects the HTTP handshake, which browsers surface only as an
    # opaque failure: `onclose` fires with code 1006 and the app can read
    # neither the HTTP status nor any custom close code. The semantic auth close
    # codes 4401/4403 only reach the client if the handshake is accepted (101)
    # first and the code travels in the close frame. Without accepting first,
    # the frontend's 4401/4403 handling (refresh-then-reconnect, clear+redirect,
    # PERMISSION_DENIED-fatal) is unreachable and every auth failure degrades
    # into an infinite 1006 reconnect loop.
    if chosen_proto:
        await websocket.accept(subprotocol=chosen_proto)
    else:
        await websocket.accept()

    try:
        user = await resolve_user(websocket.headers.get("x-proxy-userdetail"), auth_header)
    except APIError as e:
        log.warning(
            "WS auth fail cid=%s task=%s offered=%r bearer_len=%s reason=%s",
            conversation_id, task_id, offered_header,
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

    # 推导角色：viewer 允许进 WS（看历史 + 收 stream），但不允许 send user_message
    from ...core.deps import TaskRole as _TaskRole
    from ...core.deps import derive_task_role
    from ...core.storage import read_json
    _paths = get_paths()
    _meta = read_json(_paths.task_meta(task_id)) or {}
    _collabs = read_json(_paths.task_collaborators(task_id), default=[]) or []
    ws_role = derive_task_role(
        _meta, _collabs, user_id=user["id"], is_admin=bool(user.get("is_admin"))
    )
    is_viewer_ws = ws_role == _TaskRole.VIEWER

    paths = get_paths()
    conv_path = paths.task_conversation(task_id, conversation_id)
    tool_path = paths.task_tool_calls(task_id, conversation_id)

    # WS 不走 HTTP 中间件，独立分配 ws_id 进 contextvar，让 _run_turn 里 emit
    # 的事件都能带上同一个 request_id 便于反查。
    ws_id = "ws-" + secrets.token_hex(4)
    event_log.request_id_var.set(ws_id)
    event_log.user_id_var.set(user["id"])
    event_log.emit(
        task_id=task_id,
        conv_id=conversation_id,
        source="ws",
        event_type="ws_open",
        request_id=ws_id,
        user_id=user["id"],
        message=f"role={getattr(ws_role, 'value', ws_role)}",
    )

    # 回合执行放到后台任务里，主循环始终能读 `abort` / `set_plan_mode` 等控制消息。
    # `_inflight_turns` 是跨 WS 的共享注册表：用户退出 → WS close → 注册表里的 task
    # 不会被取消，继续跑到完成。同一 conv 同时只能有一个 turn。
    inflight_key = (task_id, conversation_id)

    # 注册 inflight 订阅 + 推一次当前状态：用户 B 打开页面那一刻就能看到 A 是否
    # 正在对话，发送按钮立即正确置灰；后续状态变化由 _broadcast_inflight 同 worker
    # 推送、由 _inflight_heartbeat 跨 worker 兜底。
    _register_subscriber(task_id, conversation_id, websocket)
    initial_state = inflight_svc.read_state(task_id, conversation_id)
    try:
        await websocket.send_text(
            json.dumps(_inflight_status_payload(initial_state), ensure_ascii=False)
        )
    except Exception:
        pass
    heartbeat_task = asyncio.create_task(
        _inflight_heartbeat(websocket, task_id, conversation_id),
        name=f"inflight-hb:{task_id}:{conversation_id}",
    )

    user_display_name = (
        user.get("display_name")
        or user.get("name")
        or user.get("email")
        or "用户"
    )

    async def _run_turn(msg: dict, cancel: asyncio.Event, lock_fh: IO | None) -> None:
        # mark_busy + 广播必须在 turn 真正开始执行 *之前*，且失败也要走 finally
        # 清理。先写状态再 broadcast：心跳 worker 即使 race 也只会读到合法 JSON。
        state = inflight_svc.mark_busy(
            task_id,
            conversation_id,
            user_id=user["id"],
            user_name=user_display_name,
        )
        await _broadcast_inflight(task_id, conversation_id, state)
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
            _release_conv_inflight(lock_fh)
            inflight_svc.mark_idle(task_id, conversation_id)
            await _broadcast_inflight(task_id, conversation_id, None)

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
                event_log.emit(
                    task_id=task_id,
                    conv_id=conversation_id,
                    source="ws",
                    event_type="turn_abort_requested",
                    level="WARN",
                    message="user requested abort",
                )
                continue
            if mtype == "retry_tool_call":
                if is_viewer_ws:
                    await _send_error(
                        websocket,
                        ErrorCode.PERMISSION_DENIED,
                        "您仅有查看权限，如需重试工具请申请编辑权限",
                    )
                    continue
                tool_call_id = str(msg.get("tool_call_id") or "")
                if not tool_call_id:
                    await _send_error(websocket, ErrorCode.VALIDATION_ERROR, "missing tool_call_id")
                    continue
                existing = _inflight_turns.get(inflight_key)
                if existing is not None and not existing[0].done():
                    await _send_error(
                        websocket,
                        ErrorCode.CONVERSATION_INFLIGHT,
                        "该对话正在处理中，请等待当前回合结束后再重试工具",
                    )
                    continue
                lock_fh = _try_acquire_conv_inflight(task_id, conversation_id)
                if lock_fh is None:
                    await _send_error(
                        websocket,
                        ErrorCode.CONVERSATION_INFLIGHT,
                        "该对话正在处理中，请等待当前回合结束后再重试工具",
                    )
                    continue
                state = inflight_svc.mark_busy(
                    task_id,
                    conversation_id,
                    user_id=user["id"],
                    user_name=user_display_name,
                )
                await _broadcast_inflight(task_id, conversation_id, state)
                try:
                    await _handle_retry_tool_call(
                        websocket,
                        user,
                        task_id,
                        conversation_id,
                        tool_path,
                        tool_call_id,
                    )
                finally:
                    _release_conv_inflight(lock_fh)
                    inflight_svc.mark_idle(task_id, conversation_id)
                    await _broadcast_inflight(task_id, conversation_id, None)
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
                    # If user selected specific steps (partial approval), filter
                    # the plan text to only include those steps.
                    approved_steps = msg.get("approved_steps")  # list[int] | None
                    effective_plan = plan_text
                    if isinstance(approved_steps, list) and approved_steps:
                        effective_plan = _filter_plan_steps(plan_text, approved_steps)
                        synthetic = (
                            "(系统) 用户已部分批准方案，仅批准了以下步骤，请只执行被批准的步骤：\n\n"
                            f"[partially approved plan {plan_id}, steps: {approved_steps}]\n{effective_plan}"
                        )
                    else:
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
                    # Cross-worker flock — try a few times since the prior turn
                    # might still be releasing its lock in another worker.
                    lock_fh = None
                    for _ in range(20):
                        lock_fh = _try_acquire_conv_inflight(task_id, conversation_id)
                        if lock_fh is not None:
                            break
                        await asyncio.sleep(0.1)
                    if lock_fh is None:
                        await _send_error(
                            websocket,
                            ErrorCode.CONVERSATION_INFLIGHT,
                            "该对话另一端正在处理，无法注入审批后续",
                        )
                        continue
                    new_cancel = asyncio.Event()
                    new_task = asyncio.create_task(
                        _run_turn({"type": "user_message", "content": synthetic}, new_cancel, lock_fh)
                    )
                    _inflight_turns[inflight_key] = (new_task, new_cancel)
                continue
            if mtype != "user_message":
                await _send_error(websocket, "UNKNOWN_TYPE", f"unknown type {mtype}")
                continue

            # 只读视角：拒绝发送消息——前端已置灰输入框，这里是兜底防止
            # 用户绕过 UI 直接 ws.send。
            if is_viewer_ws:
                await _send_error(
                    websocket,
                    ErrorCode.PERMISSION_DENIED,
                    "您仅有查看权限，如需对话请申请编辑权限",
                )
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
                event_log.emit(
                    task_id=task_id,
                    conv_id=conversation_id,
                    source="ws",
                    event_type="inflight_blocked",
                    level="WARN",
                    code=ErrorCode.CONVERSATION_INFLIGHT,
                    message="rejected new message: same-worker turn still running",
                )
                continue

            # Cross-worker check: another uvicorn worker may be running this
            # conv. Non-blocking flock fails ⇒ reject without starting a turn.
            lock_fh = _try_acquire_conv_inflight(task_id, conversation_id)
            if lock_fh is None:
                await _send_error(
                    websocket,
                    ErrorCode.CONVERSATION_INFLIGHT,
                    "该对话正在处理中，请稍候或点中断后再发新消息",
                )
                event_log.emit(
                    task_id=task_id,
                    conv_id=conversation_id,
                    source="ws",
                    event_type="inflight_blocked",
                    level="WARN",
                    code=ErrorCode.CONVERSATION_INFLIGHT,
                    message="rejected new message: cross-worker flock held",
                )
                continue

            new_cancel = asyncio.Event()
            new_task = asyncio.create_task(_run_turn(msg, new_cancel, lock_fh))
            _inflight_turns[inflight_key] = (new_task, new_cancel)
    finally:
        # 关键行为：WS 断开不再取消 task。让它继续跑完、把结果写进 JSONL，
        # 用户返回任务页时能直接看到持久化后的完整历史。
        heartbeat_task.cancel()
        _unregister_subscriber(task_id, conversation_id, websocket)
        event_log.emit(
            task_id=task_id,
            conv_id=conversation_id,
            source="ws",
            event_type="ws_close",
            request_id=ws_id,
            message="ws closed",
        )
        try:
            await websocket.close()
        except Exception:
            pass


