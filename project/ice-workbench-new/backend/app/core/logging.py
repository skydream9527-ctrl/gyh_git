"""Structured logging setup for ICE backend.

Features:
  - JSON mode (production): one-line JSON per log entry, machine-parseable
  - Text mode (development): human-readable colored output (default)
  - Automatic injection of request_id from contextvar
  - Access log with request path + duration + status code

Configuration via environment variables:
  ICE_LOG_FORMAT = json | text  (default: text)
  ICE_LOG_LEVEL  = DEBUG | INFO | WARNING | ERROR  (default: INFO)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Context variables (shared with RequestIdMiddleware and event_log)
# ---------------------------------------------------------------------------
# request_id_var is imported from event_log to avoid circular import.
# We define a local reference here for type-only usage in the formatter.
# The actual ContextVar lives in services/event_log.py.


def _get_request_id() -> str | None:
    """Get current request_id from event_log contextvar, if available."""
    try:
        from app.services.storage.event_log import request_id_var
        return request_id_var.get()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Outputs each log record as a single-line JSON object.

    Fields: ts, level, logger, msg, request_id, task_id, duration_ms, exc
    Extra fields from `record.__dict__` prefixed with `x_` are included as-is.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Inject request_id from contextvar
        request_id = _get_request_id()
        if request_id:
            entry["request_id"] = request_id

        # Include extra fields set via `logger.info("...", extra={"x_task_id": ...})`
        for key, value in record.__dict__.items():
            if key.startswith("x_"):
                entry[key[2:]] = value  # strip "x_" prefix

        # Exception info
        if record.exc_info and record.exc_info[1]:
            entry["exc"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Text Formatter (human-readable, for local dev)
# ---------------------------------------------------------------------------

class TextFormatter(logging.Formatter):
    """Colored, human-readable log format for development.

    Format: TIMESTAMP [LEVEL] logger: message  (request_id=xxx)
    """

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        msg = record.getMessage()

        # Append request_id if present
        request_id = _get_request_id()
        rid_suffix = f"  (rid={request_id})" if request_id else ""

        # Append extra x_ fields
        extras = []
        for key, value in record.__dict__.items():
            if key.startswith("x_"):
                extras.append(f"{key[2:]}={value}")
        extra_suffix = f"  [{', '.join(extras)}]" if extras else ""

        line = f"{ts} {color}[{record.levelname}]{reset} {record.name}: {msg}{rid_suffix}{extra_suffix}"

        if record.exc_info and record.exc_info[1]:
            line += "\n" + self.formatException(record.exc_info)

        return line


# ---------------------------------------------------------------------------
# Setup function
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    """Configure root logger based on ICE_LOG_FORMAT and ICE_LOG_LEVEL env vars.

    Call once at application startup (before any other logging).
    """
    log_format = os.getenv("ICE_LOG_FORMAT", "text").lower().strip()
    log_level_str = os.getenv("ICE_LOG_LEVEL", "INFO").upper().strip()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Remove any existing handlers on root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # uvicorn's own logger should use our formatter too
    for uvi_name in ("uvicorn", "uvicorn.error"):
        uvi_logger = logging.getLogger(uvi_name)
        uvi_logger.handlers.clear()
        uvi_logger.propagate = True


# ---------------------------------------------------------------------------
# Access log helper (used by RequestIdMiddleware)
# ---------------------------------------------------------------------------

class AccessLogHelper:
    """Logs HTTP request completion with method, path, status, and duration."""

    def __init__(self):
        self._logger = logging.getLogger("ice.access")

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_ip: str | None = None,
    ) -> None:
        level = logging.INFO if status_code < 400 else logging.WARNING
        self._logger.log(
            level,
            "%s %s %d (%.1fms)",
            method,
            path,
            status_code,
            duration_ms,
            extra={
                "x_method": method,
                "x_path": path,
                "x_status": status_code,
                "x_duration_ms": round(duration_ms, 1),
                "x_client_ip": client_ip or "-",
            },
        )


access_log = AccessLogHelper()
