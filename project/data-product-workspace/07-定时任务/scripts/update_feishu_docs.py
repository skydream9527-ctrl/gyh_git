#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书文档定时更新脚本
- 每周一9:00：打开工作梳理文档，追加新一周模板
- 每周五9:00：打开周总结文档，追加新一周模板
"""
import os
import sys
import json
import time
import subprocess
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "feishu_doc_update.json"
LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"feishu-doc-update-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def send_feishu_notification(webhook_url, content):
    """发送飞书提醒"""
    if not webhook_url:
        return
    try:
        import urllib.request
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "📝 文档更新提醒"},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": content}}
                ]
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
        log("飞书提醒发送成功")
    except Exception as e:
        log(f"飞书提醒发送失败: {str(e)}", "WARN")

def open_doc_in_browser(doc_url, dry_run=False):
    """在默认浏览器中打开飞书文档"""
    if dry_run:
        log(f"[Dry Run] 将在浏览器中打开文档: {doc_url}")
        return True
    try:
        webbrowser.open(doc_url)
        log(f"已在浏览器中打开文档: {doc_url}")
        return True
    except Exception as e:
        log(f"打开浏览器失败: {str(e)}", "ERROR")
        return False

def get_week_range(date=None):
    """获取当前周的起止日期"""
    if date is None:
        date = datetime.now()
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def generate_weekly_work_template(week_start, week_end):
    """生成周工作梳理模板（周一用）"""
    return f"""
---

## 📅 {week_start} ~ {week_end} 周工作计划

### ✅ 本周已完成
- [ ] 
- [ ] 
- [ ] 

### 🚀 本周进行中
- [ ] 
- [ ] 
- [ ] 

### 📋 待跟进事项
- [ ] 
- [ ] 

### 🤔 问题与风险
- 
"""

def generate_weekly_summary_template(week_start, week_end):
    """生成周总结模板（周五用）"""
    return f"""
---

## 📊 {week_start} ~ {week_end} 周工作总结

### 🎯 本周成果
1. 
2. 
3. 

### 📈 数据与指标
| 指标 | 本周值 | 上周值 | 环比 | 说明 |
|------|--------|--------|------|------|
|      |        |        |      |      |
|      |        |        |      |      |

### 💡 经验与反思
- 
- 

### 📅 下周计划
- [ ] 
- [ ] 
- [ ] 
"""

def update_monday_doc(config, dry_run=False):
    """周一更新工作梳理文档"""
    log("=== 开始执行周一定时更新任务 ===")
    week_start, week_end = get_week_range()
    
    notification_content = f"""
**周一文档更新提醒** 📋

已为你打开工作梳理文档，请填写本周计划：
[{config['doc_url']}]({config['doc_url']})

周期：{week_start} ~ {week_end}
"""
    
    if not dry_run:
        send_feishu_notification(config.get("notification", {}).get("feishu_webhook", ""), notification_content)
    
    open_doc_in_browser(config["doc_url"], dry_run=dry_run)
    
    log("周一定时任务执行完成：已打开工作梳理文档，等待手动填写")
    log(f"周期: {week_start} ~ {week_end}")
    # 打印模板内容，方便复制粘贴
    template = generate_weekly_work_template(week_start, week_end)
    log(f"本周计划模板:\n{template}")

def update_friday_doc(config, dry_run=False):
    """周五更新周总结文档"""
    log("=== 开始执行周五定时更新任务 ===")
    week_start, week_end = get_week_range()
    
    notification_content = f"""
**周五总结提醒** 📊

已为你打开周总结文档，请填写本周总结和下周计划：
[{config['doc_url']}]({config['doc_url']})

周期：{week_start} ~ {week_end}
"""
    
    if not dry_run:
        send_feishu_notification(config.get("notification", {}).get("feishu_webhook", ""), notification_content)
    
    open_doc_in_browser(config["doc_url"], dry_run=dry_run)
    
    log("周五定时任务执行完成：已打开周总结文档，等待手动填写")
    log(f"周期: {week_start} ~ {week_end}")
    # 打印模板内容，方便复制粘贴
    template = generate_weekly_summary_template(week_start, week_end)
    log(f"本周总结模板:\n{template}")

def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv if a != "--dry-run"]
    
    if len(args) < 2:
        print("用法: python3 update_feishu_docs.py [monday|friday] [--dry-run]")
        sys.exit(1)
    
    task_type = args[1]
    config = load_config()
    
    if task_type == "monday":
        for task in config["tasks"]:
            if task["update_type"] == "weekly_work_review":
                update_monday_doc(task, dry_run=dry_run)
                break
    elif task_type == "friday":
        for task in config["tasks"]:
            if task["update_type"] == "weekly_summary":
                update_friday_doc(task, dry_run=dry_run)
                break
    else:
        log(f"未知任务类型: {task_type}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
