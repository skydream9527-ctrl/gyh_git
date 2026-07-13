#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库活跃度体检
可手动运行或每月 cron
功能：
1. 扫描 00-知识库/ 各子域
2. 统计文件数、大小、最近修改时间、活跃文件数
3. 检查跨域引用
4. 检查 README.md 是否存在及更新时间
5. 生成健康度评级和建议报告
"""
import os
import sys
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "kb_health_config.json"
LOG_DIR = SCRIPT_DIR.parent / "logs"
REPORT_DIR = SCRIPT_DIR.parent / "reports"

for d in [LOG_DIR, REPORT_DIR]:
    d.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"kb-health-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_config():
    default_config = {
        "kb_root": "00-知识库",
        "active_days": 30,
        "dormant_days": 90,
        "report_output_dir": "07-定时任务/reports",
        "ignore_patterns": ["*.pyc", "*.log", "*.tmp", ".DS_Store", "__pycache__"],
        "min_files_for_domain": 1,
        "check_readme": True,
        "check_cross_refs": True,
        "five_dimensions": ["concepts", "methods", "pitfalls", "cases", "templates"]
    }
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        log(f"已创建默认配置: {CONFIG_PATH}")
        return default_config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def should_ignore(filename, ignore_patterns):
    """检查文件是否应跳过"""
    for pattern in ignore_patterns:
        if pattern.startswith("*."):
            if filename.endswith(pattern[1:]):
                return True
        elif filename == pattern:
            return True
    return False


def scan_domain(domain_path, ignore_patterns, active_days, dormant_days):
    """扫描单个知识域，返回统计数据"""
    now = datetime.now()
    active_cutoff = (now - timedelta(days=active_days)).timestamp()
    dormant_cutoff = (now - timedelta(days=dormant_days)).timestamp()

    stats = {
        "name": domain_path.name,
        "path": str(domain_path.relative_to(BASE_DIR)),
        "total_files": 0,
        "total_size": 0,
        "newest_mtime": 0,
        "oldest_mtime": float('inf'),
        "active_files": 0,       # 近 active_days 天修改
        "dormant_files": 0,      # active_days ~ dormant_days 天
        "zombie_files": 0,       # > dormant_days 天
        "has_readme": False,
        "readme_mtime": None,
        "has_overview": False,
        "subdirs": [],
        "file_types": defaultdict(int),
        "md_files": 0,
    }

    if not domain_path.is_dir():
        return stats

    for root, dirs, files in os.walk(domain_path):
        # 跳过隐藏目录和 __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        for f in files:
            if should_ignore(f, ignore_patterns):
                continue

            fpath = Path(root) / f
            try:
                fstat = fpath.stat()
                fsize = fstat.st_size
                fmtime = fstat.st_mtime
            except OSError:
                continue

            stats["total_files"] += 1
            stats["total_size"] += fsize
            stats["newest_mtime"] = max(stats["newest_mtime"], fmtime)
            if fmtime < stats["oldest_mtime"]:
                stats["oldest_mtime"] = fmtime

            # 活跃度分类
            if fmtime >= active_cutoff:
                stats["active_files"] += 1
            elif fmtime >= dormant_cutoff:
                stats["dormant_files"] += 1
            else:
                stats["zombie_files"] += 1

            # 文件类型
            ext = fpath.suffix.lower()
            stats["file_types"][ext] += 1
            if ext == ".md":
                stats["md_files"] += 1

            # README/OVERVIEW
            if f.lower() == "readme.md" and Path(root) == domain_path:
                stats["has_readme"] = True
                stats["readme_mtime"] = fmtime
            if f.lower() == "overview.md" and Path(root) == domain_path:
                stats["has_overview"] = True

    # 子目录列表
    if domain_path.is_dir():
        stats["subdirs"] = [d.name for d in domain_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

    # 修正 oldest_mtime
    if stats["oldest_mtime"] == float('inf'):
        stats["oldest_mtime"] = 0

    return stats


def count_cross_refs(kb_root, domain_name):
    """统计其他域对该域的引用次数"""
    ref_count = 0
    search_patterns = [domain_name, domain_name.replace('-', '_')]

    for root, dirs, files in os.walk(kb_root):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        current_domain = Path(root).relative_to(kb_root).parts[0] if Path(root) != kb_root else ""

        if current_domain == domain_name:
            continue  # 跳过自引用

        for f in files:
            if not f.endswith('.md'):
                continue
            fpath = Path(root) / f
            try:
                if fpath.stat().st_size > 500_000:
                    continue  # 跳过大文件
                content = fpath.read_text(encoding="utf-8", errors="replace")
                for pattern in search_patterns:
                    ref_count += content.count(pattern)
            except Exception:
                continue

    return ref_count


def rate_health(stats, active_days, dormant_days):
    """评估域健康度"""
    if stats["total_files"] == 0:
        return "⚫", "空域", "建议删除或合并到相关域"

    if stats["active_files"] > 0:
        ratio = stats["active_files"] / stats["total_files"]
        if ratio > 0.3:
            return "🟢", "活跃", ""
        else:
            return "🟢", "活跃（低比例）", f"仅 {stats['active_files']}/{stats['total_files']} 文件近 {active_days} 天有修改"

    if stats["dormant_files"] > 0:
        return "🟡", "休眠", f"最近 {active_days} 天无修改，但 {dormant_days} 天内有 {stats['dormant_files']} 个文件活跃"

    return "🔴", "僵尸", f"超过 {dormant_days} 天无任何文件修改，建议归档或合并"


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_time(timestamp):
    """格式化时间戳"""
    if timestamp == 0:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def generate_report(all_stats, cross_refs, date_str, config):
    """生成体检报告"""
    active_days = config.get("active_days", 30)
    dormant_days = config.get("dormant_days", 90)

    total_files = sum(s["total_files"] for s in all_stats)
    total_size = sum(s["total_size"] for s in all_stats)
    active_count = sum(1 for s in all_stats if s["active_files"] > 0)
    zombie_count = sum(1 for s in all_stats if s["active_files"] == 0 and s["dormant_files"] == 0 and s["total_files"] > 0)

    report = f"""# 知识库活跃度体检报告（{date_str}）

