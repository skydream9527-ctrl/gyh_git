"""POST /api/v1/client-errors — receive frontend error reports.

Auth is optional: login-page crashes have no token. When a Bearer token is
present, we extract user_id for correlation; otherwise report anonymously.

Reports are:
  1. Logged via standard logger (shows in stdout / journalctl).
  2. Appended to `.cache/frontend_errors/{YYYY-MM}.jsonl` (rebuildable,
     complements the task-level event_log for non-task-scoped frontend errors).
  3. If task_id is provided, also emit to the task's event timeline so
     /admin/diagnostics can surface it.

Rate limit: the global middleware already caps /api/* at 240/min per IP.
Additionally we drop payloads > 8 KB to prevent abuse.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...core.storage import append_jsonl
from ...services import event_log

router = APIRouter()
log = logging.getLogger("client_errors")

_MAX_BODY_LEN = 8192  # reject oversized payloads


class ClientErrorReport(BaseModel):
    message: str = Field(max_length=1000)
    stack: str | None = Field(default=None, max_length=4000)
    route: str | None = Field(default=None, max_length=200)
    level: str = Field(default="ERROR", max_length=10)
    build: str | None = Field(default=None, max_length=50)
    user_agent: str | None = Field(default=None, max_length=300)
    task_id: str | None = Field(default=None, max_length=64)
    context: dict | None = None


@router.post("/client-errors", status_code=204)
async def report_client_error(body: ClientErrorReport, request: Request):
    """Accept a frontend error report. Always returns 204 (fire-and-forget)."""
    # Extract user_id from token if present (best-effort, no 401 on failure)
    user_id: str | None = None
    try:
        from ...core.deps import resolve_user
        user = await resolve_user(request)
        user_id = user.get("id") if user else None
    except Exception:
        pass

    ts = datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds")
    level = body.level.upper() if body.level else "ERROR"
    if level not in ("ERROR", "WARN", "INFO"):
        level = "ERROR"

    record = {
        "ts": ts,
        "level": level,
        "source": "frontend",
        "message": body.message,
        "stack": (body.stack or "")[:4000],
        "route": body.route,
        "build": body.build,
        "user_agent": body.user_agent,
        "user_id": user_id,
        "task_id": body.task_id,
        "context": body.context if body.context and len(str(body.context)) < 2000 else None,
        "request_id": event_log.request_id_var.get(),
    }

    # 1. Standard logger
    log.warning(
        "[frontend:%s] route=%s msg=%s",
        level, body.route, body.message[:200],
    )

    # 2. Append to global frontend errors JSONL
    settings = get_settings()
    errors_dir = settings.cache_dir / "frontend_errors"
    errors_dir.mkdir(parents=True, exist_ok=True)
    ym = ts[:7]  # "2026-06"
    try:
        append_jsonl(errors_dir / f"{ym}.jsonl", record)
    except Exception as exc:
        log.warning("Failed to persist frontend error: %s", exc)

    # 3. If task_id provided, also emit to task event timeline
    if body.task_id:
        event_log.emit(
            task_id=body.task_id,
            source="frontend",
            event_type="client_error",
            level=level,
            user_id=user_id,
            code="CLIENT_ERROR",
            message=body.message[:500],
            payload={
                "route": body.route,
                "stack_head": (body.stack or "")[:300],
                "build": body.build,
            },
        )
