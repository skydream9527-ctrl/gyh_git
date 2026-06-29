"""Tests for the Retry_Controller (structured-tool-error-handling, Task 5).

The conditional-retry logic lives in the shared helper
``llm_gateway.run_tool_with_retry``, reused by the main loop (``ws.py``) and the
sub-agent loop (``agent_runtime.run_agent_turn``) so both apply identical
behaviour (R4.10).

Covers:
* Property 8 (property-based): retry triggering is consistent with
  ``recoverable`` and the Retry_Gate — recoverable+gate-on → exactly one
  retry, otherwise zero.
* Task 5.4 (example-based): fixed backoff, audit event emission, default-off
  Retry_Gate, and that a retry stays inside a single tool-execution unit (does
  not advance any round counter).
* Task 5.7 (example-based regression): with the gate off the helper is
  equivalent to a single ``run_tool_with_timeout`` (R7.4).

Property tests use ``hypothesis`` and run a minimum of 100 iterations via the
conftest ``ice`` profile (max_examples=100).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from hypothesis import given
from hypothesis import strategies as st

from app.core.config import get_settings
from app.services import llm_gateway
from app.services.llm.llm_gateway import (
    normalize_tool_outcome,
    run_tool_with_retry,
    run_tool_with_timeout,
)

# Codes whose classifier-derived ``recoverable`` is True / False respectively.
RECOVERABLE_CODES = ["KYUUBI_CONNECTION_ERROR", "SOME_TIMEOUT", "FOO_TIMEOUT"]
NON_RECOVERABLE_CODES = [
    "VALIDATION_ERROR",
    "SQL_BLOCKED",
    "KYUUBI_SYNTAX_ERROR",
    "KYUUBI_PERMISSION_ERROR",
    "TOTALLY_UNKNOWN_CODE",
    "SOMETHING_NOT_CONFIGURED",
]


def _make_factory(return_value):
    """Build a no-arg async tool factory that records its invocation count."""
    state = {"calls": 0}

    async def factory():
        state["calls"] += 1
        return return_value

    return factory, state


def _settings(*, enabled: bool, backoff: float = 0.0):
    """A minimal settings stand-in honouring the two retry attributes."""
    return SimpleNamespace(
        ICE_TOOL_RETRY_ENABLED=enabled,
        ICE_TOOL_RETRY_BACKOFF_SEC=backoff,
    )


# --- Property 8 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 8: 重试触发与 recoverable 一致
@given(
    recoverable=st.booleans(),
    gate=st.booleans(),
    rec_code=st.sampled_from(RECOVERABLE_CODES),
    non_code=st.sampled_from(NON_RECOVERABLE_CODES),
)
def test_property8_retry_matrix(recoverable, gate, rec_code, non_code):
    """For any failed tool outcome: with the Retry_Gate on, recoverable=True
    triggers exactly one retry and recoverable=False triggers zero; with the
    gate off, zero retries regardless of recoverable.

    Retry count is measured as (underlying tool invocations - 1).

    Feature: structured-tool-error-handling, Property 8: 重试触发与 recoverable 一致
    Validates: Requirements 4.1, 4.3, 4.4, 4.5, 4.6
    """
    code = rec_code if recoverable else non_code
    factory, state = _make_factory({"error_code": code, "message": "boom"})

    outcome = asyncio.run(
        run_tool_with_retry(factory, timeout=5, settings=_settings(enabled=gate))
    )

    expected_calls = 2 if (gate and recoverable) else 1
    assert state["calls"] == expected_calls
    # The outcome is always the (final) normalized failure.
    assert outcome["success"] is False
    assert outcome["error"]["code"] == code
    assert outcome["error"]["recoverable"] is recoverable


# --- Task 5.4: backoff, audit, default-off, round-neutral -------------------

def test_default_retry_gate_is_false():
    """ICE_TOOL_RETRY_ENABLED defaults to False (R4.2)."""
    assert get_settings().ICE_TOOL_RETRY_ENABLED is False


def test_backoff_is_awaited_before_retry(monkeypatch):
    """A recoverable failure waits the configured fixed backoff before
    retrying (R4.7)."""
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(llm_gateway.asyncio, "sleep", fake_sleep)

    factory, state = _make_factory(
        {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}
    )
    asyncio.run(
        run_tool_with_retry(
            factory, timeout=5, settings=_settings(enabled=True, backoff=2.5)
        )
    )

    assert state["calls"] == 2
    assert slept == [2.5]


def test_no_backoff_when_not_retrying(monkeypatch):
    """A non-recoverable failure must not sleep (no retry path)."""
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(llm_gateway.asyncio, "sleep", fake_sleep)

    factory, state = _make_factory({"error_code": "VALIDATION_ERROR", "message": "bad"})
    asyncio.run(
        run_tool_with_retry(
            factory, timeout=5, settings=_settings(enabled=True, backoff=2.5)
        )
    )

    assert state["calls"] == 1
    assert slept == []


def test_retry_emits_audit_event(monkeypatch):
    """An automatic retry records one audit event carrying the original
    error_code, error_type and retry sequence number (R4.8)."""
    events: list[dict] = []

    def fake_emit(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(llm_gateway.event_log, "emit", fake_emit)

    factory, _ = _make_factory(
        {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}
    )
    asyncio.run(
        run_tool_with_retry(
            factory,
            timeout=5,
            settings=_settings(enabled=True),
            audit_ctx={"task_id": "t-1", "conversation_id": "c-1"},
        )
    )

    assert len(events) == 1
    evt = events[0]
    assert evt["task_id"] == "t-1"
    assert evt["event_type"] == "tool_retry"
    assert evt["code"] == "KYUUBI_CONNECTION_ERROR"
    payload = evt["payload"]
    assert payload["error_code"] == "KYUUBI_CONNECTION_ERROR"
    assert payload["error_type"] == "transient"
    assert payload["attempt"] == 1


def test_no_audit_event_when_gate_off(monkeypatch):
    """With the gate off, no retry audit event is emitted."""
    events: list[dict] = []
    monkeypatch.setattr(
        llm_gateway.event_log, "emit", lambda **kwargs: events.append(kwargs)
    )

    factory, _ = _make_factory(
        {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}
    )
    asyncio.run(
        run_tool_with_retry(factory, timeout=5, settings=_settings(enabled=False))
    )

    assert events == []


def test_retry_stays_within_single_tool_execution_unit():
    """The retry happens inside one helper invocation (one tool-execution
    unit). The helper returns a single outcome with no round metadata, so it
    cannot advance the ReAct round counter (R4.9). The retry is observable only
    as a second underlying tool call."""
    factory, state = _make_factory(
        {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}
    )
    outcome = asyncio.run(
        run_tool_with_retry(factory, timeout=5, settings=_settings(enabled=True))
    )

    # Two underlying tool invocations, but one logical tool-execution unit.
    assert state["calls"] == 2
    # No round-counter field leaks out of the helper.
    assert "rounds" not in outcome
    assert "round" not in outcome


def test_retry_returns_second_outcome_on_recovery():
    """When the retry succeeds, the helper returns the (successful) retry
    outcome rather than the first failure (R4.6 success branch)."""
    state = {"calls": 0}

    async def factory():
        state["calls"] += 1
        if state["calls"] == 1:
            return {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}
        return {"rows": [[1]], "row_count": 1}

    outcome = asyncio.run(
        run_tool_with_retry(factory, timeout=5, settings=_settings(enabled=True))
    )

    assert state["calls"] == 2
    assert outcome["success"] is True
    assert outcome["result"] == {"rows": [[1]], "row_count": 1}


# --- Task 5.7: regression — gate off == single run_tool_with_timeout --------

def test_gate_off_equivalent_to_single_run(monkeypatch):
    """With the Retry_Gate off, ``run_tool_with_retry`` behaves identically to
    a single ``run_tool_with_timeout`` + ``normalize_tool_outcome`` — same
    invocation count, same outcome (R7.4)."""
    # Guard: even if something tried to sleep, the gate-off path must not.
    slept: list[float] = []
    monkeypatch.setattr(
        llm_gateway.asyncio, "sleep", lambda s: slept.append(s)
    )

    payload = {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "down"}

    factory_a, state_a = _make_factory(payload)
    via_retry = asyncio.run(
        run_tool_with_retry(factory_a, timeout=5, settings=_settings(enabled=False))
    )

    factory_b, state_b = _make_factory(payload)
    via_single = normalize_tool_outcome(
        asyncio.run(run_tool_with_timeout(factory_b, timeout=5))
    )

    assert state_a["calls"] == 1 == state_b["calls"]
    assert via_retry == via_single
    assert slept == []


def test_gate_off_success_passthrough():
    """Gate off, successful tool → returned unchanged, single invocation."""
    factory, state = _make_factory({"rows": [], "row_count": 0})
    outcome = asyncio.run(
        run_tool_with_retry(factory, timeout=5, settings=_settings(enabled=False))
    )
    assert state["calls"] == 1
    assert outcome["success"] is True
