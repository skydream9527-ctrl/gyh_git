"""Sub-agent feedback loop — extract reusable insights from sub-agent results.

After spawn_subagent returns, this module analyzes the result text for
reusable conclusions and automatically saves them as Agent Memory entries.

Extraction heuristics:
1. Look for structured sections: "结论", "Conclusion", "Key Finding", "建议"
2. If the sub-agent produced a definitive factual answer (not a question/clarification),
   it's likely reusable
3. Skip results that are purely procedural (just SQL output, raw data tables)

The extracted insights are saved with confidence=0.7 (needs verification by
repeated use to reach promotion threshold).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .context_svc import ContextPaths, MemoryWriter, _sanitize_slug

# ─── Configuration ────────────────────────────────────────────────────────────

# Minimum result length to consider for extraction (skip trivial responses)
MIN_RESULT_LENGTH = 100

# Maximum number of insights to extract per sub-agent run
MAX_INSIGHTS_PER_RUN = 2

# Confidence assigned to auto-extracted insights (lower than user-confirmed)
AUTO_EXTRACT_CONFIDENCE = 0.7

# Patterns indicating reusable conclusions
_CONCLUSION_PATTERNS = [
    re.compile(r"(?:^|\n)#+\s*(?:结论|结果|结果总结|key\s*finding|conclusion|建议|recommendation)", re.IGNORECASE),
    re.compile(r"(?:^|\n)(?:\*\*)?(?:结论|总结|发现|核心结论|关键发现)(?:\*\*)?[：:]", re.IGNORECASE),
]

# Patterns indicating procedural/raw output (not worth saving)
_SKIP_PATTERNS = [
    re.compile(r"^```sql\b", re.MULTILINE),
    re.compile(r"\|\s*\w+\s*\|.*\|.*\n\|[-\s|]+\|", re.MULTILINE),  # markdown table header
]


# ─── Public API ───────────────────────────────────────────────────────────────


def extract_and_save_insights(
    *,
    sub_agent_id: str,
    result_text: str,
    task_description: str,
    user_id: str,
    parent_agent_id: str,
) -> list[dict]:
    """Analyze sub-agent output and save reusable insights as Agent Memory.

    Args:
        sub_agent_id: the agent that produced the result
        result_text: the sub-agent's final_text output
        task_description: what the sub-agent was asked to do
        user_id: current user (for memory scoping)
        parent_agent_id: the parent agent that spawned the sub-agent

    Returns:
        List of saved memory entries (may be empty if nothing worth saving).
    """
    if not result_text or len(result_text) < MIN_RESULT_LENGTH:
        return []

    # Skip mostly-procedural outputs
    for pattern in _SKIP_PATTERNS:
        matches = pattern.findall(result_text)
        # If >50% of content is tables/SQL, skip
        if len(matches) > 3:
            return []

    insights = _extract_insights(result_text, task_description)
    if not insights:
        return []

    saved: list[dict] = []
    writer = MemoryWriter(ContextPaths(user_id=user_id, agent_id=parent_agent_id))

    for insight in insights[:MAX_INSIGHTS_PER_RUN]:
        slug = _insight_slug(sub_agent_id, insight["hook"])
        try:
            result = writer.save_memory(
                scope="agent",
                slug=slug,
                title=insight["title"],
                hook=insight["hook"],
                type_="project",
                body=insight["body"],
            )
            if result.get("saved"):
                saved.append({"slug": slug, **insight})
        except (ValueError, Exception):
            continue

    return saved


# ─── Extraction Logic ─────────────────────────────────────────────────────────


def _extract_insights(text: str, task_description: str) -> list[dict]:
    """Extract conclusion-like sections from sub-agent output."""
    insights: list[dict] = []

    for pattern in _CONCLUSION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        # Extract the section after the heading (up to next heading or 500 chars)
        start = match.end()
        section = _extract_section(text, start)
        if not section or len(section) < 30:
            continue

        # Build the insight
        hook = _summarize_hook(section)
        insights.append({
            "title": "来自 sub-agent 的发现",
            "hook": hook,
            "body": (
                f"**来源**: sub-agent 执行 \"{task_description[:100]}\"\n\n"
                f"{section[:800]}"
            ),
        })

    # If no structured conclusion found but text has clear decisive statements
    if not insights:
        decisive = _find_decisive_statement(text)
        if decisive:
            insights.append({
                "title": "sub-agent 发现",
                "hook": decisive[:80],
                "body": (
                    f"**来源**: sub-agent 执行 \"{task_description[:100]}\"\n\n"
                    f"{decisive[:500]}"
                ),
            })

    return insights


def _extract_section(text: str, start: int, max_len: int = 600) -> str:
    """Extract text from start up to the next heading or max_len."""
    end = start + max_len
    # Look for next heading within the window
    next_heading = re.search(r"\n#+\s", text[start:end])
    if next_heading:
        end = start + next_heading.start()
    return text[start:end].strip()


def _summarize_hook(section: str) -> str:
    """Extract first meaningful sentence as the hook."""
    # Take first line that isn't empty or a bullet prefix
    for line in section.split("\n"):
        line = line.strip().lstrip("- *•·")
        if len(line) > 15:
            return line[:100]
    return section[:80]


def _find_decisive_statement(text: str) -> str | None:
    """Look for strong conclusive patterns in unstructured text."""
    patterns = [
        re.compile(r"(?:因此|综上|总的来说|结论是|所以|最终)[，：:](.{20,200})", re.DOTALL),
        re.compile(r"(?:Therefore|In conclusion|Thus|Overall)[,:]?\s*(.{20,200})", re.IGNORECASE | re.DOTALL),
    ]
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(0).strip()
    return None


def _insight_slug(agent_id: str, hook: str) -> str:
    """Generate a deterministic slug from agent and hook content."""
    content_hash = hashlib.sha256(f"{agent_id}:{hook}".encode()).hexdigest()[:8]
    # Clean up to form a valid slug
    base = re.sub(r"[^a-z0-9]", "-", agent_id.lower())[:20]
    slug = f"insight-{base}-{content_hash}"
    # Ensure it meets slug validation
    slug = re.sub(r"-+", "-", slug).strip("-")
    if len(slug) < 2:
        slug = f"insight-{content_hash}"
    return slug
