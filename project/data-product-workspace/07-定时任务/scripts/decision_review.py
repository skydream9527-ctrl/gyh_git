#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策回填闭环自动化
定时执行：每天 09:00
功能：
1. 解析 DECISIONS.md「待回看决策」表格
2. 筛选到期/即将到期/已过期的决策
3. 搜集证据（每日记录、MEMORY、WORK-PLAN）
4. 生成回填简报
5. 推送飞书提醒
"""
import os
import sys
import re
import json
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "decision_review_config.json"
LOG_DIR = SCRIPT_DIR.parent / "logs"
REPORT_DIR = SCRIPT_DIR.parent / "reports"

for d in [LOG_DIR, REPORT_DIR]:
    d.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"decision-review-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_config():
    default_config = {
        "feishu_webhook": "",
        "feishu_secret": "",
        "advance_days": 2,
        "decisions_path": "DECISIONS.md",
        "evidence_sources": {
            "daily_records": "05-个人成长/每日记录",
            "memory": "MEMORY.md",
            "work_plan": "WORK-PLAN.md",
            "current": "CURRENT.md"
        },
        "report_output_dir": "07-定时任务/reports",
        "review_draft_dir": "99-临时文件/决策回看",
        "notification": {"at_users": [], "at_all": False, "notify_on_no_due": False}
    }
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        log(f"已创建默认配置: {CONFIG_PATH}")
        return default_config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_fuzzy_date(date_str):
    """解析模糊日期，如 '2026-07 月底'、'2026-07-10'、'2026-07'"""
    date_str = date_str.strip()
    # 标准格式 YYYY-MM-DD
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # YYYY-MM 月底
    m = re.match(r'(\d{4})-(\d{2})\s*月底', date_str)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if month == 12:
            return datetime(year + 1, 1, 1) - timedelta(days=1)
        return datetime(year, month + 1, 1) - timedelta(days=1)
    # YYYY-MM（默认月底）
    m = re.match(r'(\d{4})-(\d{2})$', date_str)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if month == 12:
            return datetime(year + 1, 1, 1) - timedelta(days=1)
        return datetime(year, month + 1, 1) - timedelta(days=1)
    return None

def is_review_due(review_date_str, advance_days):
    """判断是否到期或即将到期"""
    review_date = parse_fuzzy_date(review_date_str)
    if review_date is None:
        return False, "unknown", None
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    diff = (review_date - today).days
    if diff < 0:
        return True, "overdue", review_date
    if diff == 0:
        return True, "due_today", review_date
    if diff <= advance_days:
        return True, "due_soon", review_date
    return False, "not_due", review_date

def parse_decisions_table(decisions_path):
    """解析 DECISIONS.md 的决策总览表格"""
    if not decisions_path.exists():
        log(f"DECISIONS.md 不存在: {decisions_path}", "ERROR")
        return []
    content = decisions_path.read_text(encoding="utf-8")
    # 定位「决策总览」section
    section_match = re.search(r'##\s*决策总览', content)
    if not section_match:
        log("未找到「决策总览」section", "WARN")
        return []
    table_text = content[section_match.end():]
    # 解析表格行（跳过分隔线）
    rows = []
    for line in table_text.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            if line.startswith('#') or line.startswith('---'):
                break
            continue
        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c]  # 去空
        if len(cells) < 6 or cells[0].startswith('日期') or cells[0].startswith('---'):
            continue
        # 当前表格列：日期 | 决策 | 依据 | 影响 | 回看时间 | 完整简报
        review_date = cells[4]
        # 跳过持续执行的规则类决策
        if review_date in ["持续执行", ""]:
            continue
        rows.append({
            "review_date": review_date,
            "decision": cells[1],
            "check_question": cells[3],
            "status": "待回看",
            "basis": cells[2],
            "adr_link": cells[5]
        })
    return rows

def find_decision_adr(decision_title, decisions_content):
    """在 DECISIONS.md 中定位对应 ADR 完整内容"""
    # 尝试用决策标题匹配 ADR 标题（## YYYY-MM-DD ...）
    title_clean = decision_title.strip().replace('`', '').replace('*', '')
    for match in re.finditer(r'##\s+\d{4}-\d{2}-\d{2}\s+(.+?)\n', decisions_content):
        adr_title = match.group(1).strip().replace('`', '').replace('*', '')
        # 模糊匹配：决策标题的核心词在 ADR 标题中
        if title_clean in adr_title or adr_title in title_clean:
            start = match.start()
            # 找到下一个 ## 或文件末尾
            next_section = re.search(r'\n##\s+', decisions_content[start + 1:])
            end = start + 1 + next_section.start() if next_section else len(decisions_content)
            return decisions_content[start:end].strip()
    return ""

def extract_keywords_from_decision(decision):
    """从决策标题和检查问题中提取搜索关键词"""
    text = f"{decision['decision']} {decision['check_question']}"
    # 移除标点和常见停用词
    text = re.sub(r'[`|？。，、；：""（）\(\)]', ' ', text)
    # 提取有意义的词（中文2-6字，英文3+字母）
    cn_words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    en_words = re.findall(r'[a-zA-Z]{3,}', text)
    # 过滤停用词
    stop_words = {'是否', '完成', '达到', '是否已', '带来', '调整', '落地', '检查', '确认',
                  'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has'}
    keywords = [w for w in cn_words + en_words if w not in stop_words]
    return list(set(keywords))[:10]

def search_daily_records(daily_dir, keywords, days_range=30):
    """在每日记录中搜索与决策相关的证据"""
    if not daily_dir.exists():
        return []
    findings = []
    today = datetime.now()
    for f in sorted(daily_dir.glob("*.md"), reverse=True):
        if len(findings) >= 10:
            break
        # 从文件名提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', f.name)
        if date_match:
            try:
                file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                if (today - file_date).days > days_range:
                    continue
            except ValueError:
                continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        matched_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) > 300:
                continue
            if any(kw in stripped for kw in keywords):
                matched_lines.append(stripped)
                if len(matched_lines) >= 5:
                    break
        if matched_lines:
            findings.append({
                "date": date_match.group(1) if date_match else f.name,
                "file": f.name,
                "matched_lines": matched_lines
            })
    return findings

def gather_evidence(decision, config):
    """搜集决策回填所需证据"""
    keywords = extract_keywords_from_decision(decision)
    sources = config.get("evidence_sources", {})
    evidence = {"keywords": keywords, "daily_findings": [], "memory_context": "", "plan_status": ""}

    # 搜索每日记录
    daily_dir = BASE_DIR / sources.get("daily_records", "05-个人成长/每日记录")
    evidence["daily_findings"] = search_daily_records(daily_dir, keywords)

    # 读取 MEMORY.md 相关段落
    memory_path = BASE_DIR / sources.get("memory", "MEMORY.md")
    if memory_path.exists():
        try:
            memory_content = memory_path.read_text(encoding="utf-8")
            relevant = []
            for line in memory_content.splitlines():
                stripped = line.strip()
                if any(kw in stripped for kw in keywords):
                    relevant.append(stripped)
                    if len(relevant) >= 5:
                        break
            evidence["memory_context"] = "\n".join(relevant) if relevant else ""
        except Exception as e:
            log(f"读取 MEMORY.md 失败: {e}", "WARN")

    # 读取 WORK-PLAN.md 相关状态
    plan_path = BASE_DIR / sources.get("work_plan", "WORK-PLAN.md")
    if plan_path.exists():
        try:
            plan_content = plan_path.read_text(encoding="utf-8")
            relevant = []
            for line in plan_content.splitlines():
                stripped = line.strip()
                if any(kw in stripped for kw in keywords):
                    relevant.append(stripped)
                    if len(relevant) >= 5:
                        break
            evidence["plan_status"] = "\n".join(relevant) if relevant else ""
        except Exception as e:
            log(f"读取 WORK-PLAN.md 失败: {e}", "WARN")

    return evidence

def generate_review_brief(decision, adr_content, evidence, config):
    """生成决策回填简报"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    due_date = parse_fuzzy_date(decision["review_date"])
    due_str = due_date.strftime("%Y-%m-%d") if due_date else decision["review_date"]

    lines = [
        f"# 决策回看简报 — {decision['decision']}",
        f"",
        f"> 生成时间：{today_str}",
        f"> 回看截止：{due_str}",
        f"> 当前状态：{decision['status']}",
        f"",
        f"---",
        f"",
        f"## 原始决策",
        f"",
        f"**决策**: {decision['decision']}",
        f"**回看时间**: {decision['review_date']}",
        f"**检查问题**: {decision['check_question']}",
        f"",
    ]

    if adr_content:
        # 截取 ADR 的关键部分（背景、选择、依据、风险）
        lines.append("## 决策详情（ADR 摘要）")
        lines.append("")
        # 取前 80 行作为摘要
        adr_lines = adr_content.splitlines()[:80]
        lines.extend(adr_lines)
        if len(adr_content.splitlines()) > 80:
            lines.append(f"\n> ... 共 {len(adr_content.splitlines())} 行，已截取前 80 行")
        lines.append("")

    lines.extend([
        f"## 证据汇总",
        f"",
        f"**搜索关键词**: {', '.join(evidence['keywords'])}",
        f"",
    ])

    # 每日记录证据
    if evidence["daily_findings"]:
        lines.append("### 每日记录中的相关证据")
        lines.append("")
        for finding in evidence["daily_findings"][:5]:
            lines.append(f"**{finding['date']}** (`{finding['file']}`)")
            for line in finding["matched_lines"][:3]:
                lines.append(f"> {line}")
            lines.append("")
    else:
        lines.append("### 每日记录中的相关证据")
        lines.append("")
        lines.append("> 未找到相关每日记录（可能关键词不匹配或记录尚未生成）")
        lines.append("")

    # MEMORY 上下文
    if evidence["memory_context"]:
        lines.append("### MEMORY.md 相关内容")
        lines.append("```")
        lines.append(evidence["memory_context"])
        lines.append("```")
        lines.append("")

    # WORK-PLAN 状态
    if evidence["plan_status"]:
        lines.append("### WORK-PLAN.md 相关状态")
        lines.append("```")
        lines.append(evidence["plan_status"])
        lines.append("```")
        lines.append("")

    lines.extend([
        f"## 回填判定（请填写）",
        f"",
        f"根据以上证据，对照原始决策和检查问题，请填写：",
        f"",
        f"- **判定**: ✅ 成立 / ⚠️ 部分成立 / ❌ 推翻",
        f"- **实际结果 vs 预期**: ",
        f"- **偏差原因**: ",
        f"- **沉淀经验**: ",
        f"",
        f"---",
        f"",
        f"*填写完成后，请告知 AI 回写到 DECISIONS.md 对应 ADR 末尾*",
    ])

    return "\n".join(lines)

