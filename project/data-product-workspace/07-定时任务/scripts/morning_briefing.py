#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
早间待办刷新脚本
定时执行：每天 08:30
功能：
1. 从 WORK-PLAN.md 提取 P0/P1 活跃任务
2. 从 DAILY-TODO.md 提取昨日未完成项
3. 从 DECISIONS.md 提取今日/近期到期决策
4. 从前一天日报提取滚动跟进项
5. 合并去重排序，更新 DAILY-TODO.md 和 CURRENT.md
6. 推送飞书卡片提醒
"""
import os
import sys
import re
import json
import time
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "morning_briefing_config.json"
LOG_DIR = SCRIPT_DIR.parent / "logs"

LOG_DIR.mkdir(exist_ok=True, parents=True)

HEADER_WORDS = {"任务名称", "状态", "优先级", "事项", "回看时间", "来源", "类型"}


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"morning-briefing-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


def load_config():
    default_config = {
        "feishu_webhook": "",
        "feishu_secret": "",
        "max_p0_items": 6,
        "max_p1_items": 4,
        "sources": {
            "work_plan": "WORK-PLAN.md",
            "daily_todo": "05-个人成长/每日记录/DAILY-TODO.md",
            "current": "CURRENT.md",
            "decisions": "DECISIONS.md",
            "daily_records": "05-个人成长/每日记录"
        },
        "notification": {"at_all": False, "card_color": "blue"}
    }
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(exist_ok=True, parents=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        log(f"已创建默认配置: {CONFIG_PATH}")
        return default_config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_active_status(status_str):
    s = status_str.strip()
    for marker in ("🔴", "🟡", "⏸️"):
        if marker in s:
            return True
    return False


def _parse_table_rows(text, min_cols):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        if len(cells) < min_cols:
            continue
        if cells[0].startswith("---"):
            continue
        if any(c in HEADER_WORDS for c in cells[:3]):
            continue
        rows.append(cells)
    return rows


def extract_workplan_p0_p1(wp_path):
    if not wp_path.exists():
        log(f"WORK-PLAN.md 不存在: {wp_path}", "WARN")
        return []
    content = wp_path.read_text(encoding="utf-8")
    items = []

    p0_match = re.search(r'##\s*🔥\s*P0\s.*?\n(.*?)(?=\n---|\n##\s)', content, re.DOTALL)
    if p0_match:
        rows = _parse_table_rows(p0_match.group(1), 6)
        for row in rows:
            name, typ, status = row[0], row[1], row[2]
            deadline = row[3] if len(row) > 3 else ""
            if _is_active_status(status):
                items.append({
                    "name": re.sub(r'`', '', name).strip(),
                    "priority": "P0",
                    "status": status.strip(),
                    "type": typ.strip(),
                    "deadline": deadline.strip(),
                    "source": "WORK-PLAN P0"
                })

    p1_match = re.search(r'##\s*🚀\s*P1\s.*?\n(.*?)(?=\n---|\n##\s*📅)', content, re.DOTALL)
    if p1_match:
        rows = _parse_table_rows(p1_match.group(1), 4)
        for row in rows:
            name, typ, status = row[0], row[1], row[2]
            if _is_active_status(status):
                items.append({
                    "name": re.sub(r'`', '', name).strip(),
                    "priority": "P1",
                    "status": status.strip(),
                    "type": typ.strip(),
                    "deadline": "",
                    "source": "WORK-PLAN P1"
                })

    log(f"WORK-PLAN 提取: P0 {sum(1 for i in items if i['priority']=='P0')} 项, "
        f"P1 {sum(1 for i in items if i['priority']=='P1')} 项")
    return items


def extract_yesterday_unfinished(todo_path):
    if not todo_path.exists():
        log(f"DAILY-TODO.md 不存在: {todo_path}", "WARN")
        return []
    content = todo_path.read_text(encoding="utf-8")
    items = []

    section_match = re.search(r'##\s*今日待办（.*?）\s*\n(.*?)(?=\n##\s)', content, re.DOTALL)
    if not section_match:
        log("DAILY-TODO 未找到「今日待办」section", "WARN")
        return []

    rows = _parse_table_rows(section_match.group(1), 4)
    for row in rows:
        status, priority, name = row[0], row[1], row[2]
        source_raw = row[3] if len(row) > 3 else ""
        deadline = row[4] if len(row) > 4 else ""
        if "✅" in status:
            continue
        # 清理嵌套的「昨日待办(...)」前缀，只保留最内层来源
        source = source_raw.strip()
        while source.startswith("昨日待办(") and source.endswith(")"):
            source = source[len("昨日待办("):-1]
        items.append({
            "name": name.strip(),
            "priority": priority.strip(),
            "status": status.strip(),
            "type": "昨日未完成",
            "deadline": deadline.strip(),
            "source": f"昨日待办({source})" if source else "昨日待办"
        })

    log(f"昨日未完成: {len(items)} 项")
    return items


def _parse_fuzzy_date(date_str):
    date_str = date_str.strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r'(\d{4})-(\d{2})\s*月底', date_str)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if month == 12:
            return datetime(year + 1, 1, 1) - timedelta(days=1)
        return datetime(year, month + 1, 1) - timedelta(days=1)
    m = re.match(r'(\d{4})-(\d{2})$', date_str)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if month == 12:
            return datetime(year + 1, 1, 1) - timedelta(days=1)
        return datetime(year, month + 1, 1) - timedelta(days=1)
    return None


def extract_due_decisions(decisions_path):
    if not decisions_path.exists():
        log(f"DECISIONS.md 不存在: {decisions_path}", "WARN")
        return []
    content = decisions_path.read_text(encoding="utf-8")

    section_match = re.search(r'##\s*待回看决策\s*\n', content)
    if not section_match:
        log("DECISIONS 未找到「待回看决策」section", "WARN")
        return []

    table_text = content[section_match.end():]
    next_section = re.search(r'\n##\s', table_text)
    if next_section:
        table_text = table_text[:next_section.start()]

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    soon_threshold = today + timedelta(days=3)
    results = []

    rows = _parse_table_rows(table_text, 4)
    for row in rows:
        review_date_str, decision, check_q, status = row[0], row[1], row[2], row[3]
        if "✅" in status or "已回看" in status:
            continue
        review_date = _parse_fuzzy_date(review_date_str)
        if review_date is None:
            continue
        if review_date <= soon_threshold:
            if review_date.date() == today.date():
                tag = "今日到期"
            elif review_date < today:
                tag = "已过期"
            else:
                tag = "即将到期"
            results.append({
                "decision": decision.strip(),
                "review_date": review_date_str.strip(),
                "check_question": check_q.strip(),
                "tag": tag
            })

    log(f"到期/近期决策: {len(results)} 条")
    return results


def extract_yesterday_rolling(daily_dir):
    daily_dir = Path(daily_dir)
    if not daily_dir.exists():
        log(f"每日记录目录不存在: {daily_dir}", "WARN")
        return []

    daily_files = sorted(daily_dir.glob("*-每日工作回顾.md"), reverse=True)
    if not daily_files:
        log("未找到日报文件", "WARN")
        return []

    latest = daily_files[0]
    log(f"读取最近日报: {latest.name}")
    content = latest.read_text(encoding="utf-8")

    items = []
    plan_match = re.search(r'##\s*📅\s*明日计划\s*\n(.*?)(?=\n---|\n##\s)', content, re.DOTALL)
    if plan_match:
        for line in plan_match.group(1).splitlines():
            stripped = line.strip()
            m = re.match(r'^(?:\d+\.\s*|-\s*\[\s*\]\s*|-\s*)(.+)$', stripped)
            if m:
                text = m.group(1).strip()
                if text and len(text) > 2:
                    priority = "P0" if ("P0" in text or "必做" in text) else "P1"
                    items.append({
                        "name": re.sub(r'^(?:P0|P1|必做|待办)[：:\s]*', '', text).strip(),
                        "priority": priority,
                        "status": "⏳ 待开始",
                        "type": "日报滚动",
                        "deadline": "",
                        "source": f"日报明日计划({latest.stem[:10]})"
                    })

    log(f"日报滚动跟进: {len(items)} 项")
    return items


def merge_and_prioritize(p0_p1, unfinished, decisions, rolling, config):
    all_items = []
    seen_keys = set()
    max_p0 = config.get("max_p0_items", 6)
    max_p1 = config.get("max_p1_items", 4)

    def _dedup_key(name):
        return re.sub(r'[\s`*\u200b]', '', name)[:20]

    def _add(item):
        key = _dedup_key(item["name"])
        if key in seen_keys:
            return
        seen_keys.add(key)
        all_items.append(item)

    for src in [unfinished, p0_p1, rolling]:
        for item in src:
            if item.get("priority") == "P0":
                _add(item)

    for src in [unfinished, p0_p1, rolling]:
        for item in src:
            if item.get("priority") != "P0":
                _add(item)

    p0_items = [i for i in all_items if i.get("priority") == "P0"][:max_p0]
    p1_items = [i for i in all_items if i.get("priority") != "P0"][:max_p1]
    merged = p0_items + p1_items

    log(f"合并去重后: P0 {len(p0_items)} 项, P1 {len(p1_items)} 项")
    return merged


def _replace_section(content, section_pattern, new_section_content, section_title_replacement=None):
    match = re.search(section_pattern, content, re.DOTALL)
    if not match:
        return content, False

    after_title = match.end()
    rest = content[after_title:]
    next_section = re.search(r'\n##\s', rest)
    if next_section:
        section_end = after_title + next_section.start()
    else:
        section_end = len(content)

    before = content[:match.start()]
    after = content[section_end:]

    if section_title_replacement:
        new_content = section_title_replacement + new_section_content
    else:
        new_content = match.group(0).split('\n')[0] + '\n' + new_section_content

    return before + new_content + after, True


def update_daily_todo(todo_path, items, date_str):
    if not todo_path.exists():
        log(f"DAILY-TODO.md 不存在，跳过更新: {todo_path}", "WARN")
        return False
    content = todo_path.read_text(encoding="utf-8")

    table_lines = [
        "",
        "| 状态 | 优先级 | 事项 | 来源 | 截止/目标 | 下一步 |",
        "|------|--------|------|------|-----------|--------|",
    ]
    for item in items:
        table_lines.append(
            f"| ⏳ 待开始 | {item['priority']} | {item['name']} "
            f"| {item.get('source', '')} | {item.get('deadline', '')} | |"
        )
    table_lines.append("")

    new_title = f"## 今日待办（{date_str}）\n"
    new_body = "\n".join(table_lines)
    updated, ok = _replace_section(
        content, r'## 今日待办（.*?）\s*\n', new_body,
        section_title_replacement=new_title
    )

    if ok:
        with open(todo_path, "w", encoding="utf-8") as f:
            f.write(updated)
        log(f"DAILY-TODO.md 今日待办已更新为 {date_str}")
        return True
    log("DAILY-TODO.md 未找到「今日待办」section，跳过", "WARN")
    return False


def update_current_todo(current_path, items, date_str):
    if not current_path.exists():
        log(f"CURRENT.md 不存在，跳过更新: {current_path}", "WARN")
        return False
    content = current_path.read_text(encoding="utf-8")

    table_lines = [
        "",
        "> 固定跟踪文档：`05-个人成长/每日记录/DAILY-TODO.md`。每天开始工作时更新，晚上回顾时同步完成状态。",
        "",
        "| 优先级 | 事项 | 类型 | 验收/完成标准 |",
        "|--------|------|------|----------------|",
    ]
    for item in items:
        table_lines.append(
            f"| {item['priority']} | {item['name']} | {item.get('type', '')} | |"
        )
    table_lines.append("")

    new_title = f"## 今日 ToDo（{date_str}）\n"
    new_body = "\n".join(table_lines)
    updated, ok = _replace_section(
        content, r'## 今日 ToDo（.*?）\s*\n', new_body,
        section_title_replacement=new_title
    )

    if ok:
        with open(current_path, "w", encoding="utf-8") as f:
            f.write(updated)
        log(f"CURRENT.md 今日 ToDo 已更新为 {date_str}")
        return True
    log("CURRENT.md 未找到「今日 ToDo」section，跳过", "WARN")
    return False


def gen_feishu_sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def build_feishu_card(date_str, items, decisions, config):
    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekday_names[datetime.now().weekday()]

    p0_items = [i for i in items if i.get("priority") == "P0"]
    p1_items = [i for i in items if i.get("priority") != "P0"]

    lines = [f"**P0 {len(p0_items)} 项 / P1 {len(p1_items)} 项**\n"]

    if p0_items:
        lines.append("**🔴 P0 任务**")
        for item in p0_items:
            deadline_tag = f"（{item['deadline']}）" if item.get("deadline") else ""
            lines.append(f"- {item['name']}{deadline_tag}")
        lines.append("")

    if p1_items:
        lines.append("**🟡 P1 任务**")
        for item in p1_items:
            lines.append(f"- {item['name']}")
        lines.append("")

    if decisions:
        lines.append("**📋 到期决策提醒**")
        for d in decisions:
            lines.append(f"- [{d['tag']}] {d['decision']}（{d['review_date']}）")
        lines.append("")

    lines.append("📎 详见 `DAILY-TODO.md` 和 `CURRENT.md`")

    card_color = config.get("notification", {}).get("card_color", "blue")
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📋 今日待办（{date_str} 星期{weekday}）"},
            "template": card_color
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}
        ]
    }

    if config.get("notification", {}).get("at_all"):
        card["elements"].append({"tag": "hr"})
        card["elements"].append({
            "tag": "note",
            "elements": [{"tag": "lark_md", "content": "<at id=all></at>"}]
        })

    return card


def send_feishu_message(webhook_url, content, secret=""):
    if not webhook_url:
        log("飞书webhook未配置，跳过推送")
        return False
    payload = {"msg_type": "interactive", "card": content}
    if secret:
        timestamp = str(int(time.time()))
        sign = gen_feishu_sign(secret, timestamp)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0:
                log("飞书消息推送成功")
                return True
            else:
                log(f"飞书推送失败: {result}", "ERROR")
                return False
    except Exception as e:
        log(f"飞书推送异常: {str(e)}", "ERROR")
        return False


def main():
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekday_names[today.weekday()]

    log(f"=== 开始生成 {date_str}（星期{weekday}）早间待办 ===")

    config = load_config()
    sources = config.get("sources", {})

    log("从 WORK-PLAN.md 提取 P0/P1...")
    p0_p1 = extract_workplan_p0_p1(BASE_DIR / sources.get("work_plan", "WORK-PLAN.md"))

    log("从 DAILY-TODO.md 提取昨日未完成...")
    unfinished = extract_yesterday_unfinished(BASE_DIR / sources.get("daily_todo", "05-个人成长/每日记录/DAILY-TODO.md"))

    log("从 DECISIONS.md 提取到期决策...")
    decisions = extract_due_decisions(BASE_DIR / sources.get("decisions", "DECISIONS.md"))

    log("从日报提取滚动跟进...")
    rolling = extract_yesterday_rolling(BASE_DIR / sources.get("daily_records", "05-个人成长/每日记录"))

    items = merge_and_prioritize(p0_p1, unfinished, decisions, rolling, config)

    dry_run = "--dry-run" in sys.argv
    if not dry_run:
        update_daily_todo(
            BASE_DIR / sources.get("daily_todo", "05-个人成长/每日记录/DAILY-TODO.md"),
            items, date_str
        )
        update_current_todo(
            BASE_DIR / sources.get("current", "CURRENT.md"),
            items, date_str
        )
        log("已更新 DAILY-TODO.md 和 CURRENT.md")
    else:
        log("[DRY-RUN] 跳过文件更新")

    webhook = config.get("feishu_webhook", "")
    if webhook and not dry_run:
        card = build_feishu_card(date_str, items, decisions, config)
        send_feishu_message(webhook, card, config.get("feishu_secret", ""))
    elif not webhook:
        log("飞书webhook未配置，跳过推送")

    p0_count = sum(1 for i in items if i.get("priority") == "P0")
    p1_count = sum(1 for i in items if i.get("priority") != "P0")
    log(f"今日待办：P0 {p0_count} 项，P1 {p1_count} 项")
    if decisions:
        log(f"到期决策提醒：{len(decisions)} 条")

    log("=== 早间待办生成完成 ===")
    print(f"\n📋 {date_str} 早间待办已生成：P0 {p0_count} 项 / P1 {p1_count} 项")
    if decisions:
        print(f"⚠️ 到期决策提醒：{len(decisions)} 条")


if __name__ == "__main__":
    main()
