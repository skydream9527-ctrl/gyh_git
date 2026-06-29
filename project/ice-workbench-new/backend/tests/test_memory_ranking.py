"""Tests for memory_ranking.py — BM25 + composite scoring engine."""
from __future__ import annotations

import pytest

from app.services.task.context_svc import MemoryEntry
from app.services.task.memory_ranking import (
    BM25Scorer,
    _apply_budget,
    _rank_by_metadata,
    confidence_factor,
    rank_entries,
    recency_boost,
    tokenize,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _entry(slug: str, title: str = "", hook: str = "", **kwargs) -> MemoryEntry:
    """Helper to create a MemoryEntry with minimal boilerplate."""
    return MemoryEntry(
        slug=slug,
        title=title or slug,
        hook=hook or slug,
        rel_path=f"{slug}.md",
        line=f"- [{title or slug}]({slug}.md) - {hook or slug}",
        **kwargs,
    )


# ─── Tokenizer ────────────────────────────────────────────────────────────────


def test_tokenize_english():
    tokens = tokenize("Hello world, this is a test")
    assert "hello" in tokens
    assert "world" in tokens
    # Single-char tokens filtered out
    assert "a" not in tokens


def test_tokenize_chinese():
    tokens = tokenize("DAU 下跌分析报告")
    assert "dau" in tokens
    # CJK sequences are treated as single tokens by the \w+ regex
    assert "下跌分析报告" in tokens


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize(None) == []


# ─── BM25Scorer ───────────────────────────────────────────────────────────────


def test_bm25_basic_relevance():
    corpus = [
        ["dau", "definition", "uv"],
        ["report", "style", "conclusion"],
        ["gray", "release", "rollback"],
    ]
    scorer = BM25Scorer(corpus)

    # "dau" should score highest for doc 0
    scores = [scorer.score(["dau"], i) for i in range(3)]
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
    assert scores[1] == 0.0  # no match


def test_bm25_multi_token_query():
    corpus = [
        ["dau", "uv", "drop", "analysis"],
        ["report", "style"],
        ["dau", "gray", "release"],
    ]
    scorer = BM25Scorer(corpus)

    # "dau analysis" matches doc 0 (2 tokens) better than doc 2 (1 token)
    scores = [scorer.score(["dau", "analysis"], i) for i in range(3)]
    assert scores[0] > scores[2] > scores[1]


def test_bm25_empty_query():
    corpus = [["hello", "world"]]
    scorer = BM25Scorer(corpus)
    assert scorer.score([], 0) == 0.0


def test_bm25_empty_corpus():
    scorer = BM25Scorer([])
    assert scorer.n == 0


# ─── Recency & Confidence ─────────────────────────────────────────────────────


def test_recency_boost_no_history():
    assert recency_boost(None) == 0.7


def test_recency_boost_recent():
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc).isoformat()
    boost = recency_boost(now)
    # Just hit: should be very close to 1.0
    assert boost > 0.95


def test_recency_boost_old():
    # 28 days ago = 2 half-lives -> ~0.25
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(tz=timezone.utc) - timedelta(days=28)).isoformat()
    boost = recency_boost(old)
    assert 0.2 < boost < 0.3


def test_recency_boost_invalid_timestamp():
    assert recency_boost("not-a-date") == 0.7


def test_confidence_factor_boundaries():
    assert confidence_factor(0.0) == 0.5
    assert confidence_factor(1.0) == 1.0
    assert confidence_factor(0.5) == 0.75
    # Clamp out-of-range
    assert confidence_factor(-1.0) == 0.5
    assert confidence_factor(2.0) == 1.0


# ─── rank_entries (integration) ───────────────────────────────────────────────


def test_rank_entries_with_query():
    entries = [
        _entry("dau-definition", "DAU 口径", "UV 去重逻辑"),
        _entry("report-style", "报告风格", "结论先行 SQL 进附录"),
        _entry("v72-gray", "v7.2 灰度", "灰度冲突中 回滚风险"),
    ]
    result = rank_entries(entries, "DAU 下跌", limit=5)
    assert result[0].slug == "dau-definition"


def test_rank_entries_no_query_returns_all_within_budget():
    entries = [_entry(f"entry-{i}") for i in range(10)]
    result = rank_entries(entries, None, limit=20, token_budget_chars=10000)
    assert len(result) == 10


def test_rank_entries_empty_list():
    assert rank_entries([], "anything", limit=5) == []


def test_rank_entries_no_bm25_hits_falls_back():
    entries = [
        _entry("alpha", "Alpha Topic", "something about alpha"),
        _entry("beta", "Beta Topic", "something about beta"),
    ]
    # Query with no matching tokens
    result = rank_entries(entries, "zzzzz_nomatch", limit=5)
    # Falls back to metadata-ranked top 3
    assert len(result) <= 3
    assert len(result) > 0


def test_rank_entries_confidence_affects_order():
    entries = [
        _entry("low-conf", "Low", "keyword match", confidence=0.2),
        _entry("high-conf", "High", "keyword match", confidence=1.0),
    ]
    result = rank_entries(entries, "keyword match", limit=5)
    assert result[0].slug == "high-conf"


def test_rank_entries_recency_affects_order():
    from datetime import datetime, timedelta, timezone
    recent = datetime.now(tz=timezone.utc).isoformat()
    old = (datetime.now(tz=timezone.utc) - timedelta(days=60)).isoformat()

    entries = [
        _entry("old-hit", "Topic", "keyword", confidence=1.0, last_hit_at=old),
        _entry("recent-hit", "Topic", "keyword", confidence=1.0, last_hit_at=recent),
    ]
    result = rank_entries(entries, "keyword", limit=5)
    assert result[0].slug == "recent-hit"


# ─── Token Budget ─────────────────────────────────────────────────────────────


def test_apply_budget_respects_char_limit():
    entries = [_entry(f"entry-{i}", hook="x" * 20) for i in range(20)]
    # Each entry ≈ ~90 chars (line + hook + 50 overhead). Budget of 400 should fit ~4
    result = _apply_budget(entries, limit=20, budget_chars=400)
    assert 3 <= len(result) <= 6


def test_apply_budget_always_includes_first():
    """Even if a single entry exceeds budget, it's still included."""
    entries = [_entry("big", hook="x" * 5000)]
    result = _apply_budget(entries, limit=10, budget_chars=100)
    assert len(result) == 1


def test_apply_budget_respects_limit():
    entries = [_entry(f"e-{i}", hook="short") for i in range(100)]
    result = _apply_budget(entries, limit=5, budget_chars=100000)
    assert len(result) == 5
