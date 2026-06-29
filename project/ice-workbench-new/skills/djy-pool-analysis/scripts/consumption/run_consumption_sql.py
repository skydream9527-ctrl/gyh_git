#!/usr/bin/env python3
"""
run_consumption_sql.py · 消费指标分析 SQL 统一运行入口

使用：
    python3 run_consumption_sql.py tpl_dimension_drill.sql
    echo "SELECT ..." | python3 run_consumption_sql.py -
    python3 run_consumption_sql.py --sql "SELECT ..."
    python3 run_consumption_sql.py tpl_dimension_drill.sql --print-only
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from paths import TMP_DIR, SQL_QUERY_TOOL, PYTHON_CMD

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


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

    raw_sql, source = load_sql_source(sys.argv)
    cleaned = clean_sql(raw_sql)

    if print_only:
        sys.stderr.write(f"# Source: {source}\n")
        print(cleaned)
        return

    result = subprocess.run(
        [*PYTHON_CMD, SQL_QUERY_TOOL, cleaned],
        cwd=str(TMP_DIR),
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
