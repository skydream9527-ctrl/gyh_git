"""Middleware stubs — actual implementations live inline in main.py.

This module exists solely to satisfy the import statement in main.py.
The inline class definitions in main.py shadow these at runtime.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware


# These are placeholder definitions; main.py's inline versions take precedence.
class RequestIdMiddleware(BaseHTTPMiddleware):
    pass


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    pass


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    pass


_RATE_LIMIT_PER_MIN = int(os.environ.get("ICE_RATE_LIMIT_PER_MIN", "240"))


def get_rate_limit_info() -> dict:
    """Return rate limit configuration for the /health endpoint."""
    return {
        "backend": "memory",
        "per_worker_per_min": _RATE_LIMIT_PER_MIN,
        "note": "per-worker counter; effective global limit = workers * per_worker_per_min",
    }
