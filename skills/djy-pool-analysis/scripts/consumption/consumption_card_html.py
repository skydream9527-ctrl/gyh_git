#!/usr/bin/env python3
"""生成消费日报 HTML 表格（红绿渐变色标注环比）

输入：JSON 数据（通过函数调用或 stdin）
输出：自包含 HTML 文件路径
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from paths import TMP_DIR


def _color(pct: float) -> str:
    if pct is None or pct != pct:
        return "transparent"
    intensity = min(abs(pct) / 30, 1.0) * 0.35 + 0.05
    if pct > 0:
        return f"rgba(76, 175, 80, {intensity:.2f})"
    elif pct < 0:
        return f"rgba(244, 67, 54, {intensity:.2f})"
    return "transparent"


def _arrow(pct: float) -> str:
    if pct is None or pct != pct:
        return '<span class="delta">-</span>'
    sign = "+" if pct >= 0 else ""
    color = "#2e7d32" if pct >= 0 else "#c62828"
    return f'<span class="delta" style="color:{color}">{sign}{pct:.1f}%</span>'


def _fmt_num(val, decimals=0):
    if val is None:
        return "-"
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:,.{decimals}f}"


def _truncate(s: str, maxlen: int = 30) -> str:
    if not s:
        return "-"
    return s[:maxlen] + "..." if len(s) > maxlen else s


def generate_html(cp_data: list, top5_vv: list, top5_dura: list, report_date: str) -> str:
    CP_DISPLAY = {
        "cn-dihui-djy": "dihui",
        "cn-beike-djy": "beike",
        "cn-guoying-djy": "guoying",
        "cn-meilaoban-djy": "meilaoban",
    }

    cols = [
        ("消费VV", "vv", "vv_pct", 0),
        ("消费时长(分钟)", "consum_dura_min", "dura_pct", 1),
        ("分发内容量", "distribute_content_cnt", "content_pct", 0),
        ("分发作者量", "distribute_author_cnt", "author_pct", 0),
        ("篇均VV", "vv_per_item", "vv_item_pct", 1),
        ("单VV消费时长(秒)", "dura_per_vv_sec", "dura_vv_pct", 1),
    ]

    rows_html = ""
    for row in cp_data:
        cp_label = CP_DISPLAY.get(row["cp"], row["cp"])
        cells = f'<td class="cp-name">{cp_label}</td>'
        for _, val_key, pct_key, dec in cols:
            val = row.get(val_key)
            pct = row.get(pct_key)
            bg = _color(pct)
            cells += f'<td style="background:{bg}">{_fmt_num(val, dec)}<br>{_arrow(pct)}</td>'
        rows_html += f"<tr>{cells}</tr>\n"

    def top5_html(items, metric_key, metric_label, decimals):
        if not items:
            return "<p>暂无数据</p>"
        h = '<table class="top5"><tr><th>#</th><th>内容ID</th><th>标题</th><th>CP</th><th>' + metric_label + '</th></tr>'
        for i, item in enumerate(items, 1):
            item_id = item.get("item_id") or "-"
            title = _truncate(item.get("item_title") or "", 28)
            cp = CP_DISPLAY.get(item.get("item_cp_name", ""), item.get("item_cp_name", ""))
            val = _fmt_num(item.get(metric_key), decimals)
            h += f'<tr><td>{i}</td><td class="mono">{item_id}</td><td>{title}</td><td>{cp}</td><td class="num">{val}</td></tr>'
        h += "</table>"
        return h

    top_vv_html = top5_html(top5_vv, "vv", "消费VV", 0)
    top_dura_html = top5_html(top5_dura, "consum_dura_min", "消费时长(分钟)", 2)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; padding: 24px; background: #fff; width: 1200px; }}
h2 {{ font-size: 18px; color: #333; margin-bottom: 12px; }}
h3 {{ font-size: 15px; color: #555; margin: 20px 0 8px; }}
table.main {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
table.main th {{ background: #f5f5f5; padding: 10px 8px; text-align: center; font-weight: 600; border-bottom: 2px solid #e0e0e0; white-space: nowrap; }}
table.main td {{ padding: 10px 8px; text-align: center; border-bottom: 1px solid #eee; }}
table.main td.cp-name {{ font-weight: 600; text-align: left; background: transparent !important; }}
.delta {{ font-size: 11px; display: block; margin-top: 2px; }}
.top5-row {{ display: flex; gap: 24px; margin-top: 8px; align-items: stretch; }}
.top5-col {{ flex: 1; display: flex; flex-direction: column; }}
table.top5 {{ width: 100%; border-collapse: collapse; font-size: 12px; flex: 1; }}
table.top5 th {{ background: #fafafa; padding: 6px; text-align: left; border-bottom: 1px solid #e0e0e0; white-space: nowrap; }}
table.top5 td {{ padding: 6px; border-bottom: 1px solid #f0f0f0; height: 44px; vertical-align: middle; }}
table.top5 td.mono {{ font-family: monospace; font-size: 10px; color: #666; word-break: break-all; max-width: 180px; }}
table.top5 td.num {{ text-align: right; font-weight: 500; white-space: nowrap; }}
.date-label {{ color: #999; font-size: 12px; margin-bottom: 16px; }}
</style></head><body>
<h2>消费数据概览</h2>
<div class="date-label">数据日期：{report_date} · 环比对比前一日</div>
<table class="main">
<tr><th>CP</th>{"".join(f"<th>{c[0]}</th>" for c in cols)}</tr>
{rows_html}
</table>
<div class="top5-row">
<div class="top5-col">
<h3>消费VV Top5</h3>
{top_vv_html}
</div>
<div class="top5-col">
<h3>消费时长 Top5</h3>
{top_dura_html}
</div>
</div>
</body></html>"""
    return html


def render_to_file(cp_data, top5_vv, top5_dura, report_date, out_path=None):
    html = generate_html(cp_data, top5_vv, top5_dura, report_date)
    if out_path is None:
        out_path = TMP_DIR / f"consumption_card_{report_date}.html"
    Path(out_path).write_text(html, encoding="utf-8")
    return str(out_path)


if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    path = render_to_file(
        data["cp_data"], data["top5_vv"], data["top5_dura"], data["report_date"]
    )
    print(path)
