"""Minimal agent runtime — non-streaming-to-user ReAct loop used by sub-agents
and background jobs.

The main WebSocket path in `api/v1/ws.py` keeps its own streaming loop (wired
directly to the frontend); this runtime is for contexts where there is no live
WS to pump events to:

    - spawn_subagent tool: main agent delegates to a bounded child.
    - run_background tool: deferred task executed by bg_task_svc / scheduler.

It internally consumes `llm_gateway.stream_chat` (same as main loop) so tool
calling and tool_use extraction work identically. Every LLM turn and tool
call is appended to `transcript_sink` (a JSONL path) for audit.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.storage import append_jsonl
from . import llm_gateway, tool_runner


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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
            "tool_uses_log": [ {id, name, args, success, result}... ],
            "stop_reason": str,
            "rounds": int,
            "usage_total": {input_tokens, output_tokens},
        }
    """
    api_messages = list(initial_messages)
    tool_uses_log: list[dict] = []
    usage_total = {"input_tokens": 0, "output_tokens": 0}
    final_text = ""
    stop_reason = "end_turn"
    resolved_model = llm_gateway.resolve_model(model)
    last_round = 0

    for round_idx in range(max_rounds + 1):
        last_round = round_idx
        text_buf: list[str] = []
        tool_uses: list[dict] = []
        done_event: dict | None = None

        try:
            async for ev in llm_gateway.stream_chat(
                system_prompt=system_prompt,
                messages=api_messages,
                tools=tools,
                model=resolved_model,
            ):
                if ev["type"] == "text":
                    text_buf.append(ev["delta"])
                elif ev["type"] == "message_done":
                    done_event = ev
                    for block in ev.get("content") or []:
                        if block.get("type") == "tool_use":
                            tool_uses.append(block)
        except Exception as exc:
            if transcript_sink is not None:
                append_jsonl(transcript_sink, {"event": "llm_error", "at": _now(), "message": str(exc)[:500]})
            stop_reason = "llm_error"
            break

        text = "".join(text_buf)
        usage = (done_event or {}).get("usage") or {}
        usage_total["input_tokens"] += int(usage.get("input_tokens") or 0)
        usage_total["output_tokens"] += int(usage.get("output_tokens") or 0)
        stop_reason = (done_event or {}).get("stop_reason") or "end_turn"

        if transcript_sink is not None:
            append_jsonl(
                transcript_sink,
                {
                    "event": "assistant",
                    "at": _now(),
                    "round": round_idx,
                    "text": text,
                    "tool_uses": tool_uses,
                    "stop_reason": stop_reason,
                    "usage": usage,
                },
            )
        if text:
            final_text = text

        if tool_uses:
            blocks: list[dict] = []
            if text:
                blocks.append({"type": "text", "text": text})
            blocks.extend(tool_uses)
            api_messages.append({"role": "assistant", "content": blocks})
        else:
            api_messages.append({"role": "assistant", "content": text})

        if not tool_uses or round_idx == max_rounds:
            break

        # Dispatch tools (serial inside sub-runtime — parallelism is only in
        # the main loop to keep this one deterministic for audit).
        tool_results: list[dict] = []
        saw_exit_plan_mode = False
        for tu in tool_uses:
            tu_id = tu.get("id")
            tu_name = tu.get("name")
            tu_input = tu.get("input") or {}

            async def _runner(_name=tu_name, _input=tu_input):
                return await tool_runner.execute_tool(_name, _input, ctx=ctx)

            outcome = await llm_gateway.run_tool_with_timeout(_runner)
            entry = {
                "id": tu_id,
                "name": tu_name,
                "args": tu_input,
                "success": outcome.get("success", False),
                "status": outcome.get("status"),
                "result": outcome.get("result"),
                "error": outcome.get("error"),
            }
            tool_uses_log.append(entry)
            if transcript_sink is not None:
                append_jsonl(transcript_sink, {"event": "tool_call", "at": _now(), **entry})

            if tu_name == "exit_plan_mode" and outcome.get("success"):
                saw_exit_plan_mode = True

            payload = outcome.get("result") if outcome.get("success") else outcome.get("error")
            body = payload if isinstance(payload, str) else json.dumps(payload or {}, ensure_ascii=False)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": body,
                    **({"is_error": True} if not outcome.get("success") else {}),
                }
            )
        api_messages.append({"role": "user", "content": tool_results})

        # exit_plan_mode is terminal: user must approve before we re-invoke.
        if saw_exit_plan_mode:
            stop_reason = "plan_proposed"
            break

    return {
        "final_text": final_text,
        "tool_uses_log": tool_uses_log,
        "stop_reason": stop_reason,
        "rounds": last_round + 1,
        "usage_total": usage_total,
    }
