"""Example tests for specific WebSocket error-envelope instances.

Task 4.3 (websocket-token-stability). These are REPRESENTATIVE example tests,
not randomized property tests. They pin two concrete error-envelope instances
the WS_Endpoint must emit:

  12.2  LLM_KEY_MISSING envelope is emitted AND the turn is NOT started when the
        LLM key is absent.
  12.3  CONVERSATION_INFLIGHT envelope is emitted on a `user_message` collision.

Coverage map (real code path vs. structural assertion):

  12.2  REAL — drives the real `_handle_user_message` against a freshly created
        task/conversation with `settings.llm_enabled` forced False; asserts the
        inline LLM_KEY_MISSING envelope frame and that NO turn frames
        (agent_message / agent_message_done / tool_call_start / agent_typing)
        followed (the turn never started).
  12.3  REAL — drives the real `_send_error(..., CONVERSATION_INFLIGHT, ...)`
        builder used by the collision branches and asserts the full four-field
        envelope shape; plus a STRUCTURAL backstop confirming the `ws_chat`
        inflight-rejection branches actually call `_send_error` with
        `ErrorCode.CONVERSATION_INFLIGHT`.

Async coroutines are driven with `asyncio.run`; the `isolated_data_root`
autouse fixture (conftest) provides a throwaway DATA_ROOT + IndexDB schema.

Validates: Requirements 12.2, 12.3
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re

import pytest

from app.api.v1 import ws as ws_mod
from app.api.v1.ws_stream import _handle_user_message
from app.api.v1.ws_helpers import _send_error
from app.core import config as cfg
from app.core.errors import ErrorCode
from app.core.storage import get_paths, read_json
from app.services import task_svc


# Frame types that only ever appear once the agent execution loop (the Turn) has
# actually started streaming. Their ABSENCE proves "the turn is not started".
TURN_FRAME_TYPES = {
    "agent_typing",
    "agent_message",
    "agent_message_done",
    "tool_call_start",
    "tool_call_done",
}


class _FakeWebSocket:
    """Minimal WebSocket double: records every ``send_text`` payload.

    ``_send`` / ``_send_error`` swallow transport exceptions, so this sink must
    succeed for frames to be captured — it simply appends the raw text.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    def frames(self) -> list[dict]:
        return [json.loads(t) for t in self.sent]

    def frames_of_type(self, frame_type: str) -> list[dict]:
        return [f for f in self.frames() if f.get("type") == frame_type]


