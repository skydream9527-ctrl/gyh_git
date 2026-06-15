#!/usr/bin/env python3
"""组装日报图表卡片 JSON · 按 references/report_format.md 的 4 段式

用法：
  python3 build_chart_card.py <stock_csv> <c1> <c2> <c3> <c4> <c5> <c6>
  # stock_csv: chart_stock_trend 最新结果 CSV
  # c1~c6: 6 张图片对应的 image_key

输出：stdout 完整 interactive card JSON（供 feishu_post.py 使用）

4 段式（按 report_format.md）：
  段 1 · Top 3 异动
  段 2 · CP 总览（4 列并排）
  段 3 · 每家 CP 明细（分 CP 列字段 + 分级）
  段 · 趋势图（6 张独立图：① 每日入库 · ② 异常存量 · ③④⑤⑥ 每家 CP 字段）
  段 4 · 脚注（数据源 + 豁免说明）
"""
import csv
import datetime
import json
import sys


# 字段展示名
FIELD_LABEL = {
    "publish_time_n": "publish_time 空",
    "author_image_n": "author_image 空",
    "xm_author_id_n": "xm_author_id 空",
    "author_ip_n": "author_ip 空",
    "url_bad_n": "url 异常",
    "image_n": "image 空",
    "lead_author_id_n": "lead_author_id 空",
    "category_n": "category 空",
    "video_duration_bad_n": "video_duration ≤0",
    "video_detail_empty_n": "video_detail_list 整串空",
    "video_detail_incomplete_n": "video_detail 7 字段缺",
    "body_null_n": "body 空 (NEWS)",
    "word_cnt_null_n": "e_xm_body_word_cnt 空",
    "image_cnt_null_n": "e_xm_image_cnt 空",
}
FIELD_COLS = list(FIELD_LABEL.keys())


def severity(n: int) -> str:
    """≥1000=🚨紧急  100-999=⚠️高  1-99=🟡低  0=✅正常"""
    if n >= 1000:
        return "🚨"
    if n >= 100:
        return "⚠️"
    if n >= 1:
        return "🟡"
    return "✅"


def cp_level(counts: dict) -> tuple:
    """返回 (紧急数, 高数, 低数)"""
    urgent = sum(1 for v in counts.values() if v >= 1000)
    high = sum(1 for v in counts.values() if 100 <= v < 1000)
    low = sum(1 for v in counts.values() if 1 <= v < 100)
    return urgent, high, low


def cp_severity(urgent: int, high: int, low: int) -> str:
    if urgent > 0:
        return "🚨"
    if high > 0:
        return "⚠️"
    if low > 0:
        return "🟡"
    return "✅"


def load(csv_path: str):
    """返回 {cp_short: {cutoff: row}}"""
    CP_LONG = {"cn-guoying-djy": "guoying", "cn-dihui-djy": "dihui",
               "cn-beike-djy": "beike", "cn-meilaoban-djy": "meilaoban"}
    stock = {}
    for r in csv.DictReader(open(csv_path)):
        cp = CP_LONG[r["a_cp"]]
        stock.setdefault(cp, {})[r["snap_date"]] = r
    return stock


def section_top3(stock: dict) -> str:
    """找本周变化最大的 3 个字段（按绝对增量）"""
    cutoffs = sorted(list(stock["guoying"].keys()))
    first, last = cutoffs[0], cutoffs[-1]
    changes = []  # (cp, col, old, new, diff)
    for cp, rows in stock.items():
        for col in FIELD_COLS:
            old = int(rows[first][col])
            new = int(rows[last][col])
            diff = new - old
            if diff >= 100 or (new >= 1000 and diff >= 50):
                changes.append((cp, col, old, new, diff))
    changes.sort(key=lambda x: -x[4])
    lines = []
    for i, (cp, col, old, new, diff) in enumerate(changes[:3]):
        icon = "🔥" if i == 0 else ("📈" if i == 1 else "⚠️")
        # 用倍数或绝对值描述
        if old > 0 and new / old >= 5:
            desc = f"**{old:,} → {new:,}**（7 天增 {new/old:.1f} 倍）"
        else:
            desc = f"**{old:,} → {new:,}**（本周 +{diff:,}）"
        lines.append(f"{icon} **{cp}** / `{FIELD_LABEL[col]}`：{desc}")
    return "\n".join(lines)


