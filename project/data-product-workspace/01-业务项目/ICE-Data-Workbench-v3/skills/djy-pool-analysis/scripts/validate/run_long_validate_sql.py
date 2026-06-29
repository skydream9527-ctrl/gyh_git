#!/usr/bin/env python3
"""
run_long_validate_sql.py · 长 timeout 版 SQL runner

为什么需要这个：
- 标准 [run_validate_sql.py](.) 走 sql_query_tool → run_sql.DataWorks.execute_sql，
  内部 polling timeout 硬编码 250s（run_sql.py:65），重查询会被客户端主动超时杀，
  但服务端 SQL 其实还在跑——结果就是日报 chart_stock_trend.sql 这种 7 cutoff
  全量扫描的查询，集群稍有拥堵就被客户端给"误杀"。
- 本脚本绕过 sql_query_tool，直接用 pyhive 跑，polling timeout 设 900s（15 分钟），
  让服务端重查询能等到真正出结果，不再被 250s 客户端硬限制误伤。

约束：
- 只用于"已知偏重 + 结果集稳定"的 chart 类 SQL（stock_trend / daily_trend 等）。
  其它常规校验 SQL 仍走 [run_validate_sql.py](.) 享受 transient 重试。
- SQL 中支持 {{EXEMPT_FILTER}} 和 {{CUTOFF_N}} 占位符（共用 exempt_lib.render_sql）。
- 大结果自动落 csv 到 TMP_DIR；stdout 末尾 `Saved to ./data_<ts>.csv` 兼容
  djy-daily-run.sh 用 grep 'data_[0-9]+\\.csv' 抓路径的协议。

用法：
  python3 run_long_validate_sql.py scripts/validate/chart_stock_trend.sql
  python3 run_long_validate_sql.py scripts/validate/chart_stock_trend.sql --timeout 600
"""
import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pyhive import hive
from TCLIService.ttypes import TOperationState

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED = SCRIPT_DIR.parent / "shared"
sys.path.insert(0, str(SHARED))
from paths import TMP_DIR, DATA_SQL_ENV  # noqa: E402
from exempt_lib import render_sql  # noqa: E402

HOST = "proxy-service-thrift-cnbj1-dp.api.xiaomi.net"  # zjyprc
DEFAULT_TIMEOUT = 900  # 15 分钟，远超原 250s

# Transient 错误关键词（命中任一即重试）
# 包含 trino worker 抖动 + jetty/HTTP 抖动 + 远程任务通信失败
# 2026-05-15 新增 "remote task"/"taskinstanceid"/"node may have crashed"
# 命中场景：trino worker 跑到一半 crash，服务端真挂，Trino 自己提示 retry
# 2026-05-30 新增 "invalid operationhandle"/"kyuubisqlexception"
# 命中场景：kyuubi 服务端把 operation handle 清掉（轮询期长查询常见），
# 同 SQL 重跑往往直接成功（Step 2 第一次 875s 失败，第二次 121s 成）。
TRANSIENT_PATTERNS = [
    "eofexception",
    "http 500",
    "http error 500",
    "connection reset",
    "connection refused",
    "connection closed",
    "org.eclipse.jetty.io",
    "worker disconnected",
    "broken pipe",
    "read timed out",
    "could not communicate with the remote task",
    "node may have crashed",
    "under too much load",
    "transient issue",
    "taskinstanceid",
    "invalid operationhandle",
    "kyuubisqlexception",
]
MAX_RETRIES = 2
BACKOFF_SEC = [30, 60]


def has_transient_error(text):
    low = text.lower()
    return any(p in low for p in TRANSIENT_PATTERNS)


def clean_sql(text):
    return " ".join(line.split("--", 1)[0] for line in text.splitlines()).strip()


def run_query(sql, token_id, timeout):
    config = {"proxy.engine": "presto"}
    conn = hive.connect(host=HOST, configuration=config, port=80, username=token_id)
    cursor = conn.cursor()
    cursor.execute(sql, async_=True)
    start = time.time()
    while True:
        status = cursor.poll().operationState
        if status not in (
            TOperationState.INITIALIZED_STATE,
            TOperationState.RUNNING_STATE,
            TOperationState.PENDING_STATE,
        ):
            break
        if time.time() - start > timeout:
            try:
                cursor.cancel()
            except Exception:
                pass
            raise TimeoutError(
                f"SQL polling timeout >{timeout}s（服务端可能仍在跑或集群异常拥堵）"
            )
        time.sleep(0.5)
    if status == TOperationState.ERROR_STATE:
        logs = cursor.fetch_logs()
        raise RuntimeError("SQL ERROR_STATE: " + "; ".join(logs))
    if status != TOperationState.FINISHED_STATE:
        raise RuntimeError(f"unexpected status: {status}")
    cols = [f[0] for f in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sql_file")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    load_dotenv(DATA_SQL_ENV)
    token_id = os.environ.get("DATAWORKS_TOKEN_ID")
    if not token_id:
        sys.stderr.write("ERROR: DATAWORKS_TOKEN_ID not set\n")
        sys.exit(2)

    sql_path = Path(args.sql_file)
    if not sql_path.is_absolute():
        sql_path = (Path.cwd() / sql_path).resolve()
    if not sql_path.is_file():
        sys.stderr.write(f"ERROR: SQL file not found: {sql_path}\n")
        sys.exit(2)

    raw_sql = sql_path.read_text(encoding="utf-8")
    rendered = render_sql(raw_sql)
    cleaned = clean_sql(rendered)

    sys.stderr.write(f"[long-runner] start, timeout={args.timeout}s, sql={sql_path.name}\n")
    sys.stderr.flush()

    df = None
    max_attempts = MAX_RETRIES + 1
    for attempt in range(max_attempts):
        t0 = time.time()
        try:
            df = run_query(cleaned, token_id, args.timeout)
            elapsed = time.time() - t0
            sys.stderr.write(
                f"[long-runner] done in {elapsed:.1f}s, rows={len(df)}"
                + (f"（attempt {attempt + 1}/{max_attempts}）" if attempt > 0 else "")
                + "\n"
            )
            break
        except Exception as e:
            elapsed = time.time() - t0
            err_text = str(e)
            transient = has_transient_error(err_text)
            is_last = attempt == max_attempts - 1
            sys.stderr.write(
                f"[long-runner] FAILED in {elapsed:.1f}s (attempt {attempt + 1}/{max_attempts}, "
                f"transient={transient}): {err_text[:300]}\n"
            )
            if is_last or not transient:
                sys.exit(1)
            wait = BACKOFF_SEC[attempt]
            sys.stderr.write(f"[long-runner] transient 错误，等 {wait}s 后重试...\n")
            sys.stderr.flush()
            time.sleep(wait)

    ts = time.strftime("%Y%m%d%H%M%S", time.localtime())
    out_path = TMP_DIR / f"data_{ts}.csv"
    df.to_csv(out_path, index=False)
    # 与 sql_query_tool 大结果集协议一致，便于 djy-daily-run.sh grep 抓路径
    print(f"Saved to ./{out_path.name}")


if __name__ == "__main__":
    main()
