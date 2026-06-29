"""BM25 + recency + confidence composite scoring for memory retrieval.

Replaces the naive keyword-intersection ranking in context_svc._rank_entries
with a proper information-retrieval scorer. Designed as a standalone module
so context_svc.py changes are minimal (one import swap).

Scoring formula per entry:
    score = bm25(query, doc) × confidence_factor × recency_boost

Where:
- bm25: Okapi BM25 relevance between query tokens and entry text
- confidence_factor: 0.5 + 0.5 × entry.confidence (range 0.5–1.0)
- recency_boost: exponential decay based on days since last_hit_at (half-life 14d)
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context_svc import MemoryEntry

# ─── Tokenizer ────────────────────────────────────────────────────────────────


def tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens (words + CJK characters ≥2 chars)."""
    return [t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", text or "") if len(t) > 1]


def tokenize_set(text: str) -> set[str]:
    """Unique token set for deduplication checks."""
    return set(tokenize(text))


# ─── BM25 Core ────────────────────────────────────────────────────────────────


class BM25Scorer:
    """Okapi BM25 scorer for a small in-memory corpus of memory entries.

    Parameters:
        k1: term frequency saturation parameter (default 1.5)
        b: length normalization parameter (default 0.75)
    """

    def __init__(self, corpus: list[list[str]], *, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.n = len(corpus)
        self.corpus = corpus
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_lengths) / self.n if self.n else 1.0

        # Pre-compute document frequency for each unique term
        self.df: dict[str, int] = {}
        for doc in corpus:
            seen: set[str] = set()
            for token in doc:
                if token not in seen:
                    self.df[token] = self.df.get(token, 0) + 1
                    seen.add(token)

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        """Compute BM25 score for a single document against query tokens."""
        if doc_idx >= self.n:
            return 0.0
        doc = self.corpus[doc_idx]
        dl = self.doc_lengths[doc_idx]

        # Build term frequency map for this doc
        tf_map: dict[str, int] = {}
        for token in doc:
            tf_map[token] = tf_map.get(token, 0) + 1

        total = 0.0
        for token in query_tokens:
            if token not in tf_map:
                continue
            tf = tf_map[token]
            df = self.df.get(token, 0)
            # IDF with floor to avoid negative values for very common terms
            idf = math.log((self.n - df + 0.5) / (df + 0.5) + 1.0)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            total += idf * numerator / denominator
        return total


# ─── Composite Scoring ────────────────────────────────────────────────────────


def recency_boost(last_hit_at: str | None, *, half_life_days: float = 14.0) -> float:
    """Exponential decay: 1.0 if hit now, halves every `half_life_days`.

    Returns 0.7 for entries with no hit history (slight penalty vs recently used).
    """
    if not last_hit_at:
        return 0.7
    try:
        hit_dt = datetime.fromisoformat(last_hit_at)
        now_dt = datetime.now(tz=timezone.utc)
        days_ago = max(0.0, (now_dt - hit_dt).total_seconds() / 86400)
    except (ValueError, TypeError):
        return 0.7
    return math.exp(-0.693 * days_ago / half_life_days)


def confidence_factor(confidence: float) -> float:
    """Map confidence [0, 1] to a scoring multiplier [0.5, 1.0]."""
    return 0.5 + 0.5 * max(0.0, min(1.0, confidence))


def rank_entries(
    entries: list[MemoryEntry],
    query: str | None,
    *,
    limit: int = 20,
    token_budget_chars: int = 4000,
) -> list[MemoryEntry]:
    """Rank memory entries with BM25 + metadata composite scoring.

    Args:
        entries: parsed MemoryEntry list from the MEMORY.md index
        query: current user query (None = no relevance signal, rank by metadata)
        limit: hard upper-bound on returned entries (failsafe)
        token_budget_chars: approximate char budget; selection stops when exceeded

    Returns:
        Ranked list of entries fitting within the budget.
    """
    if not entries:
        return []

    # No query: rank by confidence × recency only
    if not query:
        ranked = _rank_by_metadata(entries)
        return _apply_budget(ranked, limit, token_budget_chars)

    q_tokens = tokenize(query)
    if not q_tokens:
        ranked = _rank_by_metadata(entries)
        return _apply_budget(ranked, limit, token_budget_chars)

    # Build BM25 corpus from entry text (slug + title + hook)
    corpus = [tokenize(f"{e.slug} {e.title} {e.hook}") for e in entries]
    scorer = BM25Scorer(corpus)

    scored: list[tuple[float, int, MemoryEntry]] = []
    for idx, entry in enumerate(entries):
        bm25 = scorer.score(q_tokens, idx)
        if bm25 <= 0:
            continue
        composite = (
            bm25
            * confidence_factor(entry.confidence)
            * recency_boost(entry.last_hit_at)
        )
        scored.append((composite, -idx, entry))  # -idx for stable sort

    if not scored:
        # No BM25 hits — fallback to top entries by metadata score
        fallback = _rank_by_metadata(entries)
        return _apply_budget(fallback, min(limit, 3), token_budget_chars)

    scored.sort(reverse=True)
    ranked = [entry for _, _, entry in scored]
    return _apply_budget(ranked, limit, token_budget_chars)


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _rank_by_metadata(entries: list[MemoryEntry]) -> list[MemoryEntry]:
    """Sort entries by confidence × recency when no query relevance is available."""
    scored: list[tuple[float, int, MemoryEntry]] = []
    for idx, entry in enumerate(entries):
        score = confidence_factor(entry.confidence) * recency_boost(entry.last_hit_at)
        scored.append((score, -idx, entry))
    scored.sort(reverse=True)
    return [entry for _, _, entry in scored]


def _apply_budget(
    entries: list[MemoryEntry],
    limit: int,
    budget_chars: int,
) -> list[MemoryEntry]:
    """Select top entries until char budget is exhausted or limit is reached.

    Approximates the context cost of each entry as:
        index_line + hook + ~50 chars structural overhead
    """
    selected: list[MemoryEntry] = []
    chars_used = 0
    for entry in entries[:limit]:
        entry_chars = len(entry.line) + len(entry.hook) + 50
        if chars_used + entry_chars > budget_chars and selected:
            break
        selected.append(entry)
        chars_used += entry_chars
    return selected
