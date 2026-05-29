"""Assemble an agent's runtime base prompt from declarative pieces.

This is the Claude-Code-style assembly path: each agent contributes a small
identity.md (always) + optional sop.md, and the runtime grafts on shared
partials (tool contract / context protocol / plan-mode banner), a dynamically
rendered spawn-targets table built from `list_agents()`, and a short
"recommended skills" hint pulled from the agent's `skills[]` field.

For unmigrated agents (no identity.md), `build_base_prompt()` falls back to
the legacy `prompt/system.md` byte-for-byte so the rollout is bit-stable on
agents we haven't touched yet.

The runtime entry point is `experience_card_svc.merged_system_prompt`, which
calls into us, then layers cards.md / global skill catalog / TODO / PLAN
banners on top. We do NOT render the global skill catalog or builtin tool
schemas here — those are handled by the merged path.
"""
from __future__ import annotations

from pathlib import Path

from ..core.storage import get_paths

_PARTIALS_DIR_NAME = "_partials"
_DEFAULT_FALLBACK_PROMPT = "你是一名通用 AI 助手。"


def _partials_dir() -> Path:
    return get_paths().agents / "_shared" / _PARTIALS_DIR_NAME


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _agent_dir(agent_id: str) -> Path:
    return get_paths().agents / agent_id


def has_new_layout(agent_id: str) -> bool:
    """True when the agent has opted into the v3 declarative layout.

    Selection is explicit via `agent.json.prompt_layout == "v3"`. We avoid
    auto-detection on `identity.md` existence because the legacy RuntimeFacade
    era left orphan `identity.md`/`rules.md` files in some agent dirs that
    we'd otherwise misinterpret as a v3 migration.
    """
    from . import agents_svc

    cfg = agents_svc.get_agent(agent_id) or {}
    return cfg.get("prompt_layout") == "v3"


def _render_spawn_targets(agent_id: str) -> str:
    """Render a dynamic table of spawnable child agents, scoped by the
    parent's `spawn_targets` field.

    Without a `spawn_targets` whitelist (or with `["*"]`) the parent can
    spawn any published agent. With a whitelist, only listed agents appear.

    The table format mirrors Claude Code's <agent ...> hints — the model
    picks a target by reading each row's description, no hardcoded enum.
    """
    # Imported lazily because agents_svc imports this module's siblings,
    # and agents_svc's _ensure_seed_agents is the first thing list_agents
    # runs — keep the loader path one-directional.
    from . import agents_svc

    parent = agents_svc.get_agent(agent_id) or {}
    whitelist = agents_svc.get_agent_spawn_targets(agent_id)
    candidates = []
    for a in agents_svc.list_agents():
        aid = a.get("id")
        if aid == agent_id:
            continue
        if a.get("publish_status") not in ("published", None):
            continue
        if whitelist is not None and aid not in whitelist:
            continue
        desc = (a.get("description") or "").strip()
        if not desc:
            continue
        candidates.append((aid, a.get("name") or aid, desc))

    if not candidates:
        return ""

    lines = ["## 可派单的子 Agent (spawn_subagent 目标)"]
    if whitelist is None:
        lines.append("（无白名单 — 可向任何已发布 agent 派单）")
    for aid, name, desc in candidates:
        lines.append(f'<agent id="{aid}" name="{name}">')
        lines.append(f"  {desc}")
        lines.append("</agent>")
    return "\n".join(lines)


def _render_recommended_skills(agent_id: str) -> str:
    """Render a short "recommended skills" hint — documentation type.

    The full skill catalog is rendered separately by experience_card_svc;
    this is a per-agent shortlist that tells the LLM "for your workflows
    these skill ids matter most". No auto-load; LLM still calls read_skill.
    """
    from . import agents_svc

    skills = agents_svc.get_agent_skills(agent_id)
    if not skills:
        return ""
    return (
        "## 推荐 Skill\n"
        f"本 Agent 常用以下 skill,需要时调 `read_skill(skill_id=...)` 拉全文:"
        f" {', '.join(skills)}。"
    )


def build_base_prompt(agent_id: str) -> str:
    """Assemble the runtime base prompt for an agent.

    New layout (identity.md present):
        identity.md
        ─── _partials/tool_contract.md
        ─── _partials/context_protocol.md
        ─── sop.md (if present)
        ─── _partials/spawn_routing.md + dynamic spawn targets
        ─── _partials/plan_mode.md (if features.exit_plan_mode)
        ─── recommended skills (from agent.json.skills)

    Legacy layout: returns prompt/system.md byte-for-byte. Bit-stable for
    agents we haven't migrated.

    Returns a non-empty string in all cases (default fallback if everything
    is missing).
    """
    from . import agents_svc

    adir = _agent_dir(agent_id)
    if not has_new_layout(agent_id):
        # Legacy bit-stable path — preserve trailing whitespace exactly so the
        # assembled prompt is identical to what the legacy reader produced.
        sys_path = adir / "prompt" / "system.md"
        if sys_path.exists():
            try:
                return sys_path.read_text(encoding="utf-8")
            except OSError:
                pass
        cfg = agents_svc.get_agent(agent_id) or {}
        return cfg.get("system_prompt") or _DEFAULT_FALLBACK_PROMPT
    identity_path = adir / "prompt" / "identity.md"

    parts: list[str] = []
    parts.append(_read_text(identity_path))

    partials = _partials_dir()
    tool_contract = _read_text(partials / "tool_contract.md")
    if tool_contract:
        parts.append(tool_contract)

    ctx_protocol = _read_text(partials / "context_protocol.md")
    if ctx_protocol:
        parts.append(ctx_protocol)

    sop = _read_text(adir / "prompt" / "sop.md")
    if sop:
        parts.append(sop)

    cfg = agents_svc.get_agent(agent_id) or {}
    features = cfg.get("features") or {}

    if features.get("spawn_subagent"):
        spawn_intro = _read_text(partials / "spawn_routing.md")
        spawn_table = _render_spawn_targets(agent_id)
        if spawn_intro or spawn_table:
            # Both pieces are optional; only emit a section when at least one
            # exists. Spawn_intro is shared advice; spawn_table is per-agent.
            chunk = "\n\n".join(p for p in (spawn_intro, spawn_table) if p)
            parts.append(chunk)

    if features.get("exit_plan_mode"):
        plan_partial = _read_text(partials / "plan_mode.md")
        if plan_partial:
            parts.append(plan_partial)

    recommended = _render_recommended_skills(agent_id)
    if recommended:
        parts.append(recommended)

    return "\n\n---\n\n".join(p for p in parts if p)
