#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动归档检查器（post_task Hook）
功能：
1. 检查任务产出是否已归档到 00-知识库/文档归档/（正式文档）
2. 提示索引更新、三处备份（每日回顾类）
3. 只检查+提示，不自动移动文件（避免误操作，归档动作由DocWriter/用户确认）
依据：AGENTS.md 文档强制归档规则 + hooks_config.json auto_archiver
"""
import sys

ARCHIVE_DIR = "00-知识库/文档归档"
TEMP_DIRS = ["99-临时文件", "03-数据分析"]


def check_archive(output_path):
    """output_path: 任务产出的相对/绝对路径或描述"""
    suggestions = []
    path_str = str(output_path).replace("\\", "/")

    is_doc = any(path_str.endswith(ext) for ext in [".md", ".html", ".pdf", ".pptx", ".docx"])
    is_feishu = "feishu" in path_str.lower() or "飞书" in path_str
    in_temp = any(t in path_str for t in TEMP_DIRS)
    in_archive = ARCHIVE_DIR in path_str

    if is_doc and in_temp and not in_archive:
        suggestions.append(f"产出在临时目录，正式文档需归档到 {ARCHIVE_DIR}/ 对应子目录，并更新 README 索引")
    if is_feishu:
        suggestions.append("飞书文档需用 .url.md 记录标题/日期/链接/类型/关键词并归档到 文档归档/")
    if is_doc and not in_archive and not in_temp:
        suggestions.append(f"确认正式文档是否已归档到 {ARCHIVE_DIR}/ 并更新索引")
    if "每日回顾" in path_str or "每日记录" in path_str:
        suggestions.append("每日回顾需三处备份：05-个人成长/每日记录 + 04-会议纪要/每日回顾 + 99-临时文件/每日回顾")

    return suggestions


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_archiver.py <output_path>")
        sys.exit(0)
    suggestions = check_archive(sys.argv[1])
    if not suggestions:
        print("✅ 归档检查：无需额外动作（或非文档类产出）")
        sys.exit(0)
    print(f"📦 归档提示（{len(suggestions)} 条，需确认后执行）:")
    for s in suggestions:
        print(f"   - {s}")
    sys.exit(0)
