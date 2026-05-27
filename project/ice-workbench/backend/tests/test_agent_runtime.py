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