def section_cp_row(cp: str, row: dict) -> dict:
    """一列：CP 总量 + 分级数"""
    counts = {col: int(row[col]) for col in FIELD_COLS}
    urgent, high, low = cp_level(counts)
    sev = cp_severity(urgent, high, low)
    total = int(row["total"])
    bad_any = int(row["bad_any"])
    return {
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "vertical_align": "top",
        "elements": [
            {"tag": "markdown", "content": f"{sev} **{cp}**"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"池内 **{total:,}**\n异常 **{bad_any:,}**\n🚨{urgent} · ⚠️{high} · 🟡{low}",
                },
            },
        ],
    }


def section_cp_detail(cp: str, row: dict) -> dict:
    """每家 CP 一段：按严重度列字段"""
    counts = {col: int(row[col]) for col in FIELD_COLS if int(row[col]) > 0}
    urgent, high, low = cp_level(counts)
    sev = cp_severity(urgent, high, low)
    total = int(row["total"])
    bad_any = int(row["bad_any"])
    header = f"**{sev} {cp}**（池内 {total:,} · 异常 {bad_any:,} · 🚨{urgent} ⚠️{high} 🟡{low}）"

    # 按数量倒序列字段
    sorted_fields = sorted(counts.items(), key=lambda x: -x[1])
    lines = []
    for col, n in sorted_fields:
        lines.append(f"· `{FIELD_LABEL[col]}` · {severity(n)} **{n:,}**")
    if not lines:
        lines = ["· 所有字段 ✅ 正常"]
    return {"tag": "markdown", "content": header + "\n" + "\n".join(lines)}


def _top5_lark_md(items: list) -> str:
    """将 Top5 列表格式化为 lark_md 文本：第一行 VV+时长，第二行 ID，第三行标题"""
    if not items:
        return "暂无数据"
    lines = []
    for i, it in enumerate(items, 1):
        vv = it.get("vv")
        dura = it.get("consum_dura_min")
        vv_str = f"{int(vv):,}" if vv is not None else "-"
        dura_str = f"{int(float(dura)):,}" if dura is not None else "-"
        item_id = it.get("item_id") or "-"
        title = it.get("item_title") or "-"
        lines.append(f"{i}. 消费VV **{vv_str}** · 消费时长 **{dura_str}** 分钟\n`{item_id}`\n{title}")
    return "\n".join(lines)


