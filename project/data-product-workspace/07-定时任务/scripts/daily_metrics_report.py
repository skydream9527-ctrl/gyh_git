#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日核心指标监控报表
定时执行：查询核心指标 -> 对比昨日/上周 -> 生成报表 -> 推送飞书
"""
import os
import sys
import json
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "config.json"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

for d in [LOG_DIR, REPORT_DIR]:
    d.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_config():
    if not CONFIG_PATH.exists():
        log(f"配置文件不存在: {CONFIG_PATH}", "ERROR")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

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
            webhook_url,
            data=data,
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

def query_metric(sql, date_str):
    """
    执行SQL查询，返回单个指标值
    这里可以根据实际情况替换为kyuubi/sql skill调用
    """
    sql = sql.replace("{{date}}", date_str)
    log(f"执行SQL: {sql[:200]}...")
    
    # TODO: 实际接入时替换为真实数据库查询
    # 示例返回模拟数据（真实业务场景量级）
    import random
    base_dau = 10500000
    base_duration = 42
    base_ctr = 0.112
    base_retention = 0.38
    
    if "DAU" in sql.upper():
        return round(base_dau * random.uniform(0.95, 1.05), 0)
    elif "时长" in sql or "duration" in sql.lower():
        return round(base_duration * random.uniform(0.97, 1.03), 2)
    elif "ctr" in sql.lower() or "点击" in sql:
        return round(base_ctr * random.uniform(0.98, 1.02), 4)
    elif "留存" in sql or "retention" in sql.lower():
        return round(base_retention * random.uniform(0.99, 1.01), 4)
    else:
        return round(random.uniform(0, 100), 2)

def calc_change(current, previous):
    if previous == 0:
        return 0
    return (current - previous) / previous

def format_value(value, unit="", decimal_places=2):
    if unit == "%":
        return f"{value * 100:.{decimal_places}f}%"
    elif unit == "分钟":
        return f"{value:.{decimal_places}f}分钟"
    else:
        if value >= 10000:
            return f"{value/10000:.2f}万"
        return f"{value:.{decimal_places}f}"

def build_feishu_card(report_date, metrics_data, config):
    elements = []
    
    header_text = f"**报告日期**: {report_date}\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": header_text}
    })
    elements.append({"tag": "hr"})
    
    table_header = "**指标** | **今日值** | **日环比** | **周同比**\n---|---|---|---"
    table_rows = []
    alert_metrics = []
    
    for m in metrics_data:
        name = m["name"]
        current = m["current"]
        d_change = m.get("d_change", 0)
        w_change = m.get("w_change", 0)
        unit = m.get("unit", "")
        threshold = m.get("alert_threshold", -1)
        
        d_icon = "🔴" if d_change < threshold else "🟢" if d_change > 0 else "🟡"
        w_icon = "🔴" if w_change < threshold else "🟢" if w_change > 0 else "🟡"
        
        current_str = format_value(current, unit, m.get("decimal_places", 2))
        d_str = f"{d_change*100:+.2f}% {d_icon}"
        w_str = f"{w_change*100:+.2f}% {w_icon}"
        
        table_rows.append(f"{name} | {current_str} | {d_str} | {w_str}")
        
        if d_change < threshold or w_change < threshold:
            alert_metrics.append(name)
    
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": table_header + "\n" + "\n".join(table_rows)}
    })
    
    if alert_metrics and config["alert"]["enabled"]:
        elements.append({"tag": "hr"})
        alert_text = "⚠️ **异常告警**: 以下指标波动超过阈值：\n" + "\n".join([f"- {m}" for m in alert_metrics])
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": alert_text}
        })
    
    at_text = ""
    if config["feishu"].get("at_all"):
        at_text = "<at id=all></at>"
    elif config["feishu"].get("at_users"):
        at_users = " ".join([f"<at id={uid}></at>" for uid in config["feishu"]["at_users"]])
        at_text = at_users
    if at_text:
        elements.append({"tag": "hr"})
        elements.append({"tag": "note", "elements": [{"tag": "lark_md", "content": at_text}]})
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": config["report"]["title"]},
            "template": "blue" if not alert_metrics else "red"
        },
        "elements": elements
    }
    return card

def save_markdown_report(report_date, metrics_data, config):
    md_path = REPORT_DIR / f"{report_date}-每日核心指标报告.md"
    lines = [
        f"# 📊 每日核心指标监控日报",
        f"",
        f"**报告日期**: {report_date}",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 核心指标",
        f"",
        f"| 指标 | 今日值 | 日环比 | 周同比 | 阈值告警 |",
        f"|------|--------|--------|--------|----------|"
    ]
    
    for m in metrics_data:
        name = m["name"]
        current = m["current"]
        d_change = m.get("d_change", 0)
        w_change = m.get("w_change", 0)
        unit = m.get("unit", "")
        threshold = m.get("alert_threshold", -1)
        
        current_str = format_value(current, unit, m.get("decimal_places", 2))
        d_str = f"{d_change*100:+.2f}%"
        w_str = f"{w_change*100:+.2f}%"
        alert = "🔴 异常" if d_change < threshold or w_change < threshold else "🟢 正常"
        
        lines.append(f"| {name} | {current_str} | {d_str} | {w_str} | {alert} |")
    
    lines.extend([
        f"",
        f"## 说明",
        f"",
        f"- 日环比：与昨日数据对比",
        f"- 周同比：与上周同日数据对比",
        f"- 🔴 表示指标下跌超过告警阈值",
        f"",
        f"---",
        f"*本报告由AI自动生成*"
    ])
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Markdown报告已保存: {md_path}")
    return md_path

def main():
    log("=== 开始执行每日核心指标监控任务 ===")
    config = load_config()
    
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    log(f"报告日期: {today}, 对比昨日: {yesterday}, 对比上周: {last_week}")
    
    metrics_data = []
    for metric in config["metrics"]:
        try:
            current = query_metric(metric["sql"], today)
            data = {"name": metric["name"], "current": current, 
                    "unit": metric.get("unit", ""), 
                    "decimal_places": metric.get("decimal_places", 2),
                    "alert_threshold": metric.get("alert_threshold", -1)}
            
            if metric.get("compare_yesterday", True):
                prev_d = query_metric(metric["sql"], yesterday)
                data["yesterday"] = prev_d
                data["d_change"] = calc_change(current, prev_d)
            
            if metric.get("compare_last_week", True):
                prev_w = query_metric(metric["sql"], last_week)
                data["last_week"] = prev_w
                data["w_change"] = calc_change(current, prev_w)
            
            metrics_data.append(data)
            log(f"指标 {metric['name']}: {current}")
        except Exception as e:
            log(f"查询指标 {metric['name']} 失败: {str(e)}", "ERROR")
    
    if config["report"].get("save_markdown", True):
        save_markdown_report(today, metrics_data, config)
    
    card = build_feishu_card(today, metrics_data, config)
    
    if config["feishu"].get("webhook_url"):
        send_feishu_message(config["feishu"]["webhook_url"], card, config["feishu"].get("secret", ""))
    
    log("=== 任务执行完成 ===")

if __name__ == "__main__":
    main()
