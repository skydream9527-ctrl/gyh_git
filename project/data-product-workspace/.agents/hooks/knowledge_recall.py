#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识沉淀提示器（post_task Hook）
功能：
1. 判断任务产出中是否有可复用资产（SQL / 指标口径 / 人群包 / 方法论）
2. SQL 块数达到阈值（sql_sedimentation_threshold）时提示沉淀到数据资产层
3. 只提示，不自动执行（沉淀动作由用户/Coordinator确认）
依据：hooks_config.json knowledge_recall + WORKFLOWS.md 沉淀流程
"""
import re
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = Path(__file__).parent / "hooks_config.json"


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("knowledge_recall", {})
    except Exception:
        return {}


def read_input(arg):
    """arg 可能是一段内容，也可能是一个文件/目录路径"""
    p = BASE_DIR / arg
    try:
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
        if p.exists() and p.is_dir():
            texts = []
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in {".md", ".sql", ".txt"}:
                    texts.append(f.read_text(encoding="utf-8", errors="replace"))
            return "\n".join(texts)
    except Exception:
        pass
    return arg


def recall(content):
    config = load_config()
    threshold = config.get("sql_sedimentation_threshold", 3)
    suggestions = []

    # SQL 块计数
    sql_blocks = re.findall(r'```sql', content, re.IGNORECASE)
    sql_stmt = re.findall(r'\bSELECT\b.+?\bFROM\b', content, re.IGNORECASE | re.DOTALL)
    sql_count = max(len(sql_blocks), len(sql_stmt))
    if sql_count >= threshold:
        suggestions.append(f"发现 {sql_count} 段 SQL（≥{threshold}），建议沉淀可复用 SQL 到 00-知识库/数据资产/SQL模板库/")

    if any(k in content for k in ["口径", "指标定义", "计算方式"]):
        suggestions.append("发现指标口径描述，建议回填到 00-知识库/数据资产/指标口径字典/")

    if any(k in content for k in ["人群包", "圈选", "万象"]):
        suggestions.append("发现人群包/圈选内容，建议登记到 00-知识库/数据资产/人群包资产登记/")

    if any(k in content for k in ["方法论", "踩坑", "经验", "SOP", "复盘"]):
        suggestions.append("发现方法论/踩坑，建议沉淀到 00-知识库/对应知识域 methods/ 或 pitfalls/")

    return suggestions


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python knowledge_recall.py <task_output_path_or_content>")
        sys.exit(0)
    content = read_input(sys.argv[1])
    suggestions = recall(content)
    if not suggestions:
        print("ℹ️ 未发现明显可沉淀资产")
        sys.exit(0)
    print(f"💡 知识沉淀提示（{len(suggestions)} 条，仅建议，需确认后执行）:")
    for s in suggestions:
        print(f"   - {s}")
    sys.exit(0)
