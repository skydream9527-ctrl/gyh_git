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


async def _tool_write_file(args: dict, ctx: dict | None = None) -> Any:
    """Write content into the task's workspace files/output and register it."""
    from app.services.storage import file_svc

    name = (args.get("name") or "").strip()
    content = args.get("content") or ""
    if not name:
        return {"error_code": "VALIDATION_ERROR", "message": "name is required"}
    if not isinstance(content, str):
        return {"error_code": "VALIDATION_ERROR", "message": "content must be a string"}
    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "write_file is only available in a task context",
        }
    try:
        meta = await file_svc.upload_task_file(
            task_id=task_id,
            owner_id=user_id,
            filename=name,
            data=content.encode("utf-8"),
            scope="output",
        )
    except Exception as e:
        return {"error_code": "WRITE_FILE_FAILED", "message": str(e)[:300]}
    return {
        "saved": True,
        "file_id": meta["id"],
        "name": meta["name"],
        "size_bytes": meta["size_bytes"],
        "scope": "output",
        "path": meta["path"],
        "message": f"已保存到工作区：{meta['name']}（{meta['size_bytes']} bytes）",
    }


_python_sem: asyncio.Semaphore | None = None


async def _tool_list_files(args: dict, ctx: dict | None = None) -> Any:
    """List every file in the current task workspace."""
    from app.services.storage import file_svc

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "list_files needs a task context"}
    scope = (args.get("scope") or "all").lower()
    if scope not in ("all", "uploaded", "input", "output"):
        return {"error_code": "VALIDATION_ERROR", "message": f"invalid scope: {scope}"}
    items = await file_svc.list_task_files(task_id)
    if scope != "all":
        items = [m for m in items if m.get("scope") == scope]
    out = [
        {
            "id": m["id"],
            "name": m["name"],
            "scope": m.get("scope"),
            "format": m.get("format"),
            "size_bytes": m.get("size_bytes"),
            "created_at": m.get("created_at"),
        }
        for m in items
    ]
    return {"files": out, "total": len(out), "scope": scope}


async def _tool_read_file(args: dict, ctx: dict | None = None) -> Any:
    """Read a workspace file by id or name."""
    from app.services.storage import file_svc

    from ....core.errors import APIError

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "read_file needs a task context"}

    file_id = (args.get("id") or "").strip()
    name = (args.get("name") or "").strip()
    if not file_id and not name:
        return {"error_code": "VALIDATION_ERROR", "message": "id 或 name 至少给一个"}

    if not file_id:
        items = await file_svc.list_task_files(task_id)
        # 同名按时间倒序，取最新（list_task_files 已按 created_at desc）
        match = next((m for m in items if m.get("name") == name), None)
        if not match:
            return {
                "error_code": "FILE_NOT_FOUND",
                "message": f"工作区里没有名为 `{name}` 的文件，请先用 list_files 查看。",
            }
        file_id = match["id"]

    try:
        result = await file_svc.read_file_text(task_id, file_id)
    except APIError as e:
        return {"error_code": e.error_code, "message": e.message}

    meta = result.get("meta") or {}
    if result.get("binary"):
        return {
            "id": file_id,
            "name": meta.get("name"),
            "scope": meta.get("scope"),
            "format": meta.get("format"),
            "is_binary": True,
            "size_bytes": meta.get("size_bytes"),
            "message": "二进制文件，无法以文本形式返回。",
        }
    return {
        "id": file_id,
        "name": meta.get("name"),
        "scope": meta.get("scope"),
        "format": meta.get("format"),
        "size_bytes": meta.get("size_bytes"),
        "content": result.get("content") or "",
    }


_KNOWLEDGE_TEXT_EXTS = {".yaml", ".yml", ".md", ".json", ".txt", ".sql"}
_KNOWLEDGE_MAX_BYTES = 200 * 1024  # 200KB


