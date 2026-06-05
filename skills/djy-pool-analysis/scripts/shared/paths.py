"""统一路径配置 · djy-pool-analysis skill

OUTPUT_ROOT 默认指向 git 仓库目录，产出直接落盘，便于一次性 push。
"""
import os
import sys
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get(
    "DJY_OUTPUT_ROOT",
    str(Path.home() / "Desktop" / "ai_djy_pool_analysis"),
))

REPORTS_DIR = OUTPUT_ROOT / "reports"
DAILY_REPORT_DIR = OUTPUT_ROOT / "daily_reports"
DIRTY_DIR = OUTPUT_ROOT / "dirty"
CHARTS_DIR = OUTPUT_ROOT / "charts"
TMP_DIR = OUTPUT_ROOT / "tmp"

for _d in (REPORTS_DIR, DAILY_REPORT_DIR, DIRTY_DIR, CHARTS_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

_SQL_TOOL_CANDIDATES = [
    os.environ.get("DATA_SQL_TOOL"),
    os.path.expanduser("~/.claude/skills/data-sql/scripts/sql_query_tool.py"),
    os.path.expanduser("~/djy-deploy/skills/data-sql/scripts/sql_query_tool.py"),
]
SQL_QUERY_TOOL = next(
    (p for p in _SQL_TOOL_CANDIDATES if p and os.path.exists(p)),
    _SQL_TOOL_CANDIDATES[1],
)

# data-sql skill 的 .env 与 sql_query_tool.py 同目录，提供 DATAWORKS_TOKEN_ID 等。
DATA_SQL_ENV = os.path.join(os.path.dirname(SQL_QUERY_TOOL), ".env")

def _detect_python():
    """Linux 优先用 venv（cron 无法 source activate），否则退回系统 python3。"""
    candidates = [
        os.environ.get("DJY_PYTHON"),
        os.path.expanduser("~/djy-deploy/.venv/bin/python"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return [c]
    return ["/usr/bin/python3"]


# Mac arm64 需要 arch wrap 强制 native 架构（绕开 Rosetta 环境），Linux 走 venv 检测
PYTHON_CMD = (
    ["arch", "-arm64", "/usr/bin/python3"]
    if sys.platform == "darwin"
    else _detect_python()
)
