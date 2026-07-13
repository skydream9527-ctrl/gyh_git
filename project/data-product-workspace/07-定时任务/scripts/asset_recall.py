#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「需求 → 资产」自动回流机制
手动触发：扫描已完成的分析任务，提取可复用资产，生成回填建议报告
功能：
1. 扫描 03-数据分析/ 等目录下近 N 天修改的文件
2. 按信号关键词分类（SQL模板 / 指标口径 / 人群包 / 方法论）
3. 提取可复用片段
4. 对比已有资产（去重/追加/新建）
5. 输出回填建议报告（只建议，不自动执行）
"""
import os
import sys
import re
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "asset_recall_config.json"
LOG_DIR = SCRIPT_DIR.parent / "logs"
REPORT_DIR = SCRIPT_DIR.parent / "reports"

for d in [LOG_DIR, REPORT_DIR]:
    d.mkdir(exist_ok=True, parents=True)

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg)
    log_file = LOG_DIR / f"asset-recall-{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_config():
    default_config = {
        "scan_source_dirs": ["03-数据分析", "01-业务项目"],
        "target_asset_root": "00-知识库/数据资产",
        "signal_keywords": {
            "sql_template": ["SELECT", "FROM", "WHERE", "GROUP BY", "COUNT(DISTINCT", "${", "万象", "oaid", "did"],
            "metric_definition": ["口径", "定义", "计算方式", "指标", "DAU", "留存", "CTR", "人均", "时长", "财收", "UV"],
            "crowd_package": ["人群包", "圈选", "万象", "oaid", "标签", "交集", "排除", "push包", "售卖"],
            "methodology": ["方法论", "踩坑", "优化", "模板", "复用", "沉淀", "经验", "SOP", "流程"]
        },
        "min_signal_count": 2,
        "max_suggestions": 20,
        "scan_days": 7,
        "max_file_bytes": 200000,
        "ignore_patterns": ["*.log", "*.tmp", "*.pyc", "99-临时文件/*"]
    }
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        log(f"已创建默认配置: {CONFIG_PATH}")
        return default_config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml",
    ".sql", ".html", ".css", ".sh", ".csv", ".toml", ".ini"
}

IGNORE_DIRS = {
    ".git", ".trae", ".micode", ".playwright-cli", ".vscode",
    "node_modules", "__pycache__", ".venv", "venv",
    "07-定时任务/logs", "07-定时任务/reports"
}

def should_ignore(path_str, ignore_patterns):
    for pattern in ignore_patterns:
        pattern = pattern.replace("*", "").replace("/", os.sep)
        if pattern in path_str:
            return True
    for ignore_dir in IGNORE_DIRS:
        if ignore_dir in path_str:
            return True
    return False

def scan_source_files(config):
    """扫描源目录，返回近 N 天修改的文件列表"""
    scan_dirs = config.get("scan_source_dirs", [])
    scan_days = config.get("scan_days", 7)
    max_bytes = config.get("max_file_bytes", 200000)
    ignore_patterns = config.get("ignore_patterns", [])
    cutoff = datetime.now() - timedelta(days=scan_days)
    files = []

    for scan_dir in scan_dirs:
        dir_path = BASE_DIR / scan_dir
        if not dir_path.exists():
            log(f"源目录不存在，跳过: {dir_path}", "WARN")
            continue
        for root, dirs, filenames in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]
            for filename in filenames:
                if filename.startswith("."):
                    continue
                file_path = Path(root) / filename
                if should_ignore(str(file_path.relative_to(BASE_DIR)), ignore_patterns):
                    continue
                if file_path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff:
                        continue
                    size = file_path.stat().st_size
                    content = ""
                    if size <= max_bytes:
                        try:
                            content = file_path.read_text(encoding="utf-8", errors="replace")
                        except Exception:
                            pass
                    rel_path = str(file_path.relative_to(BASE_DIR))
                    files.append({
                        "path": rel_path,
                        "mtime": mtime.strftime("%Y-%m-%d %H:%M"),
                        "size": size,
                        "content": content
                    })
                except Exception as e:
                    log(f"读取文件失败 {file_path}: {e}", "WARN")

    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files

def classify_asset_type(content, keywords_config, min_count):
    """判断文件内容属于哪类资产（可多类）"""
    if not content:
        return []
    content_lower = content.lower()
    types = []
    for asset_type, kws in keywords_config.items():
        count = sum(1 for kw in kws if kw.lower() in content_lower)
        if count >= min_count:
            types.append(asset_type)
    return types

def extract_sql_blocks(content):
    """从文件内容中提取 SQL 代码块"""
    blocks = []
    # 匹配 ```sql ... ``` 代码块
    for match in re.finditer(r'```sql\s*\n(.*?)```', content, re.DOTALL):
        sql = match.group(1).strip()
        if len(sql) < 20:
            continue
        # 提取参数 ${xxx}
        params = re.findall(r'\$\{(\w+)\}', sql)
        # 提取主要表名
        tables = re.findall(r'(?:FROM|JOIN)\s+(\w+)', sql, re.IGNORECASE)
        blocks.append({
            "sql": sql[:500],  # 截取前500字符
            "params": list(set(params)),
            "tables": list(set(tables)),
            "length": len(sql)
        })
    # 也匹配单独的 SQL 语句（非代码块）
    if not blocks:
        sql_pattern = r'(SELECT\s+.+?FROM\s+.+?WHERE\s+.+?;?)'
        for match in re.finditer(sql_pattern, content, re.DOTALL | re.IGNORECASE):
            sql = match.group(1).strip()
            if len(sql) < 30:
                continue
            params = re.findall(r'\$\{(\w+)\}', sql)
            tables = re.findall(r'(?:FROM|JOIN)\s+(\w+)', sql, re.IGNORECASE)
            blocks.append({
                "sql": sql[:500],
                "params": list(set(params)),
                "tables": list(set(tables)),
                "length": len(sql)
            })
    return blocks

def extract_metric_defs(content):
    """提取指标定义片段"""
    defs = []
    # 匹配表格中的指标定义行
    for match in re.finditer(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', content):
        name = match.group(1).strip()
        definition = match.group(2).strip()
        calc = match.group(3).strip()
        if any(kw in name or kw in definition for kw in ["DAU", "UV", "时长", "留存", "CTR", "财收", "人均"]):
            if len(name) < 20 and len(definition) > 5:
                defs.append({
                    "metric_name": name,
                    "definition": definition,
                    "calculation": calc
                })
    return defs

def extract_crowd_package_info(content):
    """提取人群包信息"""
    infos = []
    # 匹配人群包相关的描述
    patterns = [
        r'人群包[：:]\s*(.+)',
        r'圈选条件[：:]\s*(.+)',
        r'万象\s*(?:ID|人群包)\s*[：:]?\s*(.+)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            infos.append({"info": match.group(1).strip()[:200]})
    return infos

def extract_methodology(content):
    """提取方法论/踩坑/优化片段"""
    methods = []
    # 匹配标题下的内容块
    for match in re.finditer(r'#+\s*(.+?(?:方法|优化|踩坑|经验|SOP|流程|沉淀).+?)\n(.+?)(?=\n#|\Z)', content, re.DOTALL):
        topic = match.group(1).strip()
        body = match.group(2).strip()[:300]
        if len(body) > 20:
            methods.append({"topic": topic, "content": body})
    return methods

def match_existing_assets(extracted_items, asset_type, target_dir):
    """将提取内容与已有资产对比，标记去重/追加/新建"""
    results = []
    for item in extracted_items:
        # 简单去重：检查目标目录下是否有相似内容
        action = "new"
        target_file = ""
        reason = "新增资产"

        if asset_type == "sql_template":
            target_file = "SQL模板库"
            # 检查是否已有类似模板
            for existing in target_dir.glob("*.md"):
                try:
                    existing_content = existing.read_text(encoding="utf-8", errors="replace")
                    if item.get("tables") and any(t in existing_content for t in item["tables"]):
                        action = "append"
                        target_file = existing.name
                        reason = f"与已有模板 {existing.name} 涉及相同表，建议追加"
                        break
                except Exception:
                    continue

        elif asset_type == "metric_definition":
            target_file = "指标口径字典/核心指标口径.md"
            dict_path = target_dir / "指标口径字典" / "核心指标口径.md"
            if dict_path.exists():
                try:
                    dict_content = dict_path.read_text(encoding="utf-8", errors="replace")
                    if item.get("metric_name") and item["metric_name"] in dict_content:
                        action = "skip"
                        reason = f"指标 {item['metric_name']} 已存在于口径字典"
                    else:
                        action = "append"
                        reason = "追加到已有口径字典"
                except Exception:
                    pass

        elif asset_type == "crowd_package":
            target_file = "人群包资产登记/人群包登记表.md"
            action = "append"
            reason = "追加到人群包登记表"

        elif asset_type == "methodology":
            target_file = "data-analysis/methods/"
            action = "new"
            reason = "沉淀到数据分析方法论目录"

        results.append({
            "extracted": item,
            "action": action,
            "target_file": target_file,
            "reason": reason
        })
    return results

def generate_recall_report(suggestions, date_str, config):
    """生成回流建议报告"""
    target_root = config.get("target_asset_root", "00-知识库/数据资产")

    lines = [
        f"# 资产回流建议报告 — {date_str}",
        f"",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 扫描范围：{', '.join(config.get('scan_source_dirs', []))}",
        f"> 扫描天数：{config.get('scan_days', 7)} 天",
        f"> 说明：以下为自动提取的回填建议，需人工确认后执行",
        f"",
        f"---",
        f"",
    ]

    # 按资产类型分组
    by_type = {}
    for s in suggestions:
        asset_type = s.get("asset_type", "unknown")
        if asset_type not in by_type:
            by_type[asset_type] = []
        by_type[asset_type].append(s)

    type_names = {
        "sql_template": "SQL 模板",
        "metric_definition": "指标口径",
        "crowd_package": "人群包",
        "methodology": "方法论/踩坑"
    }

    if not by_type:
        lines.append("## 本次无回流建议")
        lines.append("")
        lines.append("近期内没有发现需要沉淀的新资产。")
        return "\n".join(lines)

    total = sum(len(v) for v in by_type.values())
    lines.append(f"## 概览：共 {total} 条回流建议")
    lines.append("")
    for asset_type, items in by_type.items():
        type_name = type_names.get(asset_type, asset_type)
        lines.append(f"- **{type_name}**: {len(items)} 条")
    lines.append("")

    for asset_type, items in by_type.items():
        type_name = type_names.get(asset_type, asset_type)
        lines.append(f"## {type_name}")
        lines.append("")
        lines.append(f"| 来源文件 | 提取内容摘要 | 建议动作 | 目标位置 | 原因 |")
        lines.append(f"|----------|-------------|----------|----------|------|")

        for s in items[:config.get("max_suggestions", 20)]:
            source = s.get("source", "")
            summary = s.get("summary", "")[:60]
            action = s.get("action", "")
            target = s.get("target_file", "")
            reason = s.get("reason", "")
            lines.append(f"| `{source}` | {summary} | {action} | `{target}` | {reason} |")

        lines.append("")

        # 详细提取内容
        for i, s in enumerate(items[:5]):
            lines.append(f"### 详情 {i+1}: `{s.get('source', '')}`")
            lines.append("")
            if asset_type == "sql_template" and s.get("extracted", {}).get("sql"):
                lines.append("**提取的 SQL**:")
                lines.append("```sql")
                lines.append(s["extracted"]["sql"])
                lines.append("```")
                if s["extracted"].get("params"):
                    lines.append(f"\n**参数**: {', '.join(s['extracted']['params'])}")
                if s["extracted"].get("tables"):
                    lines.append(f"**涉及表**: {', '.join(s['extracted']['tables'])}")
            elif asset_type == "metric_definition" and s.get("extracted"):
                ext = s["extracted"]
                lines.append(f"- **指标名**: {ext.get('metric_name', '')}")
                lines.append(f"- **定义**: {ext.get('definition', '')}")
                lines.append(f"- **计算方式**: {ext.get('calculation', '')}")
            elif asset_type == "methodology" and s.get("extracted"):
                ext = s["extracted"]
                lines.append(f"- **主题**: {ext.get('topic', '')}")
                lines.append(f"- **内容摘要**: {ext.get('content', '')[:200]}")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 下一步操作",
        "",
        "1. 确认上述建议是否合理",
        "2. 告知 AI「回填第 N 条」或「全部回填」",
        "3. AI 将执行回填并更新数据资产层索引",
        "",
        "*本报告由 asset_recall.py 自动生成*",
    ])

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="需求→资产 自动回流机制")
    parser.add_argument("--days", type=int, help="扫描天数（默认读配置）")
    parser.add_argument("--type", choices=["sql_template", "metric_definition", "crowd_package", "methodology"],
                        help="只提取指定类型")
    parser.add_argument("--dry-run", action="store_true", help="只输出，不保存报告")
    args = parser.parse_args()

    log("=== 开始执行资产回流扫描 ===")
    config = load_config()

    if args.days:
        config["scan_days"] = args.days

    # 1. 扫描源文件
    log(f"扫描源目录（近 {config.get('scan_days', 7)} 天）...")
    files = scan_source_files(config)
    log(f"发现 {len(files)} 个文件")

    # 2. 分类并提取
    suggestions = []
    keywords_config = config.get("signal_keywords", {})
    min_count = config.get("min_signal_count", 2)
    target_root = BASE_DIR / config.get("target_asset_root", "00-知识库/数据资产")

    for f in files:
        if not f["content"]:
            continue
        asset_types = classify_asset_type(f["content"], keywords_config, min_count)
        if args.type and args.type not in asset_types:
            continue

        for asset_type in asset_types:
            extracted = []
            if asset_type == "sql_template":
                extracted = extract_sql_blocks(f["content"])
            elif asset_type == "metric_definition":
                extracted = extract_metric_defs(f["content"])
            elif asset_type == "crowd_package":
                extracted = extract_crowd_package_info(f["content"])
            elif asset_type == "methodology":
                extracted = extract_methodology(f["content"])

            if not extracted:
                continue

            matched = match_existing_assets(extracted, asset_type, target_root)
            for m in matched:
                summary = ""
                if asset_type == "sql_template":
                    tables = m["extracted"].get("tables", [])
                    summary = f"SQL块，涉及表: {', '.join(tables[:3])}" if tables else "SQL代码块"
                elif asset_type == "metric_definition":
                    summary = f"指标: {m['extracted'].get('metric_name', '')}"
                elif asset_type == "crowd_package":
                    summary = m["extracted"].get("info", "")[:60]
                elif asset_type == "methodology":
                    summary = m["extracted"].get("topic", "")

                suggestions.append({
                    "source": f["path"],
                    "asset_type": asset_type,
                    "extracted": m["extracted"],
                    "action": m["action"],
                    "target_file": m["target_file"],
                    "reason": m["reason"],
                    "summary": summary
                })

    log(f"提取到 {len(suggestions)} 条回流建议")

    # 3. 生成报告
    date_str = datetime.now().strftime("%Y-%m-%d")
    report = generate_recall_report(suggestions, date_str, config)

    if args.dry_run:
        print(report)
        return

    # 4. 保存报告
    report_path = REPORT_DIR / f"{date_str}-资产回流建议.md"
    report_path.write_text(report, encoding="utf-8")
    log(f"报告已保存: {report_path}")

    # 输出摘要
    log("=" * 60)
    log("资产回流扫描完成")
    log(f"扫描文件: {len(files)}")
    log(f"回流建议: {len(suggestions)} 条")
    for asset_type in ["sql_template", "metric_definition", "crowd_package", "methodology"]:
        count = len([s for s in suggestions if s["asset_type"] == asset_type])
        if count:
            log(f"  {asset_type}: {count} 条")
    log(f"报告路径: {report_path}")
    log("=" * 60)

    print(f"\n✅ 资产回流扫描完成：{len(suggestions)} 条建议")
    print(f"📄 报告已生成: 07-定时任务/reports/{date_str}-资产回流建议.md")

if __name__ == "__main__":
    main()