> 自动生成，体检范围：`{config.get('kb_root', '00-知识库')}/`
> 活跃阈值：{active_days} 天 | 休眠阈值：{dormant_days} 天

## 📊 总览

| 指标 | 数值 |
|------|------|
| 知识域总数 | {len(all_stats)} |
| 文件总数 | {total_files} |
| 总大小 | {format_size(total_size)} |
| 活跃域 | {active_count} 🟢 |
| 休眠域 | {sum(1 for s in all_stats if s['active_files'] == 0 and s['dormant_files'] > 0)} 🟡 |
| 僵尸域 | {zombie_count} 🔴 |

---

## 📋 各域详情

| 域名 | 健康度 | 文件数 | 大小 | 最近修改 | 活跃/休眠/僵尸 | README | 被引用 | 建议 |
|------|--------|--------|------|----------|----------------|--------|--------|------|
"""

    for s in all_stats:
        emoji, label, suggestion = rate_health(s, active_days, dormant_days)
        readme_status = "✅" if s["has_readme"] else "❌"
        refs = cross_refs.get(s["name"], 0)
        report += (
            f"| `{s['name']}` | {emoji} {label} | {s['total_files']} | {format_size(s['total_size'])} "
            f"| {format_time(s['newest_mtime'])} | {s['active_files']}/{s['dormant_files']}/{s['zombie_files']} "
            f"| {readme_status} | {refs} | {suggestion} |\n"
        )

    report += "\n---\n\n"

    # 详细分析
    report += "## 🔍 重点关注\n\n"

    # 僵尸域
    zombies = [s for s in all_stats if s["active_files"] == 0 and s["dormant_files"] == 0 and s["total_files"] > 0]
    if zombies:
        report += "### 🔴 僵尸域（建议归档或合并）\n\n"
        for s in zombies:
            report += f"- **{s['name']}**：{s['total_files']} 个文件，最近修改 {format_time(s['newest_mtime'])}，被引用 {cross_refs.get(s['name'], 0)} 次\n"
            if cross_refs.get(s["name"], 0) > 0:
                report += f"  → 仍有跨域引用，建议保留但标记为归档\n"
            else:
                report += f"  → 无跨域引用，可考虑合并到相关域或移入 `06-归档/`\n"
        report += "\n"

    # 缺少 README 的域
    no_readme = [s for s in all_stats if not s["has_readme"] and s["total_files"] > 0]
    if no_readme:
        report += "### ❌ 缺少 README.md\n\n"
        for s in no_readme:
            report += f"- `{s['name']}/` — {s['total_files']} 个文件，建议添加 README.md 作为导航索引\n"
        report += "\n"

    # 大文件域（参考资料可能需要瘦身）
    big_domains = [s for s in all_stats if s["total_files"] > 100]
    if big_domains:
        report += "### 📦 大规模域（>100 文件）\n\n"
        for s in big_domains:
            top_types = sorted(s["file_types"].items(), key=lambda x: -x[1])[:3]
            types_str = "、".join(f"{ext}({cnt})" for ext, cnt in top_types)
            report += f"- **{s['name']}**：{s['total_files']} 文件，{format_size(s['total_size'])}，主要类型：{types_str}\n"
        report += "\n"

    # 活跃域
    active_domains = [s for s in all_stats if s["active_files"] > 0]
    if active_domains:
        report += "### 🟢 活跃域\n\n"
        for s in sorted(active_domains, key=lambda x: -x["active_files"]):
            report += f"- **{s['name']}**：近 {active_days} 天修改 {s['active_files']} 个文件，最近修改 {format_time(s['newest_mtime'])}\n"
        report += "\n"

    # 建议动作
    report += "---\n\n## 💡 建议动作\n\n"
    actions = []
    if zombies:
        actions.append(f"1. 清理 {len(zombies)} 个僵尸域：{', '.join(s['name'] for s in zombies)}")
    if no_readme:
        actions.append(f"{'2' if actions else '1'}. 为 {len(no_readme)} 个域补充 README.md")
    if big_domains:
        actions.append(f"{'3' if len(actions) >= 2 else str(len(actions)+1)}. 检查大规模域是否需要拆分子域")

    if actions:
        for a in actions:
            report += f"{a}\n"
    else:
        report += "知识库整体健康，无需紧急处理。\n"

    report += f"\n---\n\n*体检时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    return report


def main():
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    log(f"开始知识库活跃度体检: {date_str}")

    config = load_config()
    kb_root = BASE_DIR / config.get("kb_root", "00-知识库")
    ignore_patterns = config.get("ignore_patterns", [])
    active_days = config.get("active_days", 30)
    dormant_days = config.get("dormant_days", 90)

    if not kb_root.exists():
        log(f"知识库根目录不存在: {kb_root}", "ERROR")
        sys.exit(1)

    # 扫描各域
    all_stats = []
    domains = sorted([d for d in kb_root.iterdir() if d.is_dir() and not d.name.startswith('.')])

    log(f"发现 {len(domains)} 个知识域")

    for domain in domains:
        log(f"扫描: {domain.name}")
        stats = scan_domain(domain, ignore_patterns, active_days, dormant_days)
        all_stats.append(stats)
        log(f"  文件: {stats['total_files']}, 活跃: {stats['active_files']}, 僵尸: {stats['zombie_files']}")

    # 统计跨域引用
    cross_refs = {}
    if config.get("check_cross_refs", True):
        log("统计跨域引用...")
        for stats in all_stats:
            refs = count_cross_refs(kb_root, stats["name"])
            cross_refs[stats["name"]] = refs
            if refs > 0:
                log(f"  {stats['name']} 被引用 {refs} 次")

    # 生成报告
    log("生成体检报告...")
    report = generate_report(all_stats, cross_refs, date_str, config)

    report_path = REPORT_DIR / f"{date_str}-知识库体检报告.md"
    report_path.write_text(report, encoding="utf-8")
    log(f"体检报告已保存: {report_path}")

    # 输出摘要
    log("=" * 60)
    log(f"知识库体检完成！")
    log(f"知识域: {len(all_stats)}")
    log(f"总文件: {sum(s['total_files'] for s in all_stats)}")
    log(f"活跃域: {sum(1 for s in all_stats if s['active_files'] > 0)} 🟢")
    log(f"僵尸域: {sum(1 for s in all_stats if s['active_files'] == 0 and s['dormant_files'] == 0 and s['total_files'] > 0)} 🔴")
    log(f"报告: {report_path}")
    log("=" * 60)

    print(f"\n🏥 知识库体检完成: {report_path}")

if __name__ == "__main__":
    main()
