"""Phase-aware tool profiles for agents.

Allows an agent to declare named tool subsets in `agent.json.tool_profiles`.
At runtime, the current phase determines which profile is active, restricting
the tools visible to the LLM beyond the base `tools` whitelist.

Example agent.json:
    {
      "tools": ["now", "kyuubi_query", "write_file", "read_file", ...],
      "tool_profiles": {
        "planning": ["now", "read_file", "read_skill", "todo_write", "exit_plan_mode"],
        "execution": ["*"],
        "review": ["read_file", "kyuubi_query", "memory_save"]
      }
    }

Semantics:
- `"*"` means "all tools from the base tools list" (no restriction)
- A named profile restricts the agent's visible tools to that subset
- If no `tool_profiles` is declared, agent behaves as before (all tools)
- Profile resolution: explicit phase arg > task_state detection > "execution" default
"""
from __future__ import annotations

from typing import Literal

ProfileName = Literal["planning", "execution", "review"] | str


def resolve_tool_profile(
    agent_id: str,
    *,
    phase: str | None = None,
    task_state_content: str | None = None,
) -> list[str] | None:
    """Resolve the active tool profile for an agent.

    Args:
        agent_id: the agent to look up
        phase: explicit phase name (overrides detection)
        task_state_content: STATE.md content for auto-detection

    Returns:
        - List of tool names the agent should expose (intersection with base tools)
        - None if no restriction applies (agent has no tool_profiles or profile is "*")
    """
    from . import agents_svc

    cfg = agents_svc.get_agent(agent_id) or {}
    profiles = cfg.get("tool_profiles")
    if not profiles or not isinstance(profiles, dict):
        return None  # no profiles declared — no restriction

    # Determine active profile name
    active_phase = phase or _detect_phase(task_state_content) or "execution"
    profile_tools = profiles.get(active_phase)

    if profile_tools is None:
        # Phase not in profiles — fall back to execution or no restriction
        profile_tools = profiles.get("execution")
        if profile_tools is None:
            return None

    if not isinstance(profile_tools, list):
        return None

    # "*" means no restriction
    if "*" in profile_tools:
        return None

    return profile_tools


def get_effective_tools(
    agent_id: str,
    base_tools: list[str],
    *,
    phase: str | None = None,
    task_state_content: str | None = None,
) -> list[str]:
    """Return the effective tool list for an agent given the current phase.

    Intersects the base tools with the active profile. If no profile applies,
    returns base_tools unchanged.

    Args:
        agent_id: the agent
        base_tools: the full tool list from agent.json.tools
        phase: explicit phase (optional)
        task_state_content: STATE.md for auto-detection (optional)

    Returns:
        Filtered tool list.
    """
    profile = resolve_tool_profile(agent_id, phase=phase, task_state_content=task_state_content)
    if profile is None:
        return base_tools
    # Intersection preserving profile order
    base_set = set(base_tools)
    return [t for t in profile if t in base_set]


def list_profiles(agent_id: str) -> dict[str, list[str]]:
    """Return all declared profiles for an agent (for debugging/admin)."""
    from . import agents_svc

    cfg = agents_svc.get_agent(agent_id) or {}
    profiles = cfg.get("tool_profiles")
    if not profiles or not isinstance(profiles, dict):
        return {}
    return {k: v for k, v in profiles.items() if isinstance(v, list)}


# ─── Phase Detection ──────────────────────────────────────────────────────────


def _detect_phase(task_state_content: str | None) -> str | None:
    """Attempt to detect the current phase from STATE.md content.

    Looks for patterns like:
    - **Phase**: 1 (命题澄清)
    - **Phase**: planning
    - Phase: review

    Maps numeric phases to profile names:
    - Phase 1-2 → "planning"
    - Phase 3-5 → "execution"
    - Phase 6+ or "review" → "review"
    """
    if not task_state_content:
        return None

    import re
    match = re.search(r"\*?\*?Phase\*?\*?\s*[:：]\s*(\S+)", task_state_content, re.IGNORECASE)
    if not match:
        return None

    value = match.group(1).strip().rstrip(")")
    # Named phase
    if value.lower() in ("planning", "plan", "澄清", "拆解"):
        return "planning"
    if value.lower() in ("review", "报告", "总结"):
        return "review"
    if value.lower() in ("execution", "exec", "执行"):
        return "execution"

    # Numeric phase
    try:
        num = int(value)
        if num <= 2:
            return "planning"
        elif num <= 5:
            return "execution"
        else:
            return "review"
    except ValueError:
        return None
