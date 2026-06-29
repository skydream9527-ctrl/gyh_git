"""Tests for subagent_feedback.py — feedback loop extraction and storage."""
from __future__ import annotations

import pytest

from app.core.storage import get_paths
from app.services.task.context_svc import _parse_memory_index, _read_text, _MAX_CONTEXT_BYTES
from app.services.task.subagent_feedback import (
    _extract_insights,
    _find_decisive_statement,
    _insight_slug,
    extract_and_save_insights,
)


# ─── Extraction Tests ─────────────────────────────────────────────────────────


def test_extract_insights_from_conclusion_heading():
    text = """
# 分析过程

执行了若干 SQL 查询...

## 结论

CC 消费 UV 下跌主因是视频体裁在 v7.2 灰度期间的曝光量下降 15%，
影响集中在新用户群体（is_new_2024=1），建议优先回滚视频推荐策略。
"""
    insights = _extract_insights(text, "分析 CC DAU 下跌")
    assert len(insights) >= 1
    assert "视频" in insights[0]["body"] or "CC" in insights[0]["body"]


def test_extract_insights_from_bold_conclusion():
    text = """
查询了多个维度的数据...

**结论：** v7.2 的灰度组在视频消费时长上比对照组低 8%，达到显著性阈值。

需要进一步确认是否受节假日影响。
"""
    insights = _extract_insights(text, "对比灰度组")
    assert len(insights) >= 1


def test_extract_insights_from_english_conclusion():
    text = """
After analyzing the metrics across all channels:

## Key Finding

The drop is primarily driven by a 12% decrease in video consumption
among new users in the treatment group. The control group shows no
such decline, confirming the regression is experiment-related.
"""
    insights = _extract_insights(text, "analyze experiment impact")
    assert len(insights) >= 1


def test_extract_insights_decisive_statement():
    text = """
通过对比多个维度的数据，我们发现：

频道维度没有异常。

因此，本次下跌的根本原因是 v7.2 版本在内容中心页面的推荐模型回退导致的曝光质量下降。
"""
    insights = _extract_insights(text, "定位下跌原因")
    assert len(insights) >= 1
    assert "v7.2" in insights[0]["body"] or "推荐模型" in insights[0]["body"]


def test_extract_insights_returns_empty_for_short_text():
    insights = _extract_insights("Too short", "some task")
    assert insights == []


def test_extract_insights_returns_empty_for_procedural():
    text = "No real conclusion here, just data output.\n" * 5
    insights = _extract_insights(text, "query data")
    assert insights == []


# ─── find_decisive_statement ──────────────────────────────────────────────────


def test_find_decisive_zh():
    text = "经过分析，综上：本次 DAU 下跌主因是推荐模型回退，需要尽快回滚。"
    result = _find_decisive_statement(text)
    assert result is not None
    assert "推荐模型" in result


def test_find_decisive_en():
    text = "After investigation, Therefore, the root cause is the A/B test."
    result = _find_decisive_statement(text)
    assert result is not None
    assert "root cause" in result


def test_find_decisive_none():
    text = "Just some regular text without any conclusions."
    assert _find_decisive_statement(text) is None


# ─── _insight_slug ────────────────────────────────────────────────────────────


def test_insight_slug_format():
    slug = _insight_slug("data-analysis", "DAU 下跌主因是推荐回退")
    assert slug.startswith("insight-")
    assert len(slug) >= 10
    # Should be deterministic
    assert slug == _insight_slug("data-analysis", "DAU 下跌主因是推荐回退")


def test_insight_slug_different_inputs():
    s1 = _insight_slug("agent-a", "conclusion 1")
    s2 = _insight_slug("agent-a", "conclusion 2")
    assert s1 != s2


# ─── extract_and_save_insights (integration) ──────────────────────────────────


def test_extract_and_save_saves_to_agent_memory(isolated_data_root):
    paths = get_paths()
    # Ensure user dir exists
    paths.user_dir("u1").mkdir(parents=True, exist_ok=True)

    result_text = """
# 分析结果

执行了 5 条 SQL 查询。

## 结论

通过分频道分析，确认本次 CC 消费 UV 下跌的主因是「推荐频道」贡献了 70% 的跌幅，
且集中在 v7.2 灰度组。建议回滚推荐策略。
"""
    saved = extract_and_save_insights(
        sub_agent_id="data-analysis",
        result_text=result_text,
        task_description="分析 CC DAU 下跌原因",
        user_id="u1",
        parent_agent_id="general",
    )
    assert len(saved) >= 1

    # Verify memory was written
    agent_mem_dir = paths.user_agent_memory_dir("u1", "general")
    index = agent_mem_dir / "MEMORY.md"
    assert index.exists()
    index_text = index.read_text(encoding="utf-8")
    assert saved[0]["slug"] in index_text


def test_extract_and_save_skips_short_result(isolated_data_root):
    paths = get_paths()
    paths.user_dir("u1").mkdir(parents=True, exist_ok=True)

    saved = extract_and_save_insights(
        sub_agent_id="agent",
        result_text="短结果",
        task_description="task",
        user_id="u1",
        parent_agent_id="general",
    )
    assert saved == []


def test_extract_and_save_skips_empty_result(isolated_data_root):
    saved = extract_and_save_insights(
        sub_agent_id="agent",
        result_text="",
        task_description="task",
        user_id="u1",
        parent_agent_id="general",
    )
    assert saved == []
