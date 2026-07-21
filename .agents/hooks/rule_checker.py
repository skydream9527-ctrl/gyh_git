#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则校验器（pre_task Hook）
功能：
1. 读取AGENTS.md中的业务踩坑硬规则
2. 检查任务是否违反硬规则
3. 违规直接拦截，提示正确做法
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
AGENTS_PATH = BASE_DIR / "AGENTS.md"

def load_hard_rules():
    """加载AGENTS.md中的业务踩坑硬规则"""
    if not AGENTS_PATH.exists():
        return []
    content = AGENTS_PATH.read_text(encoding="utf-8")
    # 定位「业务踩坑记录」表格
    match = re.search(r'###\s*⚠️\s*业务踩坑记录.*?\n((?:\|.*?\n)+)', content, re.DOTALL)
    if not match:
        return []
    rules = []
    table_lines = match.group(1).splitlines()
    for line in table_lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) < 4 or cells[0].startswith("日期") or cells[0].startswith("---"):
            continue
        # 解析规则：坑点描述 → 强制规则
        pitfall = cells[1]
        rule = cells[2].replace("**", "").strip()
        rules.append({
            "date": cells[0],
            "pitfall": pitfall,
            "rule": rule,
            "reference": cells[3]
        })
    return rules

def check_rules(task_description):
    """
    检查任务是否违反硬规则
    返回: (allowed: bool, violations: list)
    """
    rules = load_hard_rules()
    violations = []
    task_lower = task_description.lower()
    
    for rule in rules:
        rule_lower = rule["rule"].lower()
        pitfall_lower = rule["pitfall"].lower()
        
        # 提取触发关键词（禁止/必须相关的场景）
        trigger_keywords = []
        # 人群包相关
        if "人群包" in rule["pitfall"] or "人群包" in rule["rule"]:
            trigger_keywords.extend(["人群包", "实验平台人群包"])
        # 算法评审相关
        if "算法" in rule["rule"] and ("产品形态" in rule["pitfall"] or "信息流" in rule["rule"]):
            trigger_keywords.extend(["信息流", "产品形态", "消费路径", "上线", "评审"])
        # kyuubi超时相关
        if "kyuubi" in rule["rule"] or "超时" in rule["pitfall"]:
            trigger_keywords.extend(["kyuubi", "sql", "查询", "超时"])
        # DID相关
        if "did" in rule_lower or "双重差分" in rule["rule"]:
            trigger_keywords.extend(["push", "ab实验", "实验分析", "tgi", "对比"])
        # 数据工场写入相关
        if "insert" in rule_lower or "数据工场" in rule["rule"]:
            trigger_keywords.extend(["insert", "写入", "数据工场", "生产表"])
        # RAG相关
        if "rag" in rule_lower and "nl-sql" in rule["rule"]:
            trigger_keywords.extend(["nl-sql", "rag", "自然语言取数"])
        
        # 检查是否触发规则
        if trigger_keywords and any(kw in task_lower for kw in trigger_keywords):
            # 检查是否提到了正确做法（如果提到了规则要求的做法，不算违规）
            required_actions = []
            if "必须邀请算法" in rule["rule"]:
                required_actions.append("算法")
                required_actions.append("评审")
            if "分批提交" in rule["rule"]:
                required_actions.append("分批")
            if "禁止新增" in rule["rule"] and "人群包" in rule["rule"]:
                required_actions.append("不新增")
                required_actions.append("通用后台")
            if "必须使用did" in rule_lower or "双重差分" in rule["rule"]:
                required_actions.append("did")
                required_actions.append("双重差分")
            if "用户自行建表" in rule["rule"]:
                required_actions.append("自行建表")
            if "不做复杂rag" in rule_lower or "范式库优先" in rule["rule"]:
                required_actions.append("范式库")
                required_actions.append("few-shot")
            
            # 如果任务描述中没有包含正确做法关键词，判定为违规
            if required_actions and not any(act in task_lower for act in required_actions):
                violations.append(rule)
    
    return len(violations) == 0, violations

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rule_checker.py <task_description>")
        sys.exit(0)
    task = sys.argv[1]
    allowed, violations = check_rules(task)
    if allowed:
        print(f"✅ 规则校验通过")
        sys.exit(0)
    else:
        print(f"❌ 规则校验不通过，发现 {len(violations)} 条违规:")
        for v in violations:
            print(f"   - [{v['date']}] 触发规则: {v['rule']}")
            print(f"     坑点背景: {v['pitfall']}")
        sys.exit(1)
