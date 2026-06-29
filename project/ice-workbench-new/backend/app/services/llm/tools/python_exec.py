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


def _get_python_sem() -> asyncio.Semaphore:
    global _python_sem
    if _python_sem is None:
        _python_sem = asyncio.Semaphore(
            max(1, get_settings().ICE_PYTHON_SANDBOX_CONCURRENCY)
        )
    return _python_sem


async def _tool_execute_python(args: dict, ctx: dict | None = None) -> Any:
    """Run Python code in the data-analysis sandbox.

    Inputs:
        code: full Python source (required)
        description: free-form audit string
        timeout_sec: optional override (capped at config max)

    Outputs:
        Same shape as SandboxResult.to_dict() plus registered file_ids for
        any new artifact under tasks/{tid}/files/output/. The frontend's
        left-side file panel picks up the registered files automatically.
    """
    from app.services.storage import file_svc

    from ....core.storage.paths import get_paths
    from ...sandbox import SandboxStatus, run_python

    s = get_settings()
    if not s.ICE_PYTHON_SANDBOX_ENABLED:
        return {
            "error_code": "PYTHON_SANDBOX_DISABLED",
            "message": "Python 沙箱已关闭：管理员需在 .env 设 ICE_PYTHON_SANDBOX_ENABLED=true",
        }

    code = args.get("code")
    if not isinstance(code, str) or not code.strip():
        return {"error_code": "VALIDATION_ERROR", "message": "code is required"}

    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "execute_python is only available in a task context",
        }

    timeout_req = args.get("timeout_sec")
    try:
        timeout_sec = int(timeout_req) if timeout_req is not None else s.ICE_PYTHON_SANDBOX_TIMEOUT_SEC
    except (TypeError, ValueError):
        timeout_sec = s.ICE_PYTHON_SANDBOX_TIMEOUT_SEC
    timeout_sec = max(5, min(timeout_sec, s.ICE_PYTHON_SANDBOX_TIMEOUT_SEC))

    paths = get_paths()
    task_dir = paths.task_dir(task_id)
    if not task_dir.exists():
        return {
            "error_code": "TASK_NOT_FOUND",
            "message": f"task workspace missing: {task_dir}",
        }

    try:
        async with _get_python_sem():
            result = await run_python(
                code,
                task_dir=task_dir,
                timeout_sec=timeout_sec,
                # allow_cli=True disables RLIMIT_AS in preexec; Node-based
                # CLIs (feishu / npx) reserve multi-GB virtual address space
                # for V8 + Wasm even when RSS stays small. Wall-clock timeout
                # + RLIMIT_CPU still bound runaway runs.
                memory_mb=s.ICE_PYTHON_SANDBOX_MEMORY_MB,
                fsize_mb=s.ICE_PYTHON_SANDBOX_FSIZE_MB,
                description=str(args.get("description") or "")[:200],
                allow_cli=True,
            )
    except Exception as exc:  # noqa: BLE001 — sandbox shouldn't crash the agent
        return {
            "error_code": "PYTHON_SANDBOX_ERROR",
            "message": str(exc)[:300],
        }

    payload = result.to_dict()

    # Register newly-created files under files/output/ with file_svc so the
    # frontend file panel picks them up. Only files inside files/output/ are
    # registered (the runner reports paths relative to that directory).
    registered: list[dict] = []
    if result.status == SandboxStatus.OK and result.files_created:
        out_root = paths.task_files_output(task_id)
        for f in result.files_created:
            full = out_root / f.relpath
            try:
                if not full.is_file():
                    continue
                data = full.read_bytes()
                # Filename in the registry uses just the basename. Keeping
                # subdir structure (charts/, models/, data/) on disk is fine,
                # but the file_svc registry is flat per task.
                meta = await file_svc.upload_task_file(
                    task_id=task_id,
                    owner_id=user_id,
                    filename=f.relpath.replace(os.sep, "_"),
                    data=data,
                    scope="output",
                )
                registered.append({
                    "relpath": f.relpath,
                    "file_id": meta["id"],
                    "size_bytes": meta["size_bytes"],
                    "kind": f.kind,
                })
            except Exception:  # noqa: BLE001
                # don't fail the whole tool call on file registration error
                continue

    payload["registered_files"] = registered
    return payload


_VOLCANO_MEDIA_ALIASES = {
    "浏览器": "browser",
    "browser": "browser",
    "内容中心": "newhome",
    "桌面内容中心": "newhome",
    "newhome": "newhome",
    "nh": "newhome",
    "mcc": "newhome",
}


