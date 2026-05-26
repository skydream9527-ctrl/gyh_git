"""In-memory rate limiter for auth endpoints.

Process-local — under multi-worker uvicorn each worker has its own counters.
For a single-host deployment that's still 4× harder to brute-force than no
limit at all, and avoids a Redis dependency. Move to a shared store
(Redis/Valkey) once the deployment grows past one box.

The limiter is stateful at module level: a {key: deque[timestamp]} sliding
window plus a {key: lockout_until} cooldown. Failures and the cooldown both
key on `(scope, identifier)` so login by email and login by IP each carry
their own counter.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    max_failures: int  # within `window_sec`
    window_sec: float
    lockout_sec: float


# Tuned for /auth/login: 5 failures within 60 s, then 15 min lockout per key.
LOGIN_LIMIT = RateLimitConfig(max_failures=5, window_sec=60.0, lockout_sec=900.0)
# Slower IP-level limit so brute force across many usernames from one IP also
# trips: 20 failures / 5 min, 30 min lockout.
LOGIN_IP_LIMIT = RateLimitConfig(max_failures=20, window_sec=300.0, lockout_sec=1800.0)
# /auth/register caps. Open registration + admin-approval queue means an
# attacker spamming register fills the review tray with junk; throttle hard.
# 3 attempts / hour per IP, 50 / hour globally — matches the secure-register
# reference defaults.
REGISTER_IP_LIMIT = RateLimitConfig(max_failures=3, window_sec=3600.0, lockout_sec=3600.0)
REGISTER_GLOBAL_LIMIT = RateLimitConfig(max_failures=50, window_sec=3600.0, lockout_sec=3600.0)

_lock = threading.Lock()
_failures: dict[str, deque[float]] = {}
_lockouts: dict[str, float] = {}


def _key(scope: str, ident: str) -> str:
    return f"{scope}::{(ident or '').strip().lower()}"


def check(scope: str, ident: str, cfg: RateLimitConfig) -> float | None:
    """Return None if allowed; otherwise seconds remaining in lockout.

    Call BEFORE attempting the protected operation. Pure read — does not
    record a failure. Use `record_failure` after the operation actually
    fails. Use `clear` after a success.
    """
    if not ident:
        return None
    k = _key(scope, ident)
    now = time.monotonic()
    with _lock:
        until = _lockouts.get(k)
        if until and until > now:
            return until - now
        if until and until <= now:
            _lockouts.pop(k, None)
            _failures.pop(k, None)
    return None


def record_failure(scope: str, ident: str, cfg: RateLimitConfig) -> float | None:
    """Record one failed attempt. Returns lockout-seconds-remaining if the
    failure pushed past the threshold, else None."""
    if not ident:
        return None
    k = _key(scope, ident)
    now = time.monotonic()
    with _lock:
        dq = _failures.setdefault(k, deque())
        cutoff = now - cfg.window_sec
        while dq and dq[0] < cutoff:
            dq.popleft()
        dq.append(now)
        if len(dq) >= cfg.max_failures:
            _lockouts[k] = now + cfg.lockout_sec
            dq.clear()
            return cfg.lockout_sec
    return None


def clear(scope: str, ident: str) -> None:
    if not ident:
        return
    k = _key(scope, ident)
    with _lock:
        _failures.pop(k, None)
        _lockouts.pop(k, None)


def reset_all() -> None:
    """Test helper — flushes all counters."""
    with _lock:
        _failures.clear()
        _lockouts.clear()