def _force_llm_disabled(monkeypatch) -> None:
    """Force ``settings.llm_enabled`` False deterministically.

    ``llm_enabled`` is ``bool(MIFY_GATEWAY_API_KEY) or bool(ANTHROPIC_API_KEY)``;
    clearing both env keys (overriding any value loaded from a local .env) and
    busting the settings cache makes the property return False regardless of the
    developer's environment.
    """
    monkeypatch.setenv("MIFY_GATEWAY_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    cfg.get_settings.cache_clear()
    assert cfg.get_settings().llm_enabled is False


def _create_task_and_conv(owner_id: str) -> tuple[str, str]:
    """Create a real task + default conversation and return ``(task_id, conv_id)``."""
    meta = asyncio.run(
        task_svc.create_task(
            name="ttl-error-envelope",
            paradigm="general",
            owner_id=owner_id,
            agent_id="biz-insight",
        )
    )
    task_id = meta["id"]
    workspace = read_json(get_paths().task_workspace(task_id), default={}) or {}
    conv_id = workspace["current_conversation_id"]
    return task_id, conv_id


# ---------------------------------------------------------------------------
# 12.2 — LLM_KEY_MISSING emitted AND the turn is not started (REAL path)
# ---------------------------------------------------------------------------

def test_llm_key_missing_envelope_emitted_and_turn_not_started(
    isolated_data_root, monkeypatch
):
    """When the LLM key is absent, `_handle_user_message` emits the
    LLM_KEY_MISSING error envelope and returns BEFORE starting the Turn — no
    agent streaming / tool frames are produced. (Req 12.2)"""
    _force_llm_disabled(monkeypatch)

    user = {"id": "user-001", "email": "alice@xiaomi.com", "name": "Alice"}
    task_id, conv_id = _create_task_and_conv(user["id"])

    paths = get_paths()
    conv_path = paths.task_conversation(task_id, conv_id)
    tool_path = paths.task_tool_calls(task_id, conv_id)

    ws = _FakeWebSocket()
    cancel = asyncio.Event()

    asyncio.run(
        _handle_user_message(
            ws,
            {"type": "user_message", "content": "hello there"},
            user,
            task_id,
            conv_id,
            conv_path,
            tool_path,
            cancel,
        )
    )

    frames = ws.frames()

    # Exactly one error frame, and it is the LLM_KEY_MISSING envelope.
    error_frames = [f for f in frames if f.get("type") == "error"]
    assert len(error_frames) == 1, f"expected one error frame, got {frames}"
    err = error_frames[0]

    # Full four-field envelope (Req 12.1 shape) with the right error_code.
    for field in ("code", "message", "error_code", "data"):
        assert field in err, f"missing envelope field {field!r}: {err}"
    assert err["error_code"] == ErrorCode.LLM_KEY_MISSING
    assert isinstance(err["message"], str) and err["message"].strip() != ""
    assert isinstance(err["code"], int)

    # The Turn was NOT started: no agent streaming / tool-call frames emitted.
    turn_frames = [f for f in frames if f.get("type") in TURN_FRAME_TYPES]
    assert turn_frames == [], f"turn must not start, but saw: {turn_frames}"

    # The cancel signal is untouched (no turn → nothing to cancel).
    assert cancel.is_set() is False


def test_llm_key_missing_inline_frame_is_full_envelope_structural():
    """Structural backstop for 12.2: the inline LLM_KEY_MISSING frame in
    `_handle_user_message` carries the full `{code, message, error_code, data}`
    envelope (not the legacy 3-field shape) and uses `ErrorCode.LLM_KEY_MISSING`."""
    src = inspect.getsource(ws_mod._handle_user_message)
    # The early-return guard exists.
    assert "if not s.llm_enabled:" in src
    # The inline frame references the canonical error code member.
    assert "ErrorCode.LLM_KEY_MISSING" in src
    # All four envelope keys appear in the inline error frame.
    for key in ('"code"', '"message"', '"error_code"', '"data"'):
        assert key in src, f"inline LLM_KEY_MISSING frame missing {key}"


# ---------------------------------------------------------------------------
# 12.3 — CONVERSATION_INFLIGHT emitted on a user_message collision
# ---------------------------------------------------------------------------

def test_conversation_inflight_envelope_shape():
    """The CONVERSATION_INFLIGHT rejection is emitted through the real
    `_send_error` builder and carries the full four-field envelope with
    `error_code == CONVERSATION_INFLIGHT` and a non-empty message. (Req 12.3)"""
    ws = _FakeWebSocket()
    message = "该对话正在处理中，请稍候或点中断后再发新消息"

    asyncio.run(_send_error(ws, ErrorCode.CONVERSATION_INFLIGHT, message))

    assert len(ws.sent) == 1
    frame = json.loads(ws.sent[0])

    for field in ("code", "message", "error_code", "data"):
        assert field in frame, f"missing envelope field {field!r}: {frame}"
    assert frame.get("type") == "error"
    assert frame["error_code"] == ErrorCode.CONVERSATION_INFLIGHT
    assert isinstance(frame["message"], str) and frame["message"].strip() != ""
    assert frame["message"] == message
    assert isinstance(frame["code"], int)
    assert frame["code"] == 400  # documented default
    assert frame["data"] is None


def test_user_message_collision_branch_emits_conversation_inflight_structural():
    """Structural backstop for 12.3: the `ws_chat` handler rejects a colliding
    `user_message` (same-worker registry hit AND cross-worker flock loss) by
    calling `_send_error(..., ErrorCode.CONVERSATION_INFLIGHT, ...)` — the same
    builder asserted above — without starting a second Turn."""
    src = inspect.getsource(ws_mod.ws_chat)

    # At least two CONVERSATION_INFLIGHT rejections exist on the user_message
    # path: the in-process registry hit and the cross-worker flock loss.
    inflight_rejections = re.findall(
        r"_send_error\(\s*\n?\s*websocket,\s*\n?\s*ErrorCode\.CONVERSATION_INFLIGHT",
        src,
    )
    assert len(inflight_rejections) >= 2, (
        f"expected >=2 CONVERSATION_INFLIGHT rejections, found {len(inflight_rejections)}"
    )

    # The collision path rejects and `continue`s rather than creating a turn:
    # the cross-worker guard returns None → reject, never reaching create_task.
    assert 'if lock_fh is None:' in src
