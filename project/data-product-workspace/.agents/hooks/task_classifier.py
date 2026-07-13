#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务分类器（pre_task Hook）
功能：
1. 自动识别任务类型
2. 判断是否需要派单给DataAnalyst/DocWriter
3. 返回任务分类和派单建议
"""
import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = Path(__file__).parent / "hooks_config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def classify_task(task_description):
    """
    分类任务
    返回: {
        "task_type": "coordination" | "data_analysis" | "document" | "mixed",
        "dispatch_suggestions": list,
        "confidence": float
    }
    """
    config = load_config()
    classifier_config = config.get("task_classifier", {})
    
    data_keywords = classifier_config.get("data_keywords", [
        "SQL", "查询", "取数", "分析", "数据", "指标", "DAU", "时长", "AB实验", "DID", "口径",
        "查一下", "跑个数", "统计", "维度", "报表", "看板", "漏斗", "留存", "转化率", "人群包"
    ])
    doc_keywords = classifier_config.get("doc_keywords", [
        "文档", "归档", "飞书", "报告", "纪要", "总结", "写", "整理", "同步", "导出",
        "生成文档", "更新文档", "发飞书", "备份", "写报告", "整理会议"
    ])
    threshold = classifier_config.get("confidence_threshold", 0.6)
    
    task_lower = task_description.lower()
    
    # 计算关键词匹配度
    data_matches = sum(1 for kw in data_keywords if kw.lower() in task_lower)
    doc_matches = sum(1 for kw in doc_keywords if kw.lower() in task_lower)
    
    data_score = min(1.0, data_matches / 3) if data_keywords else 0
    doc_score = min(1.0, doc_matches / 3) if doc_keywords else 0
    
    dispatch = []
    task_type = "coordination"
    
    if data_score >= threshold and doc_score >= threshold:
        task_type = "mixed"
        dispatch = ["DataAnalyst", "DocWriter"]
    elif data_score >= threshold:
        task_type = "data_analysis"
        dispatch = ["DataAnalyst"]
    elif doc_score >= threshold:
        task_type = "document"
        dispatch = ["DocWriter"]
    
    confidence = max(data_score, doc_score, 0.3)
    
    return {
        "task_type": task_type,
        "dispatch_suggestions": dispatch,
        "data_score": round(data_score, 2),
        "doc_score": round(doc_score, 2),
        "confidence": round(confidence, 2)
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python task_classifier.py <task_description>")
        print("Example: python task_classifier.py '帮我查一下昨天信息流DAU并写个分析报告'")
        sys.exit(0)
    task = sys.argv[1]
    result = classify_task(task)
    print(f"📋 任务分类结果:")
    print(f"   任务类型: {result['task_type']}")
    print(f"   数据匹配分: {result['data_score']}")
    print(f"   文档匹配分: {result['doc_score']}")
    print(f"   置信度: {result['confidence']}")
    if result['dispatch_suggestions']:
        print(f"   建议派单: {', '.join(result['dispatch_suggestions'])}")
    else:
        print(f"   建议派单: Coordinator直接处理")
