"""Tests for tool_profiles.py — phase-aware tool subset resolution."""
from __future__ import annotations

import pytest

from app.core.storage import get_paths, write_json
from app.services.agent.tool_profiles import (
    _detect_phase,
    get_effective_tools,
    list_profiles,
    resolve_tool_profile,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_agent(agent_id: str, tools: list[str], tool_profiles: dict | None = None):
    paths = get_paths()
    agent_dir = paths.agents / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "id": agent_id,
        "name": agent_id,
        "description": "test",
        "publish_status": "published",
        "tools": tools,
    }
    if tool_profiles:
        cfg["tool_profiles"] = tool_profiles
    write_json(agent_dir / "agent.json", cfg)


# ─── _detect_phase ────────────────────────────────────────────────────────────


def test_detect_phase_numeric_1():
    assert _detect_phase("- **Phase**: 1 (命题澄清)") == "planning"


def test_detect_phase_numeric_2():
    assert _detect_phase("- **Phase**: 2") == "planning"


def test_detect_phase_numeric_3():
    assert _detect_phase("- **Phase**: 3") == "execution"


def test_detect_phase_numeric_5():
    assert _detect_phase("**Phase**: 5 (SQL 执行中)") == "execution"


def test_detect_phase_numeric_6():
    assert _detect_phase("Phase: 6") == "review"


def test_detect_phase_named_planning():
    assert _detect_phase("**Phase**: planning") == "planning"


def test_detect_phase_named_review():
    assert _detect_phase("Phase: review") == "review"


def test_detect_phase_chinese():
    assert _detect_phase("**Phase**: 澄清") == "planning"
    assert _detect_phase("Phase: 报告") == "review"


def test_detect_phase_none():
    assert _detect_phase(None) is None
    assert _detect_phase("no phase info here") is None


# ─── resolve_tool_profile ─────────────────────────────────────────────────────


def test_resolve_no_profiles_returns_none(isolated_data_root):
    _make_agent("agent-no-profiles", ["read_file", "write_file"])
    assert resolve_tool_profile("agent-no-profiles") is None


def test_resolve_explicit_phase(isolated_data_root):
    _make_agent("agent-profiled", ["read_file", "write_file", "kyuubi_query"], tool_profiles={
        "planning": ["read_file"],
        "execution": ["*"],
        "review": ["read_file", "kyuubi_query"],
    })
    assert resolve_tool_profile("agent-profiled", phase="planning") == ["read_file"]
    assert resolve_tool_profile("agent-profiled", phase="review") == ["read_file", "kyuubi_query"]
    assert resolve_tool_profile("agent-profiled", phase="execution") is None  # "*" = no restriction


def test_resolve_from_task_state(isolated_data_root):
    _make_agent("agent-detect", ["read_file", "write_file"], tool_profiles={
        "planning": ["read_file"],
        "execution": ["*"],
    })
    state = "# Task State\n- **Phase**: 1 (命题澄清)"
    assert resolve_tool_profile("agent-detect", task_state_content=state) == ["read_file"]


def test_resolve_unknown_phase_falls_back_to_execution(isolated_data_root):
    _make_agent("agent-fallback", ["read_file"], tool_profiles={
        "planning": ["read_file"],
        "execution": ["*"],
    })
    # Phase 4 detected as "execution" → "*" → None
    state = "**Phase**: 4"
    assert resolve_tool_profile("agent-fallback", task_state_content=state) is None


# ─── get_effective_tools ──────────────────────────────────────────────────────


def test_effective_tools_intersection(isolated_data_root):
    _make_agent("agent-inter", ["read_file", "write_file", "kyuubi_query", "now"], tool_profiles={
        "planning": ["read_file", "now", "todo_write"],  # todo_write not in base
    })
    result = get_effective_tools(
        "agent-inter",
        ["read_file", "write_file", "kyuubi_query", "now"],
        phase="planning",
    )
    # Only items in BOTH profile AND base_tools
    assert set(result) == {"read_file", "now"}
    assert "todo_write" not in result  # not in base
    assert "write_file" not in result  # not in profile


def test_effective_tools_no_profile(isolated_data_root):
    _make_agent("agent-noprof", ["read_file", "write_file"])
    result = get_effective_tools("agent-noprof", ["read_file", "write_file"])
    assert result == ["read_file", "write_file"]


def test_effective_tools_star_profile(isolated_data_root):
    _make_agent("agent-star", ["a", "b", "c"], tool_profiles={"execution": ["*"]})
    result = get_effective_tools("agent-star", ["a", "b", "c"], phase="execution")
    assert result == ["a", "b", "c"]


# ─── list_profiles ────────────────────────────────────────────────────────────


def test_list_profiles(isolated_data_root):
    _make_agent("agent-list", ["a"], tool_profiles={
        "planning": ["a"],
        "execution": ["*"],
        "review": ["a"],
    })
    profiles = list_profiles("agent-list")
    assert set(profiles.keys()) == {"planning", "execution", "review"}