def gen_feishu_sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")

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
            headers={"Content-Type": "application/json"},
            method="POST"
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

def build_feishu_card(due_items, report_path):
    """构建飞书卡片消息"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    overdue = [d for d in due_items if d["_status"] == "overdue"]
    due_today = [d for d in due_items if d["_status"] == "due_today"]
    due_soon = [d for d in due_items if d["_status"] == "due_soon"]

    status_parts = []
    if overdue:
        status_parts.append(f"{len(overdue)} 个已过期")
    if due_today:
        status_parts.append(f"{len(due_today)} 个今日到期")
    if due_soon:
        status_parts.append(f"{len(due_soon)} 个即将到期")
    summary = "，".join(status_parts)

    lines = [f"**{summary}**\n"]

    if overdue or due_today:
        lines.append("**🔴 已到期/过期**")
        for d in overdue + due_today:
            lines.append(f"- **{d['decision']}**（{d['review_date']}）")
            lines.append(f"  检查：{d['check_question']}")
        lines.append("")

    if due_soon:
        lines.append("**🟡 即将到期**")
        for d in due_soon:
            lines.append(f"- **{d['decision']}**（{d['review_date']}）")
        lines.append("")

    lines.append(f"📎 详细回填简报：`{report_path}`")
    lines.append("请确认证据并填写回填判定（✅/⚠️/❌）")

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📋 决策回看提醒（{today_str}）"},
            "template": "orange"
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}
        ]
    }

    at_text = ""
    if at_text:
        card["elements"].append({"tag": "hr"})
        card["elements"].append({"tag": "note", "elements": [{"tag": "lark_md", "content": at_text}]})

    return card

def main():
    log("=== 开始执行决策回填闭环检查 ===")
    config = load_config()

    decisions_path = BASE_DIR / config.get("decisions_path", "DECISIONS.md")
    advance_days = config.get("advance_days", 2)

    # 1. 解析待回看决策表
    log("解析 DECISIONS.md 待回看决策表...")
    decisions = parse_decisions_table(decisions_path)
    log(f"发现 {len(decisions)} 条待回看决策")

    # 2. 筛选到期项
    due_items = []
    for d in decisions:
        if "✅" in d["status"] or "已回看" in d["status"]:
            log(f"跳过已回看: {d['decision']}")
            continue
        is_due, status, review_date = is_review_due(d["review_date"], advance_days)
        if is_due:
            d["_status"] = status
            d["_review_date"] = review_date
            due_items.append(d)
            log(f"到期决策 [{status}]: {d['decision']}（{d['review_date']}）")

    if not due_items:
        log("无到期决策，跳过")
        if not config.get("notification", {}).get("notify_on_no_due", False):
            return

    # 3. 搜集证据并生成简报
    decisions_content = decisions_path.read_text(encoding="utf-8")
    today_str = datetime.now().strftime("%Y-%m-%d")
    briefs = []

    for d in due_items:
        log(f"搜集证据: {d['decision']}...")
        adr = find_decision_adr(d["decision"], decisions_content)
        evidence = gather_evidence(d, config)
        brief = generate_review_brief(d, adr, evidence, config)
        briefs.append(brief)

    # 4. 保存简报
    review_dir = BASE_DIR / config.get("review_draft_dir", "99-临时文件/决策回看")
    review_dir.mkdir(exist_ok=True, parents=True)

    if briefs:
        # 合并为一份简报
        combined = f"# 决策回看简报 — {today_str}\n\n"
        combined += f"> 共 {len(briefs)} 个决策待回看\n\n---\n\n"
        combined += "\n\n---\n\n".join(briefs)

        report_path = review_dir / f"{today_str}-决策回看简报.md"
        report_path.write_text(combined, encoding="utf-8")
        log(f"简报已保存: {report_path}")

        # 同时保存到 reports
        report_copy = REPORT_DIR / f"{today_str}-决策回看简报.md"
        report_copy.write_text(combined, encoding="utf-8")
        log(f"简报副本: {report_copy}")

    # 5. 推送飞书
    if due_items:
        webhook = config.get("feishu_webhook", "")
        secret = config.get("feishu_secret", "")
        if webhook:
            rel_report = f"{review_dir.relative_to(BASE_DIR)}/{today_str}-决策回看简报.md"
            card = build_feishu_card(due_items, rel_report)
            send_feishu_message(webhook, card, secret)
        else:
            log("飞书webhook未配置，跳过推送")

    # 6. 输出摘要
    log("=" * 60)
    log("决策回填闭环检查完成")
    log(f"待回看决策: {len(due_items)} 条")
    for d in due_items:
        log(f"  [{d['_status']}] {d['decision']}（{d['review_date']}）")
    if briefs:
        log(f"简报路径: {review_dir}/{today_str}-决策回看简报.md")
    log("=" * 60)

    print(f"\n✅ 决策回看检查完成：{len(due_items)} 条待回看")
    if briefs:
        print(f"📄 简报已生成: 99-临时文件/决策回看/{today_str}-决策回看简报.md")

if __name__ == "__main__":
    main()
