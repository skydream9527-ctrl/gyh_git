from __future__ import annotations

from pathlib import Path


class PromptBuilder:
    def __init__(self, prompt_dir: Path):
        self._prompt_dir = prompt_dir

    def _read_file(self, filename: str) -> str:
        path = self._prompt_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def build(
        self,
        memory_summary: str = "",
        skills_snapshot: str = "",
        skill_context: str = "",
        tool_names: list[str] | None = None,
        user_memory: str = "",
        agent_memory: str = "",
        task_state: str = "",
    ) -> str:
        """Assemble the system prompt from layered sources.

        `user_memory` / `agent_memory` / `task_state` follow the Context Protocol
        defined in `_shared/context-protocol.md`. Callers typically build these
        strings via `ContextLoader` in `_shared/context.py`. Empty strings are
        skipped so agents work even without persistent memory.
        """
        layers: list[str] = []

        # Layer 1: Identity
        identity = self._read_file("identity.md")
        if identity:
            layers.append(identity)
        else:
            # Fallback: some agents use a monolithic system.md instead of
            # splitting identity/rules. Load it as the identity layer.
            system_md = self._read_file("system.md")
            if system_md:
                layers.append(system_md)

        # Layer 2: Rules
        rules = self._read_file("rules.md")
        if rules:
            layers.append(rules)

        # Layer 3: User Global Memory (persistent, cross-agent)
        if user_memory:
            layers.append(f"## User Memory\n\n{user_memory}")

        # Layer 4: Agent-scoped Memory (persistent, this user × this agent)
        if agent_memory:
            layers.append(f"## Agent Memory\n\n{agent_memory}")

        # Layer 5: Task State (ephemeral, current task)
        if task_state:
            layers.append(f"## Task State\n\n{task_state}")

        # Layer 6: Session memory (current conversation window)
        if memory_summary:
            layers.append(f"## Recent Context\n\n{memory_summary}")

        # Layer 7: Skills snapshot
        if skills_snapshot:
            layers.append(f"## {skills_snapshot}")

        # Layer 8: Active skill context
        if skill_context:
            layers.append(f"## Active Skill Instructions\n\n{skill_context}")

        # Layer 9: Tool allowlist
        if tool_names:
            tool_list = ", ".join(tool_names)
            layers.append(f"## Available Tools\n\nYou have access to: {tool_list}")

        return "\n\n---\n\n".join(layers)
