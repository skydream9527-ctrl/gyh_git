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


async def _tool_now(_: dict, ctx: dict | None = None) -> Any:
    return {"now": datetime.now(tz=timezone.utc).isoformat()}


async def _tool_echo(args: dict, ctx: dict | None = None) -> Any:
    await asyncio.sleep(0.1)
    return {"echo": args.get("text", "")}


# Semaphore that throttles concurrent Kyuubi CLI invocations even when the
# outer tool loop fires multiple kyuubi_query calls in parallel. Lazy-init so
# `ICE_KYUUBI_CONCURRENCY` from .env takes effect on first use.
_kyuubi_sem: asyncio.Semaphore | None = None


