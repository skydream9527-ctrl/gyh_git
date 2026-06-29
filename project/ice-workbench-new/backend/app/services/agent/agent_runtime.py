"""Minimal agent runtime — non-streaming-to-user ReAct loop used by sub-agents
and background jobs.

The main WebSocket path in `api/v1/ws.py` keeps its own streaming sink (wired
directly to the frontend); this runtime is for contexts where there is no live
WS to pump events to:

    - spawn_subagent tool: main agent delegates to a bounded child.
    - run_background tool: deferred task executed by bg_task_svc / scheduler.

Since the P-A kernel refactor this module is a thin adapter: it delegates the
ReAct loop to `agent_kernel.run` (the single shared loop, also used by ws.py),
plugging in a `TranscriptEventSink` so every LLM turn and tool call is appended
to `transcript_sink` (a JSONL path) for audit. The public `run_agent_turn`
signature and return shape are unchanged — locked by tests/test_agent_runtime,
tests/test_structured_error_integration and tests/test_retry_controller.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

# Re-exported so existing tests / callers can monkeypatch these module
# singletons via ``agent_runtime.<name>``. They are the SAME module objects the
# kernel imports, so patching e.g. ``agent_runtime.tool_runner.execute_tool``
# transparently affects ``agent_kernel``'s dispatch.
from app.services.admin import sysconfig_svc
from app.services.llm import llm_gateway, tool_runner
from app.services.storage import event_log

from . import agent_kernel
from .agent_event_sinks import TranscriptEventSink


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# Re-exported for backwards compatibility: some callers / tests import this
# helper from agent_runtime. The implementation now lives in the kernel.
extract_written_filenames = agent_kernel.extract_written_filenames
_extract_written_filenames = agent_kernel.extract_written_filenames


async def run_agent_turn(
    *,
    system_prompt: str,
    initial_messages: list[dict],
    tools: list[dict],
    ctx: dict,
    max_rounds: int,
    model: str | None = None,
    max_tokens: int = 2048,
    transcript_sink: Path | None = None,
) -> dict:
    """Run a bounded ReAct loop and return the final text + statistics.

    Returns:
        {
            "final_text": str,
            "tool_uses_log": [ {id, name, args, success, status, result, error}... ],
            "stop_reason": str,
            "rounds": int,
            "usage_total": {input_tokens, output_tokens},
            "files_written": [str, ...],   # files written to the workspace via
                                           # side-effecting tools; [] if none.
            # Only present WHEN the run ended in failure:
            "error_type": str,
            "recoverable": bool,
            "suggested_action": str,
        }
    """
    resolved_model = llm_gateway.resolve_model(model)

    # ctx 由调用方注入（spawn_subagent / run_background）；带上 task_id / run_id
    # 让 events 时间轴能定位到具体子任务。run_id 不存在时只记 task_id。
    _evt_task_id = (ctx or {}).get("task_id")
    _evt_run_id = (ctx or {}).get("run_id") or (ctx or {}).get("subagent_run_id")
    _evt_conv_id = (ctx or {}).get("conversation_id")
    event_log.emit(
        task_id=_evt_task_id,
        conv_id=_evt_conv_id,
        run_id=_evt_run_id,
        source="agent_runtime",
        event_type="sub_run_start",
        message=f"model={resolved_model} max_rounds={max_rounds}",
    )

    sink = TranscriptEventSink(
        transcript_sink=transcript_sink,
        task_id=_evt_task_id,
        conv_id=_evt_conv_id,
        run_id=_evt_run_id,
    )

    # Serial tool dispatch (parallel_tools=False) keeps sub-run audit ordering
    # deterministic — parallelism is reserved for the main ws loop.
    #
    # max_tokens is intentionally NOT forwarded: the pre-kernel loop never
    # passed it to stream_chat, so the gateway default (ICE_LLM_MAX_OUTPUT_TOKENS,
    # 16384) was always in effect. Callers pass 2048/4096 but it was historically
    # a no-op; forwarding it now would silently truncate long sub-agent outputs.
    # Preserve that behavior here (parity); revisit as a separate, deliberate fix.
    state = await agent_kernel.run(
        system_prompt=system_prompt,
        messages=list(initial_messages),
        tools=tools,
        ctx=ctx,
        max_rounds=max_rounds,
        sink=sink,
        model=model,
        max_tokens=None,
        parallel_tools=False,
        halt_on_plan=True,
        halt_on_human_input=True,
    )

    # llm_error 已由 sink.llm_error 以 ERROR 级别 emit 过 sub_run_llm_error，这里 INFO 即可。
    event_log.emit(
        task_id=_evt_task_id,
        conv_id=_evt_conv_id,
        run_id=_evt_run_id,
        source="agent_runtime",
        event_type="sub_run_end",
        message=f"stop={state.stop_reason} rounds={state.rounds} tools={len(state.tool_uses_log)}",
        payload={
            "input_tokens": state.usage_total["input_tokens"],
            "output_tokens": state.usage_total["output_tokens"],
        },
    )

    return {
        "final_text": state.final_text,
        "tool_uses_log": state.tool_uses_log,
        "stop_reason": state.stop_reason,
        "rounds": state.rounds,
        "usage_total": state.usage_total,
        "files_written": state.files_written,
        **state.structured_error(),
    }
