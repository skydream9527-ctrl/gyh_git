#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日工作回顾脚本
定时执行：每天23:00
功能：
1. 扫描当天工作目录新增/修改的文件
2. 生成每日工作总结模板
3. 多位置备份（个人成长/会议纪要/临时文件）
4. 提示手动补充飞书交互信息
5. 提供MEMORY.md和WORK-PLAN.md更新建议
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "daily_review_config.json"
LOG_DIR = SCRIPT_DIR.parent / "logs"

OUTPUT_DIRS = [
    BASE_DIR / "05-个人成长" / "每日记录",
    BASE_DIR / "04-会议纪要" / "每日回顾",
    BASE_DIR / "99-临时文件" / "每日回顾",
]

MEMORY_PATH = BASE_DIR / "MEMORY.md"
WORK_PLAN_PATH = BASE_DIR / "WORK-PLAN.md"

IGNORE_DIRS = {
    ".git", ".trae", ".micode", ".playwright-cli", ".vscode",
    "node_modules", "__pycache__", ".venv", "venv",
    "07-定时任务/logs", "07-定时任务/reports"
}

IGNORE_EXTENSIONS = {".pyc", ".log", ".tmp", ".swp", ".DS_Store"}

for d in [LOG_DIR] + OUTPUT_DIRS:
    d.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"daily-review-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_config():
    default_config = {
        "scan_directories": [
            "00-知识库",
            "01-业务项目",
            "02-Skill开发",
            "03-数据分析",
            "04-会议纪要",
            "05-个人成长",
            "07-定时任务"
        ],
        "feishu_webhook": ""
    }
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        log(f"已创建默认配置文件: {CONFIG_PATH}")
        return default_config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def should_ignore(path: Path) -> bool:
    path_str = str(path.relative_to(BASE_DIR))
    for ignore_dir in IGNORE_DIRS:
        if path_str.startswith(ignore_dir) or f"/{ignore_dir}/" in path_str:
            return True
    if path.suffix in IGNORE_EXTENSIONS:
        return True
    return False

def get_today_modified_files(target_date: datetime = None):
    if target_date is None:
        target_date = datetime.now()
    today = target_date.date()
    modified_files = []
    
    scan_dirs = load_config().get("scan_directories", [])
    
    for scan_dir in scan_dirs:
        dir_path = BASE_DIR / scan_dir
        if not dir_path.exists():
            continue
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not should_ignore(Path(root) / d)]
            for file in files:
                if file.startswith("."):
                    continue
                file_path = Path(root) / file
                if should_ignore(file_path):
                    continue
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime.date() == today:
                        rel_path = file_path.relative_to(BASE_DIR)
                        modified_files.append({
                            "path": str(rel_path),
                            "modified_time": mtime.strftime("%H:%M:%S"),
                            "size": file_path.stat().st_size
                        })
                except Exception as e:
                    log(f"读取文件信息失败 {file_path}: {e}", "WARN")
    
    modified_files.sort(key=lambda x: x["modified_time"])
    return modified_files

def get_git_commits(target_date: datetime = None):
    if target_date is None:
        target_date = datetime.now()
    today_str = target_date.strftime("%Y-%m-%d")
    commits = []
    try:
        result = subprocess.run(
            ["git", "log", f"--since={today_str} 00:00:00", f"--until={today_str} 23:59:59",
             "--pretty=format:%h|%s|%H", "--no-merges"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split("|", 2)
                if len(parts) >= 2:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1]
                    })
    except Exception as e:
        log(f"获取Git提交记录失败: {e}", "WARN")
    return commits

def generate_daily_report(date_str: str, modified_files, commits):
    template = f"""# {date_str} 每日工作回顾

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 状态：草稿（请补充飞书交互信息和工作总结）

---

## 📊 今日文件变更（自动扫描）

### 修改/新增文件
| 时间 | 文件路径 | 备注 |
|------|----------|------|
"""
    for f in modified_files:
        template += f"| {f['modified_time']} | {f['path']} | |\n"
    
    if not modified_files:
        template += "| - | 无文件变更 | |\n"
    
    template += f"""
### Git提交记录
"""
    if commits:
        for commit in commits:
            template += f"- [{commit['hash']}] {commit['message']}\n"
    else:
        template += "- 今日无Git提交\n"
    
    template += f"""
---

## 💬 飞书交互信息（手动补充）

请在此处粘贴今日飞书消息梳理内容（飞书总结会单独发送）：

```
【在此粘贴飞书交互摘要】
```

### 关键沟通记录
| 沟通对象 | 沟通主题 | 结论/待办 |
|----------|----------|-----------|
| | | |
| | | |
| | | |

---

## ✅ 今日完成工作

### P0 核心任务完成
- [ ] 
- [ ] 

### P1 任务完成
- [ ] 
- [ ] 

### 其他工作
- [ ] 
- [ ] 

---

## 🚧 进行中工作
| 任务名称 | 当前进度 | 下一步计划 | 阻塞点 |
|----------|----------|------------|--------|
| | | | |
| | | | |

---

## 📅 明日计划

### 必做（P0）
1. 
2. 

### 待办（P1）
1. 
2. 

---

## 💡 今日思考与收获

### 关键决策
- 

### 问题与解决
- 

### 知识点/方法论沉淀
- 

---

## 📈 绩效更新建议

### 战功（项目成果）更新点
> 标记今日工作中可纳入战功总结的内容：
- 

### 内功（组织/方法/AI沉淀）更新点
> 标记今日工作中可纳入内功总结的内容：
- 

---

## 🔄 文件更新建议

### MEMORY.md 需要更新的内容
- [ ] 关键决策记录
- [ ] 项目进展更新
- [ ] 新增知识点

### WORK-PLAN.md 需要更新的内容
- [ ] 已完成任务标记为完成
- [ ] 新增待办任务
- [ ] 进行中任务进度更新

---

*注：补充完成后，请执行更新脚本同步更新MEMORY.md和WORK-PLAN.md*
"""
    return template

def save_report(content: str, date_str: str):
    filename = f"{date_str}-每日工作回顾.md"
    saved_paths = []
    for output_dir in OUTPUT_DIRS:
        file_path = output_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        saved_paths.append(str(file_path))
        log(f"已保存: {file_path}")
    return saved_paths

def main():
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    
    log(f"开始生成 {date_str} 每日工作回顾")
    
    log("扫描今日文件变更...")
    modified_files = get_today_modified_files(today)
    log(f"发现 {len(modified_files)} 个变更文件")
    
    log("获取Git提交记录...")
    commits = get_git_commits(today)
    log(f"发现 {len(commits)} 条Git提交")
    
    log("生成回顾报告...")
    report_content = generate_daily_report(date_str, modified_files, commits)
    
    log("保存报告...")
    saved_paths = save_report(report_content, date_str)
    
    log("=" * 60)
    log("每日工作回顾已生成！")
    log(f"日期: {date_str}")
    log(f"文件变更数: {len(modified_files)}")
    log(f"Git提交数: {len(commits)}")
    log("保存位置:")
    for p in saved_paths:
        log(f"  - {p}")
    log("")
    log("下一步操作:")
    log("1. 打开报告文件，补充飞书交互信息和完成的工作内容")
    log("2. 填写今日思考、绩效更新点")
    log("3. 补充完成后，告知Agent更新MEMORY.md和WORK-PLAN.md")
    log("=" * 60)
    
    print(f"\n✅ 每日回顾已生成: {date_str}-每日工作回顾.md")
    print(f"请打开文件补充手动内容，完成后我可以帮你更新相关文件。")

if __name__ == "__main__":
    main()
