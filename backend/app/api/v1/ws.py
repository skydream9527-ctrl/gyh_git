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
from ...services import (
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
#
# This dict is per-process. With uvicorn --workers=N a second message landing on
# a different worker would slip past it, so we ALSO acquire a non-blocking
# advisory flock on a per-conversation lock file: cross-worker requests for the
# same conv_id observe each other through the kernel and get rejected the same
# way. Cross-worker `abort` is best-effort — only the worker running the turn
# can flip its cancel_event; others just refuse to start a competing turn.
_inflight_turns: dict[tuple[str, str], tuple[asyncio.Task, asyncio.Event]] = {}


def is_inflight(task_id: str, conv_id: str) -> bool:
    """Return True iff a turn for (task_id, conv_id) is currently running in this worker.

    跨 uvicorn worker 仅可见本 worker 的 inflight。前端用这个信号给对话角标
    显示 ⏳，避免切走后用户以为后台任务停了。
    """
    entry = _inflight_turns.get((task_id, conv_id))
    return entry is not None and not entry[0].done()


async def cancel_inflight_turn(task_id: str, conv_id: str) -> bool:
    """强制终止同 worker 内 (task_id, conv_id) 回合，等待任务清理完毕。

    返回 True = 找到并已结束，False = 当前 worker 内没在跑该回合。

    分三档：
      1. set cancel_event（合作式）— LLM stream 下一拍会观察到并退出
      2. task.cancel()（强制式）— 任务挂在 await 时立即抛 CancelledError
      3. 等任务跑完 finally（释放 inflight flock）；超时则强行 pop registry，
         以防卡死的 task 永远占着锁让后续消息全部被 INFLIGHT 拒掉。

    跨 uvicorn worker 部署下只能取消落在本 worker 的回合；其余 worker 的回合靠
    自身 WS 收到 abort 消息时 set。HTTP-level abort 兜底用，单 worker 场景可达。
    """
    entry = _inflight_turns.get((task_id, conv_id))
    if entry is None:
        return False
    task, cancel = entry
    cancel.set()
    if not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            pass
    # 兜底：task 自身 finally 里会用 `is cancel` 检查后 pop；这里强制 pop 防止
    # 卡死的 task 永远占着 registry 让所有新消息被 INFLIGHT 拒绝。
    cur = _inflight_turns.get((task_id, conv_id))
    if cur is not None and cur[1] is cancel:
        _inflight_turns.pop((task_id, conv_id), None)
    return True


# Per-conv WebSocket subscribers (same-worker only). When user A's turn starts
# we mark_busy + broadcast `inflight_status` to every WS already connected to
# this conv in this worker, so user B's send button greys out within ms. For
# users on a *different* worker we rely on the per-WS heartbeat below — it
# re-reads the JSON state file every HEARTBEAT_SEC and sends if changed.
_conv_subscribers: dict[tuple[str, str], set[WebSocket]] = {}
_INFLIGHT_HEARTBEAT_SEC = 10


def _register_subscriber(task_id: str, conv_id: str, ws: WebSocket) -> None:
    _conv_subscribers.setdefault((task_id, conv_id), set()).add(ws)


def _unregister_subscriber(task_id: str, conv_id: str, ws: WebSocket) -> None:
    s = _conv_subscribers.get((task_id, conv_id))
    if not s:
        return
    s.discard(ws)
    if not s:
        _conv_subscribers.pop((task_id, conv_id), None)


def _inflight_status_payload(state: dict | None) -> dict:
    if not state:
        return {"type": "inflight_status", "busy": False, "user": None, "started_at": None}
    return {
        "type": "inflight_status",
        "busy": True,
        "user": {
            "id": state.get("user_id"),
            "name": state.get("user_name") or "用户",
        },
        "started_at": state.get("started_at"),
    }


async def _broadcast_inflight(task_id: str, conv_id: str, state: dict | None) -> None:
    payload = _inflight_status_payload(state)
    for sub in list(_conv_subscribers.get((task_id, conv_id), ())):
        try:
            await sub.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            # 死连接清理交给该 WS 自己的 finally；这里别中断广播
            pass


def _state_signature(state: dict | None) -> tuple:
    if not state:
        return ("idle",)
    return ("busy", state.get("user_id"), state.get("started_at"))


async def _inflight_heartbeat(ws: WebSocket, task_id: str, conv_id: str) -> None:
    """每 N 秒读 JSON 状态文件，状态变化时推送 inflight_status。补全 same-worker
    广播覆盖不到的场景（多 worker 部署 / 锁主在另一个 worker 上）。"""
    last_sig: tuple | None = None
    try:
        while True:
            state = inflight_svc.read_state(task_id, conv_id)
            sig = _state_signature(state)
            if sig != last_sig:
                last_sig = sig
                try:
                    await ws.send_text(json.dumps(_inflight_status_payload(state), ensure_ascii=False))
                except Exception:
                    return
            await asyncio.sleep(_INFLIGHT_HEARTBEAT_SEC)
    except asyncio.CancelledError:
        return


def _conv_inflight_lock_path(task_id: str, conv_id: str):
    paths = get_paths()
    p = paths.task_dir(task_id) / "conversations" / f"{conv_id}.inflight.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _try_acquire_conv_inflight(task_id: str, conv_id: str) -> IO | None:
    """Cross-worker conv-level lock. None ⇒ another worker is mid-turn."""
    fh = open(_conv_inflight_lock_path(task_id, conv_id), "a+")
    try:
        portalocker.lock(fh, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.LockException:
        fh.close()
        return None
    return fh


def _release_conv_inflight(fh: IO | None) -> None:
    if fh is None:
        return
    try:
        portalocker.unlock(fh)
    finally:
        fh.close()


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

    # 推导角色：viewer 允许进 WS（看历史 + 收 stream），但不允许 send user_message
    from ...core.deps import TaskRole as _TaskRole, derive_task_role
    from ...core.storage import read_json
    _paths = get_paths()
    _meta = read_json(_paths.task_meta(task_id)) or {}
    _collabs = read_json(_paths.task_collaborators(task_id), default=[]) or []
    ws_role = derive_task_role(
        _meta, _collabs, user_id=user["id"], is_admin=bool(user.get("is_admin"))
    )
    is_viewer_ws = ws_role == _TaskRole.VIEWER

    if chosen_proto:
        await websocket.accept(subprotocol=chosen_proto)
    else:
        await websocket.accept()
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


async def _send(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


async def _send_error(ws: WebSocket, code: str, message: str) -> None:
    await _send(ws, {"type": "error", "error_code": code, "message": message})


async def _ws_keepalive_loop(ws: WebSocket, interval: float = 20.0) -> None:
    """每 interval 秒发一帧应用层 keepalive，给反代/底层 ws 一个非 idle 信号。

    解决场景：LLM stream 静默期、tool 执行期、history 压缩期——这些时段下行
    没有自然字节流出，nginx/cloudflare/ALB 这类反代会按 idle timeout (60-100s)
    主动切连接，前端就看到 STREAM_INTERRUPTED。

    前端 handleEvent 的 switch 没有匹配 keepalive，会被静默忽略——发了不会
    污染 partial / phase / errorCode。

    注意：这只能治"通道 idle"。如果 event loop 真被同步 IO 阻塞 30s+，
    keepalive 自身也调度不上——那是 _to_api_messages / append_jsonl 这种
    sync 调用要 to_thread 化的事，见 step 3。
    """
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                await ws.send_text('{"type":"keepalive"}')
            except Exception:
                return
    except asyncio.CancelledError:
        return


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
    await task_svc.touch_task(task_id, last_message_preview=content)

    if not s.llm_enabled:
        await _send_run_event("failed", "模型服务未配置", status="error")
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
    # keepalive sidecar：每 20s 发一帧 {"type":"keepalive"}，给反代和底层 ws
    # 协议一个非 idle 信号。多会话并行时——某个会话在压缩/工具/慢 LLM
    # 期间没有自然下行字节，原本会让 ws ping 超时被误关。
    keepalive_task = asyncio.create_task(_ws_keepalive_loop(ws))
    try:
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
                outcome = await llm_gateway.run_tool_with_timeout(_runner, timeout=timeout)
                return llm_gateway.normalize_tool_outcome(outcome)

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
                # `task_svc.load_conversation_messages` enriches persisted
                # tool_uses with status/result/error for the UI; never pass
                # those audit fields back to the model as tool_use blocks.
                blocks.append(
                    {
                        k: tu.get(k)
                        for k in ("type", "id", "name", "input")
                        if tu.get(k) is not None
                    }
                )
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
