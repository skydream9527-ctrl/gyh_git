"""WebSocket：多参与者流式对话（材料二 §6.2）。

路径：/api/v1/ws/tasks/{task_id}
鉴权：query 参数 token=<JWT>（浏览器 WS 不便带 header）。
事件协议：turn_start / text / tool_use / turn_done / error，均带 speaker。
Inflight guard：同一 task_id 单飞，避免并发回合互相打断。
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import decode_access_token
from app.core.storage import paths
from app.core.storage.jsonio import read_json
from app.services import agent_runtime

router = APIRouter(tags=["ws"])

# task_id -> 是否有回合进行中
_inflight: set[str] = set()


def _auth_ws(token: str) -> str | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    uid = payload.get("sub", "")
    if not uid or read_json(paths.user_profile(uid)) is None:
        return None
    return uid


@router.websocket("/ws/tasks/{task_id}")
async def ws_task(websocket: WebSocket, task_id: str, token: str = "") -> None:
    uid = _auth_ws(token)
    if uid is None:
        await websocket.close(code=4401)  # 未授权
        return

    await websocket.accept()

    try:
        while True:
            data: dict[str, Any] = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "message":
                user_message = data.get("content", "")
                mentioned = data.get("mentioned")

                # Inflight guard
                if task_id in _inflight:
                    await websocket.send_json({
                        "type": "error",
                        "message": "该任务已有回合进行中，请稍候",
                    })
                    continue

                _inflight.add(task_id)
                try:
                    # 在线程池跑同步生成器，逐事件推送
                    await _stream_turn(websocket, task_id, user_message, uid, mentioned)
                finally:
                    _inflight.discard(task_id)

    except WebSocketDisconnect:
        _inflight.discard(task_id)
    except Exception as e:
        _inflight.discard(task_id)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _stream_turn(
    websocket: WebSocket, task_id: str, user_message: str, uid: str, mentioned: str | None,
) -> None:
    """把同步生成器逐事件推到 WS（在 executor 中迭代避免阻塞事件循环）。"""
    loop = asyncio.get_event_loop()
    gen = agent_runtime.run_agent_turn(
        task_id, user_message=user_message, acting_user_id=uid, mentioned=mentioned,
    )

    def _next(g):
        try:
            return next(g)
        except StopIteration:
            return None

    while True:
        evt = await loop.run_in_executor(None, _next, gen)
        if evt is None:
            break
        await websocket.send_json(evt)
