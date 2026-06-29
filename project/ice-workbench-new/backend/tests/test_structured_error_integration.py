"""Integration tests for structured-tool-error-handling (Task 7).

These exercise the end-to-end wiring (avoiding real LLM/CLI) of two flows:

* 7.1 — a recoverable tool failure is retried exactly once and ultimately
  succeeds when the Retry_Gate is on. Driven through the shared
  ``llm_gateway.run_tool_with_retry`` helper resolving its settings from the
  real ``get_settings`` path (monkey-patched gate-on), so the integration
  covers settings resolution + normalize + classify + retry + backoff.
  _Requirements: 4.3, 4.10_

* 7.2 — a sub-agent run that ends in failure returns BOTH ``files_written``
  (from a successful side-effecting tool) AND the structured error fields
  (``error_type`` / ``recoverable`` / ``suggested_action``) from the last
  failed tool, driven through the real ``agent_runtime.run_agent_turn`` loop
  with stream_chat / tool dispatch fully mocked.
  _Requirements: 6.1, 6.3_

No real LLM or CLI is touched: stream_chat, tool execution, settings and the
audit sink are all stubbed.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import AsyncIterator
from unittest import mock

import pytest

from app.services import agent_runtime, llm_gateway


# ---------------------------------------------------------------------------
# 7.1 — recoverable failure retried once then succeeds (R4.3, R4.10)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recoverable_failure_is_retried_once_then_succeeds(monkeypatch):
    """A tool that fails the first time with a recoverable error
    (``KYUUBI_CONNECTION_ERROR`` → transient/recoverable) and succeeds on the
    second attempt is automatically retried exactly once when the Retry_Gate is
    on, and the helper returns the successful retry outcome.

    Validates: Requirements 4.3, 4.10
    """
    # Gate ON, zero backoff so the test runs fast. Resolved via the real
    # get_settings path (settings arg omitted below).
    monkeypatch.setattr(
        llm_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            ICE_TOOL_RETRY_ENABLED=True,
            ICE_TOOL_RETRY_BACKOFF_SEC=0.0,
        ),
    )
    # Silence the audit sink.
    monkeypatch.setattr(llm_gateway.event_log, "emit", lambda **kw: None)

    state = {"calls": 0}

    async def flaky_tool():
        state["calls"] += 1
        if state["calls"] == 1:
            # First attempt: a transient, recoverable failure.
            return {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "connection refused"}
        # Second attempt: success.
        return {"rows": [[1, "ok"]], "row_count": 1}

    outcome = await llm_gateway.run_tool_with_retry(flaky_tool, timeout=5)

    # Retry happened exactly once → two underlying invocations total.
    assert state["calls"] == 2
    # Final outcome is the successful retry result.
    assert outcome["success"] is True
    assert outcome["result"] == {"rows": [[1, "ok"]], "row_count": 1}


@pytest.mark.asyncio
async def test_recoverable_retry_does_not_loop_more_than_once(monkeypatch):
    """If the recoverable tool keeps failing, the helper retries at most once
    (two invocations) and returns the final failure with classification intact.

    Validates: Requirements 4.3, 4.10
    """
    monkeypatch.setattr(
        llm_gateway,
        "get_settings",
        lambda: SimpleNamespace(
            ICE_TOOL_RETRY_ENABLED=True,
            ICE_TOOL_RETRY_BACKOFF_SEC=0.0,
        ),
    )
    monkeypatch.setattr(llm_gateway.event_log, "emit", lambda **kw: None)

    state = {"calls": 0}

    async def always_flaky():
        state["calls"] += 1
        return {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}

    outcome = await llm_gateway.run_tool_with_retry(always_flaky, timeout=5)

    assert state["calls"] == 2
    assert outcome["success"] is False
    assert outcome["error"]["code"] == "KYUUBI_CONNECTION_ERROR"
    assert outcome["error"]["recoverable"] is True
    assert outcome["error"]["error_type"] == "transient"


# ---------------------------------------------------------------------------
# 7.2 — sub-agent failure returns files_written + structured error (R6.1, R6.3)
# ---------------------------------------------------------------------------

def _make_stream(events_per_round: list[list[dict]]):
    """Fake stream_chat yielding the supplied rounds in sequence."""
    call = {"i": 0}

    async def fake_stream(**kwargs) -> AsyncIterator[dict]:
        i = call["i"]
        call["i"] += 1
        if i >= len(events_per_round):
            yield {"type": "message_done", "content": [], "usage": {}, "stop_reason": "end_turn"}
            return
        for ev in events_per_round[i]:
            yield ev

    return fake_stream


@pytest.mark.asyncio
async def test_subagent_failure_returns_files_written_and_structured_error(monkeypatch):
    """A sub-agent run where one side-effecting (write) tool succeeds and
    another tool fails with a recoverable error, then the LLM stream errors out,
    returns both ``files_written`` (the written file) and the structured error
    fields sourced from the failed tool's classification — while preserving all
    existing return fields.

    Validates: Requirements 6.1, 6.3
    """
    round0 = [
        {
            "type": "message_done",
            "content": [
                {"type": "tool_use", "id": "tu1", "name": "writer", "input": {}},
                {"type": "tool_use", "id": "tu2", "name": "flaky", "input": {}},
            ],
            "usage": {},
            "stop_reason": "tool_use",
        }
    ]

    # stream_chat: yield round-0 tool calls, then raise on round 1 → llm_error.
    call = {"i": 0}

    async def fake_stream(**kwargs):
        i = call["i"]
        call["i"] += 1
        if i == 0:
            for ev in round0:
                yield ev
            return
        raise RuntimeError("llm boom")

    async def fake_execute_tool(name, args, ctx=None):
        if name == "writer":
            return {"saved": True, "name": "report.md"}
        # flaky → recoverable transient error.
        return {"error_code": "DEP_TIMEOUT", "message": "timed out"}

    def fake_meta(name):
        return {"side_effect": "write" if name == "writer" else "read"}

    monkeypatch.setattr(agent_runtime.llm_gateway, "stream_chat", fake_stream)
    monkeypatch.setattr(agent_runtime.tool_runner, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(agent_runtime.tool_runner, "get_tool_meta", fake_meta)
    monkeypatch.setattr(agent_runtime.sysconfig_svc, "get_system_params", lambda: {})
    monkeypatch.setattr(agent_runtime.event_log, "emit", lambda **kw: None)
    monkeypatch.setattr(agent_runtime.llm_gateway, "resolve_model", lambda m=None: "m")
    # Keep the sub-agent's own retry helper gate-off (no real retries here).
    monkeypatch.setattr(
        agent_runtime.llm_gateway,
        "get_settings",
        lambda: SimpleNamespace(ICE_TOOL_RETRY_ENABLED=False, ICE_TOOL_RETRY_BACKOFF_SEC=0.0),
    )

    result = await agent_runtime.run_agent_turn(
        system_prompt="",
        initial_messages=[{"role": "user", "content": "go"}],
        tools=[],
        ctx={"task_id": "t", "user_id": "u", "agent_id": "a", "conversation_id": "c"},
        max_rounds=5,
    )

    # files_written: only the successful write tool's file.
    assert result["files_written"] == ["report.md"]

    # Structured error fields from the failed (recoverable) tool.
    assert result["error_type"] == "transient"
    assert result["recoverable"] is True
    assert result["suggested_action"] == "retry_once"

    # Existing return fields preserved (R6.4 sanity within the integration).
    assert result["stop_reason"] == "llm_error"
    assert set(["final_text", "tool_uses_log", "stop_reason", "rounds", "usage_total"]).issubset(
        result.keys()
    )
    assert len(result["tool_uses_log"]) == 2
