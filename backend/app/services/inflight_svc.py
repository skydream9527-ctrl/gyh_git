"""Per-conversation 'who is mid-turn' state — surfaces a UX-level lock.

The cross-worker mutex is still the flock on `{cid}.inflight.lock` (see
ws.py); this module writes a sibling JSON file `{cid}.inflight.json` that
non-holders can read without acquiring the lock, so the frontend can grey out
the send button and show "user X is in conversation".

State file shape:
    {"user_id": "...", "user_name": "...",
     "started_at": "<iso8601 utc>", "worker_pid": 12345}

Stale detection: any state older than STALE_AFTER_SEC is treated as None on
read, so a worker crash that leaves an orphan file unblocks the conversation
within 30 min. The next mark_busy() simply overwrites whatever was there.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from ..core.storage import get_paths, read_json, write_json

log = logging.getLogger("inflight")

STALE_AFTER_SEC = 30 * 60


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _is_stale(started_at: str | None) -> bool:
    if not started_at:
        return True
    try:
        t = datetime.fromisoformat(started_at)
    except ValueError:
        return True
    age = (datetime.now(tz=timezone.utc) - t).total_seconds()
    return age > STALE_AFTER_SEC


def read_state(task_id: str, conv_id: str) -> dict | None:
    """Returns {user_id, user_name, started_at, worker_pid} if a turn is
    actively running, or None if idle / state file missing / state stale."""
    p = get_paths().task_conv_inflight_state(task_id, conv_id)
    data = read_json(p, default=None)
    if not isinstance(data, dict):
        return None
    if _is_stale(data.get("started_at")):
        return None
    return data


def mark_busy(task_id: str, conv_id: str, *, user_id: str, user_name: str) -> dict:
    state = {
        "user_id": user_id,
        "user_name": user_name or "用户",
        "started_at": _now_iso(),
        "worker_pid": os.getpid(),
    }
    try:
        write_json(get_paths().task_conv_inflight_state(task_id, conv_id), state)
    except Exception as exc:
        log.warning("inflight: mark_busy write failed task=%s conv=%s: %s", task_id, conv_id, exc)
    return state


def mark_idle(task_id: str, conv_id: str) -> None:
    p = get_paths().task_conv_inflight_state(task_id, conv_id)
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    except Exception as exc:
        log.warning("inflight: mark_idle unlink failed task=%s conv=%s: %s", task_id, conv_id, exc)
