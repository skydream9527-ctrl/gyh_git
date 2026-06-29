"""Tests for KYUUBI stderr classification and empty-result semantics
(structured-tool-error-handling, Task 3).

Covers:
- Property 9 (property-based): ``classify_kyuubi_stderr`` discriminates
  syntax / permission / connection / fallback from stderr text.
- Unit test: ``_tool_kyuubi`` marks an empty (zero-row) successful query with
  ``empty: True`` / ``empty_code: "KYUUBI_EMPTY"`` while keeping
  ``rows == []`` and ``row_count == 0``.

Property tests use ``hypothesis`` and run a minimum of 100 iterations via the
conftest ``ice`` profile (max_examples=100). External CLI invocation is avoided
by stubbing ``asyncio.create_subprocess_exec`` / ``shutil.which`` / settings.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import types

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services import tool_runner
from app.services.llm.tool_runner import (
    _CONNECTION_MARKERS,
    _PERMISSION_MARKERS,
    _SYNTAX_MARKERS,
    classify_kyuubi_stderr,
)

# Noise that contains none of the known markers, to interleave with keywords.
_NOISE = st.text(
    alphabet="0123456789 .,:;-_/()[]xyzqwm\n\t",
    min_size=0,
    max_size=40,
)


def _wrap(keyword: str, prefix: str, suffix: str) -> str:
    return f"{prefix}{keyword}{suffix}"


# ---------------------------------------------------------------------------
# Property 9: KYUUBI stderr 细分判别
# Feature: structured-tool-error-handling, Property 9: For any stderr text
# containing a syntax keyword -> KYUUBI_SYNTAX_ERROR; a permission keyword
# (and no syntax keyword) -> KYUUBI_PERMISSION_ERROR; a connection keyword
# (and no syntax/permission keyword) -> KYUUBI_CONNECTION_ERROR; no known
# keyword -> KYUUBI_CLI_ERROR.
# Validates: Requirements 5.1, 5.2, 5.3, 5.4
# ---------------------------------------------------------------------------


@given(
    marker=st.sampled_from(_SYNTAX_MARKERS),
    prefix=_NOISE,
    suffix=_NOISE,
)
def test_property9_syntax_marker_wins(marker, prefix, suffix):
    text = _wrap(marker, prefix, suffix)
    assert classify_kyuubi_stderr(text) == "KYUUBI_SYNTAX_ERROR"


@given(
    marker=st.sampled_from(_PERMISSION_MARKERS),
    prefix=_NOISE,
    suffix=_NOISE,
)
def test_property9_permission_marker_without_syntax(marker, prefix, suffix):
    text = _wrap(marker, prefix, suffix)
    # Guard the generated noise does not accidentally introduce a syntax marker.
    low = text.lower()
    if any(k in low for k in _SYNTAX_MARKERS):
        return
    assert classify_kyuubi_stderr(text) == "KYUUBI_PERMISSION_ERROR"


@given(
    marker=st.sampled_from(_CONNECTION_MARKERS),
    prefix=_NOISE,
    suffix=_NOISE,
)
def test_property9_connection_marker_without_syntax_or_permission(marker, prefix, suffix):
    text = _wrap(marker, prefix, suffix)
    low = text.lower()
    if any(k in low for k in _SYNTAX_MARKERS) or any(k in low for k in _PERMISSION_MARKERS):
        return
    assert classify_kyuubi_stderr(text) == "KYUUBI_CONNECTION_ERROR"


@given(noise=_NOISE)
def test_property9_no_known_marker_falls_back(noise):
    low = noise.lower()
    if (
        any(k in low for k in _SYNTAX_MARKERS)
        or any(k in low for k in _PERMISSION_MARKERS)
        or any(k in low for k in _CONNECTION_MARKERS)
    ):
        return
    assert classify_kyuubi_stderr(noise) == "KYUUBI_CLI_ERROR"


@given(value=st.one_of(st.none(), st.text(max_size=80)))
def test_property9_never_raises_and_returns_valid_code(value):
    result = classify_kyuubi_stderr(value)  # type: ignore[arg-type]
    assert result in {
        "KYUUBI_SYNTAX_ERROR",
        "KYUUBI_PERMISSION_ERROR",
        "KYUUBI_CONNECTION_ERROR",
        "KYUUBI_CLI_ERROR",
    }


# ---------------------------------------------------------------------------
# Example-based unit tests for ordering precedence (syntax > permission >
# connection) and a couple of concrete stderr samples.
# ---------------------------------------------------------------------------


def test_classify_precedence_syntax_over_permission():
    # Contains both a syntax marker and a permission marker; syntax wins.
    assert (
        classify_kyuubi_stderr("ParseException: permission denied near 'SELCT'")
        == "KYUUBI_SYNTAX_ERROR"
    )


def test_classify_precedence_permission_over_connection():
    # "connection ... unauthorized" must classify as permission, not connection.
    assert (
        classify_kyuubi_stderr("connection established but request unauthorized")
        == "KYUUBI_PERMISSION_ERROR"
    )


def test_classify_connection_sample():
    assert (
        classify_kyuubi_stderr("Connection refused: server unavailable")
        == "KYUUBI_CONNECTION_ERROR"
    )


def test_classify_fallback_sample():
    assert classify_kyuubi_stderr("kyuubi exit 7") == "KYUUBI_CLI_ERROR"


# ---------------------------------------------------------------------------
# Unit test (Task 3.4): empty result is marked but stays a success.
# Validates: Requirements 5.5
# ---------------------------------------------------------------------------


class _FakeProc:
    def __init__(self, stdout: bytes, stderr: bytes, returncode: int):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):  # pragma: no cover - not used in success path
        pass

    async def wait(self):  # pragma: no cover - not used in success path
        pass


@pytest.mark.asyncio
async def test_empty_result_marked_as_empty(monkeypatch):
    # Fake settings so the tool takes the CLI-execution branch.
    fake_settings = types.SimpleNamespace(
        KYUUBI_REGION="r",
        KYUUBI_WORKSPACE="w",
        KYUUBI_CATALOG="c",
        KYUUBI_ENGINE="e",
        KYUUBI_TOKEN="tok",
        ICE_KYUUBI_CONCURRENCY=2,
    )
    monkeypatch.setattr(tool_runner, "get_settings", lambda: fake_settings)
    # Reset the cached semaphore so it is rebuilt against fake settings.
    monkeypatch.setattr(tool_runner, "_kyuubi_sem", None, raising=False)

    # SQL audit allows the query.
    from app.services import sql_audit_svc
    monkeypatch.setattr(sql_audit_svc, "classify", lambda sql: ("allow", ""))

    # Pretend the CLI is installed.
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/kyuubi")

    payload = json.dumps({"columns": [{"name": "id"}, {"name": "v"}], "rows": []})

    async def fake_exec(*args, **kwargs):
        return _FakeProc(payload.encode(), b"", 0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    out = await tool_runner._tool_kyuubi({"sql": "SELECT id, v FROM t WHERE 1=0"}, None)

    assert isinstance(out, dict)
    assert "error_code" not in out
    assert out["empty"] is True
    assert out["empty_code"] == "KYUUBI_EMPTY"
    assert out["rows"] == []
    assert out["row_count"] == 0
    assert out["columns"] == ["id", "v"]


@pytest.mark.asyncio
async def test_nonempty_result_not_marked_empty(monkeypatch):
    fake_settings = types.SimpleNamespace(
        KYUUBI_REGION="r",
        KYUUBI_WORKSPACE="w",
        KYUUBI_CATALOG="c",
        KYUUBI_ENGINE="e",
        KYUUBI_TOKEN="tok",
        ICE_KYUUBI_CONCURRENCY=2,
    )
    monkeypatch.setattr(tool_runner, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(tool_runner, "_kyuubi_sem", None, raising=False)

    from app.services import sql_audit_svc
    monkeypatch.setattr(sql_audit_svc, "classify", lambda sql: ("allow", ""))
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/kyuubi")

    payload = json.dumps({"columns": [{"name": "id"}], "rows": [[1], [2]]})

    async def fake_exec(*args, **kwargs):
        return _FakeProc(payload.encode(), b"", 0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    out = await tool_runner._tool_kyuubi({"sql": "SELECT id FROM t"}, None)

    assert isinstance(out, dict)
    assert "error_code" not in out
    assert "empty" not in out
    assert out["row_count"] == 2
