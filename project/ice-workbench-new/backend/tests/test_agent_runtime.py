"""Happy-path tests for agent_runtime.run_agent_turn.

Stream_chat is monkey-patched so we control the LLM outputs deterministically.
Covers:
- No tools requested → single round, returns final text.
- One tool_use → tool dispatched, result fed back, second round returns text.
- exit_plan_mode called → loop terminates after one round (no extra LLM call).
- max_rounds cap respected.
"""
from __future__ import annotations

from typing import AsyncIterator

import pytest

from app.services import agent_runtime, llm_gateway, tool_runner


def _make_stream(events_per_round: list[list[dict]]):
    """Build a fake stream_chat that yields the given rounds in sequence."""
    call = {"i": 0}

    async def fake_stream(**kwargs) -> AsyncIterator[dict]:
        i = call["i"]
        call["i"] += 1
        if i >= len(events_per_round):
            # Any extra call should be a bug — emit an empty message_done.
            yield {"type": "message_done", "content": [], "usage": {}, "stop_reason": "end_turn"}
            return
        for ev in events_per_round[i]:
            yield ev

    return fake_stream


@pytest.mark.asyncio
async def test_no_tools_single_round(monkeypatch):
    """When the LLM returns text without tool_use, the loop exits after round 0."""
    events = [
        [
            {"type": "text", "delta": "hello "},
            {"type": "text", "delta": "world"},
            {"type": "message_done", "content": [{"type": "text", "text": "hello world"}], "usage": {}, "stop_reason": "end_turn"},
        ]
    ]
    monkeypatch.setattr(llm_gateway, "stream_chat", _make_stream(events))

    result = await agent_runtime.run_agent_turn(
        system_prompt="",
        initial_messages=[{"role": "user", "content": "hi"}],
        tools=[],
        ctx={"task_id": "t", "user_id": "u", "agent_id": "a", "conversation_id": "c"},
        max_rounds=5,
    )
    assert result["final_text"] == "hello world"
    assert result["rounds"] == 1
    assert result["tool_uses_log"] == []


@pytest.mark.asyncio
async def test_one_tool_round_then_answer(monkeypatch):
    """First round emits a tool_use; second round (after tool_result) emits
    text. tool_uses_log contains the executed tool."""
    events = [
        [
            {
                "type": "message_done",
                "content": [
                    {"type": "tool_use", "id": "tu1", "name": "now", "input": {}},
                ],
                "usage": {},
                "stop_reason": "tool_use",
            }
        ],
        [
            {"type": "text", "delta": "the time is fine"},
            {
                "type": "message_done",
                "content": [{"type": "text", "text": "the time is fine"}],
                "usage": {},
                "stop_reason": "end_turn",
            },
        ],
    ]
    monkeypatch.setattr(llm_gateway, "stream_chat", _make_stream(events))

    result = await agent_runtime.run_agent_turn(
        system_prompt="",
        initial_messages=[{"role": "user", "content": "what time is it"}],
        tools=tool_runner.get_anthropic_tools(in_subagent=True),
        ctx={"task_id": "t", "user_id": "u", "agent_id": "a", "conversation_id": "c"},
        max_rounds=5,
    )
    assert result["final_text"] == "the time is fine"
    assert len(result["tool_uses_log"]) == 1
    assert result["tool_uses_log"][0]["name"] == "now"
    assert result["tool_uses_log"][0]["success"] is True


@pytest.mark.asyncio
async def test_exit_plan_mode_terminates_loop(monkeypatch, isolated_data_root):
    """If the sub-agent calls exit_plan_mode, the loop exits with stop_reason
    'plan_proposed' and does NOT start another round."""
    from app.core.storage import get_paths, write_json

    idx = get_paths().task_conversations_index("t-ep")
    idx.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        idx,
        [
            {
                "id": "cv-ep",
                "title": "c",
                "created_by": "u1",
                "created_at": "2026-01-01T00:00:00Z",
                "last_message_at": "2026-01-01T00:00:00Z",
                "message_count": 0,
            }
        ],
    )
    conv = {"id": "cv-ep"}

    events = [
        [
            {
                "type": "message_done",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu1",
                        "name": "exit_plan_mode",
                        "input": {"plan": "# plan"},
                    }
                ],
                "usage": {},
                "stop_reason": "tool_use",
            }
        ],
        # If we mistakenly run a second round, this would be visible in rounds.
        [
            {"type": "text", "delta": "SHOULD NOT APPEAR"},
            {
                "type": "message_done",
                "content": [{"type": "text", "text": "SHOULD NOT APPEAR"}],
                "usage": {},
                "stop_reason": "end_turn",
            },
        ],
    ]
    monkeypatch.setattr(llm_gateway, "stream_chat", _make_stream(events))

    result = await agent_runtime.run_agent_turn(
        system_prompt="",
        initial_messages=[{"role": "user", "content": "plan it"}],
        tools=tool_runner.get_anthropic_tools(),
        ctx={
            "task_id": "t-ep",
            "user_id": "u1",
            "agent_id": "a",
            "conversation_id": conv["id"],
        },
        max_rounds=5,
    )
    assert result["stop_reason"] == "plan_proposed"
    assert result["rounds"] == 1
    assert result["final_text"] != "SHOULD NOT APPEAR"


