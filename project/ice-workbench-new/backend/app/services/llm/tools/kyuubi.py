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


def _get_kyuubi_sem() -> asyncio.Semaphore:
    global _kyuubi_sem
    if _kyuubi_sem is None:
        _kyuubi_sem = asyncio.Semaphore(max(1, get_settings().ICE_KYUUBI_CONCURRENCY))
    return _kyuubi_sem


# 关键词清单：从 kyuubi CLI stderr 文本判别错误大类。维护为模块常量，便于扩充与单测。
_SYNTAX_MARKERS = (
    "syntax error",
    "parse",
    "parseexception",
    "mismatched input",
    "extraneous input",
    "cannot resolve",
    "unresolved",
    "no viable alternative",
    "analysisexception",
    "table or view not found",
    "unknown column",
)
_PERMISSION_MARKERS = (
    "permission",
    "denied",
    "unauthorized",
    "access denied",
    "forbidden",
    "not authorized",
    "no privilege",
    "privilege",
    "token",
    "authentication",
    "authenticate",
)
_CONNECTION_MARKERS = (
    "connection",
    "connect",
    "refused",
    "timeout",
    "timed out",
    "unavailable",
    "reset",
    "network",
    "unreachable",
    "broken pipe",
    "no route to host",
    "service",
)


def classify_kyuubi_stderr(stderr: str) -> str:
    """从 kyuubi CLI stderr 文本判别错误码。纯函数，对任意输入不抛异常。

    返回 KYUUBI_SYNTAX_ERROR / KYUUBI_PERMISSION_ERROR /
    KYUUBI_CONNECTION_ERROR / KYUUBI_CLI_ERROR（兜底）。

    判别顺序：syntax → permission → connection → 兜底。permission 先于
    connection 以避免 "connection ... unauthorized" 被误判为连接错误。
    """
    text = (stderr or "").lower()
    if any(k in text for k in _SYNTAX_MARKERS):
        return "KYUUBI_SYNTAX_ERROR"
    if any(k in text for k in _PERMISSION_MARKERS):
        return "KYUUBI_PERMISSION_ERROR"
    if any(k in text for k in _CONNECTION_MARKERS):
        return "KYUUBI_CONNECTION_ERROR"
    return "KYUUBI_CLI_ERROR"


