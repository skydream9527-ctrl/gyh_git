"""Unified agent ReAct kernel.

This module is the single source of truth for the bounded ReAct loop. Before
this existed, the loop body was copy-pasted into two places:

    - ``api/v1/ws.py`` (the user-facing streaming loop), and
    - ``agent_runtime.run_agent_turn`` (the non-streaming sub-agent / bg loop).

The two copies drifted (parallel tools only existed in one, plan/human halts
only in the other, persistence targets differed), which made every change a
two-site edit. The kernel keeps ONE loop and pushes every site-specific concern
(streaming to a WebSocket vs. appending to a transcript JSONL, the Chinese
``run_event`` timeline, usage accounting, file-created notifications) behind an
``EventSink``.

Design contract
---------------
* The kernel never touches a WebSocket, never writes a JSONL, never knows about
  ``run_event`` labels. It only:
    1. calls ``llm_gateway.stream_chat``,
    2. collects text + ``tool_use`` blocks,
    3. dispatches tools via ``llm_gateway.run_tool_with_retry`` (parallel-safe
       reads fan out via ``asyncio.gather`` when ``parallel_tools=True``;
       everything else runs serially in original order),
    4. feeds ``tool_result`` blocks back, and
    5. emits semantic callbacks on the sink at every interesting point.
* Everything observable goes through ``EventSink``. A caller that wants nothing
  observed passes ``NullEventSink`` (or omits the sink entirely).
* ``run`` returns an ``AgentState`` snapshot; callers map it to whatever shape
  they need (``run_agent_turn`` maps it to its legacy dict contract; ws.py reads
  the halt fields to emit the right done-frame).

Behavioural parity with the old loops is locked by the existing
``tests/test_agent_runtime.py`` / ``tests/test_structured_error_integration.py``
/ ``tests/test_retry_controller.py`` suites (they drive ``run_agent_turn``,
which now delegates here).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.services.admin import sysconfig_svc
from app.services.llm import error_classifier, llm_gateway, tool_runner

# ============================================================
# Cancellation
# ============================================================


class CancelToken(Protocol):
    """Anything with an ``is_set()`` predicate works as a cancel signal.

    ``asyncio.Event`` satisfies this directly, so ws.py can pass its existing
    ``cancel_event`` unchanged. Contexts without cancellation (sub-agents, bg
    jobs) pass ``None`` and the kernel treats the turn as never-cancelled.
    """

    def is_set(self) -> bool: ...


def _cancelled(cancel: CancelToken | None) -> bool:
    return cancel is not None and cancel.is_set()


# ============================================================
# Loop state
# ============================================================


@dataclass
class ToolCall:
    """A single tool invocation within a round, plus its outcome once run."""

    id: str
    name: str
    input: dict
    parallel: bool = False
    started_at: str | None = None
    ended_at: str | None = None
    outcome: dict | None = None  # normalized {success, status, result, error}


@dataclass
class AgentState:
    """Mutable snapshot of one ``run`` invocation.

    ``messages`` is the live Anthropic-shaped conversation the kernel grows each
    round (assistant blocks + synthetic ``tool_result`` user turns). Callers may
    read it after the run to persist the final transcript.
    """

    messages: list[dict]
    final_text: str = ""
    stop_reason: str = "end_turn"
    rounds: int = 0
    usage_total: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    tool_uses_log: list[dict] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    # Counters surfaced to the ws fallback message ("已执行工具 N 步…").
    tool_attempt_count: int = 0
    tool_success_count: int = 0
    tool_failure_count: int = 0
    # Last normalized tool error (or LLM error) — drives structured-error output.
    last_error: dict | None = None
    # Terminal halt signals. Exactly one (at most) is set when the loop stops
    # early for a reason other than "no more tools" / "max rounds".
    aborted: bool = False
    plan_proposed: dict | None = None       # exit_plan_mode result payload
    human_intervention: dict | None = None  # request_human_input result payload

    def structured_error(self) -> dict:
        """Replicate ``run_agent_turn``'s failure-field derivation verbatim.

        A run "ended in failure" when the LLM stream errored, or it produced no
        answer text while a tool had failed. In those cases expose the last
        failure's ``error_type`` / ``recoverable`` / ``suggested_action`` so a
        parent agent can decide retry / switch / report (R6.3).
        """
        failed = self.stop_reason == "llm_error" or (not self.final_text and self.last_error is not None)
        if not failed:
            return {}
        err = self.last_error or {}
        if err.get("error_type") is not None:
            return {
                "error_type": err.get("error_type"),
                "recoverable": err.get("recoverable"),
                "suggested_action": err.get("suggested_action"),
            }
        cls = error_classifier.classify(err.get("code") or "LLM_ERROR")
        return {
            "error_type": cls["error_type"],
            "recoverable": cls["recoverable"],
            "suggested_action": cls["suggested_action"],
        }


# ============================================================
# Observation interface
# ============================================================


class EventSink(Protocol):
    """Observation surface for one ReAct run.

    Every method is async (WebSocket sends are async; JSONL writes go through
    ``asyncio.to_thread``) and MUST NOT raise — a misbehaving sink can degrade
    observability but must never abort the agent loop. ``BaseEventSink`` gives
    no-op defaults so a sink only overrides the hooks it cares about.

    Call order per round::

        round_started
        (text_delta | tool_args_delta)*
        assistant_message
        [ tool_started, ... (parallel group) ]
        [ tool_started ... tool_completed ] (serial group, interleaved)
        tool_completed*  (all calls, in original order)
        round_finished

    ``llm_error`` replaces ``assistant_message`` when the stream throws.
    ``run_finished`` fires exactly once after the loop exits.
    """

    async def round_started(self, *, round_idx: int, model: str, message_id: str) -> None: ...

    async def text_delta(self, *, message_id: str, delta: str) -> None: ...

    async def tool_args_delta(
        self, *, message_id: str, index: int, tool_call_id: str | None,
        tool_name: str | None, args_chunk: str,
    ) -> None: ...

    async def assistant_message(
        self, *, message_id: str, text: str, tool_uses: list[dict],
        usage: dict, stop_reason: str | None, round_idx: int,
    ) -> None: ...

    async def llm_error(self, *, round_idx: int, model: str, exc: BaseException) -> None: ...

    async def tool_started(self, *, call: ToolCall, round_idx: int) -> None: ...

    async def tool_completed(self, *, call: ToolCall, round_idx: int) -> None: ...

    async def round_finished(self, *, round_idx: int, state: AgentState) -> None: ...

    async def aborted(self, *, message_id: str, text: str, tool_uses: list[dict], usage: dict) -> None: ...

    async def run_finished(self, *, state: AgentState) -> None: ...


class BaseEventSink:
    """No-op implementation of every ``EventSink`` hook.

    Subclass and override only the hooks you need. All defaults are awaitable
    no-ops so the kernel can call the full protocol unconditionally.
    """

    async def round_started(self, *, round_idx, model, message_id) -> None:  # noqa: D102
        return None

    async def text_delta(self, *, message_id, delta) -> None:
        return None

    async def tool_args_delta(self, *, message_id, index, tool_call_id, tool_name, args_chunk) -> None:
        return None

    async def assistant_message(self, *, message_id, text, tool_uses, usage, stop_reason, round_idx) -> None:
        return None

    async def llm_error(self, *, round_idx, model, exc) -> None:
        return None

    async def tool_started(self, *, call, round_idx) -> None:
        return None

    async def tool_completed(self, *, call, round_idx) -> None:
        return None

    async def round_finished(self, *, round_idx, state) -> None:
        return None

    async def aborted(self, *, message_id, text, tool_uses, usage) -> None:
        return None

    async def run_finished(self, *, state) -> None:
        return None


class NullEventSink(BaseEventSink):
    """Explicit "observe nothing" sink for fire-and-forget runs."""


# ============================================================
# Helpers (moved verbatim from agent_runtime)
# ============================================================


def extract_written_filenames(result: Any) -> list[str]:
    """Best-effort extraction of workspace filenames from a side-effecting
    tool's *successful* result. Never raises.

    Tools report written files in a few shapes:
      * ``write_file`` → ``{"saved": True, "name": "report.md", ...}``
      * ``execute_python`` → ``{"registered_files": [{"relpath": "chart.png"}]}``
      * volcano / misc → ``{"file_name": "..."}``
      * generic list shapes → ``{"files_written": [...]}`` / ``{"files": [...]}``
    """
    names: list[str] = []
    if not isinstance(result, dict):
        return names
    try:
        for key in ("name", "file_name", "filename"):
            v = result.get(key)
            if isinstance(v, str) and v:
                names.append(v)
        for rf in result.get("registered_files") or []:
            if isinstance(rf, dict):
                v = rf.get("relpath") or rf.get("name") or rf.get("file_name")
                if isinstance(v, str) and v:
                    names.append(v)
        for key in ("files_written", "files"):
            for v in result.get(key) or []:
                if isinstance(v, str) and v:
                    names.append(v)
                elif isinstance(v, dict):
                    nv = v.get("name") or v.get("relpath") or v.get("file_name")
                    if isinstance(nv, str) and nv:
                        names.append(nv)
    except Exception:  # noqa: BLE001 - extraction is best-effort, never fatal
        return names
    return names


def _tool_result_block(call: ToolCall) -> dict:
    """Build the Anthropic ``tool_result`` block fed back to the model.

    Matches both legacy loops: success → result payload, failure → error
    payload, serialized to a string unless already a string; ``is_error`` set
    on failure.
    """
    outcome = call.outcome or {}
    success = outcome.get("success")
    payload = outcome.get("result") if success else outcome.get("error")
    body = payload if isinstance(payload, str) else json.dumps(payload or {}, ensure_ascii=False)
    block = {"type": "tool_result", "tool_use_id": call.id, "content": body}
    if not success:
        block["is_error"] = True
    return block


def _assistant_blocks(text: str, tool_uses: list[dict]) -> list[dict] | str:
    """Rebuild assistant content for the running message list."""
    if not tool_uses:
        return text
    blocks: list[dict] = []
    if text:
        blocks.append({"type": "text", "text": text})
    blocks.extend(tool_uses)
    return blocks


# ============================================================
# The loop
# ============================================================


async def run(
    *,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    ctx: dict,
    max_rounds: int,
    sink: EventSink | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    parallel_tools: bool = False,
    cancel: CancelToken | None = None,
    halt_on_plan: bool = True,
    halt_on_human_input: bool = True,
    raise_on_llm_error: bool = False,
    new_id=None,
    settings=None,
) -> AgentState:
    """Run a bounded ReAct loop and return the final :class:`AgentState`.

    Args:
        system_prompt / messages / tools / model / max_tokens: passed straight
            to ``llm_gateway.stream_chat``. ``messages`` is grown in place.
        ctx: tool-execution context (``task_id`` / ``user_id`` / ``agent_id`` /
            ``conversation_id`` / ``emit_event`` …) forwarded to
            ``tool_runner.execute_tool``.
        max_rounds: hard cap on ReAct rounds (loop runs ``range(max_rounds+1)``
            to mirror both legacy loops exactly).
        sink: observation surface; ``None`` ⇒ :class:`NullEventSink`.
        parallel_tools: when True, ``_meta.parallel_safe`` tools in a round fan
            out via ``asyncio.gather``; others stay serial. The sub-agent
            runtime keeps this False for deterministic audit ordering.
        cancel: cooperative cancel token checked between/within rounds.
        halt_on_plan / halt_on_human_input: stop the loop (without feeding
            results back to the LLM) when ``exit_plan_mode`` /
            ``request_human_input`` succeed.
        raise_on_llm_error: when True, re-raise an exception from the LLM stream
            after the sink has recorded it (the ws path wants the exception to
            reach its terminal error-frame handler). When False (default), the
            error is swallowed and surfaced via ``state.stop_reason ==
            "llm_error"`` + ``state.structured_error()`` (the sub-agent path).
        new_id: id factory for assistant message ids (defaults to uuid4 hex).
        settings: optional pre-fetched settings (avoids a repeat lookup).
    """
    import uuid

    from ...core.config import get_settings

    sink = sink or NullEventSink()
    s = settings if settings is not None else get_settings()
    if new_id is None:
        def new_id() -> str:  # noqa: E306
            return uuid.uuid4().hex
    sys_params = sysconfig_svc.get_system_params()
    parallel_enabled = bool(parallel_tools and getattr(s, "ICE_PARALLEL_TOOLS_ENABLED", False))

    state = AgentState(messages=messages)
    resolved_model = llm_gateway.resolve_model(model)

    for round_idx in range(max_rounds + 1):
        state.rounds = round_idx + 1

        if _cancelled(cancel):
            # Cancelled before this round produced anything. Mirror the old ws
            # loop's pre-round check: emit the "aborted" run_event (sink.aborted
            # with empty text skips the partial-persist), then stop.
            state.aborted = True
            await sink.aborted(message_id=new_id(), text="", tool_uses=[], usage={})
            return await _finish(sink, state)

        message_id = new_id()
        await sink.round_started(round_idx=round_idx, model=resolved_model, message_id=message_id)

        # ---- 1. LLM call -------------------------------------------------
        text_buf: list[str] = []
        tool_uses: list[dict] = []
        done_event: dict | None = None
        try:
            async for ev in llm_gateway.stream_chat(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools,
                model=resolved_model,
                max_tokens=max_tokens,
            ):
                if _cancelled(cancel):
                    break
                etype = ev.get("type")
                if etype == "text":
                    text_buf.append(ev["delta"])
                    await sink.text_delta(message_id=message_id, delta=ev["delta"])
                elif etype == "tool_use_delta":
                    await sink.tool_args_delta(
                        message_id=message_id,
                        index=ev.get("index", 0),
                        tool_call_id=ev.get("id"),
                        tool_name=ev.get("name"),
                        args_chunk=ev.get("args_chunk", ""),
                    )
                elif etype == "message_done":
                    done_event = ev
                    for block in ev.get("content") or []:
                        if block.get("type") == "tool_use":
                            tool_uses.append(block)
        except Exception as exc:  # noqa: BLE001 - surfaced via sink + state
            await sink.llm_error(round_idx=round_idx, model=resolved_model, exc=exc)
            state.stop_reason = "llm_error"
            if state.last_error is None:
                state.last_error = {"code": "LLM_ERROR", "message": str(exc)[:300]}
            # ws path re-raises so the handler emits its terminal error frame
            # (preserving the old inline behavior where an APIError propagated
            # as-is and any other exception was wrapped as GATEWAY_ERROR). The
            # sub-agent / bg path keeps raise_on_llm_error=False and instead
            # returns a state whose structured_error() describes the failure.
            if raise_on_llm_error:
                raise
            return await _finish(sink, state)

        text = "".join(text_buf)
        usage = (done_event or {}).get("usage") or {}
        state.usage_total["input_tokens"] += int(usage.get("input_tokens") or 0)
        state.usage_total["output_tokens"] += int(usage.get("output_tokens") or 0)
        state.stop_reason = (done_event or {}).get("stop_reason") or "end_turn"
        if text:
            state.final_text = text

        # ---- 2. Cancel mid-stream: persist partial, bail -----------------
        if _cancelled(cancel):
            await sink.aborted(message_id=message_id, text=text, tool_uses=tool_uses, usage=usage)
            state.aborted = True
            if text:
                state.final_text = text
            return await _finish(sink, state)

        await sink.assistant_message(
            message_id=message_id, text=text, tool_uses=tool_uses,
            usage=usage, stop_reason=state.stop_reason, round_idx=round_idx,
        )
        messages.append({"role": "assistant", "content": _assistant_blocks(text, tool_uses)})

        # ---- 3. Terminate? -----------------------------------------------
        if not tool_uses or round_idx == max_rounds:
            await sink.round_finished(round_idx=round_idx, state=state)
            break

        # ---- 4. Partition parallel / serial ------------------------------
        calls = [
            ToolCall(id=tu.get("id"), name=tu.get("name"), input=tu.get("input") or {})
            for tu in tool_uses
        ]
        parallel_idx: list[int] = []
        serial_idx: list[int] = []
        for i, call in enumerate(calls):
            meta = tool_runner.get_tool_meta(call.name or "")
            if parallel_enabled and meta.get("parallel_safe"):
                call.parallel = True
                parallel_idx.append(i)
            else:
                serial_idx.append(i)

        async def _run_one(i: int) -> None:
            call = calls[i]
            call.started_at = _now()

            async def _runner():
                return await tool_runner.execute_tool(call.name, call.input, ctx=ctx)

            timeout = llm_gateway.tool_timeout_for(call.name, sys_params)
            call.outcome = await llm_gateway.run_tool_with_retry(
                _runner,
                timeout=timeout,
                settings=s,
                audit_ctx={
                    "task_id": ctx.get("task_id"),
                    "conversation_id": ctx.get("conversation_id") or ctx.get("conv_id"),
                    "run_id": ctx.get("run_id") or ctx.get("subagent_run_id"),
                },
            )
            call.ended_at = _now()

        # Parallel group: announce all (so the UI shows them spinning together),
        # then gather. A gather exception degrades to a synthetic error outcome.
        for i in parallel_idx:
            calls[i].started_at = _now()
            await sink.tool_started(call=calls[i], round_idx=round_idx)
        if parallel_idx:
            gathered = await asyncio.gather(
                *[_run_one(i) for i in parallel_idx], return_exceptions=True
            )
            for i, res in zip(parallel_idx, gathered):
                if isinstance(res, Exception):
                    calls[i].outcome = {
                        "status": "error",
                        "success": False,
                        "error": {"error_code": "TOOL_EXCEPTION", "message": str(res)[:300]},
                    }
                    calls[i].ended_at = _now()

        # Serial group: announce + run one at a time, in original order.
        for i in serial_idx:
            calls[i].started_at = _now()
            await sink.tool_started(call=calls[i], round_idx=round_idx)
            await _run_one(i)

        # ---- 5. Outcomes + tool_result feedback (original order) ---------
        tool_results: list[dict] = []
        for call in calls:
            outcome = call.outcome or {"status": "error", "success": False, "error": {}}
            call.outcome = outcome
            state.tool_attempt_count += 1
            if outcome.get("success"):
                state.tool_success_count += 1
                meta = tool_runner.get_tool_meta(call.name)
                if (meta.get("side_effect") or "read") in ("write", "network"):
                    for fn in extract_written_filenames(outcome.get("result")):
                        if fn not in state.files_written:
                            state.files_written.append(fn)
            else:
                state.tool_failure_count += 1
                state.last_error = outcome.get("error") or {}

            state.tool_uses_log.append(
                {
                    "id": call.id,
                    "name": call.name,
                    "args": call.input,
                    "success": outcome.get("success", False),
                    "status": outcome.get("status"),
                    "result": outcome.get("result"),
                    "error": outcome.get("error"),
                }
            )
            await sink.tool_completed(call=call, round_idx=round_idx)
            tool_results.append(_tool_result_block(call))

            # Detect terminal tool signals (recorded; loop break decided below
            # so every tool_completed / audit fires first).
            if (
                halt_on_plan
                and call.name == "exit_plan_mode"
                and outcome.get("success")
            ):
                res = outcome.get("result")
                state.plan_proposed = res if isinstance(res, dict) else {"plan": True}
            if (
                halt_on_human_input
                and call.name == "request_human_input"
                and outcome.get("success")
                and isinstance(outcome.get("result"), dict)
                and outcome["result"].get("waiting_for_human")
            ):
                state.human_intervention = outcome["result"]

        messages.append({"role": "user", "content": tool_results})
        await sink.round_finished(round_idx=round_idx, state=state)

        if state.human_intervention is not None:
            state.stop_reason = "human_intervention"
            break
        if state.plan_proposed is not None:
            state.stop_reason = "plan_proposed"
            break

    return await _finish(sink, state)


async def _finish(sink: EventSink, state: AgentState) -> AgentState:
    await sink.run_finished(state=state)
    return state


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).isoformat()
