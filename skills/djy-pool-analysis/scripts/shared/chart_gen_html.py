#!/usr/bin/env python3
"""生成 djy 日报图表 HTML（v9 版 · 含消费数据概览 + 内容池图表）

用法：
  python3 chart_gen_html.py <stock_csv> <daily_csv> <end_date_YYYYMMDD> <out_html> [consumption_json] [id_consistency_csv]

  consumption_json 可选，格式：
  {"cp_data": [...], "top5_vv": [...], "top5_dura": [...], "report_date": "2026-05-05"}

  id_consistency_csv 可选（2026-05-26 起）：来自 chart_id_consistency_trend.sql，
  列：snap_date, a_cp, multi_xm_authors_n, multi_cp_leads_n
  数据合并到 c3~c6 趋势图（在 FIELD_MAP 末尾两条曲线展示）

依赖：Chart.js + chartjs-plugin-datalabels（CDN）
"""
import csv
import datetime
import json
import os
import sys


CPS = ["guoying", "dihui", "beike", "meilaoban"]
CP_LONG = {
    "guoying": "cn-guoying-djy",
    "dihui": "cn-dihui-djy",
    "beike": "cn-beike-djy",
    "meilaoban": "cn-meilaoban-djy",
}
# 配色参考：产品序列 AI 转型启动会模版（暗蓝/绿/橙/紫）
CP_COLORS = {"guoying": "#3B82F6", "dihui": "#10B981", "beike": "#F97316", "meilaoban": "#A855F7"}
CP_COLORS_DARK = {"guoying": "#5AB4FF", "dihui": "#34C759", "beike": "#FF6B2B", "meilaoban": "#B98EFF"}

FIELD_MAP = [
    ("publish_time_n", "publish_time 空"),
    ("author_image_n", "author_image 空"),
    ("xm_author_id_n", "xm_author_id 空"),
    ("author_ip_n", "author_ip 空"),
    ("url_bad_n", "url 异常"),
    ("image_n", "image 空"),
    ("lead_author_id_n", "lead_author_id 空"),
    ("category_n", "category 空"),
    ("video_duration_bad_n", "video_duration ≤0"),
    ("video_detail_empty_n", "video_detail_list 整串空"),
    ("video_detail_incomplete_n", "video_detail 7 字段缺"),
    ("body_null_n", "body 空 (NEWS)"),
    ("word_cnt_null_n", "e_xm_body_word_cnt 空"),
    ("image_cnt_null_n", "e_xm_image_cnt 空"),
    # 三元 ID 一致性（来自 chart_id_consistency_trend.sql · 2026-05-26 起）
    ("multi_xm_authors_n", "cp_author 多 xm"),
    ("multi_cp_leads_n", "lead 多 cp_author"),
]

FIELD_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#59A14F", "#EDC948", "#76B7B2",
    "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC", "#86BCB6", "#D37295",
    "#FABFD2", "#A0CBE8", "#499894", "#D7B5A6",
]