async def _tool_kyuubi(args: dict, ctx: dict | None = None) -> Any:
    """Run a SQL query through the bundled `kyuubi` CLI.

    The connection context (region / workspace / catalog / engine / token) is
    pinned in server settings so the LLM never has to ask the user about it.
    Caller passes only `sql` (and optional `limit`).

    Records every attempt to sql_audit regardless of outcome.
    """
    import json as _json
    import os
    import shutil
    import time

    from app.services.admin import sql_audit_svc

    sql = (args.get("sql") or "").strip()
    limit = int(args.get("limit") or 100)
    decision, reason = sql_audit_svc.classify(sql)
    started = time.monotonic()
    s = get_settings()

    conn_ctx = {
        "region": s.KYUUBI_REGION,
        "workspace": s.KYUUBI_WORKSPACE,
        "catalog": s.KYUUBI_CATALOG,
        "engine": s.KYUUBI_ENGINE,
    }

    out: Any
    error_message: str | None = None
    rows_returned: int | None = None

    cli_path = shutil.which("kyuubi")

    if decision == "block":
        out = {"error_code": "SQL_BLOCKED", "message": reason, "context": conn_ctx}
    elif not s.KYUUBI_TOKEN:
        out = {
            "error_code": ErrorCode.KYUUBI_NOT_CONFIGURED,
            "message": "Kyuubi 未配置：请管理员在 .env 设置 KYUUBI_TOKEN",
            "context": conn_ctx,
        }
    elif not cli_path:
        out = {
            "error_code": ErrorCode.KYUUBI_NOT_CONFIGURED,
            "message": (
                "Kyuubi CLI 未安装：请管理员在后端环境安装 `kyuubi` 命令行（pipx install xiaomi-kyuubi-cli）"
            ),
            "context": conn_ctx,
        }
    else:
        try:
            async with _get_kyuubi_sem():
                env = {**os.environ, "KYUUBI_APIKEY": s.KYUUBI_TOKEN}
                cmd = [
                    cli_path, "sql", "query", sql,
                    "--region", conn_ctx["region"],
                    "--workspace", conn_ctx["workspace"],
                    "--catalog", conn_ctx["catalog"],
                    "--engine", conn_ctx["engine"],
                    "--format", "json",
                    "--limit", str(limit),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                try:
                    stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=300.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    error_message = "kyuubi CLI timeout (300s)"
                    out = {"error_code": "KYUUBI_TIMEOUT", "message": error_message, "context": conn_ctx}
                else:
                    stdout_s = stdout_b.decode(errors="replace")
                    stderr_s = stderr_b.decode(errors="replace")
                    if proc.returncode != 0:
                        error_message = (stderr_s.strip() or f"kyuubi exit {proc.returncode}")[:600]
                        out = {
                            "error_code": classify_kyuubi_stderr(stderr_s),
                            "message": error_message,
                            "context": conn_ctx,
                        }
                    else:
                        try:
                            data = _json.loads(stdout_s)
                        except _json.JSONDecodeError:
                            out = {
                                "columns": [],
                                "rows": [],
                                "row_count": 0,
                                "raw_output": stdout_s.strip()[:4000],
                                "context": conn_ctx,
                                "warning": reason if decision == "warn" else None,
                            }
                        else:
                            cols = data.get("columns") or []
                            col_names = [c.get("name") if isinstance(c, dict) else c for c in cols]
                            rows = data.get("rows") or []
                            rows_returned = len(rows)
                            out = {
                                "columns": col_names,
                                "rows": rows[:limit],
                                "row_count": rows_returned,
                                "context": conn_ctx,
                                "warning": reason if decision == "warn" else None,
                            }
                            # 空结果是成功查询的语义标记，不放进 error_code，避免被
                            # normalize_tool_outcome 误判为失败。
                            if rows_returned == 0:
                                out["empty"] = True
                                out["empty_code"] = "KYUUBI_EMPTY"
        except Exception as e:
            error_message = str(e)[:300]
            out = {"error_code": "KYUUBI_CLI_ERROR", "message": error_message, "context": conn_ctx}

    # 默认保存 SQL 文本与查询数据到任务工作区，供用户复用与审计。
    # 仅在查询成功且有行返回时保存；失败保存绝不影响主链路。
    if (
        rows_returned and rows_returned > 0
        and (ctx or {}).get("task_id") and (ctx or {}).get("user_id")
        and isinstance(out, dict) and "error_code" not in out
    ):
        try:
            import csv as _csv
            import io as _io

            from app.services.storage import file_svc as _file_svc
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_uid = uuid.uuid4().hex[:6]
            sql_name = f"query_{ts_str}_{short_uid}.sql"
            csv_name = f"query_{ts_str}_{short_uid}.csv"
            await _file_svc.upload_task_file(
                task_id=ctx["task_id"], owner_id=ctx["user_id"],
                filename=sql_name, data=sql.encode("utf-8"), scope="output",
            )
            buf = _io.StringIO()
            writer = _csv.writer(buf)
            writer.writerow(out.get("columns") or [])
            for row in (out.get("rows") or []):
                writer.writerow(["" if v is None else v for v in row])
            await _file_svc.upload_task_file(
                task_id=ctx["task_id"], owner_id=ctx["user_id"],
                filename=csv_name, data=buf.getvalue().encode("utf-8"), scope="output",
            )
        except Exception:
            pass  # 静默：保存失败绝不阻塞 LLM 主链路

    try:
        await sql_audit_svc.record(
            user_id=(ctx or {}).get("user_id"),
            agent_id=(ctx or {}).get("agent_id"),
            task_id=(ctx or {}).get("task_id"),
            conversation_id=(ctx or {}).get("conversation_id"),
            sql=sql,
            decision=decision,
            block_reason=reason if decision != "allow" else None,
            error_message=error_message,
            rows_returned=rows_returned,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    except Exception:
        pass
    return out