def build_card(csv_path: str, img_keys: dict, consumption_img: str = None, consumption_json: str = None, report_url: str = None):
    """img_keys: {'c1': 'img_v3_...', 'c2': ..., 'c3': ..., 'c4': ..., 'c5': ..., 'c6': ...}
    consumption_img: 可选，消费数据表格的 image_key（置顶显示）
    consumption_json: 可选，消费数据 JSON 路径（用于提取 Top5 文本）
    report_url: 可选，GitLab Pages 完整 HTML 报告链接（显示在脚注上方）
    """
    stock = load(csv_path)
    cutoffs = sorted(list(stock["guoying"].keys()))
    last = cutoffs[-1]
    date_label = datetime.date.today().strftime("%Y-%m-%d")
    now_label = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    elements = []

    # ==== 消费数据概览（置顶） ====
    if consumption_img:
        elements.append({"tag": "markdown", "content": "**📈 消费数据概览**"})
        elements.append({
            "tag": "img",
            "img_key": consumption_img,
            "alt": {"tag": "plain_text", "content": "CP 维度消费指标"},
            "mode": "fit_horizontal",
            "preview": True,
        })
        # Top5 文本（从 consumption_json 读取）
        if consumption_json:
            import os
            if os.path.isfile(consumption_json):
                cdata = json.load(open(consumption_json, encoding="utf-8"))
                top5_vv_text = _top5_lark_md(cdata.get("top5_vv", []))
                top5_dura_text = _top5_lark_md(cdata.get("top5_dura", []))
                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**消费VV Top5**\n{top5_vv_text}"}})
                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**消费时长 Top5**\n{top5_dura_text}"}})
        elements.append({"tag": "hr"})

    # ==== 段 1 · Top 3 异动 ====
    elements.append({"tag": "markdown", "content": "**🔥 当前异常趋势 Top 3**"})
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": section_top3(stock)}})
    elements.append({"tag": "hr"})

    # ==== 段 2 · CP 总览 4 列 ====
    elements.append({"tag": "markdown", "content": f"**📋 CP 总览 · 截止 {last[:4]}-{last[4:6]}-{last[6:]}**"})
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "columns": [section_cp_row(cp, stock[cp][last]) for cp in ["guoying", "dihui", "beike", "meilaoban"]],
    })
    elements.append({"tag": "hr"})

    # ==== 段 3 · 每家 CP 明细 ====
    elements.append({"tag": "markdown", "content": "**🔍 每家 CP 异常字段明细**"})
    for cp in ["guoying", "dihui", "beike", "meilaoban"]:
        elements.append(section_cp_detail(cp, stock[cp][last]))
    elements.append({"tag": "hr"})

    # ==== 趋势图 · 整体 2 张 ====
    elements.append({"tag": "markdown", "content": "**📊 整体趋势**"})
    for cid, alt in [
        ("c1", "① 4 家 CP 每日入库内容数"),
        ("c2", "② 4 家 CP 内容池异常存量趋势"),
    ]:
        elements.append({
            "tag": "img",
            "img_key": img_keys[cid],
            "alt": {"tag": "plain_text", "content": alt},
            "mode": "fit_horizontal",
            "preview": True,
        })
    elements.append({"tag": "hr"})

    # 区域 B（c3-c6）不推送到飞书卡片

    # ==== 报告链接 ====
    if report_url:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"📎 [查看完整 HTML 报告]({report_url})"}})

    # ==== 段 4 · 脚注 ====
    footnote = (
        "数据源 paimon_zjyprc_hadoop.browser.business_content_pool_realtime · "
        "豁免 28 条 item + beike 的 author_ip 空 · "
        f"跑数时间 {now_label}"
    )
    elements.append({"tag": "hr"})
    elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": footnote}]})

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📊 djy 内容池校验 · 日报 · {date_label}"},
            "subtitle": {"tag": "plain_text", "content": f"数据截至 {now_label} · 口径=全量存量"},
            "template": "blue",
        },
        "elements": elements,
    }
    return {"card": card}


def main():
    args = sys.argv[1:]
    consumption_img = None
    consumption_json = None
    report_url = None
    if "--consumption-img" in args:
        idx = args.index("--consumption-img")
        consumption_img = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
    if "--consumption-json" in args:
        idx = args.index("--consumption-json")
        consumption_json = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
    if "--report-url" in args:
        idx = args.index("--report-url")
        report_url = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if len(args) < 7:
        print(__doc__)
        print("\n额外参数：")
        print("  --consumption-img <image_key>   消费数据表格图片（置顶显示）")
        print("  --consumption-json <json_path>  消费数据 JSON（提取 Top5 文本）")
        print("  --report-url <url>              GitLab Pages 完整报告链接")
        sys.exit(1)
    csv_path = args[0]
    img_keys = {f"c{i}": args[i] for i in range(1, 7)}
    print(json.dumps(build_card(csv_path, img_keys, consumption_img, consumption_json, report_url), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
