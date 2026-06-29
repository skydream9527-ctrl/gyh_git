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


async def _tool_volcano_abtest_analyze(args: dict, ctx: dict | None = None) -> Any:
    """Run agents/volcano-abtest/scripts/analyze.py via the host `datum` CLI.

    Parameters are validated and forwarded as `-m / -e / -s / -d` args.
    The script's stdout (markdown report) is captured. On success the report
    is saved to the task's files/output/ so it appears in the file panel.

    Failure modes (returned as error_code envelopes — never raises):
      DATUM_NOT_INSTALLED   — datum CLI not on PATH
      ANALYZE_SCRIPT_MISSING — analyze.py not found under agents/volcano-abtest
      VALIDATION_ERROR       — bad params
      VOLCANO_ABTEST_TIMEOUT — script exceeded 320s
      VOLCANO_ABTEST_FAILED  — non-zero exit; stderr returned in `message`
    """
    import os
    import shutil
    import sys

    from app.services.storage import file_svc

    from ....core.storage.paths import get_paths

    media_raw = (args.get("media") or "").strip()
    exp_id = (args.get("exp_id") or "").strip()
    start_date = (args.get("start_date") or "").strip()
    end_date = (args.get("end_date") or "").strip()
    if not (media_raw and exp_id and start_date and end_date):
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "media, exp_id, start_date, end_date are all required",
        }
    media = _VOLCANO_MEDIA_ALIASES.get(media_raw, media_raw.lower())
    if media not in ("browser", "newhome"):
        return {
            "error_code": "VALIDATION_ERROR",
            "message": (
                f"未知 media '{media_raw}'，可选：浏览器/browser、"
                "内容中心/桌面内容中心/newhome/nh/mcc"
            ),
        }
    if not exp_id.isdigit():
        return {
            "error_code": "VALIDATION_ERROR",
            "message": f"exp_id 必须为纯数字，收到 '{exp_id}'",
        }

    if not shutil.which("datum"):
        return {
            "error_code": "DATUM_NOT_INSTALLED",
            "message": (
                "datum CLI 未安装：请管理员在后端环境安装 datum 命令行（参见 skills/datum-cli/SKILL.md）"
            ),
        }

    paths = get_paths()
    script = paths.agents / "volcano-abtest" / "scripts" / "analyze.py"
    if not script.is_file():
        return {
            "error_code": "ANALYZE_SCRIPT_MISSING",
            "message": f"未找到分析脚本：{script}",
        }

    cmd = [
        sys.executable, str(script),
        "-m", media,
        "-e", exp_id,
        "-s", start_date,
        "-d", end_date,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=320.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "error_code": "VOLCANO_ABTEST_TIMEOUT",
                "message": "analyze.py 超时（320s），通常是 datum 查询排队或权限问题",
            }
    except FileNotFoundError as exc:
        return {"error_code": "VOLCANO_ABTEST_FAILED", "message": str(exc)[:300]}

    stdout_s = stdout_b.decode(errors="replace")
    stderr_s = stderr_b.decode(errors="replace")
    if proc.returncode != 0:
        return {
            "error_code": "VOLCANO_ABTEST_FAILED",
            "message": (stderr_s.strip() or f"analyze.py exit {proc.returncode}")[:1200],
            "exit_code": proc.returncode,
        }

    report_md = stdout_s.strip()
    if not report_md:
        return {
            "error_code": "VOLCANO_ABTEST_EMPTY",
            "message": "脚本未输出报告内容（可能查询无数据）",
            "stderr": stderr_s.strip()[:600],
        }

    # 落盘到任务工作区，与 kyuubi_query 的行为一致。
    saved_meta: dict | None = None
    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if task_id and user_id:
        try:
            fname = f"abtest_{media}_{exp_id}_{start_date}-{end_date}.md"
            saved_meta = await file_svc.upload_task_file(
                task_id=task_id,
                owner_id=user_id,
                filename=fname,
                data=report_md.encode("utf-8"),
                scope="output",
            )
        except Exception:
            saved_meta = None

    return {
        "report_md": report_md,
        "media": media,
        "exp_id": exp_id,
        "start_date": start_date,
        "end_date": end_date,
        "file_id": (saved_meta or {}).get("id"),
        "file_name": (saved_meta or {}).get("name"),
        "stderr_tail": stderr_s.strip()[-400:] if stderr_s else "",
    }


_VALID_PERM_LEVELS = {"view", "edit", "full_access"}


