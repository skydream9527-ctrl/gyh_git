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
5. 自动抽取WORK-PLAN.md更新建议、绩效素材和决策记录草稿
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
DECISIONS_PATH = BASE_DIR / "DECISIONS.md"

TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".sql", ".html", ".css", ".sh", ".csv", ".toml", ".ini"
}
MAX_SIGNAL_FILE_BYTES = 200_000

IGNORE_DIRS = {
    ".git", ".trae", ".micode", ".playwright-cli", ".vscode",
    "node_modules", "__pycache__", ".venv", "venv",
    "07-定时任务/logs", "07-定时任务/reports"
}

IGNORE_EXTENSIONS = {".pyc", ".log", ".tmp", ".swp", ".DS_Store"}

FOCUS_RULES = [
    {
        "name": "nl-sql自然语言取数",
        "priority": "P0",
        "keywords": ["nl-sql", "nl_sql", "nlmapping", "nl-mapping", "mapping", "核心指标", "数据资产", "reference"]
    },
    {
        "name": "ICE Data Workbench / AI工作台",
        "priority": "P0/P1",
        "keywords": ["ice-data-workbench", "ice workbench", "ice-workbench", "workbench", "agent", "skill"]
    },
    {
        "name": "核心看板与日常数据需求",
        "priority": "P0",
        "keywords": ["看板", "周报", "驾驶舱", "财收", "dau", "日报", "监控"]
    },
    {
        "name": "数据分析交付",
        "priority": "P0/P1",
        "keywords": ["03-数据分析", "分析报告", "sql查询", "retention", "留存", "迁移", "实验"]
    },
    {
        "name": "工作记录与工作流自动化",
        "priority": "内功",
        "keywords": ["daily_work_review", "weekly_work_review", "workflows", "current.md", "decisions.md", "memory.md", "agents.md"]
    },
]

TASK_SIGNAL_KEYWORDS = ["- [ ]", "TODO", "待办", "下一步", "阻塞", "进行中", "P0", "P1"]
DECISION_SIGNAL_KEYWORDS = ["关键决策", "决策", "决定", "取舍", "明确不做", "风险", "回看", "原则"]
KNOWLEDGE_SIGNAL_KEYWORDS = ["知识点", "方法论", "沉淀", "模板", "复用", "踩坑"]

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

def unique_items(items, limit=None):
    seen = set()
    result = []
    for item in items:
        normalized = " ".join(str(item).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
        if limit and len(result) >= limit:
            break
    return result

def format_checklist(items, empty_text="暂无自动抽取建议，请手动补充"):
    if not items:
        return f"- [ ] {empty_text}\n"
    return "".join(f"- [ ] {item}\n" for item in items)

def path_text(path_value):
    return str(path_value).replace("\\", "/")

def is_text_candidate(file_path: Path):
    return file_path.suffix.lower() in TEXT_EXTENSIONS and file_path.stat().st_size <= MAX_SIGNAL_FILE_BYTES

def read_changed_text(rel_path):
    file_path = BASE_DIR / rel_path
    try:
        if not file_path.exists() or not file_path.is_file() or not is_text_candidate(file_path):
            return ""
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log(f"读取文本信号失败 {rel_path}: {e}", "WARN")
        return ""

def extract_signal_lines(modified_files, keywords, max_files=8, max_lines_per_file=2):
    signals = []
    for file_info in modified_files:
        rel_path = file_info["path"]
        text = read_changed_text(rel_path)
        if not text:
            continue
        matched_in_file = 0
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) > 220:
                continue
            if any(keyword.lower() in stripped.lower() for keyword in keywords):
                signals.append(f"`{rel_path}`：{stripped}")
                matched_in_file += 1
                if matched_in_file >= max_lines_per_file:
                    break
        if len(signals) >= max_files:
            break
    return unique_items(signals, max_files)

