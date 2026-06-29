"""Concrete :class:`agent_kernel.EventSink` implementations for non-streaming
contexts (sub-agents, background jobs, the scheduler).

The user-facing WebSocket sink lives in ``api/v1/ws_event_sink.py`` because it
depends on the live ``WebSocket`` object and the ws-frame protocol; keeping it
out of the services layer avoids an import edge from services → api.

``TranscriptEventSink`` reproduces, byte-for-byte, the JSONL records and
``event_log`` events that ``agent_runtime.run_agent_turn`` used to write inline,
so audit transcripts produced before and after the kernel refactor are
identical.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.services.storage import event_log

from ...core.storage import append_jsonl
from .agent_kernel import BaseEventSink


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class TranscriptEventSink(BaseEventSink):
    """Append-only audit sink used by ``run_agent_turn``.

    Writes the same three transcript record shapes the legacy loop wrote:
      * ``{"event": "assistant", round, text, tool_uses, stop_reason, usage}``
      * ``{"event": "tool_call", id, name, args, success, status, result, error}``
      * ``{"event": "llm_error", at, message}``  (on stream failure)

    and emits the ``sub_run_llm_error`` ``event_log`` event on LLM failure. The
    ``sub_run_start`` / ``sub_run_end`` events stay in ``run_agent_turn`` because
    they bracket the whole turn, not the per-round loop.

    ``transcript_sink=None`` is allowed (bg/sub contexts that only want the
    ``event_log`` side-effects), so every write is guarded.
    """

    def __init__(
        self,
        *,
        transcript_sink: Path | None,
        task_id: str | None = None,
        conv_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        self._sink = transcript_sink
        self._task_id = task_id
        self._conv_id = conv_id
        self._run_id = run_id

    def _append(self, record: dict) -> None:
        if self._sink is None:
            return
        try:
            append_jsonl(self._sink, record)
        except Exception:  # noqa: BLE001 - audit writes must never break the loop
            pass

    async def assistant_message(self, *, message_id, text, tool_uses, usage, stop_reason, round_idx) -> None:
        self._append(
            {
                "event": "assistant",
                "at": _now(),
                "round": round_idx,
                "text": text,
                "tool_uses": tool_uses,
                "stop_reason": stop_reason,
                "usage": usage,
            }
        )

    async def tool_completed(self, *, call, round_idx) -> None:
        outcome = call.outcome or {}
        self._append(
            {
                "event": "tool_call",
                "at": _now(),
                "id": call.id,
                "name": call.name,
                "args": call.input,
                "success": outcome.get("success", False),
                "status": outcome.get("status"),
                "result": outcome.get("result"),
                "error": outcome.get("error"),
            }
        )

    async def llm_error(self, *, round_idx, model, exc) -> None:
        self._append({"event": "llm_error", "at": _now(), "message": str(exc)[:500]})
        event_log.emit(
            task_id=self._task_id,
            conv_id=self._conv_id,
            run_id=self._run_id,
            source="agent_runtime",
            event_type="sub_run_llm_error",
            level="ERROR",
            code="LLM_ERROR",
            message=f"{type(exc).__name__}: {str(exc)[:300]}",
            payload={"round": round_idx, "model": model},
        )
