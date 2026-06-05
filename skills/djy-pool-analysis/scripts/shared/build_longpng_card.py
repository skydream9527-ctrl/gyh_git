#!/usr/bin/env python3
"""组装「长图版」日报卡片 JSON · 一张 HTML 长图 + 脚注链接

用法：
  python3 build_longpng_card.py --image-key <img_v3_...> \\
      --date <YYYYMMDD>        # 数据日期（T-1，用于标题/文件名）
      --report-url <pages_url> # GitLab Pages 完整 HTML 报告链接

输出：stdout 完整 interactive card JSON（供 feishu_post.py 使用）

卡片结构（2026-05-11 精简版）：
  - header：标题 + 副标题（数据日期 + 跑数时间）
  - img：长图（HTML 整页截图，mode=fit_horizontal，preview=true 可点开放大）
  - div：查看完整报告链接
  - note：数据源 + 豁免 + 跑数时间
"""
import argparse
import datetime
import json
import sys


def build_card(image_key: str, date_yyyymmdd: str, report_url: str) -> dict:
    try:
        d = datetime.datetime.strptime(date_yyyymmdd, "%Y%m%d").date()
        date_label = d.strftime("%Y-%m-%d")
    except ValueError:
        date_label = date_yyyymmdd

    now_label = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    elements = [
        {
            "tag": "img",
            "img_key": image_key,
            "alt": {"tag": "plain_text", "content": f"djy 内容池日报 · {date_label}"},
            "mode": "fit_horizontal",
            "preview": True,
        },
    ]

    if report_url:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"📎 [查看完整 HTML 报告（含交互图表）]({report_url})",
            },
        })

    footnote = (
        "数据源 paimon_zjyprc_hadoop.browser.business_content_pool_realtime · "
        "豁免 28 条 item + beike 的 author_ip 空 · "
        f"跑数时间 {now_label}"
    )
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": footnote}],
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📊 djy 内容池校验 · 日报 · {date_label}"},
            "subtitle": {"tag": "plain_text", "content": f"数据截至 {date_label} · 口径=全量存量 · 点击图片可放大"},
            "template": "blue",
        },
        "elements": elements,
    }
    return {"card": card}


def main():
    ap = argparse.ArgumentParser(description="长图版日报卡片 JSON 生成器")
    ap.add_argument("--image-key", required=True, help="飞书图床 image_key")
    ap.add_argument("--date", required=True, help="数据日期 YYYYMMDD（T-1）")
    ap.add_argument("--report-url", required=True, help="GitLab Pages HTML 报告 URL")
    args = ap.parse_args()

    card_json = build_card(args.image_key, args.date, args.report_url)
    print(json.dumps(card_json, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