def infer_focus_matches(modified_files, commits):
    evidence = {rule["name"]: [] for rule in FOCUS_RULES}
    haystacks = []
    for file_info in modified_files:
        haystacks.append((file_info["path"], file_info["path"]))
    for commit in commits:
        haystacks.append((f"commit {commit['hash']}", commit["message"]))

    for label, value in haystacks:
        value_lower = value.lower()
        for rule in FOCUS_RULES:
            if any(keyword.lower() in value_lower for keyword in rule["keywords"]):
                evidence[rule["name"]].append(label)

    matches = []
    for rule in FOCUS_RULES:
        items = unique_items(evidence[rule["name"]], 3)
        if items:
            matches.append({
                "name": rule["name"],
                "priority": rule["priority"],
                "evidence": items
            })
    return matches

def infer_performance_materials(modified_files, commits):
    win_items = []
    capability_items = []
    changed_paths = [path_text(item["path"]) for item in modified_files]
    commit_messages = [commit["message"] for commit in commits]

    if any(path.startswith("01-业务项目/ICE-Data-Workbench-v3") for path in changed_paths):
        win_items.append("ICE Data Workbench / AI工作台有实质推进，可沉淀为平台化建设战功素材")
    if any(path.startswith("01-业务项目/TokenWisdom") for path in changed_paths):
        win_items.append("TokenWisdom 产品方案或原型有迭代，可沉淀为 AI Native 产品探索素材")
    if any(path.startswith("03-数据分析/") for path in changed_paths):
        win_items.append("数据分析 SQL/报告/数据源有新增或修改，可沉淀为业务数据支撑战功素材")
    if any("分析报告" in path or "PRD" in path or "design" in path.lower() for path in changed_paths):
        win_items.append("今日有报告/PRD/设计稿类产出，建议补充业务背景、交付对象和影响")

    if any(path.startswith("00-知识库/") for path in changed_paths):
        capability_items.append("知识库有新增或更新，可沉淀为方法论/知识复用内功素材")
    if any(path.startswith("07-定时任务/") for path in changed_paths):
        capability_items.append("定时任务或自动化脚本有更新，可沉淀为个人工作流自动化内功素材")
    if any(path.startswith("02-Skill开发/") for path in changed_paths):
        capability_items.append("Skill 开发资产有更新，可沉淀为 AI 能力建设内功素材")
    if any(path in {"AGENTS.md", "USER.md", "CURRENT.md", "DECISIONS.md", "WORKFLOWS.md", "MEMORY.md", "WORK-PLAN.md"} for path in changed_paths):
        capability_items.append("工作区入口/记忆/计划文件有更新，可沉淀为工作 Agent 化方法论素材")
    if any("自动" in message or "agent" in message.lower() or "skill" in message.lower() for message in commit_messages):
        capability_items.append("提交记录涉及自动化/Agent/Skill，可补充 AI 提效方式和复用价值")

    return {
        "wins": unique_items(win_items, 6),
        "capabilities": unique_items(capability_items, 6),
    }

