"""Shared helpers for the agent-runtime-consolidation golden baseline.

This module is NOT collected by pytest (no ``test_`` prefix). It is imported by
both ``scripts/dump_agent_runtime_baseline.py`` (records the pre-refactor
golden snapshot) and ``tests/test_agent_runtime_baseline.py`` (asserts the
post-refactor output is byte-for-byte identical).

The snapshot must be computed against the *real* on-disk ``agents/`` directory,
not the isolated temp ``DATA_ROOT`` that the test fixture seeds with only the 6
default agents. To stay mutation-safe and deterministic, callers copy the real
agents into a throwaway ``DATA_ROOT`` first via :func:`seed_real_agents`, then
compute the snapshot there.

Design ref: agent-runtime-consolidation design.md "Testing Strategy" 1 & 2,
tasks.md Task 0.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

# backend/tests/baseline_support.py → repo root is parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_AGENTS_DIR = REPO_ROOT / "agents"
BASELINE_DIR = Path(__file__).resolve().parent / "_baseline"
TOOL_SCHEMAS_FILE = BASELINE_DIR / "tool_schemas.json"
AGENT_CONFIG_FILE = BASELINE_DIR / "agent_config.json"

# Runtime feature flag keys (mirror agents_svc._FEATURE_KEYS). Captured under
# both default=True and default=False so the "missing field → passthrough
# default" semantics are locked, not just the present-field case.
FEATURE_KEYS = ("spawn_subagent", "run_background", "todo_write", "exit_plan_mode")


def seed_real_agents(data_root: Path) -> None:
    """Copy the real on-disk agents into ``<data_root>/agents`` so snapshot
    computation sees every published agent (general, volcano-abtest, etc.),
    not just the 6 seeded defaults — without ever mutating the repo copy.
    """
    dst = data_root / "agents"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REAL_AGENTS_DIR, dst, dirs_exist_ok=True)


def _agent_ids() -> list[str]:
    from app.services import agents_svc

    ids = []
    for a in agents_svc.list_agents():
        aid = a.get("id")
        if isinstance(aid, str):
            ids.append(aid)
    return sorted(ids)


def _resolved_feature_flags(agent_id: str, default: bool) -> dict[str, bool]:
    from app.services import agents_svc

    return {f: agents_svc.get_agent_feature(agent_id, f, default) for f in FEATURE_KEYS}


def compute_agent_config_snapshot() -> dict[str, Any]:
    """One entry per agent capturing every config getter's output.

    Locks Requirement 5.2 (getter ↔ baseline parity) and the AgentConfig
    default semantics of Requirement 4.
    """
    from app.services import agents_svc

    snap: dict[str, Any] = {}
    for aid in _agent_ids():
        snap[aid] = {
            "tools": agents_svc.get_agent_tools(aid),
            "disallowed_tools": agents_svc.get_agent_disallowed_tools(aid),
            "model": agents_svc.get_agent_model(aid),
            "effort": agents_svc.get_agent_effort(aid),
            "max_turns": agents_svc.get_agent_max_turns(aid),
            "permission_mode": agents_svc.get_agent_permission_mode(aid),
            "hooks": agents_svc.get_agent_hooks(aid),
            "initial_prompt": agents_svc.get_agent_initial_prompt(aid),
            "spawn_targets": agents_svc.get_agent_spawn_targets(aid),
            "skills": agents_svc.get_agent_skills(aid),
            "spawnable": agents_svc.list_spawnable_agent_ids(aid),
            "features_default_true": _resolved_feature_flags(aid, True),
            "features_default_false": _resolved_feature_flags(aid, False),
        }
    return snap


def _scenarios_for(agent_id: str) -> dict[str, dict]:
    """Named get_anthropic_tools(...) call scenarios per agent.

    Each scenario mirrors a real runtime call site and exercises a distinct
    branch of the filter/rewrite logic (plan-mode gating, subagent gating,
    whitelist on/off, read_skill description rewrite, spawn_subagent enum).
    """
    from app.services import agents_svc

    whitelist = agents_svc.get_agent_tools(agent_id)
    disallowed = agents_svc.get_agent_disallowed_tools(agent_id)
    skills = agents_svc.get_agent_skills(agent_id)
    spawnable = agents_svc.list_spawnable_agent_ids(agent_id)
    flags = _resolved_feature_flags(agent_id, True)

    base = dict(
        plan_mode=False,
        in_subagent=False,
        feature_flags=flags,
        tool_whitelist=whitelist,
        disallowed_tools=disallowed,
        task_skill_ids=skills,
        spawn_targets=spawnable,
    )
    return {
        "default": {**base},
        "plan_mode": {**base, "plan_mode": True},
        "subagent": {**base, "in_subagent": True},
        "no_whitelist": {**base, "tool_whitelist": None},
        "no_skills": {**base, "task_skill_ids": []},
    }


def compute_tool_schema_snapshot() -> dict[str, Any]:
    """One entry per (agent, scenario) capturing get_anthropic_tools output.

    Locks Requirement 6.2 (byte-for-byte schema parity incl. ordering,
    read_skill description and spawn_subagent enum).
    """
    from app.services import tool_runner

    snap: dict[str, Any] = {}
    for aid in _agent_ids():
        per_agent: dict[str, Any] = {}
        for name, kwargs in _scenarios_for(aid).items():
            per_agent[name] = tool_runner.get_anthropic_tools(**kwargs)
        snap[aid] = per_agent
    return snap