def _consumption_card_html(data: dict) -> str:
    """消费数据概览：大盘 4 大卡 + 4 家 CP 指标小卡 + Top5 内容表 + 折叠详细表。"""
    CP_DISPLAY = {
        "cn-dihui-djy": "dihui", "cn-beike-djy": "beike",
        "cn-guoying-djy": "guoying", "cn-meilaoban-djy": "meilaoban",
    }

    def _tag(pct, size=""):
        """size: '' 默认 / 'dod' 日环比稍大 / 'wow' 周同比稍小"""
        size_cls = (" tag-" + size) if size else ""
        if pct is None or pct != pct:
            return f'<span class="tag tag-flat{size_cls}">-</span>'
        sign = "+" if pct >= 0 else ""
        txt = f"{sign}{pct:.1f}%"
        if pct >= 30:
            cls = "tag tag-up-strong"
        elif pct > 0.5:
            cls = "tag tag-up"
        elif pct <= -30:
            cls = "tag tag-down-strong"
        elif pct < -0.5:
            cls = "tag tag-down"
        else:
            cls = "tag tag-flat"
        return f'<span class="{cls}{size_cls}">{txt}</span>'

    def _fmt(val, dec=0):
        if val is None:
            return "-"
        return f"{int(val):,}" if dec == 0 else f"{val:,.{dec}f}"

    def _fmt_short(val):
        """大数字简写：1.23亿 / 1234.5万"""
        if val is None:
            return "-"
        av = abs(val)
        if av >= 1e8:
            return f"{val/1e8:.2f} 亿"
        if av >= 1e4:
            return f"{val/1e4:.1f} 万"
        return f"{int(val):,}"

    def _trunc(s, n=28):
        if not s:
            return "-"
        return s[:n] + "..." if len(s) > n else s

    cp_data = data.get("cp_data", [])

    # ---- 大盘 4 大卡（合计 × 环比反推）----
    def _reverse_yesterday(rows, val_key, pct_key):
        """按 pct 反推昨日合计 = Σ (今日值 / (1 + pct/100))"""
        yest = 0.0
        for r in rows:
            v = r.get(val_key)
            p = r.get(pct_key)
            if v is None or p is None or p != p:
                continue
            denom = 1 + p / 100.0
            if abs(denom) < 1e-9:
                continue
            yest += v / denom
        return yest

    def _total_pct(today_sum, yest_sum):
        if yest_sum <= 1e-9:
            return None
        return (today_sum - yest_sum) / yest_sum * 100

    total_vv = sum((r.get("vv") or 0) for r in cp_data)
    total_dura = sum((r.get("consum_dura_min") or 0) for r in cp_data)
    total_content = sum((r.get("distribute_content_cnt") or 0) for r in cp_data)
    active_cp = sum(1 for r in cp_data if (r.get("vv") or 0) > 0)

    yest_vv = _reverse_yesterday(cp_data, "vv", "vv_pct")
    yest_dura = _reverse_yesterday(cp_data, "consum_dura_min", "dura_pct")
    yest_content = _reverse_yesterday(cp_data, "distribute_content_cnt", "content_pct")

    total_vv_pct = _total_pct(total_vv, yest_vv)
    total_dura_pct = _total_pct(total_dura, yest_dura)
    total_content_pct = _total_pct(total_content, yest_content)

    # 周同比合计（用 cp_trend_7d 第 0 天数据，T-6 当天合计；周同比应该是 vs T-7 当天，
    # 但 cp_trend_7d 起点是 T-6。所以这里用 _reverse_yesterday 同样思路反推 T-7 合计）
    week_vv = _reverse_yesterday(cp_data, "vv", "vv_wow_pct")
    week_dura = _reverse_yesterday(cp_data, "consum_dura_min", "dura_wow_pct")
    week_content = _reverse_yesterday(cp_data, "distribute_content_cnt", "content_wow_pct")
    total_vv_wow = _total_pct(total_vv, week_vv)
    total_dura_wow = _total_pct(total_dura, week_dura)
    total_content_wow = _total_pct(total_content, week_content)

    def _big_card(label, value_html, dod_pct, wow_pct, hint):
        dod_html = _tag(dod_pct, "dod") if dod_pct is not None else ""
        wow_html = _tag(wow_pct, "wow") if wow_pct is not None else ""
        tags = (
            f'<span class="tag-row" style="display:block;margin-top:6px">'
            f'<span style="color:#64748b;font-size:11px">日环比</span> {dod_html} '
            f'<span style="color:#94a3b8;font-size:11px;margin-left:10px">周同比</span> {wow_html}'
            f'</span>'
        )
        return (
            '<div class="health-card">'
            f'<div class="label">{label}</div>'
            f'<div class="big">{value_html}</div>'
            f'{tags}'
            f'<div class="hint">{hint}</div>'
            '</div>'
        )

    active_cls = "health-ok" if active_cp == 4 else ("health-warn" if active_cp >= 2 else "health-bad")
    active_color = "green" if active_cp == 4 else ("amber" if active_cp >= 2 else "red")
    overview_cards = (
        '<div class="health-overview" style="margin-bottom:16px">'
        + _big_card("大盘消费 VV", _fmt_short(total_vv), total_vv_pct, total_vv_wow, "4 家 CP 合计 · 环比 / 周同比")
        + _big_card("大盘消费时长", _fmt_short(total_dura) + " 分钟", total_dura_pct, total_dura_wow, "4 家 CP 合计 · 环比 / 周同比")
        + _big_card("大盘分发内容量", _fmt_short(total_content), total_content_pct, total_content_wow, "4 家 CP 合计 · 环比 / 周同比")
        + f'<div class="health-card {active_cls}"><div class="label">活跃 CP 数</div>'
        + f'<div class="big {active_color}">{active_cp}/4</div>'
        + f'<div class="hint">消费 VV &gt; 0 的家数</div></div>'
        + '</div>'
    )

    # ---- 4 家 CP 指标小卡 ----
    # cols 元组：(显示名, 值字段, 环比字段, 周同比字段, 小数位)
    cols = [
        ("消费VV", "vv", "vv_pct", "vv_wow_pct", 0),
        ("消费时长(分钟)", "consum_dura_min", "dura_pct", "dura_wow_pct", 1),
        ("分发内容量", "distribute_content_cnt", "content_pct", "content_wow_pct", 0),
        ("分发作者量", "distribute_author_cnt", "author_pct", "author_wow_pct", 0),
        ("篇均VV", "vv_per_item", "vv_item_pct", "vv_item_wow_pct", 1),
        ("单VV消费时长(秒)", "dura_per_vv_sec", "dura_vv_pct", "dura_vv_wow_pct", 1),
    ]
    key_cols = cols[:3]

    cp_cards = ""
    for row in cp_data:
        cp_label = CP_DISPLAY.get(row["cp"], row["cp"])
        color = CP_COLORS.get(cp_label, "#94a3b8")
        kvs = ""
        for name, vk, dod_k, wow_k, dec in key_cols:
            # 左右布局：左侧 label+数字，右侧 环/周 tag 竖排
            kvs += (
                f'<div class="kv2">'
                f'<div class="kv2-left">'
                f'<div class="k">{name}</div>'
                f'<div class="num">{_fmt(row.get(vk), dec)}</div>'
                f'</div>'
                f'<div class="kv2-right">'
                f'<div class="dod-wow"><span class="lbl">日环比</span>{_tag(row.get(dod_k), "dod")}</div>'
                f'<div class="dod-wow"><span class="lbl">周同比</span>{_tag(row.get(wow_k), "wow")}</div>'
                f'</div>'
                f'</div>'
            )
        cp_cards += (
            f'<div class="cp-card">'
            f'<div class="cp-bar" style="background:{color}"></div>'
            f'<div class="cp-body">'
            f'<div class="name"><span><span class="dot" style="background:{color}"></span>{cp_label}</span></div>'
            f'{kvs}'
            f'</div></div>'
        )

    # ---- Top5 榜单（标题可点击跳转内容播放）----
    def _top5_list(items, val_key, val_unit, dec):
        if not items:
            return '<p style="color:#94a3b8;font-size:12px;text-align:center;padding:24px">暂无数据</p>'
        lis = ""
        for i, it in enumerate(items, 1):
            title = it.get("item_title") or "(无标题)"
            iid = it.get("item_id") or ""
            cp = CP_DISPLAY.get(it.get("item_cp_name", ""), it.get("item_cp_name", ""))
            itype = it.get("item_type") or ""
            val = _fmt(it.get(val_key), dec)
            url = (it.get("url") or "").strip()
            rank_cls = f"rank rank-{i}" if i <= 3 else "rank"
            title_html = (
                f'<a href="{url}" target="_blank" rel="noopener">{title}</a>'
                if url else title
            )
            meta = f"{cp} · {itype}" if itype else cp
            lis += (
                '<li>'
                f'<span class="{rank_cls}">{i}</span>'
                '<span class="title-wrap">'
                f'<span class="title">{title_html}</span>'
                f'<span class="meta">{meta}</span>'
                f'<span class="iid" title="长按/双击可选中复制">{iid}</span>'
                '</span>'
                f'<span class="val">{val}<span class="unit">{val_unit}</span></span>'
                '</li>'
            )
        return f'<ul class="top5-list">{lis}</ul>'

    top5_vv = data.get("top5_vv", [])
    top5_dura = data.get("top5_dura", [])
    top5_html = (
        '<div class="grid2" style="margin-top:16px">'
        '<div class="top5-card">'
        '<h3 style="color:#059669">🔥 Top5 消费 VV</h3>'
        '<div class="hint">当日 VV 最高的 5 条内容 · 点击标题跳转原内容</div>'
        f'{_top5_list(top5_vv, "vv", "次", 0)}'
        '</div>'
        '<div class="top5-card">'
        '<h3 style="color:#0284c7">⏱ Top5 消费时长</h3>'
        '<div class="hint">当日消费时长最高的 5 条内容 · 点击标题跳转原内容</div>'
        f'{_top5_list(top5_dura, "consum_dura_min", "分钟", 1)}'
        '</div>'
        '</div>'
    )

    # ---- 折叠详细表（紧凑双行：数字 + 一行 日/周 横排 tag）----
    rows_html = ""
    for row in cp_data:
        cp_label = CP_DISPLAY.get(row["cp"], row["cp"])
        cells = f'<td style="font-weight:600;text-align:left;padding:6px 8px;font-size:12px">{cp_label}</td>'
        for _, vk, dod_k, wow_k, dec in cols:
            cells += (
                f'<td class="metric-cell">'
                f'<div class="metric-val">{_fmt(row.get(vk), dec)}</div>'
                f'<div class="metric-tags-row">'
                f'<span><span class="lbl">日环比</span>{_tag(row.get(dod_k), "dod")}</span>'
                f'<span><span class="lbl">周同比</span>{_tag(row.get(wow_k), "wow")}</span>'
                f'</div></td>'
            )
        rows_html += f"<tr>{cells}</tr>"

    headers = "".join(
        f'<th style="padding:10px 10px;text-align:center;font-weight:600;color:#475569;'
        f'border-bottom:2px solid #cbd5e1;white-space:nowrap;font-size:12px">{c[0]}</th>'
        for c in [("CP",)] + [(x[0],) for x in cols]
    )

    report_date = data.get("report_date", "")
    # ---- 30 天趋势图：1 张 canvas + 5 个 metric tab 切换（数据由 __CONSUM_TREND__ 注入）----
    has_trend = bool(data.get("cp_trend_30d", {}).get("cp"))
    trend_section = ""
    if has_trend:
        trend_section = '''
<div class="card" style="grid-column:1/-1;margin-top:16px">
<h3>📈 4 家 CP 消费 30 天趋势</h3>
<div class="hint">T-29 ~ T 共 30 天 · 全量入库口径 · 切换上方 Tab 查看不同指标</div>
<div id="cc_tabs" style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0">
<button class="cc-tab active" data-metric="vv">消费 VV</button>
<button class="cc-tab" data-metric="consum_dura_min">消费时长（分钟）</button>
<button class="cc-tab" data-metric="distribute_content_cnt">分发内容量</button>
<button class="cc-tab" data-metric="vv_per_item">篇均 VV</button>
<button class="cc-tab" data-metric="dura_per_vv_sec">单 VV 时长（秒）</button>
</div>
<div style="height:380px;position:relative"><canvas id="cc_main"></canvas></div>
</div>'''
    return f'''{overview_cards}
<div class="card" style="grid-column:1/-1">
<h3>📊 4 家 CP 核心指标拆解</h3>
<div class="hint">数据日期：{report_date} · 环比 vs 前一日 · 周同比 vs 上周同一日 · 关键指标前 3 列</div>
<div class="cp-grid">{cp_cards}</div>
<details open><summary>📋 查看全部 6 列指标（含篇均 VV / 单 VV 时长）</summary>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="background:#f8fafc">{headers}</tr>
{rows_html}
</table>
</details>
</div>
{trend_section}
{top5_html}'''


