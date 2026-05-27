#!/usr/bin/env python3
"""火山ABtest实验分析 - 查询数据并生成指标涨跌报告（含p值+有效用户率+逐日趋势）"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

TABLES = {
    "browser": "ads_browser_toutiao_abtest_common_1d",
    "newhome": "ads_newhome_toutiao_abtest_common_1d",
}

PVALUE_TABLES = {
    "browser": "dm_browser_toutiao_abtest_pvalue_df",
    "newhome": "dm_newhome_toutiao_abtest_pvalue_df",
}

MEDIA_ALIASES = {
    "浏览器": "browser",
    "browser": "browser",
    "内容中心": "newhome",
    "桌面内容中心": "newhome",
    "newhome": "newhome",
    "nh": "newhome",
    "mcc": "newhome",
}

CORE_METRICS = {
    "per_duration": "人均消费时长(min)",
    "per_feed_dur": "人均信息流时长(min)",
    "per_vv": "人均VV",
    "ctr": "CTR",
    "valid_user_rate": "有效用户率",
    "arpu": "ARPU",
    "consume_rate": "消费渗透率",
    "per_eview": "人均广告曝光",
}

VV_METRICS = {
    "per_tuwen_vv": "图文",
    "per_mini_vv": "小视频",
    "per_inline_vv": "内流",
    "per_skit_vv": "短剧",
    "per_livestream_vv": "直播",
    "per_novel_vv": "小说",
    "per_shortstory_vv": "短故事",
}

DURATION_METRICS = {
    "per_news_dura": "资讯",
    "per_video_dura": "视频",
    "per_mini_video_dura": "小视频",
    "per_skit_dura": "短剧",
    "per_livestream_dura": "直播",
    "per_novel_dura": "小说",
    "per_shortstory_dura": "短故事",
}

PVALUE_FIELD_MAP = {
    "ctr": "p_ctr_num",
    "per_duration": "p_avg_dura_num",
    "per_feed_dur": "p_avg_dura_num",
    "per_vv": "p_avg_click_num",
    "valid_user_rate": "p_valid_user_rate_num",
    "arpu": "p_avg_fee_num",
    "consume_rate": "p_utr_num",
    "per_eview": "p_avg_eview_num",
}

SQL_TEMPLATES = {
    "browser": """
SELECT
    tester_version_name,
    sum(expos_uv_num) as total_uv,
    sum(group_uv_num) as total_group_uv,
    sum(valid_uv_num) as total_valid_uv,
    sum(browser_duration/60000)/sum(expos_uv_num) as per_duration,
    sum(feed_dur/60000)/sum(expos_uv_num) as per_feed_dur,
    sum(vv)/sum(expos_uv_num) as per_vv,
    sum(tuwen_vv)/sum(expos_uv_num) as per_tuwen_vv,
    sum(mini_vv)/sum(expos_uv_num) as per_mini_vv,
    sum(inline_vv)/sum(expos_uv_num) as per_inline_vv,
    sum(skit_vv)/sum(expos_uv_num) as per_skit_vv,
    sum(livestream_vv)/sum(expos_uv_num) as per_livestream_vv,
    sum(novel_vv)/sum(expos_uv_num) as per_novel_vv,
    sum(shortstory_vv)/sum(expos_uv_num) as per_shortstory_vv,
    sum(news_dura/60000)/sum(expos_uv_num) as per_news_dura,
    sum(video_dura/60000)/sum(expos_uv_num) as per_video_dura,
    sum(skit_dura/60000)/sum(expos_uv_num) as per_skit_dura,
    sum(livestream_dura/60000)/sum(expos_uv_num) as per_livestream_dura,
    sum(novel_dura/60000)/sum(expos_uv_num) as per_novel_dura,
    sum(shortstory_dura/60000)/sum(expos_uv_num) as per_shortstory_dura,
    sum(mini_video_dur/60000)/sum(expos_uv_num) as per_mini_video_dura,
    sum(valid_uv_num)/sum(group_uv_num) as valid_user_rate,
    sum(fee)/sum(expos_uv_num) as arpu,
    sum(consum_uv_num)/sum(expos_uv_num) as consume_rate,
    sum(click_pv_cnt)/sum(expos_pv_cnt) as ctr,
    sum(eview)/sum(expos_uv_num) as per_eview
