"""Inspection helpers for Agent runtime context and child runs."""
from __future__ import annotations

from app.services.llm import tool_runner
from app.services.task.context_svc import ContextLoader, ContextPaths

from ...core.storage import get_paths, read_jsonl
from . import agent_workflow_svc, agents_svc


def inspect_context(
    *,
    task_id: str,
    agent_id: str,
    user_id: str | None = None,
    query: str | None = None,
) -> dict:
    tools = tool_runner.get_anthropic_tools(
        tool_whitelist=agents_svc.get_agent_tools(agent_id),
        disallowed_tools=agents_svc.get_agent_disallowed_tools(agent_id),
        spawn_targets=agents_svc.list_spawnable_agent_ids(agent_id),
    )
    return {
        "agent_id": agent_id,
        "context": ContextLoader(
            ContextPaths(user_id=user_id, agent_id=agent_id, task_id=task_id),
            query=query,
        ).describe(),
        "tools": [t["name"] for t in tools],
        "disallowed_tools": agents_svc.get_agent_disallowed_tools(agent_id),
        "spawn_targets": agents_svc.list_spawnable_agent_ids(agent_id),
        "permission_mode": agents_svc.get_agent_permission_mode(agent_id),
        "max_turns": agents_svc.get_agent_max_turns(agent_id),
        "effort": agents_svc.get_agent_effort(agent_id),
        "hooks": agents_svc.get_agent_hooks(agent_id),
        "workflows": agent_workflow_svc.list_workflows(agent_id),
    }


def list_subagent_runs(task_id: str, *, limit: int = 50) -> list[dict]:
    root = get_paths().task_dir(task_id) / "subagent_runs"
    if not root.exists():
        return []
    runs: list[dict] = []
    for path in sorted(root.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        events = read_jsonl(path)
        spawn = next((e for e in events if e.get("event") == "spawn"), {})
        done = next((e for e in reversed(events) if e.get("event") in ("done", "timeout", "error")), {})
        runs.append(
            {
                "run_id": spawn.get("run_id") or path.stem,
                "agent_id": spawn.get("agent_id"),
                "parent_agent": spawn.get("parent_agent"),
                "parent_conv": spawn.get("parent_conv"),
                "prompt": spawn.get("prompt"),
                "started_at": spawn.get("at"),
                "last_event": done.get("event"),
                "duration_ms": done.get("duration_ms"),
                "tool_count": done.get("tool_count"),
                "path": str(path),
            }
        )
        if len(runs) >= limit:
            break
    return runs