def _health_overview_html(stock_bad: dict, ingest: dict, per_cp: dict) -> str:
    """健康度总览 4 张大数字卡：
    1) 今日异常字段总条数（= 4 家最新 bad_any 之和）
    2) 7 天内异常变化（= 今日 bad_any 之和 - 7 天前 bad_any 之和）
    3) 告警级别（按最严重单字段阈值 ≥1000/≥100/≥1/=0 → 🚨/⚠️/🟡/✅）
    4) CP 推送状态（近 7 天总入库>0 的家数 / 4）
    """
    total_now = sum(v[-1] for v in stock_bad.values())
    total_7d_ago = sum(v[0] for v in stock_bad.values())
    delta_7d = total_now - total_7d_ago

    # 告警级别：扫全部 CP 的全部字段当前值，取最大
    max_single = 0
    for cp in per_cp:
        for _, series in per_cp[cp].items():
            if series and series[-1] > max_single:
                max_single = series[-1]
    if max_single >= 1000:
        alert_emoji, alert_txt, alert_cls = "🚨", "紧急", "health-crit"
        big_cls, big_hint = "purple", "≥1000 条 · 🚨 紧急"
    elif max_single >= 100:
        alert_emoji, alert_txt, alert_cls = "⚠️", "高", "health-bad"
        big_cls, big_hint = "red", "100-999 条 · ⚠️ 高"
    elif max_single >= 1:
        alert_emoji, alert_txt, alert_cls = "🟡", "低", "health-warn"
        big_cls, big_hint = "amber", "1-99 条 · 🟡 低"
    else:
        alert_emoji, alert_txt, alert_cls = "✅", "正常", "health-ok"
        big_cls, big_hint = "green", "全字段 0 异常"

    # CP 推送状态：近 7 天总入库 > 0 的家数
    pushing = sum(1 for v in ingest.values() if sum(v) > 0)
    if pushing == 4:
        push_cls, push_big_cls = "health-ok", "green"
        push_hint = "4/4 家 CP 正常推送"
    elif pushing >= 2:
        push_cls, push_big_cls = "health-warn", "amber"
        push_hint = f"{4 - pushing} 家停推（近 7 天 0 入库）"
    else:
        push_cls, push_big_cls = "health-bad", "red"
        push_hint = f"{4 - pushing} 家停推（近 7 天 0 入库）"

    if delta_7d > 0:
        delta_cls, delta_big_cls = "health-warn", "amber"
        delta_hint = f"7 天新增 +{delta_7d:,} 条"
        delta_val = f"+{delta_7d:,}"
    elif delta_7d < 0:
        delta_cls, delta_big_cls = "health-ok", "green"
        delta_hint = f"7 天净消化 {delta_7d:,} 条"
        delta_val = f"{delta_7d:,}"
    else:
        delta_cls, delta_big_cls = "health-ok", "green"
        delta_hint = "7 天存量持平"
        delta_val = "0"

    total_cls = "health-ok" if total_now == 0 else ("health-warn" if total_now < 10000 else "health-bad")
    total_big_cls = "green" if total_now == 0 else ("amber" if total_now < 10000 else "red")

    return (
        '<div class="section">'
        '<div class="section-title">🏥 内容池健康度总览'
        '<span class="desc">字段质量与 CP 推送状态快照</span></div>'
        '<div class="health-overview">'
        f'<div class="health-card {total_cls}"><div class="label">当前异常字段总条数</div>'
        f'<div class="big {total_big_cls}">{total_now:,}</div>'
        f'<div class="hint">4 家 CP 在线池存量合计（已排豁免）</div></div>'
        f'<div class="health-card {delta_cls}"><div class="label">近 7 天存量变化</div>'
        f'<div class="big {delta_big_cls}">{delta_val}</div>'
        f'<div class="hint">{delta_hint}</div></div>'
        f'<div class="health-card {alert_cls}"><div class="label">告警级别</div>'
        f'<div class="big {big_cls}">{alert_emoji} {alert_txt}</div>'
        f'<div class="hint">最严重单字段 {max_single:,} 条 · {big_hint}</div></div>'
        f'<div class="health-card {push_cls}"><div class="label">CP 推送状态</div>'
        f'<div class="big {push_big_cls}">{pushing}/4</div>'
        f'<div class="hint">{push_hint}</div></div>'
        '</div></div>'
    )