# ---------------------------------------------------------------------------
# Task 6 — sub-agent structured failure return (files_written + error fields)
# ---------------------------------------------------------------------------

import asyncio
from unittest import mock

from hypothesis import given, settings
from hypothesis import strategies as st


def _patch_runtime(rounds, fake_execute_tool, fake_meta):
    """Context-manager bundle: patch stream_chat + tool dispatch + side IO so
    run_agent_turn runs fully in-process with no LLM/CLI/file access."""
    return (
        mock.patch.object(agent_runtime.llm_gateway, "stream_chat", _make_stream(rounds)),
        mock.patch.object(agent_runtime.tool_runner, "execute_tool", fake_execute_tool),
        mock.patch.object(agent_runtime.tool_runner, "get_tool_meta", fake_meta),
        mock.patch.object(agent_runtime.sysconfig_svc, "get_system_params", lambda: {}),
        mock.patch.object(agent_runtime.event_log, "emit", lambda **kw: None),
        mock.patch.object(agent_runtime.llm_gateway, "resolve_model", lambda m=None: "m"),
    )


async def _drive(rounds, fake_execute_tool, fake_meta):
    p1, p2, p3, p4, p5, p6 = _patch_runtime(rounds, fake_execute_tool, fake_meta)
    with p1, p2, p3, p4, p5, p6:
        return await agent_runtime.run_agent_turn(
            system_prompt="",
            initial_messages=[{"role": "user", "content": "go"}],
            tools=[],
            ctx={"task_id": "t", "user_id": "u", "agent_id": "a", "conversation_id": "c"},
            max_rounds=5,
        )


@st.composite
def _tool_call_seq(draw):
    n = draw(st.integers(min_value=0, max_value=8))
    return [
        {
            "side_effect": draw(st.sampled_from(["read", "write", "network"])),
            "success": draw(st.booleans()),
        }
        for _ in range(n)
    ]


# Feature: structured-tool-error-handling, Property 10: 子 agent 运行序列返回的
# files_written 恰好等于该次运行中所有成功写入工作区的文件名集合；无写入时为空列表。
# Validates: Requirements 6.1, 6.2
@settings(max_examples=150, deadline=None)
@given(calls=_tool_call_seq())
def test_property10_files_written_completeness(calls):
    meta_map: dict[str, str] = {}
    result_map: dict[str, tuple[bool, str]] = {}
    tool_blocks: list[dict] = []
    expected: list[str] = []

    for i, c in enumerate(calls):
        name = f"tool_{i}"
        fname = f"file_{i}.md"
        meta_map[name] = c["side_effect"]
        result_map[name] = (c["success"], fname)
        tool_blocks.append({"type": "tool_use", "id": f"tu{i}", "name": name, "input": {}})
        # Only successful side-effecting (write/network) tools contribute.
        if c["success"] and c["side_effect"] in ("write", "network"):
            expected.append(fname)

    rounds: list[list[dict]] = []
    if tool_blocks:
        rounds.append(
            [{"type": "message_done", "content": tool_blocks, "usage": {}, "stop_reason": "tool_use"}]
        )
    # Final round returns a clean answer so the run is a success.
    rounds.append(
        [
            {"type": "text", "delta": "done"},
            {"type": "message_done", "content": [{"type": "text", "text": "done"}], "usage": {}, "stop_reason": "end_turn"},
        ]
    )

    async def fake_execute_tool(name, args, ctx=None):
        success, fname = result_map[name]
        if success:
            # write_file-shaped successful result carrying the workspace name.
            return {"saved": True, "name": fname}
        return {"error_code": "TOOL_X_FAILED", "message": "boom"}

    def fake_meta(name):
        return {"side_effect": meta_map.get(name, "read")}

    result = asyncio.run(_drive(rounds, fake_execute_tool, fake_meta))

    assert set(result["files_written"]) == set(expected)
    # No spurious duplicates: filenames are unique per call.
    assert len(result["files_written"]) == len(set(result["files_written"]))


