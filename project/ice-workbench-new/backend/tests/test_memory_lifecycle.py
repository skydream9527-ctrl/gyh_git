"""Tests for memory_lifecycle.py — metadata enrichment, usage bump, HISTORY.jsonl."""
from __future__ import annotations

import json

import pytest

from app.core.storage import get_paths
from app.services.task.context_svc import (
    ContextPaths,
    MemoryEntry,
    MemoryWriter,
    _atomic_write_text,
    _memory_file,
    _parse_frontmatter,
)
from app.services.task.memory_lifecycle import (
    append_task_history,
    bump_entries,
    bump_usage,
    enrich_entry,
    render_memory_file,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _entry(slug: str, **kwargs) -> MemoryEntry:
    return MemoryEntry(
        slug=slug,
        title=slug,
        hook=slug,
        rel_path=f"{slug}.md",
        line=f"- [{slug}]({slug}.md) - {slug}",
        **kwargs,
    )


def _write_memory_file(base, slug: str, type_: str = "feedback", body: str = "content",
                        confidence: str = "0.80", usage_count: str = "5",
                        last_hit_at: str | None = None):
    """Write a memory file with lifecycle metadata in frontmatter."""
    lines = [
        "---",
        f"name: {slug}",
        f"description: {slug} hook",
        "created_at: 2026-01-15T00:00:00+00:00",
        "updated_at: 2026-05-01T00:00:00+00:00",
        "metadata:",
        f"  type: {type_}",
        f"  confidence: {confidence}",
        f"  usage_count: {usage_count}",
    ]
    if last_hit_at:
        lines.append(f"  last_hit_at: {last_hit_at}")
    lines.extend(["---", "", body, ""])
    path = base / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ─── enrich_entry ─────────────────────────────────────────────────────────────


def test_enrich_entry_reads_metadata(isolated_data_root):
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    _write_memory_file(base, "test-mem", confidence="0.85", usage_count="3",
                        last_hit_at="2026-06-01T12:00:00+00:00")

    entry = _entry("test-mem")
    enriched = enrich_entry(entry, base)

    assert enriched.confidence == 0.85
    assert enriched.usage_count == 3
    assert enriched.last_hit_at == "2026-06-01T12:00:00+00:00"
    assert enriched.created_at == "2026-01-15T00:00:00+00:00"


def test_enrich_entry_missing_file_returns_defaults(isolated_data_root):
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    base.mkdir(parents=True, exist_ok=True)

    entry = _entry("nonexistent")
    enriched = enrich_entry(entry, base)

    # Returns original defaults
    assert enriched.confidence == 1.0
    assert enriched.usage_count == 0
    assert enriched.last_hit_at is None


def test_enrich_entry_legacy_file_without_metadata(isolated_data_root):
    """Legacy memory files (no confidence/usage_count) still parse fine."""
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    base.mkdir(parents=True, exist_ok=True)
    # Write old-style file without lifecycle fields
    legacy_content = _memory_file("legacy-mem", "some hook", "feedback", "body text")
    (base / "legacy-mem.md").write_text(legacy_content, encoding="utf-8")

    entry = _entry("legacy-mem")
    enriched = enrich_entry(entry, base)

    assert enriched.confidence == 1.0  # default
    assert enriched.usage_count == 0   # default


# ─── bump_usage ───────────────────────────────────────────────────────────────


def test_bump_usage_increments_count(isolated_data_root):
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    path = _write_memory_file(base, "bump-test", usage_count="2")

    bump_usage(path)

    text = path.read_text(encoding="utf-8")
    fields, _ = _parse_frontmatter(text)
    metadata = fields.get("metadata", {})
    assert metadata["usage_count"] == "3"
    assert "last_hit_at" in metadata
    assert fields.get("updated_at") is not None


def test_bump_usage_missing_file_no_error(isolated_data_root):
    paths = get_paths()
    fake_path = paths.user_memory_dir("u1") / "nonexistent.md"
    # Should not raise
    bump_usage(fake_path)


def test_bump_entries_updates_multiple(isolated_data_root):
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    _write_memory_file(base, "mem-a", usage_count="0")
    _write_memory_file(base, "mem-b", usage_count="5")

    entries = [_entry("mem-a"), _entry("mem-b")]
    bump_entries(entries, base)

    text_a = (base / "mem-a.md").read_text(encoding="utf-8")
    text_b = (base / "mem-b.md").read_text(encoding="utf-8")
    fields_a, _ = _parse_frontmatter(text_a)
    fields_b, _ = _parse_frontmatter(text_b)
    assert fields_a["metadata"]["usage_count"] == "1"
    assert fields_b["metadata"]["usage_count"] == "6"


# ─── append_task_history ──────────────────────────────────────────────────────


def test_append_task_history_creates_file(isolated_data_root):
    paths = get_paths()
    history_path = paths.task_state_history("t1")

    append_task_history(history_path, content="# State v1", agent_id="analyst", had_previous=False)

    assert history_path.exists()
    lines = history_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["agent_id"] == "analyst"
    assert record["had_previous"] is False
    assert "checksum" in record
    assert "ts" in record


def test_append_task_history_appends_multiple(isolated_data_root):
    paths = get_paths()
    history_path = paths.task_state_history("t2")

    append_task_history(history_path, content="v1", agent_id="a1", had_previous=False)
    append_task_history(history_path, content="v2", agent_id="a1", had_previous=True)
    append_task_history(history_path, content="v3", agent_id="a2", had_previous=True)

    lines = history_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    records = [json.loads(ln) for ln in lines]
    assert records[0]["had_previous"] is False
    assert records[1]["had_previous"] is True
    assert records[2]["agent_id"] == "a2"
    # Checksums differ for different content
    assert records[0]["checksum"] != records[1]["checksum"]


# ─── render_memory_file ───────────────────────────────────────────────────────


def test_render_memory_file_includes_lifecycle_fields():
    output = render_memory_file(
        "test-slug", "hook text", "feedback", "body content",
        confidence=0.9, usage_count=3,
    )
    fields, body = _parse_frontmatter(output)

    assert fields["name"] == "test-slug"
    assert fields["description"] == "hook text"
    assert "created_at" in fields
    assert "updated_at" in fields
    metadata = fields["metadata"]
    assert metadata["type"] == "feedback"
    assert metadata["confidence"] == "0.90"
    assert metadata["usage_count"] == "3"
    assert body.strip() == "body content"


def test_render_memory_file_preserves_existing_created_at():
    output = render_memory_file(
        "slug", "hook", "project", "body",
        created_at="2026-01-01T00:00:00+00:00",
    )
    fields, _ = _parse_frontmatter(output)
    assert fields["created_at"] == "2026-01-01T00:00:00+00:00"


# ─── Integration: save_task_state writes HISTORY.jsonl ────────────────────────


def test_save_task_state_writes_history(isolated_data_root):
    paths = get_paths()
    ctx = ContextPaths(user_id="u1", agent_id="analyst", task_id="t1")
    writer = MemoryWriter(ctx)

    writer.save_task_state("# Phase 1\ncontent")
    writer.save_task_state("# Phase 2\nupdated")

    history_path = paths.task_state_history("t1")
    assert history_path.exists()
    lines = history_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    r0 = json.loads(lines[0])
    r1 = json.loads(lines[1])
    assert r0["had_previous"] is False
    assert r1["had_previous"] is True
    assert r0["agent_id"] == "analyst"
