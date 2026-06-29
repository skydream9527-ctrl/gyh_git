"""WebSocket :class:`agent_kernel.EventSink` for the user-facing streaming loop.

This sink reproduces — frame for frame — every WebSocket message, ``run_event``
timeline entry, ``event_log`` record and JSONL persistence call that
``api/v1/ws.py``'s ``_handle_user_message`` used to emit inline inside its
copy of the ReAct loop. Wiring it into ``agent_kernel.run`` lets ws.py drop its
duplicated loop body while keeping the streaming protocol byte-identical.

It lives under ``api/v1`` (not ``services``) because it depends on the live
``WebSocket`` object and the ws-frame protocol, which are API-layer concerns.

What stays in the handler (NOT here)
-------------------------------------
The pre-amble (history load, compaction, prompt/tool build, ``agent_typing``
start, keepalive) and the post-amble (empty-final fallback, the terminal
``agent_message_done`` frame, plan/human/abort done-frames, ``agent_typing``
stop, task-status reset) remain in ``_handle_user_message``. The kernel sets
``state.aborted`` / ``state.plan_proposed`` / ``state.human_intervention`` /
``state.final_text`` / ``state.tool_attempt_count`` and exposes
``sink.files_created`` so the handler can drive those terminal frames exactly as
before.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.services.agent.agent_kernel import BaseEventSink

from ...core.storage import append_jsonl
from ...services import (
    conversation_svc,
    event_log,
    tool_runner,
    usage_svc,
)

log = logging.getLogger("ws")


# Estimated execution times and user-facing progress messages for known slow
# tools. Fast tools (<1s) get no hint so the UI falls through to a generic
# "执行中" label without a timer.
_TOOL_PROGRESS_MAP: dict[str, tuple[str, int]] = {
    "kyuubi_query": ("正在执行 SQL 查询…", 15),
    "execute_python": ("Python 沙箱执行中…", 20),
    "feishu_publish": ("正在发布到飞书…", 10),
    "feishu_send_message": ("正在发送飞书消息…", 5),
    "feishu_upload_image": ("正在上传图片到飞书…", 8),
    "spawn_subagent": ("子 Agent 正在执行…", 30),
    "run_background": ("后台任务已启动…", 5),
    "data_platform_call": ("正在调用数据平台…", 10),
    "volcano_abtest_analyze": ("火山实验分析中…", 20),
}


def _tool_progress_hint(tool_name: str) -> tuple[str, int | None]:
    """Return (progress_hint, estimated_sec) for a tool, or (generic, None)."""
    entry = _TOOL_PROGRESS_MAP.get(tool_name)
    if entry:
        return entry
    return ("执行中…", None)


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class WebSocketEventSink(BaseEventSink):
    """Streaming sink bound to one WebSocket turn.

    Args mirror the locals ``_handle_user_message`` already has in scope, so the
    migration is a near-mechanical "pass these in, delete the loop body".
    """

    def __init__(
        self,
        *,
        ws,
        send,            # async (ws, dict) -> None        (the module-level _send)
        send_run_event,  # async (...) -> None             (the closure _send_run_event)
        conv_path,
        tool_path,
        agent_id: str,
        run_id: str,
        model_id: str,
        user: dict,
        task_id: str,
        conversation_id: str,
    ) -> None:
        self._ws = ws
        self._send = send
        self._send_run_event = send_run_event
        self._conv_path = conv_path
        self._tool_path = tool_path
        self._agent_id = agent_id
        self._run_id = run_id
        self._model_id = model_id
        self._user = user
        self._task_id = task_id
        self._conversation_id = conversation_id
        # Exposed back to the handler for the terminal agent_message_done frame.
        self.files_created: list[dict] = []

    # ---- LLM round -----------------------------------------------------

    async def round_started(self, *, round_idx, model, message_id) -> None:
        # The handler-supplied model_id is what the loop historically displayed
        # (kernel's resolved model is identical for the streaming path).
        await self._send_run_event(
            "llm",
            "模型生成中",
            detail=f"第 {round_idx + 1} 轮 · {self._model_id}",
            payload={"round": round_idx + 1, "model": self._model_id},
        )

    async def text_delta(self, *, message_id, delta) -> None:
        await self._send(
            self._ws,
            {"type": "agent_message", "message_id": message_id, "content": delta},
        )

    async def tool_args_delta(self, *, message_id, index, tool_call_id, tool_name, args_chunk) -> None:
        await self._send(
            self._ws,
            {
                "type": "tool_call_preview",
                "message_id": message_id,
                "index": index,
                "id": tool_call_id,
                "name": tool_name,
                "args_chunk": args_chunk,
            },
        )

    async def assistant_message(self, *, message_id, text, tool_uses, usage, stop_reason, round_idx) -> None:
        await self._send_run_event(
            "llm",
            "模型生成完成",
            status="done",
            detail=f"{len(text)} 字 · {len(tool_uses)} 个工具",
            payload={"round": round_idx + 1, "tool_count": len(tool_uses)},
        )
        record = {
            "id": message_id,
            "role": "assistant",
            "content": text,
            "tool_uses": tool_uses,
            "agent_id": self._agent_id,
            "run_id": self._run_id,
            "stop_reason": stop_reason,
            "usage": usage or {},
            "created_at": _now(),
        }
        await asyncio.to_thread(append_jsonl, self._conv_path, record)
        await conversation_svc.touch_last_message(
            task_id=self._task_id, conv_id=self._conversation_id
        )
        # FTS index assistant message (fire-and-forget)
        if text and len(text) >= 5:
            async def _fts_assist():
                try:
                    from ...services.task import fts_svc
                    await fts_svc.ensure_fts_table()
                    await fts_svc.index_message(
                        task_id=self._task_id,
                        conversation_id=self._conversation_id,
                        message_id=message_id,
                        role="assistant",
                        content=text,
                        created_at=record["created_at"],
                    )
                except Exception:
                    pass
            asyncio.create_task(_fts_assist())
        try:
            await usage_svc.record_usage(
                user_id=self._user["id"],
                agent_id=self._agent_id,
                task_id=self._task_id,
                conversation_id=self._conversation_id,
                model=self._model_id,
                input_tokens=int((usage or {}).get("input_tokens") or 0),
                output_tokens=int((usage or {}).get("output_tokens") or 0),
                success=True,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("record_usage failed: %s", exc)

    async def aborted(self, *, message_id, text, tool_uses, usage) -> None:
        # Persist whatever was generated before the cancel so the user can
        # follow up. The terminal abort frames are emitted by the handler.
        await self._send_run_event("aborted", "用户已中断执行", status="aborted")
        if text or tool_uses:
            await asyncio.to_thread(
                append_jsonl,
                self._conv_path,
                {
                    "id": message_id,
                    "role": "assistant",
                    "content": text,
                    "tool_uses": tool_uses,
                    "agent_id": self._agent_id,
                    "stop_reason": "user_aborted",
                    "usage": usage or {},
                    "created_at": _now(),
                },
            )
            await conversation_svc.touch_last_message(
                task_id=self._task_id, conv_id=self._conversation_id
            )

    async def llm_error(self, *, round_idx, model, exc) -> None:
        # Mirror the inline gateway-error event_log record. The handler re-raises
        # as APIError(502) for the terminal error frame; the kernel surfaces the
        # error via state, so here we only record the structured event.
        event_log.emit(
            task_id=self._task_id,
            conv_id=self._conversation_id,
            run_id=self._run_id,
            source="llm_gateway",
            event_type="gateway_error",
            level="ERROR",
            code="GATEWAY_ERROR",
            message=f"{type(exc).__name__}: {str(exc)[:300]}",
            payload={"model": self._model_id, "round": round_idx},
        )

    # ---- Tools ---------------------------------------------------------

    async def tool_started(self, *, call, round_idx) -> None:
        # Provide progress hints for known slow tools so the UI shows a
        # descriptive message and estimated duration while executing.
        progress_hint, estimated_sec = _tool_progress_hint(call.name)
        await self._send_run_event(
            "tool",
            f"开始执行 {tool_runner.get_display_name(call.name)}",
            detail="并行执行" if call.parallel else None,
            payload={"tool_call_id": call.id, "tool_name": call.name},
        )
        await self._send(
            self._ws,
            {
                "type": "tool_call_start",
                "tool_call_id": call.id,
                "tool_name": call.name,
                "display_name": tool_runner.get_display_name(call.name),
                "arguments": call.input or {},
                "progress_hint": progress_hint,
                "estimated_sec": estimated_sec,
            },
        )

    async def tool_completed(self, *, call, round_idx) -> None:
        outcome = call.outcome or {}
        success = outcome.get("success")
        await self._send_run_event(
            "tool",
            f"{tool_runner.get_display_name(call.name)} 执行结束",
            status="done" if success else "error",
            detail=str(outcome.get("status") or ""),
            payload={"tool_call_id": call.id, "tool_name": call.name},
        )
        await self._send(
            self._ws,
            {
                "type": "tool_call_done",
                "tool_call_id": call.id,
                "tool_name": call.name,
                "status": outcome.get("status"),
                "success": success,
                "result": outcome.get("result"),
                "error": outcome.get("error"),
            },
        )
        if not success:
            err = outcome.get("error") or {}
            err_code = (err.get("error_code") if isinstance(err, dict) else None) or "TOOL_ERROR"
            err_msg = (err.get("message") if isinstance(err, dict) else str(err)) or "tool failed"
            event_log.emit(
                task_id=self._task_id,
                conv_id=self._conversation_id,
                run_id=self._run_id,
                source="tool_runner",
                event_type="tool_error",
                level="WARN",
                code=err_code,
                message=f"{call.name}: {err_msg}",
                payload={"tool_call_id": call.id, "status": outcome.get("status")},
            )
        if (
            call.name == "write_file"
            and success
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
            self.files_created.append(file_meta)
            await self._send(self._ws, {"type": "file_created", "file": file_meta})
        await asyncio.to_thread(
            append_jsonl,
            self._tool_path,
            {
                "id": call.id,
                "tool_name": call.name,
                "arguments": call.input or {},
                "status": outcome.get("status"),
                "success": success,
                "result": outcome.get("result"),
                "error": outcome.get("error"),
                "started_at": call.started_at,
                "ended_at": call.ended_at,
            },
        )
