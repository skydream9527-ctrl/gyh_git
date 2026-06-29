from __future__ import annotations

import json
from pathlib import Path

from app.services import tool_runner


REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "agents"
SKILLS_DIR = REPO_ROOT / "skills"


def _agent_json_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*/agent.json"))


def _load_agent(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _real_tool_names() -> set[str]:
    return set(tool_runner._DISPATCH)


def _real_agentic_skill_ids() -> set[str]:
    return {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")}


def _published_agent_ids() -> set[str]:
    out: set[str] = set()
    for path in _agent_json_files():
        cfg = _load_agent(path)
        if cfg.get("publish_status") in ("published", None):
            out.add(cfg.get("id") or path.parent.name)
    return out


def test_published_agents_declare_valid_tool_surface():
    real_tools = _real_tool_names()
    for path in _agent_json_files():
        cfg = _load_agent(path)
        if cfg.get("publish_status") == "coming_soon":
            continue
        aid = cfg.get("id") or path.parent.name
        tools = cfg.get("tools")
        assert isinstance(tools, list) and tools, f"{aid} must declare non-empty tools[]"
        assert len(tools) == len(set(tools)), f"{aid} tools[] has duplicates"
        unknown = sorted(set(tools) - real_tools)
        assert not unknown, f"{aid} tools[] references unknown tools: {unknown}"


def test_declared_agentic_skills_exist():
    real_skills = _real_agentic_skill_ids()
    for path in _agent_json_files():
        cfg = _load_agent(path)
        aid = cfg.get("id") or path.parent.name
        skills = cfg.get("skills") or []
        assert isinstance(skills, list), f"{aid} skills must be a list"
        unknown = sorted(set(skills) - real_skills)
        assert not unknown, f"{aid} skills[] references missing skills: {unknown}"


def test_read_agent_knowledge_requires_knowledge_directory():
    for path in _agent_json_files():
        cfg = _load_agent(path)
        aid = cfg.get("id") or path.parent.name
        tools = cfg.get("tools") or []
        if "read_agent_knowledge" in tools:
            assert (path.parent / "knowledge").is_dir(), (
                f"{aid} exposes read_agent_knowledge but has no knowledge/ directory"
            )


def test_spawn_targets_reference_existing_agents():
    known_agent_ids = {(_load_agent(p).get("id") or p.parent.name) for p in _agent_json_files()}
    for path in _agent_json_files():
        cfg = _load_agent(path)
        aid = cfg.get("id") or path.parent.name
        targets = cfg.get("spawn_targets")
        if targets is None:
            continue
        assert isinstance(targets, list), f"{aid} spawn_targets must be a list"
        if targets == ["*"]:
            continue
        unknown = sorted(set(targets) - known_agent_ids)
        assert not unknown, f"{aid} spawn_targets references unknown agents: {unknown}"


def test_v3_agents_have_identity_and_no_legacy_system_prompt_field():
    expected_v3 = {"general", "data-analysis", "know", "ab-experiment", "gray-release", "zijian-data-analysis"}
    seen_v3: set[str] = set()
    for path in _agent_json_files():
        cfg = _load_agent(path)
        aid = cfg.get("id") or path.parent.name
        assert "system_prompt" not in cfg, f"{aid} must not duplicate prompt in agent.json"
        if cfg.get("prompt_layout") != "v3":
            continue
        seen_v3.add(aid)
        assert (path.parent / "prompt" / "identity.md").is_file(), (
            f"{aid} uses prompt_layout=v3 but has no prompt/identity.md"
        )
    missing = expected_v3 - seen_v3
    assert not missing, f"expected migrated v3 agents are not v3: {sorted(missing)}"


def test_spawn_feature_and_tool_list_are_consistent():
    for path in _agent_json_files():
        cfg = _load_agent(path)
        aid = cfg.get("id") or path.parent.name
        tools = set(cfg.get("tools") or [])
        features = cfg.get("features") or {}
        if features.get("spawn_subagent") is False:
            assert "spawn_subagent" not in tools, (
                f"{aid} disables spawn_subagent but still exposes the tool"
            )
