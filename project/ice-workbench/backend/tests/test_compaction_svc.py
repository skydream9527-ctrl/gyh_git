"""Unit tests for compaction_svc — threshold, split adjustment, cache."""
from __future__ import annotations

import pytest

from app.services import compaction_svc


def _msg(role: str, text: str) -> dict:
    return {"role": role, "content": text}


def _tool_use(text: str, tu_id: str = "tu1") -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "text", "text": text},
            {"type": "tool_use", "id": tu_id, "name": "now", "input": {}},
        ],
    }


def _tool_result(tu_id: str = "tu1", text: str = "ok") -> dict:
    return {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tu_id, "content": text}],
    }


@pytest.mark.asyncio
async def test_below_threshold_returns_original(monkeypatch, isolated_data_root):
    """Short conversations pass through untouched — no LLM call."""
    monkeypatch.setenv("ICE_COMPACTION_THRESHOLD_MSGS", "40")
    monkeypatch.setenv("ICE_COMPACTION_KEEP_LAST", "20")
    from app.core.config import get_settings

    get_settings.cache_clear()

    msgs = [_msg("user", f"m{i}") for i in range(10)]
    out = await compaction_svc.maybe_compact(task_id="t", conv_id="c", api_messages=msgs)
    assert out == msgs


@pytest.mark.asyncio
async def test_above_threshold_triggers_summary(monkeypatch, isolated_data_root):
    """When the threshold is exceeded, the head is replaced by a synthetic
    summary and the tail is preserved verbatim. LLM is mocked."""
    monkeypatch.setenv("ICE_COMPACTION_THRESHOLD_MSGS", "10")
    monkeypatch.setenv("ICE_COMPACTION_KEEP_LAST", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()

    calls = {"n": 0}

    async def fake_complete_once(**kwargs):
        calls["n"] += 1
        return {"text": "FAKE SUMMARY", "usage": {}, "model": "mock"}

    from app.services import llm_gateway
    monkeypatch.setattr(llm_gateway, "complete_once", fake_complete_once)

    msgs = [_msg("user" if i % 2 == 0 else "assistant", f"m{i}") for i in range(20)]
    out = await compaction_svc.maybe_compact(task_id="t-c", conv_id="c", api_messages=msgs)
    # First message is the synthetic summary marker + fake summary body.
    assert out[0]["role"] == "user"
    assert "FAKE SUMMARY" in out[0]["content"]
    assert "历史摘要" in out[0]["content"]
    # Tail count is 5.
    assert len(out) == 6  # 1 summary + 5 kept
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_cache_reused_on_same_head(monkeypatch, isolated_data_root):
    """Second call with the same compacted head does not re-invoke the LLM."""
    monkeypatch.setenv("ICE_COMPACTION_THRESHOLD_MSGS", "10")
    monkeypatch.setenv("ICE_COMPACTION_KEEP_LAST", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()

    calls = {"n": 0}

    async def fake(**kwargs):
        calls["n"] += 1
        return {"text": "SUMMARY", "usage": {}, "model": "mock"}

    from app.services import llm_gateway
    monkeypatch.setattr(llm_gateway, "complete_once", fake)

    msgs = [_msg("user", f"m{i}") for i in range(20)]
    await compaction_svc.maybe_compact(task_id="t-cc", conv_id="c", api_messages=msgs)
    await compaction_svc.maybe_compact(task_id="t-cc", conv_id="c", api_messages=msgs)
    assert calls["n"] == 1  # cache hit on the second call


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_truncation(monkeypatch, isolated_data_root):
    monkeypatch.setenv("ICE_COMPACTION_THRESHOLD_MSGS", "10")
    monkeypatch.setenv("ICE_COMPACTION_KEEP_LAST", "5")
    from app.core.config import get_settings

    get_settings.cache_clear()

    async def boom(**kwargs):
        raise RuntimeError("gateway down")

    from app.services import llm_gateway
    monkeypatch.setattr(llm_gateway, "complete_once", boom)

    msgs = [_msg("user", f"m{i}") for i in range(20)]
    out = await compaction_svc.maybe_compact(task_id="t-x", conv_id="c", api_messages=msgs)
    # Fallback returns exactly the tail (no summary injected).
    assert len(out) == 5
    assert out == msgs[-5:]


def test_adjust_split_avoids_tool_result_boundary():
    """_adjust_split extends the tail backward so the first kept message is
    NOT a tool_result-only user message (which would orphan the tool_use)."""
    msgs = [
        _msg("user", "intro"),
        _tool_use("doing", "x1"),
        _tool_result("x1"),
        _msg("assistant", "ok"),
        _tool_use("doing", "x2"),
        _tool_result("x2"),
        _msg("assistant", "done"),
        _msg("user", "followup"),
    ]
    # Asking to keep the last 2 would split right at msg[6] (assistant "done").
    # That IS a clean boundary so it should return index 6.
    idx = compaction_svc._adjust_split(msgs, 2)
    assert idx == 6
    # Asking to keep the last 3 would naturally split at msg[5] (a tool_result
    # user) — the boundary must be adjusted backward.
    idx2 = compaction_svc._adjust_split(msgs, 3)
    assert idx2 < 5  # pulled back past the tool_result
    # Specifically, the first kept message should be a clean start.
    assert compaction_svc._is_clean_boundary(msgs[idx2])
