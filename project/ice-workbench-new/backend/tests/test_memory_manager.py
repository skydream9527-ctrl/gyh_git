"""Tests for memory_manager.py — decay, archive, and auto-promote."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.storage import get_paths, write_json
from app.services.task.context_svc import (
    ContextPaths,
    MemoryWriter,
    _parse_frontmatter,
    _parse_memory_index,
    _read_text,
    _MAX_CONTEXT_BYTES,
)
from app.services.task.memory_lifecycle import render_memory_file
from app.services.task.memory_manager import (
    ARCHIVE_THRESHOLD_DAYS,
    STALE_THRESHOLD_DAYS,
    MemoryLifecycleManager,
    auto_promote_candidates,
    promote_to_team,
)
from app.services.task.team_memory import ensure_team


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _create_user(uid: str, team: str | None = None):
    paths = get_paths()
    paths.user_dir(uid).mkdir(parents=True, exist_ok=True)
    profile = {"id": uid, "email": f"{uid}@test.com", "name": uid}
    if team:
        profile["team"] = team
    write_json(paths.user_profile(uid), profile)


def _write_project_memory(uid: str, slug: str, last_hit_days_ago: float, *, stale: bool = False, stale_days_ago: float = 0):
    """Write a project-type memory with controlled timestamps."""
    paths = get_paths()
    base = paths.user_memory_dir(uid)
    base.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=timezone.utc)
    last_hit = (now - timedelta(days=last_hit_days_ago)).isoformat()

    lines = [
        "---",
        f"name: {slug}",
        f"description: {slug} hook",
        f"created_at: {(now - timedelta(days=60)).isoformat()}",
        f"updated_at: {last_hit}",
        "metadata:",
        "  type: project",
        f"  usage_count: 3",
        f"  last_hit_at: {last_hit}",
    ]
    if stale:
        stale_since = (now - timedelta(days=stale_days_ago)).isoformat()
        lines.append("  status: stale")
        lines.append(f"  stale_since: {stale_since}")
    lines.extend(["---", "", f"{slug} body content", ""])
    (base / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")

    # Ensure index has the entry
    index = paths.user_memory_index(uid)
    existing = index.read_text(encoding="utf-8") if index.exists() else ""
    if f"{slug}.md" not in existing:
        with open(index, "a", encoding="utf-8") as f:
            f.write(f"- [{slug}]({slug}.md) - {slug} hook\n")


def _write_agent_memory(uid: str, agent_id: str, slug: str, usage_count: int = 5):
    """Write an agent memory file with a controlled usage count."""
    paths = get_paths()
    base = paths.user_agent_memory_dir(uid, agent_id)
    base.mkdir(parents=True, exist_ok=True)

    content = render_memory_file(
        slug, f"{slug} hook", "feedback", f"{slug} body",
        usage_count=usage_count, confidence=0.9,
    )
    (base / f"{slug}.md").write_text(content, encoding="utf-8")

    index = paths.user_agent_memory_index(uid, agent_id)
    existing = index.read_text(encoding="utf-8") if index.exists() else ""
    if f"{slug}.md" not in existing:
        with open(index, "a", encoding="utf-8") as f:
            f.write(f"- [{slug}]({slug}.md) - {slug} hook\n")


# ─── Decay Tests ──────────────────────────────────────────────────────────────


def test_decay_marks_old_project_stale(isolated_data_root):
    _create_user("u1")
    _write_project_memory("u1", "old-project", last_hit_days_ago=35)

    mgr = MemoryLifecycleManager("u1")
    report = mgr.run_sweep()

    assert "old-project" in report["user_memory"]["stale_marked"]

    # Verify the file was updated
    paths = get_paths()
    text = (paths.user_memory_dir("u1") / "old-project.md").read_text(encoding="utf-8")
    fields, _ = _parse_frontmatter(text)
    assert fields["metadata"]["status"] == "stale"
    assert "stale_since" in fields["metadata"]


def test_decay_skips_recent_project(isolated_data_root):
    _create_user("u1")
    _write_project_memory("u1", "recent-project", last_hit_days_ago=5)

    mgr = MemoryLifecycleManager("u1")
    report = mgr.run_sweep()

    assert report["user_memory"]["stale_marked"] == []
    assert report["user_memory"]["archived"] == []


def test_decay_skips_non_project_types(isolated_data_root):
    """Only project-type entries are subject to decay."""
    _create_user("u1")
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    base.mkdir(parents=True, exist_ok=True)
    # Write a feedback-type entry that's very old
    content = render_memory_file("old-feedback", "hook", "feedback", "body", usage_count=0)
    (base / "old-feedback.md").write_text(content, encoding="utf-8")
    index = paths.user_memory_index("u1")
    with open(index, "a", encoding="utf-8") as f:
        f.write("- [old-feedback](old-feedback.md) - hook\n")

    mgr = MemoryLifecycleManager("u1")
    report = mgr.run_sweep()

    assert report["user_memory"]["stale_marked"] == []


# ─── Archive Tests ────────────────────────────────────────────────────────────


def test_archive_moves_stale_entry(isolated_data_root):
    _create_user("u1")
    _write_project_memory("u1", "stale-entry", last_hit_days_ago=45, stale=True, stale_days_ago=10)

    mgr = MemoryLifecycleManager("u1")
    report = mgr.run_sweep()

    assert "stale-entry" in report["user_memory"]["archived"]

    paths = get_paths()
    # Original file should be gone
    assert not (paths.user_memory_dir("u1") / "stale-entry.md").exists()
    # Should be in archive
    assert (paths.user_memory_archive_dir("u1") / "stale-entry.md").exists()
    # Should be removed from index
    index_text = paths.user_memory_index("u1").read_text(encoding="utf-8")
    assert "stale-entry" not in index_text


def test_archive_skips_recently_stale(isolated_data_root):
    """Entries that became stale less than ARCHIVE_THRESHOLD_DAYS ago are kept."""
    _create_user("u1")
    _write_project_memory("u1", "new-stale", last_hit_days_ago=35, stale=True, stale_days_ago=3)

    mgr = MemoryLifecycleManager("u1")
    report = mgr.run_sweep()

    assert report["user_memory"]["archived"] == []
    paths = get_paths()
    assert (paths.user_memory_dir("u1") / "new-stale.md").exists()


# ─── Auto-Promote Tests ──────────────────────────────────────────────────────


def test_auto_promote_finds_candidates(isolated_data_root):
    _create_user("u1")
    _create_user("u2")
    _create_user("u3")

    # Same slug in multiple users' agent memory
    _write_agent_memory("u1", "data-analysis", "common-insight", usage_count=5)
    _write_agent_memory("u2", "data-analysis", "common-insight", usage_count=4)
    _write_agent_memory("u3", "data-analysis", "common-insight", usage_count=3)

    candidates = auto_promote_candidates("data-analysis")
    assert len(candidates) == 1
    assert candidates[0]["slug"] == "common-insight"
    assert len(candidates[0]["authors"]) == 3


def test_auto_promote_skips_low_usage(isolated_data_root):
    _create_user("u1")
    _create_user("u2")

    _write_agent_memory("u1", "analyst", "low-usage", usage_count=1)
    _write_agent_memory("u2", "analyst", "low-usage", usage_count=2)

    candidates = auto_promote_candidates("analyst")
    assert candidates == []


def test_auto_promote_skips_single_user(isolated_data_root):
    _create_user("u1")
    _write_agent_memory("u1", "analyst", "personal", usage_count=10)

    candidates = auto_promote_candidates("analyst")
    assert candidates == []


def test_promote_to_team_writes_memory(isolated_data_root):
    _create_user("u1", team="my-team")
    _create_user("u2", team="my-team")
    ensure_team("my-team")

    _write_agent_memory("u1", "data-analysis", "shared-rule", usage_count=5)
    _write_agent_memory("u2", "data-analysis", "shared-rule", usage_count=4)

    promoted = promote_to_team("data-analysis", "my-team")
    assert len(promoted) == 1
    assert promoted[0]["slug"] == "shared-rule"

    # Verify team memory was written
    paths = get_paths()
    team_file = paths.team_memory_dir("my-team") / "shared-rule.md"
    assert team_file.exists()
    content = team_file.read_text(encoding="utf-8")
    assert "Auto-promoted" in content


def test_promote_to_team_dry_run(isolated_data_root):
    _create_user("u1")
    _create_user("u2")
    ensure_team("dry-team")

    _write_agent_memory("u1", "analyst", "dry-rule", usage_count=5)
    _write_agent_memory("u2", "analyst", "dry-rule", usage_count=4)

    promoted = promote_to_team("analyst", "dry-team", dry_run=True)
    assert len(promoted) == 1

    # Nothing actually written
    paths = get_paths()
    assert not (paths.team_memory_dir("dry-team") / "dry-rule.md").exists()