def _biz_cards_html(actions: list) -> str:
    """业务建议卡（可选）。actions = [{"priority": "high|mid|low", "title": "...", "body": "..."}]
    当前默认不调用（Claude prompt 里未产出这类内容），保留 API 供未来扩展。
    """
    if not actions:
        return ""
    tag_map = {"high": "高优", "mid": "中优", "low": "低优"}
    parts = [
        '<div class="section"><div class="section-title">💡 业务建议 & 下步动作'
        '<span class="desc">按优先级排序</span></div>'
    ]
    for a in actions:
        pr = a.get("priority", "mid")
        tag = tag_map.get(pr, "中优")
        parts.append(
            f'<div class="biz-card prio-{pr}"><span class="prio-tag">{tag}</span>'
            f'<h4>{a.get("title", "")}</h4>'
            f'<div class="body">{a.get("body", "")}</div></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def _footer_html(end_label: str) -> str:
    """页脚三行口径说明"""
    return (
        '<div class="footer">'
        '<div class="row">'
        '<span>📅 生成时间 <code>' + end_label + '</code></span>'
        '<span>🗂 数据源 <code>paimon_zjyprc_hadoop.browser.business_content_pool_realtime</code></span>'
        '</div>'
        '<div class="row">'
        '<span>🛡 豁免源 <code>exemptions.json</code> 自动注入（28 条 item 级 + beike author_ip CP 级）</span>'
        '</div>'
        '<div class="row">'
        '<span>📤 推送 GitLab Pages 发布 HTML + 飞书群机器人推送卡片</span>'
        '<span>📐 告警阈值 ≥1000 🚨 / 100-999 ⚠️ / 1-99 🟡 / 0 ✅</span>'
        '</div>'
        '</div>'
    )


def build(stock_csv: str, daily_csv: str, end_ymd: str, out_html: str, consumption_json: str = None, biz_actions: list = None, id_consistency_csv: str = None):
    end_dt = datetime.datetime.strptime(end_ymd, "%Y%m%d")
    cutoffs = [(end_dt - datetime.timedelta(days=6 - i)).strftime("%Y%m%d") for i in range(7)]
    dates_label = [(end_dt - datetime.timedelta(days=6 - i)).strftime("%m-%d") for i in range(7)]

    # daily: {cp: {"YYYY-MM-DD": total}}
    daily = {cp: {} for cp in CPS}
    for r in csv.DictReader(open(daily_csv)):
        cp_short = {v: k for k, v in CP_LONG.items()}[r["a_cp"]]
        daily[cp_short][r["create_date"]] = int(r["total"])
    # INGEST 对齐 dates_label
    ingest = {
        cp: [
            daily[cp].get((end_dt - datetime.timedelta(days=6 - i)).strftime("%Y-%m-%d"), 0)
            for i in range(7)
        ]
        for cp in CPS
    }

    # stock: {cp: {cutoff: row}}
    stock = {cp: {} for cp in CPS}
    for r in csv.DictReader(open(stock_csv)):
        cp_short = {v: k for k, v in CP_LONG.items()}[r["a_cp"]]
        stock[cp_short][r["snap_date"]] = r

    # id_consistency: 合并到 stock dict 同一 (cp, cutoff) 行（chart_id_consistency_trend.sql 输出）
    # 列：multi_xm_authors_n, multi_cp_leads_n —— 与 chart_stock_trend 共享 snap_date 维度
    if id_consistency_csv:
        for r in csv.DictReader(open(id_consistency_csv)):
            cp_short = {v: k for k, v in CP_LONG.items()}[r["a_cp"]]
            row = stock[cp_short].get(r["snap_date"])
            if row is None:
                # 用 dict 兜住 cutoff 缺失场景，per_cp 取值会自动 fallback 到 0
                row = {"snap_date": r["snap_date"], "a_cp": r["a_cp"]}
                stock[cp_short][r["snap_date"]] = row
            row["multi_xm_authors_n"] = r["multi_xm_authors_n"]
            row["multi_cp_leads_n"] = r["multi_cp_leads_n"]

    # 缺失 cutoff 兜底为 0（如 meilaoban 5/18 起算豁免，5/18 之前无数据）
    stock_bad = {cp: [int(stock[cp][c]["bad_any"]) if c in stock[cp] else 0 for c in cutoffs] for cp in CPS}
    per_cp = {
        cp: {label: [int(stock[cp][c].get(col, 0) or 0) if c in stock[cp] else 0 for c in cutoffs] for col, label in FIELD_MAP}
        for cp in CPS
    }

    html = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>djy 日报图表 · __END__</title>
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Hiragino Sans GB","Microsoft YaHei",Arial,sans-serif;background:linear-gradient(135deg,#eff6ff 0%,#ecfdf5 100%);min-height:100vh;padding:36px 20px;color:#1e293b;-webkit-font-smoothing:antialiased}
.container{max-width:1440px;margin:0 auto}
.header{background:linear-gradient(135deg,#3b82f6,#10b981);color:#fff;border-radius:20px;padding:32px 38px;margin-bottom:28px;box-shadow:0 8px 24px rgba(59,130,246,0.18)}
.header h1{font-size:28px;font-weight:800;margin-bottom:6px;letter-spacing:-0.5px}
.header .sub{font-size:14px;opacity:0.92}
.header .meta{margin-top:12px;font-size:12px;opacity:0.9;background:rgba(255,255,255,0.18);padding:7px 14px;border-radius:100px;display:inline-block}
[data-theme="dark"] .header{background:linear-gradient(135deg,rgba(59,130,246,0.4),rgba(139,92,246,0.4));border:1px solid rgba(255,255,255,0.12);box-shadow:0 12px 40px rgba(59,130,246,0.18)}
.section{margin-bottom:28px}
.section-title{font-size:18px;font-weight:700;color:#1e293b;margin-bottom:16px;display:flex;align-items:center;gap:10px}
.section-title::before{content:'';width:4px;height:22px;background:linear-gradient(180deg,#3b82f6,#10b981);border-radius:2px}
.section-title .desc{font-size:12px;color:#64748b;font-weight:400;margin-left:auto}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#fff;border-radius:18px;padding:22px;box-shadow:0 4px 12px rgba(15,23,42,0.05)}
.card h3{margin:0 0 4px 0;font-size:13px;color:#334155;font-weight:700}
.card .hint{font-size:11px;color:#94a3b8;margin-bottom:10px}
canvas{max-height:300px}
.insight{background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:14px;padding:14px 20px;margin-top:14px;font-size:13px;color:#78350f;line-height:1.7;border:1px solid rgba(217,119,6,0.15)}
.insight strong{color:#92400e}
[data-theme="dark"] .insight{background:linear-gradient(135deg,rgba(245,158,11,0.10),rgba(217,119,6,0.08));color:rgba(254,215,170,0.95);border-color:rgba(245,158,11,0.25)}
[data-theme="dark"] .insight strong{color:#fcd34d}
.footer{font-size:12px;color:#94a3b8;padding:22px 4px 8px;border-top:1px dashed #cbd5e1;margin-top:24px;line-height:1.9}
.footer .row{display:flex;flex-wrap:wrap;gap:6px 18px;justify-content:center}
.footer code{background:#f1f5f9;padding:1px 6px;border-radius:4px;font-size:11px;color:#475569}
/* 健康度总览 */
.health-overview{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:28px}
.health-card{background:#fff;border-radius:18px;padding:22px 24px;box-shadow:0 4px 12px rgba(15,23,42,0.05);border-top:3px solid #3b82f6;position:relative}
.health-card .label{font-size:11px;color:#64748b;margin-bottom:10px;font-weight:600;letter-spacing:0.4px;text-transform:uppercase}
.health-card .big{font-size:36px;font-weight:900;color:#1e293b;line-height:1;letter-spacing:-1.5px;font-variant-numeric:tabular-nums}
.health-card .tag-row{display:flex;gap:8px;margin-top:8px;font-size:11px}
.health-card .hint{font-size:11px;color:#94a3b8;margin-top:8px}
.health-card.health-ok{border-top-color:#10b981}
.health-card.health-warn{border-top-color:#f59e0b}
.health-card.health-bad{border-top-color:#dc2626}
.health-card.health-crit{border-top-color:#7c3aed}
.health-card .big.green{color:#059669}.health-card .big.red{color:#dc2626}.health-card .big.amber{color:#d97706}.health-card .big.purple{color:#7c3aed}
/* CP 指标小卡 */
.cp-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:16px}
.cp-card{background:#fff;border-radius:14px;padding:0;border:1px solid #e2e8f0;overflow:hidden;position:relative}
.cp-card .cp-bar{height:4px;width:100%}
.cp-card .cp-body{padding:14px 18px 16px 18px}
.cp-card .name{font-size:14px;color:#1e293b;font-weight:700;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between}
.cp-card .name .dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:8px;vertical-align:middle}
.cp-card .kv{display:flex;justify-content:space-between;align-items:baseline;margin:8px 0;font-size:12px}
.cp-card .kv .k{color:#64748b}
.cp-card .kv .v{font-weight:700;color:#1e293b;font-size:14px}
.cp-card .kv .v .num{font-size:15px;letter-spacing:-0.2px}
.cp-card .kv .v .tag{margin-left:6px;font-size:10px}
/* Top5 榜单 */
.top5-card{background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(15,23,42,0.04)}
.top5-card h3{margin:0 0 4px 0;font-size:14px;font-weight:700}
.top5-card .hint{font-size:11px;color:#94a3b8;margin-bottom:12px}
.top5-list{list-style:none;margin:0;padding:0}
.top5-list li{display:flex;align-items:center;gap:10px;padding:10px 8px;border-bottom:1px solid #f1f5f9;transition:background 0.15s}
.top5-list li:last-child{border-bottom:none}
.top5-list li:hover{background:#f8fafc}
.top5-list .rank{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0;background:#94a3b8}
.top5-list .rank-1{background:linear-gradient(135deg,#fbbf24,#f59e0b)}
.top5-list .rank-2{background:linear-gradient(135deg,#cbd5e1,#94a3b8)}
.top5-list .rank-3{background:linear-gradient(135deg,#f97316,#ea580c)}
.top5-list .title-wrap{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.top5-list .title{font-size:13px;color:#1e293b;font-weight:500;line-height:1.4;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;word-break:break-word}
.top5-list .title a{color:#1e293b;text-decoration:none}
.top5-list .title a:hover{color:#3b82f6;text-decoration:underline}
.top5-list .meta{font-size:10px;color:#94a3b8}
.top5-list .iid{font-family:ui-monospace,"SF Mono","Menlo",monospace;font-size:10px;color:#cbd5e1;word-break:break-all;line-height:1.3;user-select:all;cursor:text}
.top5-list .iid:hover{color:#64748b}
.top5-list .val{font-size:14px;font-weight:700;color:#1e293b;flex-shrink:0;white-space:nowrap;text-align:right;min-width:70px}
.top5-list .val .unit{font-size:10px;font-weight:500;color:#94a3b8;margin-left:2px}
/* 涨跌 tag · 仅字体颜色（无背景）· 日环比 > 周同比 字号 */
.tag{padding:0 2px;font-size:11px;font-weight:700;white-space:nowrap;display:inline-block;font-variant-numeric:tabular-nums}
.tag.tag-dod{font-size:13px}
.tag.tag-wow{font-size:11px;font-weight:600}
.tag-up{color:#059669}
.tag-down{color:#dc2626}
.tag-flat{color:#64748b}
.tag-up-strong{color:#047857}
.tag-down-strong{color:#991b1b}
/* 业务建议卡 */
.biz-card{background:#fff;border-radius:14px;padding:18px 22px;margin-bottom:14px;border-left:4px solid #3b82f6;box-shadow:0 2px 8px rgba(15,23,42,0.04)}
.biz-card.prio-high{border-left-color:#dc2626}
.biz-card.prio-mid{border-left-color:#f59e0b}
.biz-card.prio-low{border-left-color:#3b82f6}
.biz-card h4{font-size:15px;color:#1e293b;margin-bottom:6px;font-weight:600}
.biz-card .body{font-size:13px;color:#475569;line-height:1.8}
.biz-card .prio-tag{float:right;font-size:11px;padding:2px 10px;border-radius:4px;font-weight:600}
.biz-card.prio-high .prio-tag{background:#fee2e2;color:#991b1b}
.biz-card.prio-mid .prio-tag{background:#fef3c7;color:#92400e}
.biz-card.prio-low .prio-tag{background:#dbeafe;color:#1e40af}
/* 折叠详细表 */
details{background:#fff;border-radius:12px;padding:6px 18px;margin-top:10px;box-shadow:0 2px 6px rgba(15,23,42,0.04)}
details summary{cursor:pointer;font-size:13px;color:#475569;padding:8px 0;font-weight:500;list-style:none}
details summary::before{content:'▸ ';color:#94a3b8}
details[open] summary::before{content:'▾ '}
details table{margin:8px 0 12px 0}
/* 消费 30 天趋势 metric 切换 tab */
.cc-tab{padding:6px 14px;border:1px solid #cbd5e1;background:#fff;color:#475569;border-radius:6px;font-size:12px;cursor:pointer;transition:all 0.15s}
.cc-tab:hover{background:#f1f5f9;border-color:#94a3b8}
.cc-tab.active{background:#1e40af;color:#fff;border-color:#1e40af;font-weight:600}
/* === 暗黑主题 overrides（按 [data-theme="dark"] 切换）=== */
/* 配色完全对齐 产品序列 AI 转型启动会 模版 */
[data-theme="dark"] body{background:#0d1117;background-image:radial-gradient(ellipse 90% 70% at 50% 0%,rgba(20,40,100,0.85) 0%,transparent 60%),radial-gradient(ellipse 60% 60% at 100% 100%,rgba(40,10,80,0.5) 0%,transparent 50%),radial-gradient(ellipse 50% 50% at 0% 100%,rgba(10,30,70,0.45) 0%,transparent 50%),linear-gradient(160deg,#0e1628 0%,#0d1117 40%,#10091e 100%);background-attachment:fixed;color:#fff}
[data-theme="dark"] .card,[data-theme="dark"] .health-card,[data-theme="dark"] .cp-card,[data-theme="dark"] .top5-card,[data-theme="dark"] .biz-card,[data-theme="dark"] details{background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.12);box-shadow:none;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px)}
[data-theme="dark"] .card h3,[data-theme="dark"] .top5-card h3{color:rgba(255,255,255,0.92)}
[data-theme="dark"] .card .hint,[data-theme="dark"] .footer,[data-theme="dark"] .top5-card .hint,[data-theme="dark"] .top5-list .meta,[data-theme="dark"] .health-card .label,[data-theme="dark"] .health-card .hint{color:rgba(255,255,255,0.5)}
[data-theme="dark"] .health-card .big{color:rgba(255,255,255,0.95)}
[data-theme="dark"] .section-title{color:rgba(255,255,255,0.92)}
[data-theme="dark"] .section-title .desc{color:rgba(255,255,255,0.5)}
[data-theme="dark"] .cp-card{background:rgba(255,255,255,0.04)}
[data-theme="dark"] .cp-card .name{color:rgba(255,255,255,0.92);border-bottom-color:rgba(255,255,255,0.08)}
[data-theme="dark"] .cp-card .kv2{border-bottom-color:rgba(255,255,255,0.08)}
[data-theme="dark"] .cp-card .kv2-left .k,[data-theme="dark"] .dod-wow .lbl,[data-theme="dark"] .metric-row .lbl,[data-theme="dark"] .metric-tags-row .lbl{color:rgba(255,255,255,0.7)}
[data-theme="dark"] .cp-card .kv2-left .num,[data-theme="dark"] .metric-val{color:#fff}
[data-theme="dark"] .card .hint,[data-theme="dark"] .top5-card .hint,[data-theme="dark"] .health-card .label,[data-theme="dark"] .health-card .hint,[data-theme="dark"] .top5-list .meta{color:rgba(255,255,255,0.62)}
[data-theme="dark"] .footer{color:rgba(255,255,255,0.55)}
[data-theme="dark"] .tag-flat{color:rgba(255,255,255,0.6)}
[data-theme="dark"] .top5-list li{border-bottom-color:rgba(255,255,255,0.06)}
[data-theme="dark"] .top5-list .title,[data-theme="dark"] .top5-list .title a,[data-theme="dark"] .top5-list .val{color:rgba(255,255,255,0.92)}
[data-theme="dark"] .top5-list li:hover{background:rgba(255,255,255,0.04)}
[data-theme="dark"] .top5-list .iid{color:rgba(255,255,255,0.25)}
[data-theme="dark"] details summary{color:rgba(255,255,255,0.7)}
[data-theme="dark"] .insight{background:rgba(245,158,11,0.12);color:rgba(255,255,255,0.85)}
[data-theme="dark"] .footer code{background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.7)}
[data-theme="dark"] .footer{border-top-color:rgba(255,255,255,0.08)}
[data-theme="dark"] table tr{background:transparent !important}
[data-theme="dark"] table th{color:rgba(255,255,255,0.7) !important;border-bottom-color:rgba(255,255,255,0.15) !important}
[data-theme="dark"] .metric-cell{border-bottom-color:rgba(255,255,255,0.06)}
[data-theme="dark"] .cc-tab{background:rgba(255,255,255,0.04);border-color:rgba(255,255,255,0.12);color:rgba(255,255,255,0.7)}
[data-theme="dark"] .cc-tab:hover{background:rgba(255,255,255,0.08);border-color:rgba(255,255,255,0.25)}
[data-theme="dark"] .cc-tab.active{background:#3b82f6;color:#fff;border-color:#3b82f6}
/* 涨跌 tag 暗黑色（仅字体）*/
[data-theme="dark"] .tag-up{color:#5dd884}
[data-theme="dark"] .tag-down{color:#ff7b72}
[data-theme="dark"] .tag-flat{color:rgba(255,255,255,0.5)}
[data-theme="dark"] .tag-up-strong{color:#34c759}
[data-theme="dark"] .tag-down-strong{color:#ff453a}
/* === 主题切换按钮 === */
.theme-toggle{position:fixed;top:20px;right:20px;z-index:9999;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.25);color:#fff;width:42px;height:42px;border-radius:50%;cursor:pointer;font-size:18px;backdrop-filter:blur(10px);transition:all 0.2s;display:flex;align-items:center;justify-content:center}
.theme-toggle:hover{background:rgba(255,255,255,0.25);transform:scale(1.05)}
[data-theme="dark"] .theme-toggle{background:rgba(255,255,255,0.08);border-color:rgba(255,255,255,0.18)}
/* CP 小卡左右布局：左 label+数字，右 环/周 tag 竖排 */
.kv2{display:flex;align-items:center;justify-content:space-between;margin:10px 0;padding-bottom:8px;border-bottom:1px dashed #e2e8f0;gap:12px}
.kv2:last-child{border-bottom:none}
.kv2-left{flex:1;min-width:0}
.kv2-left .k{font-size:11px;color:#475569;margin-bottom:2px;font-weight:500}
.kv2-left .num{font-size:16px;font-weight:700;color:#0f172a;font-variant-numeric:tabular-nums}
.kv2-right{display:flex;flex-direction:column;align-items:flex-end;gap:4px;font-size:11px}
.dod-wow{display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.dod-wow .lbl{color:#64748b;font-size:10px;font-weight:500}
/* 详细表 cell：数字 + 日环比/周同比 竖排 */
.metric-cell{text-align:center;padding:8px 8px;line-height:1.4;border-bottom:1px solid #f1f5f9}
.metric-val{font-size:14px;font-weight:700;color:#1e293b;margin-bottom:3px;font-variant-numeric:tabular-nums}
.metric-tags-row{display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px;line-height:1.4}
.metric-tags-row .lbl{color:#64748b;font-size:10px;margin-right:3px;font-weight:500}
</style></head><body>
<button class="theme-toggle" onclick="toggleTheme()" title="切换主题" id="themeBtn">🌙</button>
<div class="container">
<div class="header">
<h1>📊 djy 内容池日报</h1>
<div class="sub">数据截至 __END__ · 4 家 CP 字段质量巡检 + 消费核心指标</div>
<div class="meta">口径：business_content_pool_realtime · 在线池存量（c2~c6）+ 全量入库量（c1）· item 豁免自动注入</div>
</div>
__CONSUMPTION_SECTION__
__HEALTH_OVERVIEW__
<div class="section"><div class="section-title">📌 区域 A · 整体对比<span class="desc">每日入库量 & 异常存量趋势</span></div>
<div class="grid2">
<div class="card"><h3>① 4 家 CP 每日入库内容数（增量 · 全量含下线）</h3><div class="hint">看 CP 当日推送节奏</div><canvas id="c1"></canvas></div>
<div class="card"><h3>② 4 家 CP 在线池异常存量趋势（截止 N 日）</h3><div class="hint">含全部规则 · 已排豁免 + beike author_ip</div><canvas id="c2"></canvas></div>
</div>
<div class="insight"><strong>📌 观察要点：</strong>入库量应相对稳定，单日环比下跌 &gt;50% 需跟进停推告警；异常存量曲线理想状态近乎持平，出现陡升通常意味着新批次字段映射异常或上游规则变更。</div>
</div>
<div class="section"><div class="section-title">🎛 区域 B · 每家 CP 在线池字段存量趋势<span class="desc">16 个字段维度（含三元 ID 一致性）· 全 0 字段自动折叠</span></div>
<div class="grid2">
<div class="card"><h3>③ guoying 在线池字段趋势</h3><div class="hint">7 天全 0 的字段默认隐藏</div><canvas id="c3"></canvas></div>
<div class="card"><h3>④ dihui 在线池字段趋势</h3><div class="hint">7 天全 0 的字段默认隐藏</div><canvas id="c4"></canvas></div>
<div class="card"><h3>⑤ beike 在线池字段趋势</h3><div class="hint">7 天全 0 的字段默认隐藏</div><canvas id="c5"></canvas></div>
<div class="card"><h3>⑥ meilaoban 在线池字段趋势</h3><div class="hint">7 天全 0 的字段默认隐藏</div><canvas id="c6"></canvas></div>
</div>
<div class="insight"><strong>🎛 观察要点：</strong>每家 CP 按字段维度拆解 7 天走势，重点关注<strong>陡升或持续高位</strong>字段——前者是突发故障信号，后者是长期未修复的积压问题。</div>
</div>
__BIZ_CARDS__
__FOOTER__
</div>
<script>
// 主题切换：从 localStorage 读取，默认浅色
// playwright headless set_content 注入的页面 origin 是 about:blank，访问 localStorage
// 会抛 SecurityError；try/catch 包裹避免整个 <script> 中止导致 Chart 全部不渲染。
function getTheme(){try{return localStorage.getItem("djy_theme")||"light"}catch(e){return "light"}}
function setStoredTheme(v){try{localStorage.setItem("djy_theme",v)}catch(e){}}
function applyTheme(t){
  const isDark=(t==="dark");
  const tick=isDark?"rgba(255,255,255,0.85)":"#334155";
  const axisTitle=isDark?"rgba(255,255,255,0.92)":"#1e293b";
  const grid=isDark?"rgba(255,255,255,0.10)":"rgba(0,0,0,0.06)";
  if(isDark){
    document.documentElement.setAttribute("data-theme","dark");
    document.body.setAttribute("data-theme","dark");
    document.getElementById("themeBtn").textContent="☀️";
    colors=colorsDark;
  }else{
    document.documentElement.removeAttribute("data-theme");
    document.body.removeAttribute("data-theme");
    document.getElementById("themeBtn").textContent="🌙";
    colors=colorsLight;
  }
  Chart.defaults.color=tick;
  Chart.defaults.borderColor=grid;
  // 遍历所有 chart 实例：换 CP 色 + 强制 tick / axis title / grid 颜色
  if(window.Chart && Chart.instances){
    Object.values(Chart.instances).forEach(c=>{
      c.data.datasets.forEach(ds=>{
        const newC=colors[ds.label];
        if(newC){
          ds.borderColor=newC;
          ds.backgroundColor=newC+"22";
          ds.pointBackgroundColor=newC;
        }
      });
      const sc=c.options.scales||{};
      ["x","y"].forEach(k=>{
        if(sc[k]){
          sc[k].ticks=Object.assign(sc[k].ticks||{},{color:tick});
          if(sc[k].title){sc[k].title.color=axisTitle}
          sc[k].grid=Object.assign(sc[k].grid||{},{color:grid});
        }
      });
      // 同步 datalabels 颜色（高亮值用 CP 色，否则跟随主题）
      if(c.options.plugins&&c.options.plugins.legend&&c.options.plugins.legend.labels){
        c.options.plugins.legend.labels.color=axisTitle;
      }
      c.update();
    });
  }
}
function toggleTheme(){
  const cur=getTheme();
  const next=cur==="dark"?"light":"dark";
  setStoredTheme(next);
  applyTheme(next);
}
// 初始化（在 Chart.register 之前应用，避免闪屏）
(function(){const t=getTheme();if(t==="dark"){document.documentElement.setAttribute("data-theme","dark");document.body.setAttribute("data-theme","dark");}})();

Chart.register(ChartDataLabels);
Chart.defaults.set("plugins.datalabels",{display:false});
// 初始化 Chart.js 颜色（基于当前主题）
(function(){const t=getTheme();if(t==="dark"){Chart.defaults.color="rgba(255,255,255,0.85)";Chart.defaults.borderColor="rgba(255,255,255,0.10)";}else{Chart.defaults.color="#334155";Chart.defaults.borderColor="rgba(0,0,0,0.06)";}})();
// 同步按钮 emoji
document.addEventListener("DOMContentLoaded",()=>{const t=getTheme();const btn=document.getElementById("themeBtn");if(btn)btn.textContent=t==="dark"?"☀️":"🌙"});
const dates=__DATES__,cps=__CPS__,colorsLight=__COLORS__,colorsDark=__COLORS_DARK__,ingest=__INGEST__,stockBad=__STOCK_BAD__,perCP=__PER_CP__,fieldColors=__FIELD_COLORS__,consumTrend=__CONSUM_TREND__;
let colors=(getTheme()==="dark")?colorsDark:colorsLight;
const common={responsive:true,maintainAspectRatio:false,plugins:{legend:{position:"top",labels:{usePointStyle:true,font:{size:11},padding:10}},tooltip:{mode:"index",intersect:false,backgroundColor:"rgba(0,0,0,0.85)"}},interaction:{mode:"nearest",axis:"x",intersect:false}};
function fmtNum(n){if(n>=10000)return(n/10000).toFixed(1)+"w";if(n>=1000)return(n/1000).toFixed(1)+"k";return n}
const labelSchemeC={display:ctx=>{const d=ctx.dataset.data,m=Math.max(...d),mi=d.indexOf(m),l=ctx.dataIndex===d.length-1,x=ctx.dataIndex===mi&&m>0,c=d[ctx.dataIndex];return c>0&&(l||x)},align:"top",anchor:"end",font:{size:10,weight:"700"},color:ctx=>ctx.dataset.borderColor,formatter:v=>fmtNum(v)};
function lineStyle(c){return{borderColor:c,backgroundColor:c+"22",borderWidth:2.5,tension:0.35,pointRadius:0,pointHoverRadius:6,pointBackgroundColor:c,pointBorderColor:"#fff",pointBorderWidth:2}}
new Chart(document.getElementById("c1"),{type:"line",data:{labels:dates,datasets:cps.map(cp=>({label:cp,data:ingest[cp],...lineStyle(colors[cp])}))},options:{...common,scales:{y:{beginAtZero:true,title:{display:true,text:"每日入库条数"}}},plugins:{...common.plugins,datalabels:labelSchemeC}}});
new Chart(document.getElementById("c2"),{type:"line",data:{labels:dates,datasets:cps.map(cp=>({label:cp,data:stockBad[cp],...lineStyle(colors[cp])}))},options:{...common,scales:{y:{beginAtZero:true,title:{display:true,text:"存量异常条数"}}},plugins:{...common.plugins,datalabels:labelSchemeC}}});
function makePerCPChart(id,cp){const f=perCP[cp],ds=Object.keys(f).map((k,i)=>{const v=f[k],z=v.every(x=>x===0),c=fieldColors[i%fieldColors.length];return{label:k,data:v,...lineStyle(c),borderWidth:2,hidden:z}});new Chart(document.getElementById(id),{type:"line",data:{labels:dates,datasets:ds},options:{...common,scales:{y:{beginAtZero:true,title:{display:true,text:"存量异常条数"}}},plugins:{...common.plugins,legend:{position:"top",labels:{usePointStyle:true,font:{size:10},padding:6,boxWidth:8}},datalabels:labelSchemeC}}})}
["c3|guoying","c4|dihui","c5|beike","c6|meilaoban"].forEach(s=>{const[id,cp]=s.split("|");makePerCPChart(id,cp)});
// 消费 30 天趋势：1 张 canvas + 5 个 metric tab 切换（仅在 consumTrend 有数据时绘制）
if(consumTrend && consumTrend.cp){
  const cpShortMap={"cn-dihui-djy":"dihui","cn-beike-djy":"beike","cn-guoying-djy":"guoying","cn-meilaoban-djy":"meilaoban"};
  const cpsLong=Object.keys(consumTrend.cp);
  const yTitles={"vv":"VV","consum_dura_min":"分钟","distribute_content_cnt":"条数","vv_per_item":"VV/条","dura_per_vv_sec":"秒/VV"};
  const ccEl=document.getElementById("cc_main");
  let ccChart=null;
  function buildDatasets(metricKey){
    return cpsLong.map(cpL=>{
      const cpS=cpShortMap[cpL]||cpL;
      const series=consumTrend.cp[cpL][metricKey]||[];
      return{label:cpS,data:series,...lineStyle(colors[cpS]||"#94a3b8")};
    });
  }
  // 30 天每个非零点都显示数值（小字号）；legend 放底部，避免顶部数字被遮
  const labelSchemeConsum={display:ctx=>(ctx.dataset.data[ctx.dataIndex]||0)>0,align:"top",anchor:"end",font:{size:9,weight:"600"},color:ctx=>ctx.dataset.borderColor,formatter:v=>fmtNum(v)};
  function renderConsum(metricKey){
    if(!ccEl) return;
    const ds=buildDatasets(metricKey);
    if(ccChart){
      ccChart.data.datasets=ds;
      ccChart.options.scales.y.title.text=yTitles[metricKey]||"";
      ccChart.update();
    }else{
      const N=consumTrend.dates.length;
      ccChart=new Chart(ccEl,{type:"line",data:{labels:consumTrend.dates,datasets:ds},options:{...common,layout:{padding:{top:24,right:24,bottom:0}},scales:{y:{beginAtZero:true,title:{display:true,text:yTitles[metricKey]||""},grace:"12%"},x:{offset:false,ticks:{autoSkip:false,maxRotation:45,minRotation:45,font:{size:10},callback:function(val,idx){return(idx===0||idx===N-1||idx%3===0)?this.getLabelForValue(val):""}}}},plugins:{...common.plugins,legend:{position:"bottom",labels:{usePointStyle:true,font:{size:11},padding:6,boxHeight:8}},datalabels:labelSchemeConsum,tooltip:{...common.plugins.tooltip,callbacks:{label:ctx=>ctx.dataset.label+": "+fmtNum(ctx.parsed.y)}}}}});
    }
  }
  document.querySelectorAll(".cc-tab").forEach(btn=>{
    btn.addEventListener("click",()=>{
      document.querySelectorAll(".cc-tab").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active");
      renderConsum(btn.dataset.metric);
    });
  });
  renderConsum("vv");
}
</script></body></html>"""

    # 消费数据部分
    consumption_html = ""
    consum_trend = {}
    if consumption_json and os.path.isfile(consumption_json):
        with open(consumption_json, "r", encoding="utf-8") as f:
            cdata = json.load(f)
        # 兼容老 JSON：优先 cp_trend_30d，回退 cp_trend_7d
        consum_trend = cdata.get("cp_trend_30d") or cdata.get("cp_trend_7d") or {}
        consumption_html = (
            '<div class="section"><div class="section-title">📈 消费数据概览'
            '<span class="desc">大盘合计 · 4 CP 拆解 · 7 天趋势 · Top5 内容</span></div>'
            + _consumption_card_html(cdata)
            + '<div class="insight"><strong>📈 观察要点：</strong>大盘 VV / 时长环比骤降 &gt;30% 需核查 CP 侧推送状态；'
            '分发内容量大涨但<strong>篇均 VV 下滑</strong>通常意味着新内容冷启动不佳，建议看 Top5 观察标题质量与时效性。</div>'
            '</div>'
        )

    end_label = end_dt.strftime("%Y-%m-%d")
    health_html = _health_overview_html(stock_bad, ingest, per_cp)
    biz_html = _biz_cards_html(biz_actions or [])
    footer_html = _footer_html(end_label)

    rendered = (
        html.replace("__END__", end_label)
        .replace("__HEALTH_OVERVIEW__", health_html)
        .replace("__CONSUMPTION_SECTION__", consumption_html)
        .replace("__BIZ_CARDS__", biz_html)
        .replace("__FOOTER__", footer_html)
        .replace("__DATES__", json.dumps(dates_label, ensure_ascii=False))
        .replace("__CPS__", json.dumps(CPS))
        .replace("__COLORS__", json.dumps(CP_COLORS))
        .replace("__COLORS_DARK__", json.dumps(CP_COLORS_DARK))
        .replace("__INGEST__", json.dumps(ingest))
        .replace("__STOCK_BAD__", json.dumps(stock_bad))
        .replace("__PER_CP__", json.dumps(per_cp, ensure_ascii=False))
        .replace("__FIELD_COLORS__", json.dumps(FIELD_COLORS))
        .replace("__CONSUM_TREND__", json.dumps(consum_trend, ensure_ascii=False))
    )

    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    open(out_html, "w", encoding="utf-8").write(rendered)
    print(f"✅ HTML: {out_html}")


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    consumption_json = sys.argv[5] if len(sys.argv) > 5 else None
    id_consistency_csv = sys.argv[6] if len(sys.argv) > 6 else None
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], consumption_json, id_consistency_csv=id_consistency_csv)


if __name__ == "__main__":
    main()
