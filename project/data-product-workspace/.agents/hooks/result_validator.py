#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果校验器（post_execution Hook）
功能：
1. 检查子Agent返回结果是否符合交付要求
2. 校验数据标注（来源/表名/时间/口径）、结构（表格优先）、完整性
3. 关键问题（数据结论无来源标注）判定不通过，软问题只提示
依据：MEMORY.md 输出要求 + DataAnalyst「数据标注」强制规则 + AGENTS.md 数据标注来源规则
"""
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

# 数据类结果信号词（出现则视为含数据/取数结论，需要来源标注）
DATA_SIGNAL_KEYWORDS = ["DAU", "留存", "CTR", "时长", "UV", "人群包", "占比", "同比", "环比", "SELECT", "查询结果", "指标"]
# 来源标注信号词
SOURCE_SIGNAL_KEYWORDS = ["来源", "表名", "口径", "查询时间", "数据来源", "dt=", "date=", "分区", "iceberg", "hive"]
# 推断标注
INFER_KEYWORDS = ["推断", "估计", "假设"]


def validate_result(result_content):
    """
    校验结果内容
    返回: (passed: bool, issues: list[dict])  issue = {level: 'error'|'warn', msg}
    """
    issues = []
    text = result_content
    text_lower = text.lower()

    is_data_result = any(kw.lower() in text_lower for kw in DATA_SIGNAL_KEYWORDS)

    # 1. 数据结果必须有来源标注（硬规则）
    if is_data_result:
        has_source = any(kw.lower() in text_lower for kw in SOURCE_SIGNAL_KEYWORDS)
        if not has_source:
            issues.append({"level": "error",
                           "msg": "含数据/指标结论但未发现来源标注（表名/口径/查询时间/分区），违反数据标注硬规则"})

    # 2. 含具体数值但无来源也无「推断」标注（软）
    has_number = bool(re.search(r'\d+(\.\d+)?%|\d{3,}', text))
    if has_number and is_data_result \
            and not any(k in text for k in SOURCE_SIGNAL_KEYWORDS) \
            and not any(k in text for k in INFER_KEYWORDS):
        issues.append({"level": "warn", "msg": "含具体数值但既无来源也无「推断」标注，请补来源或标注推断"})

    # 3. 对比/清单类建议用表格（软，用户偏好：表格优先）
    if is_data_result and "|" not in text and len(text) > 200:
        issues.append({"level": "warn", "msg": "数据/对比类内容建议用表格呈现（用户偏好：表格优先）"})

    # 4. 完整性：结果过短或为空
    if len(text.strip()) < 10:
        issues.append({"level": "error", "msg": "结果内容过短或为空，疑似未完成"})

    passed = not any(i["level"] == "error" for i in issues)
    return passed, issues


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python result_validator.py <result_content>")
        sys.exit(0)
    passed, issues = validate_result(sys.argv[1])
    if not issues:
        print("✅ 结果校验通过（数据标注/结构/完整性）")
        sys.exit(0)
    errors = [i for i in issues if i["level"] == "error"]
    warns = [i for i in issues if i["level"] == "warn"]
    if errors:
        print(f"❌ 结果校验不通过，{len(errors)} 个必须修正:")
        for i in errors:
            print(f"   - {i['msg']}")
    if warns:
        print(f"⚠️ {len(warns)} 个建议优化:")
        for i in warns:
            print(f"   - {i['msg']}")
    sys.exit(0 if passed else 1)
