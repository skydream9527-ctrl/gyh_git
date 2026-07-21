#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优先级检查器（pre_task Hook）
功能：
1. 读取MEMORY.md中Q3明确不做清单
2. 判断当前任务是否属于P2或明确不做范围
3. 如果是，直接拦截并提示优先级规则
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
MEMORY_PATH = BASE_DIR / "MEMORY.md"

def load_not_do_list():
    """加载MEMORY.md中的明确不做清单"""
    if not MEMORY_PATH.exists():
        return []
    content = MEMORY_PATH.read_text(encoding="utf-8")
    # 定位「明确不做」section
    match = re.search(r'###\s*明确不做.*?\n((?:- ❌.*?\n)+)', content)
    if not match:
        return []
    items = []
    for line in match.group(1).splitlines():
        line = line.strip()
        if line.startswith("- ❌"):
            items.append(line.replace("- ❌", "").strip())
    return items

def check_priority(task_description):
    """
    检查任务优先级
    返回: (allowed: bool, reason: str, matched_item: str)
    """
    not_do_list = load_not_do_list()
    
    # 关键词匹配（简单规则，后续可升级为向量匹配）
    task_lower = task_description.lower()
    for item in not_do_list:
        item_lower = item.lower()
        # 提取核心关键词匹配
        keywords = [w for w in re.split(r'[（）()\s]+', item_lower) if len(w) >= 2]
        match_count = sum(1 for kw in keywords if kw in task_lower)
        if match_count >= len(keywords) * 0.5:
            return False, f"任务属于Q3明确不做清单内容，资源受限阶段禁止投入精力", item
    
    # P2任务暂不自动拦截，只做提醒（后续根据配置调整）
    return True, "", ""

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python priority_checker.py <task_description>")
        sys.exit(0)
    task = sys.argv[1]
    allowed, reason, matched = check_priority(task)
    if allowed:
        print(f"✅ 优先级检查通过")
        sys.exit(0)
    else:
        print(f"❌ 优先级检查不通过: {reason}")
        print(f"   匹配到不做项: {matched}")
        sys.exit(1)
