"""Agent-local prompt workflows.

Workflows are lightweight slash-command-style prompt templates stored under
`agents/{agent_id}/workflows/*.md`. They are injected as an index only; the
actual body can be read through the existing agent file APIs.
"""
from __future__ import annotations

from pathlib import Path

from ..core.storage import get_paths

_MAX_WORKFLOWS = 20


def list_workflows(agent_id: str) -> list[dict]:
    root = get_paths().agents / agent_id / "workflows"
    if not root.exists() or not root.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(root.glob("*.md"))[:_MAX_WORKFLOWS]:
        out.append(_read_workflow(path))
    return out


def _read_workflow(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    title = path.stem
    description = ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                key, sep, value = line.partition(":")
                if not sep:
                    continue
                if key.strip() == "title":
                    title = value.strip().strip("\"'")
                elif key.strip() == "description":
                    description = value.strip().strip("\"'")
    if not description:
        for line in text.splitlines():
            stripped = line.strip("# ").strip()
            if stripped:
                description = stripped[:180]
                break
    return {
        "id": path.stem,
        "title": title,
        "description": description,
        "path": f"workflows/{path.name}",
    }


def render_workflow_index(agent_id: str) -> str:
    workflows = list_workflows(agent_id)
    if not workflows:
        return ""
    lines = ["## Agent Workflows", "这些是本 Agent 的可复用工作流模板。用户请求匹配时按模板推进。"]
    for wf in workflows:
        lines.append(f"- `/{wf['id']}` — {wf['title']}: {wf['description']} ({wf['path']})")
    return "\n".join(lines)
