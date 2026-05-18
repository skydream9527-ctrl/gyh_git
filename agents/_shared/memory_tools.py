"""Memory / task-state 相关的 ToolDef，由 RuntimeFacade 默认注册给每个 agent。

依赖 `context.get_current_paths()` 读取当前请求的 ContextPaths —— 必须在
RuntimeFacade.handle_message 外层用 `set_current_paths()` 绑定后才能工作。

暴露 3 个工具：
- `memory_save` — 写 user-global 或 agent-scoped 的一条记忆
- `memory_delete` — 删掉一条记忆并同步清索引
- `task_state_save` — 覆盖写 tasks/{tid}/STATE.md
"""

from __future__ import annotations

import logging
from typing import Any

from .context import MemoryWriter, get_current_paths
from .tool_registry import ToolDef

logger = logging.getLogger(__name__)


def build_memory_tools() -> list[ToolDef]:
    """Return the three memory tools. Handlers close over contextvars at call time.

    All three are flagged `always_available=True` so they remain callable even
    when a matched skill restricts the tool allowlist via its `allowed_tools`
    frontmatter. Memory persistence is cross-cutting — a skill that restricts
    SQL tools shouldn't also prevent the agent from remembering what it just
    learned about the user.
    """
    return [
        ToolDef(
            name="memory_save",
            always_available=True,
            description=(
                "Persist a single memory entry as a markdown file with YAML frontmatter "
                "and upsert the corresponding MEMORY.md index line. Use scope='user' for "
                "cross-agent preferences; scope='agent' for domain-specific memory of "
                "this agent only. See agents/_shared/context-protocol.md for when to "
                "write each memory type."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["user", "agent"],
                        "description": (
                            "'user' writes to users/{uid}/memory/; 'agent' writes to "
                            "users/{uid}/memory/agents/{agent_id}/."
                        ),
                    },
                    "slug": {
                        "type": "string",
                        "description": (
                            "kebab-case or snake_case identifier; becomes the filename "
                            "{slug}.md. Lowercase alphanumerics with - or _ separators only."
                        ),
                    },
                    "title": {
                        "type": "string",
                        "description": "Human-readable title shown in the MEMORY.md index link.",
                    },
                    "hook": {
                        "type": "string",
                        "description": (
                            "One-line summary appended after `— ` in the index line. Used by "
                            "future relevance matching."
                        ),
                    },
                    "type": {
                        "type": "string",
                        "enum": ["user", "feedback", "project", "reference"],
                        "description": (
                            "Memory type per Context Protocol: user=role/profile, "
                            "feedback=user corrections/prefs, project=ongoing work context, "
                            "reference=pointer to external resource."
                        ),
                    },
                    "body": {
                        "type": "string",
                        "description": (
                            "Memory body in markdown. For 'feedback' and 'project' types, "
                            "include **Why:** and **How to apply:** lines."
                        ),
                    },
                },
                "required": ["scope", "slug", "title", "hook", "type", "body"],
            },
            handler=_handle_memory_save,
        ),
        ToolDef(
            name="memory_delete",
            always_available=True,
            description=(
                "Remove a single memory entry and clean its line from MEMORY.md index. "
                "Use when memory is outdated, superseded, or user explicitly asks to forget."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["user", "agent"]},
                    "slug": {"type": "string"},
                },
                "required": ["scope", "slug"],
            },
            handler=_handle_memory_delete,
        ),
        ToolDef(
            name="task_state_save",
            always_available=True,
            description=(
                "Overwrite tasks/{tid}/STATE.md with the full current task state. "
                "Call after every Phase/Step transition, key decision, or suspend/resume "
                "event. Content should be a half-structured markdown block per each "
                "agent's Context section schema (Phase, 命题, 拆解, 挂起项, etc.)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full STATE.md content (overwrites, does not append).",
                    },
                },
                "required": ["content"],
            },
            handler=_handle_task_state_save,
        ),
    ]


def _writer_or_error() -> tuple[MemoryWriter | None, dict | None]:
    """Resolve the current-request MemoryWriter; return (None, error_dict) if unavailable."""
    paths = get_current_paths()
    if paths is None:
        return None, {
            "success": False,
            "error": (
                "context paths not bound; runtime must call set_current_paths() before "
                "dispatching tool calls, and workspace_root/user_id must be configured."
            ),
        }
    return MemoryWriter(paths), None


def _handle_memory_save(args: dict[str, Any]) -> dict:
    writer, err = _writer_or_error()
    if err:
        return err
    scope = args.get("scope")
    try:
        kwargs = dict(
            slug=args["slug"],
            title=args["title"],
            hook=args["hook"],
            type_=args["type"],
            body=args["body"],
        )
        if scope == "user":
            path = writer.save_user_memory(**kwargs)
        elif scope == "agent":
            path = writer.save_agent_memory(**kwargs)
        else:
            return {"success": False, "error": f"invalid scope {scope!r}; expected 'user' or 'agent'"}
    except (KeyError, ValueError) as exc:
        return {"success": False, "error": str(exc)}
    return {
        "success": True,
        "result": {"scope": scope, "slug": args["slug"], "path": str(path)},
    }


def _handle_memory_delete(args: dict[str, Any]) -> dict:
    writer, err = _writer_or_error()
    if err:
        return err
    scope = args.get("scope")
    slug = args.get("slug")
    if not slug:
        return {"success": False, "error": "slug is required"}
    try:
        if scope == "user":
            existed = writer.delete_user_memory(slug)
        elif scope == "agent":
            existed = writer.delete_agent_memory(slug)
        else:
            return {"success": False, "error": f"invalid scope {scope!r}; expected 'user' or 'agent'"}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "result": {"scope": scope, "slug": slug, "existed": existed}}


def _handle_task_state_save(args: dict[str, Any]) -> dict:
    writer, err = _writer_or_error()
    if err:
        return err
    content = args.get("content")
    if content is None:
        return {"success": False, "error": "content is required"}
    try:
        path = writer.save_task_state(content)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "result": {"path": str(path)}}