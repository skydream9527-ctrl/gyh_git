#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每周工作总结脚本
定时执行：每周日 22:00
功能：
1. 汇总本周一到周日的每日工作回顾
2. 自动统计本周完成的工作、文件产出
3. 生成本周工作总结、下周计划模板
4. 更新WORK-PLAN.md中的完成项
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import re

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR.parent / "logs"
DAILY_DIR = BASE_DIR / "05-个人成长" / "每日记录"
WEEKLY_DIR = BASE_DIR / "05-个人成长" / "每周总结"
WORK_PLAN_PATH = BASE_DIR / "WORK-PLAN.md"

for d in [LOG_DIR, WEEKLY_DIR, DAILY_DIR]:
    d.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"weekly-review-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def get_week_dates(end_date=None):
    if end_date is None:
        end_date = datetime.now()
    start_date = end_date - timedelta(days=end_date.weekday())
    return start_date.date(), end_date.date()

def read_daily_reports(start_date, end_date):
    reports = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        file_path = DAILY_DIR / f"{date_str}-每日工作回顾.md"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                reports[date_str] = f.read()
        current_date += timedelta(days=1)
    return reports

def extract_completed_tasks(content):
    completed = []
    lines = content.split("\n")
    in_section = False
    for line in lines:
        if "今日完成工作" in line:
            in_section = True
            continue
        if in_section and line.startswith("---"):
            break
        if in_section:
            match = re.match(r"^- \[(x|X)\] (.+)$", line.strip())
            if match:
                completed.append(match.group(2).strip())
    return completed

def extract_key_decisions(content):
    decisions = []
    lines = content.split("\n")
    in_section = False
    for line in lines:
        if "关键决策" in line and "###" in line:
            in_section = True
            continue
        if in_section and (line.startswith("### ") or line.startswith("---")):
            break
        if in_section and line.strip().startswith("-"):
            decisions.append(line.strip().lstrip("- "))
    return decisions

def count_files(daily_content):
    count = 0
    in_table = False
    for line in daily_content.split("\n"):
        if "修改/新增文件" in line:
            in_table = True
            continue
        if in_table and line.startswith("---"):
            break
        if in_table and "|" in line and not "时间" in line and not "------" in line:
            if "无文件变更" not in line:
                count += 1
    return count

def generate_weekly_report(start_date, end_date, daily_reports):
    week_num = start_date.isocalendar()[1]
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    all_completed = []
    all_decisions = []
    total_files = 0
    daily_stats = []
    
    for date_str in sorted(daily_reports.keys()):
        content = daily_reports[date_str]
        completed = extract_completed_tasks(content)
        decisions = extract_key_decisions(content)
        files = count_files(content)
        all_completed.extend([(date_str, t) for t in completed])
        all_decisions.extend(decisions)
        total_files += files
        daily_stats.append((date_str, len(completed), files))
    
    template = f"""# {start_str} ~ {end_str} 第{week_num}周工作总结

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 周次：2026年第{week_num}周
> 状态：草稿（请补充完善）

---

## 📊 本周概览

| 指标 | 数值 |
|------|------|
| 覆盖天数 | {len(daily_reports)} 天 |
| 完成任务数 | {len(all_completed)} 项 |
| 新增/修改文件 | {total_files} 个 |
| 关键决策记录 | {len(all_decisions)} 条 |

### 每日统计
| 日期 | 完成任务 | 文件变更 |
|------|----------|----------|
"""
    for date_str, task_count, file_count in daily_stats:
        template += f"| {date_str} | {task_count} | {file_count} |\n"
    
    template += f"""
---

## ✅ 本周完成工作

### P0 核心任务完成
"""
    for date_str, task in all_completed:
        if task:
            template += f"- [{date_str}] {task}\n"
    
    if not all_completed:
        template += "- （请从每日记录中勾选已标记完成的任务）\n"
    
    template += f"""
### P1 任务完成
- 

### 临时/紧急任务完成
- 

---

## 📈 本周进展（按项目维度）

### ICE Data Workbench / nl-sql
- 

### TokenWisdom 探索
- 

### 数据分析需求
- 

### 其他工作
- 

---

## 💡 本周关键思考与决策

"""
    if all_decisions:
        for d in all_decisions:
            template += f"- {d}\n"
    else:
        template += "- \n"
    
    template += f"""
### 问题与解决
- 

### 方法论/知识点沉淀
- 

---

## 🚧 进行中工作与阻塞点
| 任务名称 | 当前进度 | 阻塞点 | 下周计划 |
|----------|----------|--------|----------|
| | | | |
| | | | |

---

## 📅 下周计划（{ (end_date + timedelta(days=1)).strftime('%Y-%m-%d') } ~ { (end_date + timedelta(days=7)).strftime('%Y-%m-%d') }）

### P0 必做任务
1. 
2. 
3. 

### P1 高优先级
1. 
2. 

---

## 🎯 绩效沉淀（周末填写）

### 战功（项目成果）素材
> 本周产出可用于季度战功总结的内容：
- 

### 内功（组织/方法/AI沉淀）素材
> 本周可用于内功总结的内容：
- 

### 可复用资产沉淀
> 本周完成后可沉淀到知识库的内容：
- 

---

## 🔄 文件更新清单
完成总结后需要更新：
- [ ] WORK-PLAN.md：标记已完成任务，更新下周计划
- [ ] MEMORY.md：更新关键决策、项目进展
- [ ] 绩效/过程素材：将本周战功/内功素材记录到绩效素材库

---

"""
    return template

def save_report(content, start_date, end_date):
    filename = f"{start_date.strftime('%Y-%m-%d')}-to-{end_date.strftime('%Y-%m-%d')}-周总结.md"
    file_path = WEEKLY_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    log(f"周总结已保存: {file_path}")
    return file_path

def main():
    today = datetime.now()
    if today.weekday() != 6:
        log(f"今天不是周日（周{today.weekday() + 1}），但仍生成本周总结", "WARN")
    
    start_date, end_date = get_week_dates(today)
    log(f"生成周总结: {start_date} ~ {end_date}")
    
    log("读取每日回顾...")
    daily_reports = read_daily_reports(start_date, end_date)
    log(f"读取到 {len(daily_reports)} 天的每日回顾")
    
    log("生成周总结...")
    report_content = generate_weekly_report(start_date, end_date, daily_reports)
    
    file_path = save_report(report_content, start_date, end_date)
    
    log("=" * 60)
    log("周总结已生成！")
    log(f"时间范围: {start_date} ~ {end_date}")
    log(f"文件位置: {file_path}")
    log("")
    log("下一步操作:")
    log("1. 打开周总结文件，补充完善内容")
    log("2. 填写完成工作、思考、下周计划")
    log("3. 标记绩效素材，沉淀到知识库")
    log("4. 完成后更新WORK-PLAN.md和MEMORY.md")
    log("=" * 60)
    
    print(f"\n✅ 周总结已生成: {file_path.name}")

if __name__ == "__main__":
    main()
