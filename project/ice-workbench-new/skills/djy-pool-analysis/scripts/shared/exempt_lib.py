#!/usr/bin/env python3
"""
exempt_lib.py · 豁免数据源单一读取层

职责：
- 读 skill 根目录的 exemptions.json
- 生成 SQL 模板替换用的 NOT IN 片段
- 对外提供 Python API 供 run_validate_sql.py 和其他脚本调用

使用：
    from exempt_lib import get_exempt_filter, get_exempt_ids, render_sql
"""
import json
import os
import sys

EXEMPT_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..",
    "exemptions.json",
)


def load_exemptions():
    with open(EXEMPT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def get_exempt_ids(cp=None):
    entries = load_exemptions()
    if cp:
        entries = [e for e in entries if e["a_cp"] == cp]
    return [e["a_item_id"] for e in entries]


def get_exempt_filter(indent="    "):
    # CP 级时间过滤：meilaoban 因 2026-05-18 域名切换前数据存在大量历史污染，
    # 起算点之前的内容全量豁免（total / 异常 / 趋势 / detail 一并过滤）。
    cp_time_clause = (
        "AND NOT (a_cp = 'cn-meilaoban-djy' "
        "AND (create_time IS NULL OR create_time = '' OR LOWER(create_time) = 'null' "
        "OR from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') < '2026-05-18'))"
    )
    ids = get_exempt_ids()
    if not ids:
        return cp_time_clause
    inner = ",\n".join(f"{indent}'{id_}'" for id_ in ids)
    closing_indent = indent[:-2] if len(indent) >= 2 else ''
    return (
        f"AND a_item_id NOT IN (\n{inner}\n{closing_indent})\n"
        f"  {cp_time_clause}"
    )


def render_sql(template_text):
    out = template_text.replace("{{EXEMPT_FILTER}}", get_exempt_filter())
    # 动态日期占位符（**日报口径 T-1 锚定**：CUTOFF_0 = 昨天，CUTOFF_N = 昨天往前第 N 天）
    #   {{CUTOFF_N}}      → YYYYMMDD  （chart_stock_trend.sql 用，paimon date 字段格式）
    #   {{CUTOFF_ISO_N}}  → YYYY-MM-DD（chart_daily_trend.sql 用，from_unixtime 输出格式）
    # 锚点说明：消费表 T+1 产出，今天只能拿昨日消费数据；为让 stock/daily/消费三者日期对齐，
    # 整个日报统一锚 T-1。如需运行时自定义锚点（补发/回溯），可设 DJY_DATE_ANCHOR=YYYY-MM-DD。
    if "{{CUTOFF_" in out:
        from datetime import date, timedelta
        import os
        anchor_env = os.environ.get("DJY_DATE_ANCHOR", "").strip()
        if anchor_env:
            anchor = date.fromisoformat(anchor_env)
        else:
            anchor = date.today() - timedelta(days=1)  # T-1
        for n in range(31):
            d = anchor - timedelta(days=n)
            out = out.replace(f"{{{{CUTOFF_ISO_{n}}}}}", d.strftime("%Y-%m-%d"))
            out = out.replace(f"{{{{CUTOFF_{n}}}}}", d.strftime("%Y%m%d"))
    return out


def stats():
    entries = load_exemptions()
    total = len(entries)
    by_cp = {}
    by_category = {}
    by_status = {}
    for e in entries:
        by_cp[e["a_cp"]] = by_cp.get(e["a_cp"], 0) + 1
        by_category[e.get("category", "uncategorized")] = (
            by_category.get(e.get("category", "uncategorized"), 0) + 1
        )
        by_status[e.get("status", "unknown")] = (
            by_status.get(e.get("status", "unknown"), 0) + 1
        )
    return {
        "total": total,
        "by_cp": by_cp,
        "by_category": by_category,
        "by_status": by_status,
    }


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if action == "filter":
        print(get_exempt_filter())
    elif action == "ids":
        for id_ in get_exempt_ids():
            print(id_)
    elif action == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))
    else:
        print(f"unknown action: {action}", file=sys.stderr)
        print("usage: exempt_lib.py [filter|ids|stats]", file=sys.stderr)
        sys.exit(1)