FROM {table}
WHERE date BETWEEN {start} AND {end}
    AND tester_fight_ids = '{exp_id}'
GROUP BY tester_version_name
ORDER BY tester_version_name
""",
    "newhome": """
SELECT
    tester_version_name,
    sum(expos_uv_num) as total_uv,
    sum(group_uv_num) as total_group_uv,
    sum(valid_uv_num) as total_valid_uv,
    sum(browser_duration/60000)/sum(expos_uv_num) as per_duration,
    sum(feed_dura/60000)/sum(expos_uv_num) as per_feed_dur,
    sum(vv)/sum(expos_uv_num) as per_vv,
    sum(news_vv_cnt)/sum(expos_uv_num) as per_tuwen_vv,
    sum(mini_video_vv_cnt)/sum(expos_uv_num) as per_mini_vv,
    sum(video_vv_cnt)/sum(expos_uv_num) as per_inline_vv,
    sum(playlet_vv_cnt)/sum(expos_uv_num) as per_skit_vv,
    0 as per_livestream_vv,
    sum(book_read_vv)/sum(expos_uv_num) as per_novel_vv,
    0 as per_shortstory_vv,
    sum(news_browser_duration/60000)/sum(expos_uv_num) as per_news_dura,
    sum(video_play_over_duration/60000)/sum(expos_uv_num) as per_video_dura,
    sum(playlet_duration/60000)/sum(expos_uv_num) as per_skit_dura,
    sum(live_event_duration/60000)/sum(expos_uv_num) as per_livestream_dura,
    sum(book_read_dura/60000)/sum(expos_uv_num) as per_novel_dura,
    0 as per_shortstory_dura,
    sum(mini_video_play_over_duration/60000)/sum(expos_uv_num) as per_mini_video_dura,
    sum(valid_uv_num)/sum(group_uv_num) as valid_user_rate,
    sum(fee)/sum(expos_uv_num) as arpu,
    sum(consum_uv)/sum(expos_uv_num) as consume_rate,
    sum(click_pv_cnt)/sum(expos_pv_cnt) as ctr,
    sum(eview)/sum(expos_uv_num) as per_eview
FROM {table}
WHERE date BETWEEN {start} AND {end}
    AND tester_fight_ids = '{exp_id}'
GROUP BY tester_version_name
ORDER BY tester_version_name
""",
}

DAILY_SQL = {
    "browser": """
SELECT
    date,
    tester_version_name,
    expos_uv_num as uv,
    feed_dur/60000/expos_uv_num as per_feed_dur,
    valid_uv_num*1.0/group_uv_num as valid_user_rate,
    click_pv_cnt*1.0/expos_pv_cnt as ctr
FROM {table}
WHERE date BETWEEN {start} AND {end}
    AND tester_fight_ids = '{exp_id}'
ORDER BY date, tester_version_name
""",
    "newhome": """
SELECT
    date,
    tester_version_name,
    expos_uv_num as uv,
    feed_dura/60000/expos_uv_num as per_feed_dur,
    valid_uv_num*1.0/group_uv_num as valid_user_rate,
    click_pv_cnt*1.0/expos_pv_cnt as ctr
FROM {table}
WHERE date BETWEEN {start} AND {end}
    AND tester_fight_ids = '{exp_id}'
ORDER BY date, tester_version_name
""",
}

PVALUE_SQL = """
SELECT *
FROM {table}
WHERE date BETWEEN {start} AND {end}
    AND tester_fight_id = '{exp_id}'
