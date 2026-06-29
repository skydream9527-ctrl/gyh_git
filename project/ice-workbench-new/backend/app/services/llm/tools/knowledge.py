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

_KNOWLEDGE_TEXT_EXTS = {".yaml", ".yml", ".md", ".json", ".txt", ".sql"}
_KNOWLEDGE_MAX_BYTES = 200 * 1024  # 200KB


async def _tool_read_agent_knowledge(args: dict, ctx: dict | None = None) -> Any:
    """Read a file from agents/<agent_id>/knowledge/<path>.

    Security: rejects absolute paths, traversal ('..'), and anything resolving
    outside the agent's knowledge directory. Rejects binary extensions; caps
    size at 200KB.
    """
    from ....core.storage import get_paths

    agent_id = (ctx or {}).get("agent_id")
    if not agent_id:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "read_agent_knowledge needs an agent context",
        }

    raw = (args.get("path") or "").strip()
    if not raw:
        return {"error_code": "VALIDATION_ERROR", "message": "path is required"}

    from pathlib import PurePosixPath

    pp = PurePosixPath(raw)
    if pp.is_absolute() or any(part == ".." for part in pp.parts):
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "path must be relative and must not contain '..'",
        }

    base = (get_paths().agents / agent_id / "knowledge").resolve()
    if not base.exists():
        return {
            "error_code": "KNOWLEDGE_NOT_FOUND",
            "message": f"agent '{agent_id}' has no knowledge/ directory",
        }

    target = (base / raw).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "path escapes the knowledge directory",
        }

    if not target.exists() or not target.is_file():
        return {
            "error_code": "FILE_NOT_FOUND",
            "message": f"knowledge file not found: {raw}",
        }

    ext = target.suffix.lower()
    if ext not in _KNOWLEDGE_TEXT_EXTS:
        return {
            "error_code": "UNSUPPORTED_FORMAT",
            "message": (
                f"binary/unsupported extension: {ext}. "
                f"Supported: {sorted(_KNOWLEDGE_TEXT_EXTS)}"
            ),
        }

    size = target.stat().st_size
    if size > _KNOWLEDGE_MAX_BYTES:
        return {
            "error_code": "FILE_TOO_LARGE",
            "message": f"{raw} is {size} bytes (limit {_KNOWLEDGE_MAX_BYTES})",
        }

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "error_code": "ENCODING_ERROR",
            "message": f"{raw} is not valid UTF-8",
        }
    except OSError as e:
        return {"error_code": "READ_FAILED", "message": str(e)[:300]}

    return {
        "agent_id": agent_id,
        "path": raw,
        "size_bytes": size,
        "content": content,
    }


async def _tool_read_skill(args: dict, ctx: dict | None = None) -> Any:
    """Return skill content. Resolution rule:
      - inside a task (ctx.task_id present): ONLY tasks/<task_id>/skills/<sid>/.
        Skills not bound to the task are invisible — call returns SKILL_NOT_FOUND
        even if the same skill exists in the global catalog.
      - outside a task (admin sandbox / test_run): falls back to global skills/<sid>/.

    Supports `path` arg:
      - omitted or empty → SKILL.md
      - 'ls' / '/' → list files in the skill dir
      - otherwise → the relative file (e.g. 'reference/browser/table-schema.md')

    Path traversal (..), absolute paths, and symlinks outside the skill dir
    are rejected.
    """
    from pathlib import Path

    from ....core.storage import get_paths

    sid = (args.get("skill_id") or "").strip()
    if not sid:
        return {"error_code": "VALIDATION_ERROR", "message": "skill_id is required"}
    rel = (args.get("path") or "").strip().lstrip("/")

    task_id = (ctx or {}).get("task_id")
    paths = get_paths()

    base: Path | None = None
    source: str
    if task_id:
        candidate = paths.task_skills_dir(task_id) / sid
        source = "task"
        if candidate.exists() and candidate.is_dir():
            base = candidate.resolve()
    else:
        candidate = paths.skills / sid
        source = "global"
        if candidate.exists() and candidate.is_dir():
            base = candidate.resolve()

    if base is None:
        if task_id:
            bound: list[str] = []
            skills_root = paths.task_skills_dir(task_id)
            if skills_root.exists():
                bound = sorted(p.name for p in skills_root.iterdir() if p.is_dir())
            hint = (
                f"未在本任务的 Skills 列表里找到 '{sid}'。"
                f"已绑定的 skill：{bound or '（无）'}。"
                "如需使用，请在工作区右栏「🧰 本任务 Skills」点击 +添加。"
            )
            return {
                "error_code": "SKILL_NOT_FOUND",
                "message": hint,
                "bound_skill_ids": bound,
            }
        return {
            "error_code": "SKILL_NOT_FOUND",
            "message": f"skill '{sid}' not found in global catalog",
        }

    # "ls" or "/" → directory listing
    if rel in ("", "ls", "/") and (args.get("path") in ("ls", "/")):
        entries = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rp = p.relative_to(base).as_posix()
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            entries.append({"path": rp, "size": sz})
        return {
            "skill_id": sid,
            "source": source,
            "files": entries,
            "total": len(entries),
        }

    # No path → SKILL.md (legacy behavior)
    target_rel = rel or "SKILL.md"
    if ".." in target_rel.split("/") or target_rel.startswith("/"):
        return {"error_code": "VALIDATION_ERROR", "message": "path 非法"}
    target = (base / target_rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return {"error_code": "VALIDATION_ERROR", "message": "path 越界"}
    if not target.exists() or not target.is_file():
        return {
            "error_code": "SKILL_FILE_NOT_FOUND",
            "message": f"skill '{sid}' 内无文件 '{target_rel}'（试试 path=ls 看全部）",
        }
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error_code": "SKILL_BINARY", "message": f"'{target_rel}' 是二进制文件"}
    except OSError as e:
        return {"error_code": "SKILL_READ_FAILED", "message": str(e)[:300]}
    return {
        "skill_id": sid,
        "source": source,
        "path": target_rel,
        "size_bytes": len(text.encode("utf-8")),
        "content": text,
    }


# ──────────────────────── v2 tool dispatches ─────────────────────────────


