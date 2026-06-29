"""Auto-extracted from tool_runner.py — DO NOT edit tool_runner.py for these functions."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ....core.config import get_settings
from ....core.errors import ErrorCode


async def _tool_memory_save(args: dict, ctx: dict | None = None) -> Any:
    """Persist user-level or agent-level memory and update MEMORY.md."""
    from app.services.task.context_svc import ContextPaths, MemoryWriter

    visibility = (args.get("visibility") or "private").strip()
    if visibility not in ("private", "team", "org"):
        return {"error_code": "VALIDATION_ERROR", "message": "visibility must be one of: private, team, org"}

    try:
        result = MemoryWriter(
            ContextPaths(
                user_id=(ctx or {}).get("user_id"),
                agent_id=(ctx or {}).get("agent_id"),
                task_id=(ctx or {}).get("task_id"),
            )
        ).save_memory(
            scope=(args.get("scope") or "").strip(),  # type: ignore[arg-type]
            slug=args.get("slug") or "",
            title=args.get("title") or "",
            hook=args.get("hook") or "",
            type_=args.get("type") or "",
            body=args.get("body") or "",
        )
    except ValueError as exc:
        return {"error_code": "VALIDATION_ERROR", "message": str(exc)}
    except Exception as exc:
        return {"error_code": "MEMORY_SAVE_FAILED", "message": str(exc)[:300]}

    # If visibility != private, rewrite the file with lifecycle metadata including visibility
    if visibility != "private" and result.get("saved"):
        try:
            from pathlib import Path

            from app.services.task.context_svc import _atomic_write_text, _parse_frontmatter, _read_text
            from app.services.task.memory_lifecycle import render_memory_file

            memory_path = Path(result["path"])
            existing = _read_text(memory_path)
            if existing:
                fields, body = _parse_frontmatter(existing)
                meta = fields.get("metadata") or {}
                new_content = render_memory_file(
                    args.get("slug") or "",
                    args.get("hook") or args.get("title") or "",
                    args.get("type") or "feedback",
                    body or args.get("body") or "",
                    visibility=visibility,
                )
                _atomic_write_text(memory_path, new_content)
        except Exception:
            pass  # best-effort; the core save already succeeded

    return result


async def _tool_memory_delete(args: dict, ctx: dict | None = None) -> Any:
    """Delete user-level or agent-level memory and update MEMORY.md."""
    from app.services.task.context_svc import ContextPaths, MemoryWriter

    try:
        result = MemoryWriter(
            ContextPaths(
                user_id=(ctx or {}).get("user_id"),
                agent_id=(ctx or {}).get("agent_id"),
                task_id=(ctx or {}).get("task_id"),
            )
        ).delete_memory(
            scope=(args.get("scope") or "").strip(),  # type: ignore[arg-type]
            slug=args.get("slug") or "",
        )
    except ValueError as exc:
        return {"error_code": "VALIDATION_ERROR", "message": str(exc)}
    except Exception as exc:
        return {"error_code": "MEMORY_DELETE_FAILED", "message": str(exc)[:300]}
    return result


async def _tool_task_state_save(args: dict, ctx: dict | None = None) -> Any:
    """Overwrite tasks/{task_id}/STATE.md."""
    from app.services.task.context_svc import ContextPaths, MemoryWriter

    try:
        result = MemoryWriter(
            ContextPaths(
                user_id=(ctx or {}).get("user_id"),
                agent_id=(ctx or {}).get("agent_id"),
                task_id=(ctx or {}).get("task_id"),
            )
        ).save_task_state(args.get("content") or "")
    except ValueError as exc:
        return {"error_code": "VALIDATION_ERROR", "message": str(exc)}
    except Exception as exc:
        return {"error_code": "TASK_STATE_SAVE_FAILED", "message": str(exc)[:300]}
    return result


