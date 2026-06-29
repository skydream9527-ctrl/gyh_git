"""Per-conversation 'who is mid-turn' state — surfaces a UX-level lock.

The cross-worker mutex is still the flock on `{cid}.inflight.lock` (see
ws.py); this module writes a sibling JSON file `{cid}.inflight.json` that
non-holders can read without acquiring the lock, so the frontend can grey out
the send button and show "user X is in conversation".

State file shape:
    {"user_id": "...", "user_name": "...",
     "started_at": "<iso8601 utc>", "worker_pid": 12345}

Stale detection: state is treated as None (idle) on read when ANY of:
  1. `worker_pid` is set but the process no longer exists — covers the common
     case of `uvicorn --reload` swapping workers mid-turn, where _run_turn's
     `finally` never gets to call mark_idle and the JSON sidecar lingers.
     The `.inflight.lock` flock is auto-released by the kernel on process
     death, so cross-worker mutex matches reality already; this is just the
     UX-level state catching up.
  2. `started_at` is older than STALE_AFTER_SEC — last-resort backstop for
     PID reuse on long-running boxes (a new unrelated process happens to grab
     the dead worker's PID before we read).
On either trigger we best-effort unlink the file so subsequent reads are O(1).
"""
from __future__ import annotations

import errno
import logging
import os
from datetime import datetime, timezone

from ...core.storage import get_paths, read_json, write_json

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


def _pid_alive(pid: object) -> bool:
    """True iff `pid` looks like a live OS process on this host.

    Unknown / missing pid ⇒ True (don't bypass the time-based stale check).
    EPERM ⇒ True (process exists but we can't signal it; e.g. different uid).
    ESRCH ⇒ False (no such process — the canonical "worker is gone" signal).
    """
    if not isinstance(pid, int) or pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except OSError as e:
        if e.errno == errno.ESRCH:
            return False
        return True
    return True


def read_state(task_id: str, conv_id: str) -> dict | None:
    """Returns {user_id, user_name, started_at, worker_pid} if a turn is
    actively running, or None if idle / state file missing / state stale.

    "Stale" includes BOTH a time-based threshold and a worker-pid liveness
    check — the latter catches `uvicorn --reload` worker swaps that leave an
    orphan JSON sidecar pointing at a dead PID. Without that check the
    frontend would show a "your other tab is busy" banner for up to 30 min
    even when nothing is actually running.
    """
    p = get_paths().task_conv_inflight_state(task_id, conv_id)
    data = read_json(p, default=None)
    if not isinstance(data, dict):
        return None
    if _is_stale(data.get("started_at")) or not _pid_alive(data.get("worker_pid")):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        except Exception as exc:
            log.warning("inflight: stale cleanup failed task=%s conv=%s: %s", task_id, conv_id, exc)
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