def build_auto_insights(modified_files, commits):
    focus_matches = infer_focus_matches(modified_files, commits)
    task_signals = extract_signal_lines(modified_files, TASK_SIGNAL_KEYWORDS)
    decision_signals = extract_signal_lines(modified_files, DECISION_SIGNAL_KEYWORDS)
    knowledge_signals = extract_signal_lines(modified_files, KNOWLEDGE_SIGNAL_KEYWORDS, max_files=6)
    performance = infer_performance_materials(modified_files, commits)

    work_plan_updates = []
    for match in focus_matches:
        evidence = "、".join(f"`{item}`" for item in match["evidence"])
        work_plan_updates.append(
            f"更新 `{match['name']}`（{match['priority']}）的进度/下一步；证据：{evidence}"
        )
    for signal in task_signals[:5]:
        work_plan_updates.append(f"检查是否新增或更新待办：{signal}")

    memory_updates = []
    if focus_matches:
        focus_names = "、".join(match["name"] for match in focus_matches[:3])
        memory_updates.append(f"如今日推进改变项目状态，更新 `MEMORY.md` 对应项目进展：{focus_names}")
    for signal in knowledge_signals[:3]:
        memory_updates.append(f"如该内容可长期复用，更新 `MEMORY.md` 或知识库索引：{signal}")

    decision_records = []
    for signal in decision_signals[:6]:
        decision_records.append(f"确认是否写入 `DECISIONS.md`：{signal}")
    if any(item["path"] in {"CURRENT.md", "WORK-PLAN.md", "DECISIONS.md", "MEMORY.md", "AGENTS.md", "WORKFLOWS.md"} for item in modified_files):
        decision_records.append("工作区规则/当前重点/计划或记忆发生变更，确认是否补充决策背景、影响和回看时间")
    if any("不做" in item or "取舍" in item or "优先" in item for item in decision_records):
        decision_records.append("涉及优先级或不做清单变化，建议同步更新 `CURRENT.md` 和 `WORK-PLAN.md`")

    return {
        "work_plan_updates": unique_items(work_plan_updates, 10),
        "memory_updates": unique_items(memory_updates, 8),
        "performance_wins": performance["wins"],
        "performance_capabilities": performance["capabilities"],
        "decision_records": unique_items(decision_records, 8),
    }

def generate_daily_report(date_str: str, modified_files, commits, auto_insights=None):
    if auto_insights is None:
        auto_insights = build_auto_insights(modified_files, commits)

    template = f"""# {date_str} 每日工作回顾

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 状态：草稿（请补充飞书交互信息和工作总结）
> 自动抽取说明：以下建议基于今日文件变更、Git提交和关键词启发式生成，需人工确认后再回写正式文件。

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
{format_checklist(auto_insights['decision_records'], '暂无自动抽取的决策记录，请手动补充')}

### 问题与解决
-

### 知识点/方法论沉淀
{format_checklist(auto_insights['memory_updates'], '暂无自动抽取的知识/记忆更新建议，请手动补充')}

---

## 📈 绩效更新建议

### 战功（项目成果）更新点
> 标记今日工作中可纳入战功总结的内容：
{format_checklist(auto_insights['performance_wins'], '暂无自动抽取的战功素材，请手动补充')}

### 内功（组织/方法/AI沉淀）更新点
> 标记今日工作中可纳入内功总结的内容：
{format_checklist(auto_insights['performance_capabilities'], '暂无自动抽取的内功素材，请手动补充')}

---

## 🔄 文件更新建议

### MEMORY.md 需要更新的内容
{format_checklist(auto_insights['memory_updates'], '暂无自动抽取的 MEMORY.md 更新建议')}

### WORK-PLAN.md 需要更新的内容
{format_checklist(auto_insights['work_plan_updates'], '暂无自动抽取的 WORK-PLAN.md 更新建议')}

### DECISIONS.md 需要更新的内容
{format_checklist(auto_insights['decision_records'], '暂无自动抽取的 DECISIONS.md 更新建议')}

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

    log("自动抽取计划、绩效和决策建议...")
    auto_insights = build_auto_insights(modified_files, commits)
    log(f"WORK-PLAN建议 {len(auto_insights['work_plan_updates'])} 条，绩效素材 {len(auto_insights['performance_wins']) + len(auto_insights['performance_capabilities'])} 条，决策记录 {len(auto_insights['decision_records'])} 条")

    log("生成回顾报告...")
    report_content = generate_daily_report(date_str, modified_files, commits, auto_insights)

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
    log("2. 逐条确认自动抽取的WORK-PLAN、绩效素材和决策记录")
    log("3. 补充完成后，告知Agent回写MEMORY.md、WORK-PLAN.md和DECISIONS.md")
    log("=" * 60)

    print(f"\n✅ 每日回顾已生成: {date_str}-每日工作回顾.md")
    print(f"请打开文件确认自动抽取建议并补充手动内容，完成后我可以帮你回写相关文件。")

if __name__ == "__main__":
    main()