def test_files_written_success_example():
    """Example-based complement: one write tool + one read tool that both
    return a `name`; only the write tool's file is reported (R6.1)."""
    rounds = [
        [
            {
                "type": "message_done",
                "content": [
                    {"type": "tool_use", "id": "tu1", "name": "writer", "input": {}},
                    {"type": "tool_use", "id": "tu2", "name": "reader", "input": {}},
                ],
                "usage": {},
                "stop_reason": "tool_use",
            }
        ],
        [
            {"type": "text", "delta": "ok"},
            {"type": "message_done", "content": [{"type": "text", "text": "ok"}], "usage": {}, "stop_reason": "end_turn"},
        ],
    ]

    async def fake_execute_tool(name, args, ctx=None):
        return {"saved": True, "name": "report.md" if name == "writer" else "input.csv"}

    def fake_meta(name):
        return {"side_effect": "write" if name == "writer" else "read"}

    result = asyncio.run(_drive(rounds, fake_execute_tool, fake_meta))
    assert result["files_written"] == ["report.md"]
    # Success run: no structured error fields attached.
    assert "error_type" not in result
    assert "recoverable" not in result
    assert "suggested_action" not in result


def _stream_round0_then_raise(round0_events):
    """stream_chat that yields round-0 events, then raises on the next round."""
    call = {"i": 0}

    async def fake(**kwargs):
        i = call["i"]
        call["i"] += 1
        if i == 0:
            for ev in round0_events:
                yield ev
            return
        raise RuntimeError("llm boom")

    return fake


@pytest.mark.asyncio
async def test_failure_returns_structured_error_fields(monkeypatch):
    """A run that fails (a recoverable tool error followed by an LLM stream
    error) surfaces error_type / recoverable / suggested_action while keeping
    all existing return fields (R6.3, R6.4)."""
    round0 = [
        {
            "type": "message_done",
            "content": [{"type": "tool_use", "id": "tu1", "name": "flaky", "input": {}}],
            "usage": {},
            "stop_reason": "tool_use",
        }
    ]

    async def fake_execute_tool(name, args, ctx=None):
        # *_TIMEOUT → transient / recoverable / retry_once
        return {"error_code": "DEP_TIMEOUT", "message": "timed out"}

    monkeypatch.setattr(agent_runtime.llm_gateway, "stream_chat", _stream_round0_then_raise(round0))
    monkeypatch.setattr(agent_runtime.tool_runner, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(agent_runtime.tool_runner, "get_tool_meta", lambda n: {"side_effect": "read"})
    monkeypatch.setattr(agent_runtime.sysconfig_svc, "get_system_params", lambda: {})
    monkeypatch.setattr(agent_runtime.event_log, "emit", lambda **kw: None)
    monkeypatch.setattr(agent_runtime.llm_gateway, "resolve_model", lambda m=None: "m")

    result = await agent_runtime.run_agent_turn(
        system_prompt="",
        initial_messages=[{"role": "user", "content": "go"}],
        tools=[],
        ctx={"task_id": "t", "user_id": "u", "agent_id": "a", "conversation_id": "c"},
        max_rounds=5,
    )

    # Structured error fields present and sourced from the failed tool's
    # normalized classification.
    assert result["error_type"] == "transient"
    assert result["recoverable"] is True
    assert result["suggested_action"] == "retry_once"

    # All existing return fields retained (R6.4).
    assert result["stop_reason"] == "llm_error"
    assert result["final_text"] == ""
    assert isinstance(result["tool_uses_log"], list) and len(result["tool_uses_log"]) == 1
    assert result["tool_uses_log"][0]["success"] is False
    assert isinstance(result["rounds"], int)
    assert result["usage_total"] == {"input_tokens": 0, "output_tokens": 0}
    assert result["files_written"] == []
