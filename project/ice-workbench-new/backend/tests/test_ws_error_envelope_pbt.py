"""Property-based test for WebSocket error-envelope completeness.

Feature: websocket-token-stability, Property 11: WebSocket error envelope completeness

For any application error reported over the WebSocket, the emitted frame is an
Error_Envelope containing all four fields ``code``, ``message``, ``error_code``,
and ``data``, where ``error_code`` is a member of the ErrorCode set and
``message`` is a non-empty string.

The test drives ``app.api.v1.ws._send_error`` directly through a fake WebSocket
sink that captures ``send_text`` payloads, then parses the captured JSON and
asserts the envelope shape. ``_send_error`` routes through ``_send`` which
swallows transport exceptions, so the fake sink always succeeds (its
``send_text`` simply appends), guaranteeing a frame is captured.

Runs a minimum of 100 iterations via the conftest ``ice`` Hypothesis profile
(max_examples=100, default).

Validates: Requirements 12.1, 12.3
"""
from __future__ import annotations

import asyncio
import json

from hypothesis import given
from hypothesis import strategies as st

from app.api.v1.ws import _send_error
from app.core.errors import ErrorCode

# The real ErrorCode set: every public string-valued attribute on ErrorCode.
ERROR_CODE_VALUES = sorted(
    v
    for k, v in vars(ErrorCode).items()
    if not k.startswith("_") and isinstance(v, str)
)
ERROR_CODE_SET = set(ERROR_CODE_VALUES)

# Draw error codes from the real ErrorCode members.
error_codes = st.sampled_from(ERROR_CODE_VALUES)

# Non-empty human-readable messages: at least one non-whitespace character so
# the "non-empty string" contract is meaningfully exercised.
messages = st.text(min_size=1, max_size=200).filter(lambda s: s.strip() != "")

# Optional numeric HTTP-ish code and arbitrary JSON-serialisable data payloads.
codes = st.integers(min_value=100, max_value=599)
data_payloads = st.one_of(
    st.none(),
    st.text(max_size=50),
    st.integers(),
    st.booleans(),
    st.lists(st.integers(), max_size=5),
    st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), max_size=5),
)


class _FakeWebSocket:
    """Minimal WebSocket sink: records every ``send_text`` payload.

    ``_send`` swallows exceptions, so this sink must succeed for a frame to be
    captured — it simply appends the raw text to ``sent``.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


@given(error_code=error_codes, message=messages, code=codes, data=data_payloads)
def test_error_envelope_has_all_four_fields(error_code, message, code, data):
    """Every emitted error frame carries the full Error_Envelope: ``code``,
    ``message``, ``error_code``, ``data`` — with ``error_code`` a real
    ErrorCode member and ``message`` a non-empty string.

    Feature: websocket-token-stability, Property 11: WebSocket error envelope completeness
    Validates: Requirements 12.1, 12.3
    """
    ws = _FakeWebSocket()

    asyncio.run(_send_error(ws, error_code, message, code=code, data=data))

    # Exactly one frame is emitted per error.
    assert len(ws.sent) == 1
    frame = json.loads(ws.sent[0])

    # All four envelope fields are present.
    for field in ("code", "message", "error_code", "data"):
        assert field in frame, f"missing envelope field {field!r}"

    # Field types / values.
    assert isinstance(frame["code"], int)
    assert frame["code"] == code

    assert isinstance(frame["message"], str)
    assert frame["message"] != ""
    assert frame["message"].strip() != ""
    assert frame["message"] == message

    assert isinstance(frame["error_code"], str)
    assert frame["error_code"] == error_code
    assert frame["error_code"] in ERROR_CODE_SET

    # data is echoed verbatim (round-trips through JSON unchanged).
    assert frame["data"] == data

    # Frame is tagged as an error for legacy clients.
    assert frame.get("type") == "error"


@given(error_code=error_codes, message=messages)
def test_error_envelope_default_code_and_data(error_code, message):
    """When ``code``/``data`` are omitted, the envelope still has all four
    fields with the documented defaults (code 400, data null) and a non-empty
    message drawn from a real ErrorCode.

    Feature: websocket-token-stability, Property 11: WebSocket error envelope completeness
    Validates: Requirements 12.1, 12.3
    """
    ws = _FakeWebSocket()

    asyncio.run(_send_error(ws, error_code, message))

    assert len(ws.sent) == 1
    frame = json.loads(ws.sent[0])

    assert set(("code", "message", "error_code", "data")).issubset(frame.keys())
    assert frame["code"] == 400
    assert frame["data"] is None
    assert frame["error_code"] == error_code
    assert frame["error_code"] in ERROR_CODE_SET
    assert isinstance(frame["message"], str) and frame["message"].strip() != ""
