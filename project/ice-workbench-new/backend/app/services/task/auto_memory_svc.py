"""Auto-memory extraction — distill reusable insights from completed conversations.

After a conversation turn completes successfully (agent produced final_text with
tool results), this module checks whether the exchange contains patterns worth
persisting as Agent Memory. It runs as a fire-and-forget background task so it
never blocks the WS response.

Criteria for extraction:
- The turn involved at least 2 tool calls (non-trivial work was done)
- The agent's final text contains conclusion-like patterns
- The conclusion isn't purely procedural (not just "done" / "已完成")
- The same insight hasn't been saved recently (dedup by content hash)

Extracted insights are saved with type="project" to the user's agent-scoped
memory, making them available in subsequent conversations with the same agent.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("auto_memory")

# ─── Configuration ────────────────────────────────────────────────────────────

# Minimum requirements for triggering extraction
MIN_FINAL_TEXT_LENGTH = 120
MIN_TOOL_CALLS = 2

# Patterns that indicate a meaningful conclusion worth saving
_INSIGHT_PATTERNS = [
    re.compile(r"(?:^|\n)#+\s*(?:结论|总结|分析结果|关键发现|建议|结果|核心结论)", re.IGNORECASE),
    re.compile(r"(?:^|\n)(?:\*\*)?(?:结论|总结|发现|核心结论|关键发现|分析结论|下一步)(?:\*\*)?[：:]", re.IGNORECASE),
    re.compile(r"(?:综上所述|因此|总的来说|根据以上分析|综合来看)[，,：:]", re.IGNORECASE),
]

# Patterns indicating the text is too procedural to save
_SKIP_PATTERNS = [
    re.compile(r"^(?:好的|没问题|已完成|done|ok)\s*[。.!]?\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:请问|你想|需要我|还有什么)", re.IGNORECASE),
]

# Maximum insights per turn
MAX_INSIGHTS = 2


# ─── Public API ───────────────────────────────────────────────────────────────


async def maybe_extract_and_save(
    *,
    user_id: str,
    agent_id: str,
    task_id: str,
    final_text: str,
    tool_attempt_count: int,
    tool_success_count: int,
    task_name: str | None = None,
) -> list[dict]:
    """Analyze a completed turn and save any reusable insights to agent memory.

    This should be called as a fire-and-forget task (asyncio.create_task) so it
    doesn't block the WS response.

    Returns list of saved memory entries (empty if nothing worth saving).
    """
    if not final_text or len(final_text) < MIN_FINAL_TEXT_LENGTH:
        return []
    if tool_attempt_count < MIN_TOOL_CALLS:
        return []
    if tool_success_count == 0:
        return []

    # Check if text is too procedural
    for pattern in _SKIP_PATTERNS:
        if pattern.search(final_text):
            return []

    # Extract conclusion sections
    insights = _extract_conclusions(final_text, task_name or "")
    if not insights:
        return []

    # Save to agent memory
    from .context_svc import ContextPaths, MemoryWriter

    writer = MemoryWriter(ContextPaths(user_id=user_id, agent_id=agent_id, task_id=task_id))
    saved: list[dict] = []

    for insight in insights[:MAX_INSIGHTS]:
        slug = _make_slug(agent_id, insight["hook"])
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
                log.info(
                    "auto_memory: saved insight '%s' for user=%s agent=%s",
                    slug, user_id[:8], agent_id,
                )
        except Exception as exc:
            log.debug("auto_memory: save failed for slug=%s: %s", slug, exc)
            continue

    return saved


# ─── Extraction Logic ─────────────────────────────────────────────────────────


def _extract_conclusions(text: str, task_name: str) -> list[dict]:
    """Extract structured conclusion sections from the final text."""
    insights: list[dict] = []

    for pattern in _INSIGHT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        start = match.end()
        section = _extract_section(text, start)
        if not section or len(section) < 30:
            continue

        hook = _first_meaningful_line(section)
        if not hook or len(hook) < 10:
            continue

        # Dedup: skip if we already have an insight with very similar hook
        if any(_similar(hook, existing["hook"]) for existing in insights):
            continue

        insights.append({
            "title": f"自动沉淀 · {task_name[:30]}" if task_name else "自动沉淀 · 分析结论",
            "hook": hook[:100],
            "body": (
                f"**来源**: 任务「{task_name[:60]}」的对话结论\n"
                f"**时间**: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}\n\n"
                f"{section[:1000]}"
            ),
        })

    return insights


def _extract_section(text: str, start: int, max_len: int = 800) -> str:
    """Extract text from position up to next heading or max_len."""
    end = start + max_len
    next_heading = re.search(r"\n#+\s", text[start:end])
    if next_heading:
        end = start + next_heading.start()
    return text[start:end].strip()


def _first_meaningful_line(section: str) -> str | None:
    """Get the first non-trivial line as a summary hook."""
    for line in section.split("\n"):
        line = line.strip().lstrip("- *•·>")
        if len(line) > 15 and not line.startswith("|"):
            return line[:120]
    return None


def _similar(a: str, b: str) -> bool:
    """Quick similarity check — if first 40 chars match, consider duplicate."""
    return a[:40] == b[:40]


def _make_slug(agent_id: str, hook: str) -> str:
    """Deterministic slug from agent + hook content."""
    content_hash = hashlib.sha256(f"{agent_id}:{hook}".encode()).hexdigest()[:8]
    base = re.sub(r"[^a-z0-9]", "-", agent_id.lower())[:16]
    slug = f"auto-{base}-{content_hash}"
    return re.sub(r"-+", "-", slug).strip("-")