ORDER BY date DESC
LIMIT 1
"""


def find_datum():
    for p in [Path.home() / "bin" / "datum", Path("/usr/local/bin/datum")]:
        if p.exists():
            return str(p)
    r = subprocess.run(["which", "datum"], capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip()
    print("Error: datum CLI not found", file=sys.stderr)
    sys.exit(1)


def parse_date(s: str) -> int:
    s = s.strip().replace("年", "-").replace("月", "-").replace("日", "")
    if s.isdigit() and len(s) == 8:
        return int(s)
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"]:
        try:
            return int(datetime.strptime(s, fmt).strftime("%Y%m%d"))
        except ValueError:
            pass
    for fmt in ["%m.%d", "%m-%d", "%m/%d"]:
        try:
            dt = datetime.strptime(s, fmt)
            return int(dt.replace(year=datetime.now().year).strftime("%Y%m%d"))
        except ValueError:
            pass
    print(f"Error: 无法解析日期 '{s}'", file=sys.stderr)
    sys.exit(1)


def run_query(datum: str, sql: str, schema: str = "browser") -> Optional[dict]:
    r = subprocess.run(
        [datum, "query", "--region", "zjyprc", "--engine", "doris",
         "--catalog", "doris_zjyprc_hadoop", "--schema", schema,
         "--sql", sql],
        capture_output=True, text=True, timeout=300,
    )
    output = r.stdout.strip()
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                if "error" in data:
                    print(f"Query error: {data['error']['message']}", file=sys.stderr)
                    return None
                return data
            except json.JSONDecodeError:
                pass
    if r.returncode != 0:
        print(f"Query failed: {r.stderr[:200]}", file=sys.stderr)
    return None


def parse_results(data: dict) -> dict:
    cols = [c["name"] for c in data["columns"]]
    groups = {}
    for row in data["rows"]:
        name = row[0]
        groups[name] = {
            cols[i]: (float(row[i]) if row[i] is not None else 0.0)
            for i in range(1, len(cols))
        }
    return groups


def parse_daily(data: dict) -> list[dict]:
    cols = [c["name"] for c in data["columns"]]
    rows = []
    for row in data["rows"]:
        rows.append({cols[i]: row[i] for i in range(len(cols))})
    return rows


def parse_pvalues(data: dict) -> dict:
    if not data or not data.get("rows"):
        return {}
    cols = [c["name"] for c in data["columns"]]
    row = data["rows"][0]
    return {cols[i]: row[i] for i in range(len(cols))}


def find_control(groups: dict) -> str:
    for name in groups:
        if "对照" in name or "control" in name.lower() or "baseline" in name.lower():
            return name
    for name in groups:
        if "v1" in name.lower():
            return name
    return sorted(groups.keys())[0]


def pct(val: float, base: float) -> Optional[float]:
    return (val / base - 1) * 100 if base else None


def fmt(p: Optional[float]) -> str:
    if p is None:
        return "N/A"
    return f"{'+' if p > 0 else ''}{p:.2f}%"


def significance_label(p_val) -> str:
    if p_val is None:
        return ""
    try:
        p = float(p_val)
    except (TypeError, ValueError):
        return ""
    if p < 0.001:
        return "极显著"
    elif p < 0.05:
        return "显著"
    else:
        return "不显著"


def fmt_with_sig(change: Optional[float], p_val, threshold: float = 1.0) -> str:
    s = fmt(change)
    sig = significance_label(p_val)
    if change is not None and abs(change) >= threshold:
        s = f"**{s}**"
    if sig:
        s += f" ({sig})"
    return s


def fmt_date(d: int) -> str:
    s = str(d)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def short_name(name: str) -> str:
    clean = name.replace("实验组", "").replace("对照组", "").strip()
    return clean if clean else name


def generate_report(
    media: str, exp_id: str, start: int, end: int,
    groups: dict, ctrl: str, pvalues: dict, daily_data: list[dict],
) -> str:
    media_cn = "浏览器" if media == "browser" else "桌面内容中心"
    base = groups[ctrl]
    exp = {k: v for k, v in groups.items() if k != ctrl}
    names = sorted(exp.keys())
    sn = {n: short_name(n) for n in names}

    d1 = datetime.strptime(str(start), "%Y%m%d")
    d2 = datetime.strptime(str(end), "%Y%m%d")
    days = (d2 - d1).days + 1

    uv_vals = [g["total_uv"] for g in groups.values()]
    balanced = max(uv_vals) / min(uv_vals) < 1.05 if min(uv_vals) > 0 else False

    lines = [
        f"## 实验ID：{exp_id}（{media_cn}）",
        f"**日期范围：{fmt_date(start)} ~ {fmt_date(end)}（{days}天加权）**",
        f"**样本量：各组 ~{base['total_uv']/days/10000:.0f}万 日均UV，{'均衡分流' if balanced else '非均匀分流'}**",
        "",
    ]

    # --- 核心指标 ---
    sep = "|------|" + "|".join("-----" for _ in names) + "|"
    lines.append(f"### 核心指标变化（vs {ctrl}）")
    lines.append("")
    lines.append("| 指标 | " + " | ".join(sn[n] for n in names) + " |")
    lines.append(sep)
    for key, label in CORE_METRICS.items():
        row = f"| {label} |"
        p_field = PVALUE_FIELD_MAP.get(key)
        p_val = pvalues.get(p_field) if p_field else None
        for n in names:
            change = pct(exp[n][key], base[key])
            row += f" {fmt_with_sig(change, p_val)} |"
        lines.append(row)
    lines.append("")

    # --- 有效用户率绝对值 ---
    lines.append("### 有效用户率详情")
    lines.append("")
    lines.append("| 组别 | 进组UV(日均) | 有效UV(日均) | 有效用户率 |")
    lines.append("|------|------------|------------|----------|")
    for name in [ctrl] + names:
        g = groups[name]
        tag = ctrl if name == ctrl else sn[name]
        rate = g["valid_user_rate"] * 100
        lines.append(
            f"| {tag} | {g['total_group_uv']/days:,.0f} | {g['total_valid_uv']/days:,.0f} | {rate:.3f}% |"
        )
    lines.append("")

    # --- VV 拆解 ---
    lines.append("### VV 结构拆解")
    lines.append("")
    lines.append("| 内容类型 | " + " | ".join(sn[n] for n in names) + " |")
    lines.append(sep)
    for key, label in VV_METRICS.items():
        if base.get(key, 0) == 0:
            continue
        row = f"| {label} |"
        for n in names:
            p = pct(exp[n].get(key, 0), base[key])
            row += f" {fmt(p)} |"
        lines.append(row)
    lines.append("")

    # --- 时长拆解 ---
    lines.append("### 时长结构拆解")
    lines.append("")
    lines.append("| 内容类型 | " + " | ".join(sn[n] for n in names) + " |")
    lines.append(sep)
    for key, label in DURATION_METRICS.items():
        if base.get(key, 0) == 0:
            continue
        row = f"| {label} |"
        for n in names:
            p = pct(exp[n].get(key, 0), base[key])
            row += f" {fmt(p)} |"
        lines.append(row)
    lines.append("")

    # --- 逐日趋势 ---
    if daily_data:
        lines.append("### 逐日信息流时长涨跌幅")
        lines.append("")
        lines.append("| 日期 | 涨跌幅 | 有效用户率涨跌幅 |")
        lines.append("|------|--------|----------------|")

        by_date: dict[str, dict] = {}
        for row in daily_data:
            d = str(row["date"])
            if d not in by_date:
                by_date[d] = {}
            by_date[d][row["tester_version_name"]] = row

        for d in sorted(by_date.keys()):
            day_groups = by_date[d]
            if ctrl not in day_groups:
                continue
            ctrl_dur = float(day_groups[ctrl].get("per_feed_dur", 0) or 0)
            ctrl_vur = float(day_groups[ctrl].get("valid_user_rate", 0) or 0)
            for n in names:
                if n in day_groups:
                    exp_dur = float(day_groups[n].get("per_feed_dur", 0) or 0)
                    exp_vur = float(day_groups[n].get("valid_user_rate", 0) or 0)
                    dur_chg = pct(exp_dur, ctrl_dur) if ctrl_dur else None
                    vur_chg = pct(exp_vur, ctrl_vur) if ctrl_vur else None
                    date_str = f"{d[4:6]}-{d[6:8]}"
                    lines.append(f"| {date_str} | {fmt(dur_chg)} | {fmt(vur_chg)} |")
        lines.append("")

    # --- 原始数据 ---
    lines.append("### 原始数据（加权人均）")
    lines.append("")
    lines.append("```")
    lines.append(f"{'组别':<12} {'日均UV':>10} {'消费时长':>10} {'信息流时长':>10} {'人均VV':>8} {'CTR':>8} {'有效率':>8} {'ARPU':>8}")
    for name in [ctrl] + names:
        g = groups[name]
        tag = "基准" if name == ctrl else sn[name]
        lines.append(
            f"{tag:<12} {g['total_uv']/days:>10,.0f} "
            f"{g['per_duration']:>10.2f} {g['per_feed_dur']:>10.2f} "
            f"{g['per_vv']:>8.2f} {g['ctr']:>8.4f} "
            f"{g['valid_user_rate']*100:>8.3f}% {g['arpu']:>8.4f}"
        )
    lines.append("```")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="火山ABtest实验分析")
    ap.add_argument("-m", "--media", required=True, help="浏览器/browser, 内容中心/newhome/nh/mcc")
    ap.add_argument("-e", "--exp-id", required=True, help="实验ID")
    ap.add_argument("-s", "--start-date", required=True, help="开始日期")
    ap.add_argument("-d", "--end-date", required=True, help="结束日期")
    args = ap.parse_args()

    media = MEDIA_ALIASES.get(args.media, args.media.lower())
    if media not in TABLES:
        print(f"Error: 未知媒体 '{args.media}'，可选: 浏览器/browser, 内容中心/newhome/nh/mcc", file=sys.stderr)
        sys.exit(1)

    start = parse_date(args.start_date)
    end = parse_date(args.end_date)
    datum = find_datum()
    table = TABLES[media]

    # Switch workspace
    subprocess.run(
        [datum, "config", "use", "数据研发"],
        capture_output=True, text=True,
    )

    # 1. Main aggregated query
    print(f"[1/3] 查询加权汇总... {media} | 实验{args.exp_id} | {start}~{end}", file=sys.stderr)
    sql = SQL_TEMPLATES[media].format(table=table, exp_id=args.exp_id, start=start, end=end)
    data = run_query(datum, sql)
    if not data:
        print("Error: 主查询失败", file=sys.stderr)
        sys.exit(1)

    groups = parse_results(data)
    if not groups:
        print("Error: 该实验无数据返回", file=sys.stderr)
        sys.exit(1)

    # 2. P-value query
    print("[2/3] 查询p值...", file=sys.stderr)
    pvalue_table = PVALUE_TABLES.get(media)
    pvalues = {}
    if pvalue_table:
        pv_sql = PVALUE_SQL.format(table=pvalue_table, exp_id=args.exp_id, start=start, end=end)
        pv_data = run_query(datum, pv_sql)
        if pv_data:
            pvalues = parse_pvalues(pv_data)

    # 3. Daily trend query
    print("[3/3] 查询逐日趋势...", file=sys.stderr)
    daily_sql = DAILY_SQL[media].format(table=table, exp_id=args.exp_id, start=start, end=end)
    daily_data_raw = run_query(datum, daily_sql)
    daily_data = parse_daily(daily_data_raw) if daily_data_raw else []

    ctrl = find_control(groups)
    report = generate_report(media, args.exp_id, start, end, groups, ctrl, pvalues, daily_data)
    print(report)


if __name__ == "__main__":
    main()
