"""Tests for P1: Team Memory layer, visibility, ContextLoader four-layer injection."""
from __future__ import annotations

import pytest

from app.core.storage import get_paths, write_json
from app.services.task.context_svc import ContextPaths, ContextLoader, MemoryEntry, MemoryWriter
from app.services.task.memory_lifecycle import enrich_entry, render_memory_file
from app.services.task.team_memory import (
    TeamMemoryWriter,
    ensure_team,
    load_team_memory_section,
    resolve_user_team,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _create_user(user_id: str, team: str | None = None):
    paths = get_paths()
    user_dir = paths.user_dir(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    profile = {"id": user_id, "email": f"{user_id}@test.com", "name": user_id}
    if team:
        profile["team"] = team
    write_json(paths.user_profile(user_id), profile)


# ─── resolve_user_team ────────────────────────────────────────────────────────


def test_resolve_user_team_returns_team(isolated_data_root):
    _create_user("u1", team="cc-analysts")
    assert resolve_user_team("u1") == "cc-analysts"


def test_resolve_user_team_no_team(isolated_data_root):
    _create_user("u2", team=None)
    assert resolve_user_team("u2") is None


def test_resolve_user_team_nonexistent_user(isolated_data_root):
    assert resolve_user_team("ghost") is None


# ─── ensure_team ──────────────────────────────────────────────────────────────


def test_ensure_team_creates_structure(isolated_data_root):
    paths = get_paths()
    ensure_team("my-team", name="My Team")

    assert paths.team_dir("my-team").is_dir()
    assert paths.team_memory_dir("my-team").is_dir()
    meta = paths.team_meta("my-team")
    assert meta.exists()
    import json
    data = json.loads(meta.read_text(encoding="utf-8"))
    assert data["id"] == "my-team"
    assert data["name"] == "My Team"


# ─── TeamMemoryWriter ─────────────────────────────────────────────────────────


def test_team_memory_writer_save_and_read(isolated_data_root):
    paths = get_paths()
    ensure_team("analytics")
    writer = TeamMemoryWriter("analytics")

    result = writer.save_memory(
        slug="dau-definition",
        title="DAU 口径",
        hook="UV 去重逻辑",
        type_="project",
        body="DAU = 按设备 ID 去重的日活跃用户数。",
        author_id="u1",
    )
    assert result["saved"] is True
    assert result["team_id"] == "analytics"

    # Index should contain the entry
    index = paths.team_memory_index("analytics")
    assert index.exists()
    text = index.read_text(encoding="utf-8")
    assert "dau-definition.md" in text
    assert "DAU 口径" in text

    # Memory file should exist with content
    mem_file = paths.team_memory_dir("analytics") / "dau-definition.md"
    assert mem_file.exists()
    content = mem_file.read_text(encoding="utf-8")
    assert "scope: team" in content
    assert "author: u1" in content


def test_team_memory_writer_delete(isolated_data_root):
    ensure_team("analytics")
    writer = TeamMemoryWriter("analytics")
    writer.save_memory(slug="to-delete", title="tmp", hook="tmp", type_="reference", body="old")

    result = writer.delete_memory(slug="to-delete")
    assert result["deleted"] is True

    paths = get_paths()
    assert not (paths.team_memory_dir("analytics") / "to-delete.md").exists()
    index_text = paths.team_memory_index("analytics").read_text(encoding="utf-8")
    assert "to-delete" not in index_text


# ─── load_team_memory_section ─────────────────────────────────────────────────


def test_load_team_memory_section_returns_content(isolated_data_root):
    ensure_team("cc-team")
    writer = TeamMemoryWriter("cc-team")
    writer.save_memory(slug="cc-dau", title="CC DAU", hook="内容中心日活口径", type_="project", body="标准定义...")

    section = load_team_memory_section("cc-team", query="DAU")
    assert "Team Memory" in section
    assert "CC DAU" in section


def test_load_team_memory_section_empty_team(isolated_data_root):
    ensure_team("empty-team")
    section = load_team_memory_section("empty-team")
    assert section == ""


def test_load_team_memory_section_none_team(isolated_data_root):
    assert load_team_memory_section(None) == ""


# ─── Visibility in render_memory_file ─────────────────────────────────────────


def test_render_memory_file_with_visibility():
    from app.services.task.context_svc import _parse_frontmatter
    output = render_memory_file(
        "shared-rule", "team convention", "feedback", "Always use T+1 DAU.",
        visibility="team",
    )
    fields, body = _parse_frontmatter(output)
    assert fields["metadata"]["visibility"] == "team"


def test_render_memory_file_private_omits_visibility():
    from app.services.task.context_svc import _parse_frontmatter
    output = render_memory_file(
        "private-rule", "my pref", "feedback", "I like charts.",
        visibility="private",
    )
    fields, _ = _parse_frontmatter(output)
    # private is default — should not appear in frontmatter to keep files clean
    assert "visibility" not in fields.get("metadata", {})


# ─── enrich_entry reads visibility ────────────────────────────────────────────


def test_enrich_entry_reads_visibility(isolated_data_root):
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    base.mkdir(parents=True, exist_ok=True)
    content = render_memory_file("shared", "hook", "project", "body", visibility="team")
    (base / "shared.md").write_text(content, encoding="utf-8")

    entry = MemoryEntry(slug="shared", title="t", hook="h", rel_path="shared.md", line="l")
    enriched = enrich_entry(entry, base)
    assert enriched.visibility == "team"


def test_enrich_entry_defaults_to_private(isolated_data_root):
    paths = get_paths()
    base = paths.user_memory_dir("u1")
    base.mkdir(parents=True, exist_ok=True)
    # Old file without visibility
    content = "---\nname: old\ndescription: hook\nmetadata:\n  type: feedback\n---\n\nbody\n"
    (base / "old.md").write_text(content, encoding="utf-8")

    entry = MemoryEntry(slug="old", title="t", hook="h", rel_path="old.md", line="l")
    enriched = enrich_entry(entry, base)
    assert enriched.visibility == "private"


# ─── ContextLoader four-layer injection ───────────────────────────────────────


def test_context_loader_includes_team_memory(isolated_data_root):
    """ContextLoader.build_context_section should include team memory when user has a team."""
    _create_user("u1", team="my-team")
    ensure_team("my-team")
    TeamMemoryWriter("my-team").save_memory(
        slug="team-rule", title="Team Rule", hook="shared convention",
        type_="feedback", body="Always format dates as YYYY-MM-DD.",
    )

    ctx = ContextPaths(user_id="u1", agent_id="analyst", task_id=None)
    loader = ContextLoader(ctx, query="convention")
    section = loader.build_context_section()

    assert "Team Memory" in section
    assert "Team Rule" in section


def test_context_loader_no_team_skips_team_memory(isolated_data_root):
    """User without a team should not get team memory injected."""
    _create_user("u2", team=None)

    ctx = ContextPaths(user_id="u2", agent_id="analyst", task_id=None)
    loader = ContextLoader(ctx)
    section = loader.build_context_section()

    assert "Team Memory" not in section


def test_context_loader_order_is_user_agent_team_task(isolated_data_root):
    """Verify injection order: User > Agent > Team > Task."""
    _create_user("u1", team="t1")
    ensure_team("t1")
    paths = get_paths()

    # Write user memory
    writer = MemoryWriter(ContextPaths(user_id="u1", agent_id="analyst"))
    writer.save_memory(scope="user", slug="user-mem", title="UserMem", hook="user level", type_="user", body="user content")
    writer.save_memory(scope="agent", slug="agent-mem", title="AgentMem", hook="agent level", type_="feedback", body="agent content")

    # Write team memory
    TeamMemoryWriter("t1").save_memory(slug="team-mem", title="TeamMem", hook="team level", type_="project", body="team content")

    # Write task state
    task_writer = MemoryWriter(ContextPaths(user_id="u1", agent_id="analyst", task_id="task1"))
    task_writer.save_task_state("# Task State\n- Phase: 3")

    ctx = ContextPaths(user_id="u1", agent_id="analyst", task_id="task1")
    section = ContextLoader(ctx).build_context_section()

    # All four layers present
    assert "User Global Memory" in section
    assert "Agent Memory" in section
    assert "Team Memory" in section
    assert "Task State" in section

    # Order: User before Agent before Team before Task
    user_pos = section.index("User Global Memory")
    agent_pos = section.index("Agent Memory")
    team_pos = section.index("Team Memory")
    task_pos = section.index("Task State")
    assert user_pos < agent_pos < team_pos < task_pos
