"""Memory lifecycle management: metadata enrichment, usage tracking, history.

This module handles:
1. Enriching MemoryEntry with file-level metadata (confidence, usage_count, etc.)
2. Bumping usage stats when entries are retrieved
3. Appending incremental state-change records to HISTORY.jsonl

Designed as a standalone helper — context_svc.py calls into this module
without needing structural changes to its own classes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context_svc import MemoryEntry

# ─── HISTORY.jsonl ────────────────────────────────────────────────────────────


def append_task_history(
    history_path: Path,
    *,
    content: str,
    agent_id: str | None = None,
    had_previous: bool = False,
) -> None:
    """Append an incremental state-change record to HISTORY.jsonl.

    Each line records a timestamp, content checksum, and metadata about the
    state transition — enough to reconstruct the timeline without storing
    full snapshots of every version.
    """
    record = {
        "ts": _now(),
        "agent_id": agent_id,
        "checksum": hashlib.sha256(content.encode("utf-8")).hexdigest()[:12],
        "size_bytes": len(content.encode("utf-8")),
        "had_previous": had_previous,
    }
    _append_jsonl(history_path, record)


# ─── Memory Metadata Enrichment ──────────────────────────────────────────────


def enrich_entry(entry: MemoryEntry, base: Path) -> MemoryEntry:
    """Read a memory file's frontmatter and populate lifecycle fields.

    Returns a new MemoryEntry with confidence/usage_count/last_hit_at/created_at
    filled from the file. If the file doesn't exist or lacks the fields, returns
    the original entry unchanged (all defaults are safe).
    """
    from .context_svc import MemoryEntry as ME
    from .context_svc import _parse_frontmatter, _read_text, _safe_child

    target = _safe_child(base, entry.rel_path)
    if target is None:
        return entry
    text = _read_text(target)
    if not text:
        return entry

    fields, _ = _parse_frontmatter(text)
    metadata = fields.get("metadata") or {}

    try:
        confidence = float(metadata.get("confidence", 1.0))
    except (TypeError, ValueError):
        confidence = 1.0
    try:
        usage_count = int(metadata.get("usage_count", 0))
    except (TypeError, ValueError):
        usage_count = 0

    last_hit_at = metadata.get("last_hit_at") or None
    created_at = fields.get("created_at") or None
    visibility = metadata.get("visibility") or "private"

    return ME(
        slug=entry.slug,
        title=entry.title,
        hook=entry.hook,
        rel_path=entry.rel_path,
        line=entry.line,
        confidence=max(0.0, min(1.0, confidence)),
        usage_count=max(0, usage_count),
        last_hit_at=last_hit_at,
        created_at=created_at,
        visibility=visibility if visibility in ("private", "team", "org") else "private",
    )


def enrich_entries(entries: list[MemoryEntry], base: Path) -> list[MemoryEntry]:
    """Batch-enrich a list of entries from their backing files."""
    return [enrich_entry(e, base) for e in entries]


# ─── Usage Bump ───────────────────────────────────────────────────────────────


def bump_usage(memory_path: Path) -> None:
    """Increment usage_count and update last_hit_at in a memory file's frontmatter.

    Best-effort: silently returns on any error (never blocks retrieval).
    """
    from ...core.storage.lock import multi_lock
    from .context_svc import (
        _atomic_write_text,
        _parse_frontmatter,
        _read_text,
        _render_frontmatter,
    )

    try:
        text = _read_text(memory_path)
        if not text:
            return
        fields, body = _parse_frontmatter(text)
        metadata = fields.get("metadata") or {}

        try:
            usage_count = int(metadata.get("usage_count", 0)) + 1
        except (TypeError, ValueError):
            usage_count = 1

        metadata["usage_count"] = str(usage_count)
        metadata["last_hit_at"] = _now()
        fields["metadata"] = metadata
        fields["updated_at"] = _now()

        new_text = _render_frontmatter(fields, body)
        with multi_lock([memory_path]):
            _atomic_write_text(memory_path, new_text)
    except Exception:
        pass  # best-effort; never block the retrieval path


def bump_entries(entries: list[MemoryEntry], base: Path) -> None:
    """Bump usage stats for all retrieved entries (best-effort)."""
    from .context_svc import _safe_child

    for entry in entries:
        target = _safe_child(base, entry.rel_path)
        if target is not None and target.exists():
            bump_usage(target)


# ─── Lifecycle-Aware Memory File Renderer ─────────────────────────────────────


def render_memory_file(
    slug: str,
    hook: str,
    type_: str,
    body: str,
    *,
    created_at: str | None = None,
    confidence: float = 1.0,
    usage_count: int = 0,
    last_hit_at: str | None = None,
    visibility: str = "private",
) -> str:
    """Render a memory file with full lifecycle metadata in frontmatter.

    This is the P0/P1 replacement for context_svc._memory_file, adding:
    - created_at / updated_at timestamps
    - metadata.confidence, metadata.usage_count, metadata.last_hit_at
    - metadata.visibility (private | team | org)
    """
    ts_now = _now()
    created = created_at or ts_now
    lines = [
        "---",
        f"name: {slug}",
        f"description: {hook.strip()}",
        f"created_at: {created}",
        f"updated_at: {ts_now}",
        "metadata:",
        f"  type: {type_}",
        f"  confidence: {confidence:.2f}",
        f"  usage_count: {usage_count}",
    ]
    if last_hit_at:
        lines.append(f"  last_hit_at: {last_hit_at}")
    if visibility and visibility != "private":
        lines.append(f"  visibility: {visibility}")
    lines.extend(["---", "", body.rstrip(), ""])
    return "\n".join(lines)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _append_jsonl(path: Path, record: dict) -> None:
    """Append a single JSON line to a JSONL file (creates parent dirs if needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
