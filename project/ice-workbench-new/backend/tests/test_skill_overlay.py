"""Tests for skill_overlay.py — team-level skill customization."""
from __future__ import annotations

import pytest

from app.core.storage import get_paths
from app.services.agent.skill_overlay import (
    _parse_overlay,
    _replace_section,
    apply_overlay,
    get_overlay_path,
    has_overlay,
    list_overlays,
)
from app.services.task.team_memory import ensure_team


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _write_overlay(team_id: str, skill_id: str, content: str):
    paths = get_paths()
    overlay_dir = paths.team_dir(team_id) / "skill_overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / f"{skill_id}.md").write_text(content, encoding="utf-8")


# ─── _parse_overlay ───────────────────────────────────────────────────────────


def test_parse_overlay_with_frontmatter():
    raw = "---\nmode: replace_section\ntarget_section: 表名映射\n---\n\n新的映射内容"
    mode, target, body = _parse_overlay(raw)
    assert mode == "replace_section"
    assert target == "表名映射"
    assert body == "新的映射内容"


def test_parse_overlay_append_mode():
    raw = "---\nmode: append\n---\n\n追加内容"
    mode, target, body = _parse_overlay(raw)
    assert mode == "append"
    assert target is None
    assert body == "追加内容"


def test_parse_overlay_no_frontmatter():
    raw = "直接追加的内容\n不需要 frontmatter"
    mode, target, body = _parse_overlay(raw)
    assert mode == "append"
    assert target is None
    assert body == raw


# ─── has_overlay / list_overlays ──────────────────────────────────────────────


def test_has_overlay_true(isolated_data_root):
    ensure_team("t1")
    _write_overlay("t1", "kyuubi", "overlay content")
    assert has_overlay("t1", "kyuubi") is True


def test_has_overlay_false(isolated_data_root):
    ensure_team("t1")
    assert has_overlay("t1", "nonexistent") is False


def test_list_overlays(isolated_data_root):
    ensure_team("t2")
    _write_overlay("t2", "kyuubi", "a")
    _write_overlay("t2", "nl-sql", "b")
    result = list_overlays("t2")
    assert set(result) == {"kyuubi", "nl-sql"}


def test_list_overlays_empty(isolated_data_root):
    ensure_team("t3")
    assert list_overlays("t3") == []


# ─── apply_overlay — append mode ──────────────────────────────────────────────


def test_apply_overlay_append(isolated_data_root):
    ensure_team("team-a")
    _write_overlay("team-a", "kyuubi", "## CC 特殊表名\n- `fact_cc` → CC 消费表")

    base = "# Kyuubi Skill\n\n使用 kyuubi 查询数据。\n\n## 基本用法\nSELECT ..."
    result = apply_overlay(base, "team-a", "kyuubi")

    assert "# Kyuubi Skill" in result
    assert "基本用法" in result
    assert "Team Overlay (team-a)" in result
    assert "CC 特殊表名" in result


def test_apply_overlay_no_overlay_returns_base(isolated_data_root):
    ensure_team("team-b")
    base = "# Original"
    result = apply_overlay(base, "team-b", "missing-skill")
    assert result == base


# ─── apply_overlay — replace_section mode ─────────────────────────────────────


def test_apply_overlay_replace_section(isolated_data_root):
    ensure_team("team-c")
    overlay = "---\nmode: replace_section\ntarget_section: 表名映射\n---\n\n新的 CC 映射表"
    _write_overlay("team-c", "nl-sql", overlay)

    base = "# NL-SQL\n\n## 概述\n把自然语言转 SQL\n\n## 表名映射\n默认映射\n\n## 使用方法\n..."
    result = apply_overlay(base, "team-c", "nl-sql")

    assert "# NL-SQL" in result
    assert "概述" in result
    assert "新的 CC 映射表" in result
    assert "默认映射" not in result  # replaced
    assert "使用方法" in result  # next section preserved


def test_apply_overlay_replace_section_not_found_falls_back(isolated_data_root):
    ensure_team("team-d")
    overlay = "---\nmode: replace_section\ntarget_section: 不存在的段落\n---\n\n追加内容"
    _write_overlay("team-d", "skill-x", overlay)

    base = "# Skill X\n\n## 段落 A\ncontent"
    result = apply_overlay(base, "team-d", "skill-x")

    # Heading not found → appended instead
    assert "# Skill X" in result
    assert "段落 A" in result
    assert "追加内容" in result


# ─── _replace_section internal ────────────────────────────────────────────────


def test_replace_section_middle():
    base = "# Doc\n\n## Intro\nhello\n\n## Target\nold content\n\n## End\nbye"
    result = _replace_section(base, "Target", "new content")
    assert "new content" in result
    assert "old content" not in result
    assert "Intro" in result
    assert "End" in result


def test_replace_section_last():
    base = "# Doc\n\n## Intro\nhello\n\n## Target\nold content here"
    result = _replace_section(base, "Target", "replaced")
    assert "replaced" in result
    assert "old content" not in result
    assert "Intro" in result
