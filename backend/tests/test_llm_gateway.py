"""Unit tests for the OpenAI-compat conversion in llm_gateway."""
from __future__ import annotations

import json

from app.services.llm_gateway import (
    PRESET_MODELS,
    _anthropic_tools_to_openai,
    _messages_to_openai,
    _normalize_stop_reason,
    normalize_tool_outcome,
    tool_timeout_for,
)


def test_anthropic_tools_to_openai_shape():
    native = [
        {
            "name": "echo",
            "description": "Echo text",
            "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
        }
    ]
    out = _anthropic_tools_to_openai(native)
    assert out is not None and len(out) == 1
    fn = out[0]
    assert fn["type"] == "function"
    assert fn["function"]["name"] == "echo"
    assert fn["function"]["parameters"] == native[0]["input_schema"]


def test_messages_to_openai_user_text():
    out = _messages_to_openai(
        [{"role": "user", "content": "你好"}],
        system_prompt="SYS",
    )
    assert out[0] == {"role": "system", "content": "SYS"}
    assert out[1] == {"role": "user", "content": "你好"}


def test_messages_to_openai_assistant_with_tool_use():
    msgs = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "我来查一下。"},
                {
                    "type": "tool_use",
                    "id": "call_1",
                    "name": "kyuubi_query",
                    "input": {"sql": "SELECT 1"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": {"rows": 1}}
            ],
        },
    ]
    out = _messages_to_openai(msgs, system_prompt="SYS")
    assert out[0]["role"] == "system"

    assistant = out[1]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "我来查一下。"
    assert len(assistant["tool_calls"]) == 1
    tc = assistant["tool_calls"][0]
    assert tc["id"] == "call_1"
    assert tc["function"]["name"] == "kyuubi_query"
    assert json.loads(tc["function"]["arguments"]) == {"sql": "SELECT 1"}

    tool_msg = out[2]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "call_1"
    assert "rows" in tool_msg["content"]


def test_normalize_stop_reason():
    assert _normalize_stop_reason("tool_calls") == "tool_use"
    assert _normalize_stop_reason("stop") == "end_turn"
    assert _normalize_stop_reason("length") == "length"
    assert _normalize_stop_reason(None) is None


def test_preset_models_contains_8():
    ids = {m["id"] for m in PRESET_MODELS}
    # ids include the owner/* prefix expected by the mify gateway router
    assert "ppio/pa/claude-opus-4-7" in ids
    assert "azure_openai/gpt-5.4" in ids
    assert "vertex_ai/gemini-3.1-pro-preview" in ids
    assert "xiaomi/glm-5" in ids
    assert "xiaomi/mimo-v2.5-pro" in ids
    assert len(PRESET_MODELS) == 8


def test_route_resolution():
    from app.services.llm_gateway import _route

    assert _route("ppio/pa/claude-opus-4-7") == "anthropic_native"
    assert _route("ppio/pa/claude-sonnet-4-6") == "anthropic_native"
    assert _route("azure_openai/gpt-5.4") == "openai_responses"


def test_tool_timeout_uses_admin_setting_for_normal_tools():
    assert tool_timeout_for("read_skill", {"tool_call_timeout_s": 45}) == 45


def test_tool_timeout_keeps_kyuubi_above_inner_cli_deadline():
    assert tool_timeout_for("kyuubi_query", {"tool_call_timeout_s": 30}) == 330


def test_tool_timeout_is_capped():
    assert tool_timeout_for("read_skill", {"tool_call_timeout_s": 9999}) == 600


def test_normalize_tool_outcome_converts_error_payload_to_failure():
    out = normalize_tool_outcome(
        {
            "success": True,
            "status": "done",
            "result": {"error_code": "KYUUBI_CLI_ERROR", "message": "bad sql"},
        }
    )
    assert out["success"] is False
    assert out["status"] == "error"
    assert out["error"]["code"] == "KYUUBI_CLI_ERROR"
