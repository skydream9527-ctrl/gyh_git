"""WebSocket helper utilities — extracted from ws.py for maintainability.

Contains: send helpers, inflight registry, file-lock inflight guard,
subscriber registry (multi-tab broadcast), keepalive loop, and message
format conversion utilities.
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
from fastapi import WebSocket

from ...core.storage import get_paths

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
# Cross-worker status latency: the heartbeat re-reads the inflight JSON sidecar
# every _INFLIGHT_HEARTBEAT_SEC and pushes inflight_status on change, covering
# clients whose lock owner lives on another worker. Kept at 2s so cross-worker
# busy/idle transitions reach other workers within the 2s contract (Req 10.4,
# 10.6). The loop only does light work — a single inflight_svc.read_state JSON
# read plus a send-on-change — so a 2s cadence does not meaningfully thrash disk
# (the sidecar is a tiny file, typically served from page cache).
_INFLIGHT_HEARTBEAT_SEC = 2


# Application-layer keepalive cadence during a Turn. The WS_Endpoint sends a
# {"type":"keepalive"} frame every _WS_KEEPALIVE_SEC seconds while a Turn runs.
# This formalizes the ≤30s inter-frame contract (Req 7.1, 7.2): 20s sits safely
# inside the 30s ceiling (and inside the uvicorn --ws-ping-interval 30 window),
# so consecutive keepalive frames are always ≤30s apart and the first frame
# arrives within 30s of the Turn starting.
_WS_KEEPALIVE_SEC = 20.0


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


async def _send(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


async def _send_error(
    ws: WebSocket,
    error_code: str,
    message: str,
    *,
    code: int = 400,
    data=None,
) -> None:
    """Emit the uniform application error envelope over the WS transport.

    Mirrors `APIError.to_envelope` so WS errors carry the same four fields as
    HTTP errors: `{code, message, error_code, data}` (Req 12.1). `type` and
    `error_code` are retained so legacy clients keep parsing; `code`/`data`
    are additive and backward compatible.
    """
    await _send(
        ws,
        {
            "type": "error",
            "code": code,
            "message": message,
            "error_code": error_code,
            "data": data,
        },
    )


async def _ws_keepalive_loop(ws: WebSocket, interval: float = _WS_KEEPALIVE_SEC) -> None:
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
