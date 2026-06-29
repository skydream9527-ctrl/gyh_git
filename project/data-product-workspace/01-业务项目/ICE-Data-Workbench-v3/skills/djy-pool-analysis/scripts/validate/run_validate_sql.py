#!/usr/bin/env python3
"""
run_validate_sql.py · 内容池校验 SQL 统一运行入口

所有使用场景（日报/定时任务/手动/adhoc）都应通过本脚本跑 SQL，保证：
- 豁免列表自动注入（从 exemptions.json 读）
- SQL 注释、多行、空格正确清理
- 调用 data-sql 的 sql_query_tool.py 执行
- **针对 Trino 集群 transient 故障（worker 断连 / 临时 500 / 连接抖动）自动重试**

使用：

    # 1. 跑已有 SQL 模板（日报主流程）
    python3 run_validate_sql.py template_a_stock.sql
    python3 run_validate_sql.py rule20_author_mapping.sql

    # 2. 预览最终拼好的 SQL 不执行（调试用）
    python3 run_validate_sql.py template_a_stock.sql --print-only

    # 3. 跑临时 SQL（adhoc 模式，从 stdin 读）
    cat custom.sql | python3 run_validate_sql.py -
    echo "SELECT a_cp, COUNT(*) FROM ... WHERE ... {{EXEMPT_FILTER}} GROUP BY a_cp" \\
        | python3 run_validate_sql.py -

    # 4. 直接传 SQL 字符串（adhoc，单行）
    python3 run_validate_sql.py --sql "SELECT ... {{EXEMPT_FILTER}} ..."

    # 5. 关闭自动重试（调试用，强制单次跑）
    python3 run_validate_sql.py template_a_stock.sql --no-retry

约束：
- SQL 里有 {{EXEMPT_FILTER}} 占位符才能享受自动豁免；没占位符时按原样跑
- 本脚本不修改你的 SQL 文件，只在内存里替换后执行

重试策略（2026-05-12 新增）：
- 仅匹配 Trino/Kyuubi 已知的 transient 错误关键词（`EofException` / `HTTP 500` /
  `Connection reset` / `org.eclipse.jetty.io` / `Worker disconnected` / `Broken pipe` /
  `Read timed out` / `Connection closed`）才触发重试。
- 非 transient（语法错、权限错、SQL 查询超时等）直接退出，不浪费集群资源。
- 总共最多 3 次尝试（初次 + 2 次重试），backoff 30s → 60s。
- 设计目的：Trino worker 偶发 OOM/GC/重启 是外部不可控故障，重试能自愈；
  但不会掩盖真正的 SQL 问题。
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from paths import TMP_DIR, SQL_QUERY_TOOL, PYTHON_CMD
from exempt_lib import render_sql

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Transient 错误关键词（命中任一即重试）
# 参考：2026-05-12 观察到的 EofException + HTTP 500 + org.eclipse.jetty.io
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
]
MAX_RETRIES = 2        # 初次 + 重试 2 次 = 最多 3 次尝试
BACKOFF_SEC = [30, 60]  # 第 1 次重试前等 30s，第 2 次前等 60s


def has_transient_error(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in TRANSIENT_PATTERNS)


def execute_sql_with_retry(cleaned_sql: str, no_retry: bool = False) -> int:
    """执行 SQL，transient 错误自动重试；返回最终退出码。"""
    max_attempts = 1 if no_retry else (MAX_RETRIES + 1)
    for attempt in range(max_attempts):
        result = subprocess.run(
            [*PYTHON_CMD, SQL_QUERY_TOOL, cleaned_sql],
            cwd=str(TMP_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
        # 输出透传，保持和旧版兼容
        if result.stdout:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()
        if result.stderr:
            sys.stderr.write(result.stderr)
            sys.stderr.flush()

        # sql_query_tool 把 "Execution timed out (250s)" 当成正常 result 字符串返回 RC=0，
        # 这里识别字符串、强制翻译成失败（2026-05-15: rule21 因此默默拿到空结果，
        # 上游 djy-daily-run.sh 误以为成功）
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0:
            if "execution timed out" in combined.lower():
                sys.stderr.write(
                    "\n[run_validate_sql] sql_query_tool 报告 Execution timed out "
                    "但退出码为 0；强制翻译为失败。\n"
                )
                return 1
            return 0

        is_last = (attempt == max_attempts - 1)
        transient = has_transient_error(combined)

        if is_last or not transient:
            if transient:
                sys.stderr.write(f"\n[run_validate_sql] transient 错误重试 {MAX_RETRIES} 次仍失败，放弃。\n")
            else:
                sys.stderr.write("\n[run_validate_sql] 非 transient 错误（语法/权限/数据范围等），不重试。\n")
            return result.returncode

        wait = BACKOFF_SEC[attempt]
        sys.stderr.write(
            f"\n[run_validate_sql] transient 错误检测到（attempt {attempt + 1}/{max_attempts}），"
            f"等待 {wait}s 后重试...\n"
        )
        sys.stderr.flush()
        time.sleep(wait)

    return 1  # 不会走到这里


def clean_sql(text):
    lines = []
    for line in text.splitlines():
        if "--" in line:
            line = line.split("--", 1)[0]
        lines.append(line)
    return " ".join(lines).strip()


def resolve_sql_file(name):
    if os.path.isabs(name):
        return name if os.path.isfile(name) else None
    for base in [os.getcwd(), SCRIPT_DIR]:
        candidate = os.path.join(base, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def load_sql_source(argv):
    if "--sql" in argv:
        i = argv.index("--sql")
        if i + 1 >= len(argv):
            sys.stderr.write("ERROR: --sql requires a SQL string\n")
            sys.exit(2)
        return argv[i + 1], "<--sql arg>"

    positional = [a for a in argv[1:] if not a.startswith("--")]
    if not positional:
        sys.stderr.write("ERROR: must provide <sql_file> or '-' for stdin\n")
        sys.stderr.write(__doc__)
        sys.exit(2)

    target = positional[0]
    if target == "-":
        return sys.stdin.read(), "<stdin>"

    path = resolve_sql_file(target)
    if not path:
        sys.stderr.write(f"ERROR: SQL file not found: {target}\n")
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), path


def main():
    print_only = "--print-only" in sys.argv
    no_retry = "--no-retry" in sys.argv

    raw_sql, source = load_sql_source(sys.argv)
    rendered = render_sql(raw_sql)
    cleaned = clean_sql(rendered)

    if print_only:
        sys.stderr.write(f"# Source: {source}\n")
        sys.stderr.write(f"# Exemption auto-injected from exemptions.json\n")
        print(cleaned)
        return

    rc = execute_sql_with_retry(cleaned, no_retry=no_retry)
    sys.exit(rc)


if __name__ == "__main__":
    main()
