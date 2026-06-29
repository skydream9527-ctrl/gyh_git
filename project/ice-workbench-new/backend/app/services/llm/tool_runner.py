"""Skill tool execution. Builtins are globally callable across Agents.

Tools available regardless of which Agent the conversation is bound to:
    - now / echo            : trivial demo
    - kyuubi_query          : SELECT via xiaomi-kyuubi-cli
    - feishu_publish        : create a Feishu doc via the bundled `feishu` CLI
    - write_file            : drop generated content into the task workspace
                              (tasks/{tid}/files/output/...) so it shows up in
                              the left-side file panel.
"""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from ...core.config import get_settings
from ...core.errors import ErrorCode

# Built-in demo tools usable without external services.
BUILTIN_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "now",
            "description": "Return the current UTC datetime in ISO 8601.",
            "parameters": {"type": "object", "properties": {}},
        },
        "_meta": {
            "display_name": "当前时间",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "echo",
            "description": "Echo back the given text. Useful for testing tool calling.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        "_meta": {
            "display_name": "回声",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kyuubi_query",
            "description": (
                "Run a SELECT against Xiaomi Kyuubi SQL gateway. Read-only. "
                "The server already has the connection context configured "
                "(region=chnbj, workspace=11329, catalog=iceberg_zjyprc_hadoop, "
                "engine=presto, token=***). Do NOT ask the user for any of these — "
                "just call with the `sql` argument. Use fully-qualified table names "
                "like `iceberg_zjyprc_hadoop.<schema>.<table>`. Always include LIMIT."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SELECT statement to execute. Must include LIMIT.",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "Optional row cap, defaults to 100.",
                    },
                },
                "required": ["sql"],
            },
        },
        "_meta": {
            "display_name": "SQL 查询",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write text content to a file in the current task workspace. "
                "The file is registered under tasks/{task_id}/files/output/ and "
                "appears immediately in the user's left-side file panel. "
                "Use this whenever you produce a deliverable the user should be "
                "able to open / download / iterate on (markdown report, SQL "
                "script, CSV data, JSON, etc.). DO NOT use it for in-line answers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Filename including extension, e.g. 'report.md', 'query.sql', 'data.csv'.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content as text (UTF-8).",
                    },
                },
                "required": ["name", "content"],
            },
        },
        "_meta": {
            "display_name": "保存文件到工作区",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": (
                "Execute Python code in a sandboxed subprocess. Two main "
                "uses: (1) data analysis with pandas / numpy / scipy / "
                "sklearn / statsmodels / prophet / ruptures / matplotlib / "
                "seaborn pre-installed; (2) driving CLI tools that an "
                "agentic skill (feishu / kyuubi / datum / etc.) tells you "
                "to run — call them with subprocess.run([...], "
                "capture_output=True, text=True). Network is ON and the "
                "host's CLI auth files are reachable (HOME inherited), so "
                "`feishu fetch`, `kyuubi sql query`, `datum query` etc. "
                "work. Wall-clock + CPU timeout 60s, memory 1GB, output "
                "files captured under <task_workspace>/files/output/. cwd "
                "is files/output/. Print key results to stdout for the "
                "user; write artifacts to disk."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Full Python source. Use relative paths (cwd = "
                            "<task_workspace>/files/output/). Print key "
                            "results to stdout for the LLM/user to see; write "
                            "artifacts to disk."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "One-line summary of what this run computes "
                            "(audit / display, not behavior)."
                        ),
                    },
                    "timeout_sec": {
                        "type": "integer",
                        "description": (
                            "Optional override for wall-clock + CPU limit; "
                            "defaults to ICE_PYTHON_SANDBOX_TIMEOUT_SEC."
                        ),
                    },
                },
                "required": ["code"],
            },
        },
        "_meta": {
            "display_name": "执行 Python 分析",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volcano_abtest_analyze",
            "description": (
                "Run the volcano ABtest analysis pipeline for ONE experiment "
                "and return a markdown report. Wraps "
                "agents/volcano-abtest/scripts/analyze.py via the host's `datum` "
                "CLI — queries doris_zjyprc_hadoop ABtest tables (weighted "
                "aggregates + p-values + daily trends) and formats a report. "
                "Use this whenever the user asks for 火山实验 / abtest analysis "
                "with an experiment id + date range. Report is also saved to "
                "the task workspace as `abtest_<media>_<exp_id>_<start>-<end>.md` "
                "so it shows up in the user's file panel. Return field "
                "`report_md` is the same markdown — paste it into your reply, "
                "then append your own ### 实验分析 section."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "media": {
                        "type": "string",
                        "description": (
                            "Media type. One of: 浏览器 / browser (浏览器), "
                            "内容中心 / 桌面内容中心 / newhome / nh / mcc (桌面内容中心)."
                        ),
                    },
                    "exp_id": {
                        "type": "string",
                        "description": "Experiment id (numeric string), e.g. '5033339'.",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date. Accepts 4.9 / 2026-04-09 / 20260409.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date. Same formats as start_date.",
                    },
                },
                "required": ["media", "exp_id", "start_date", "end_date"],
            },
        },
        "_meta": {
            "display_name": "火山 ABtest 分析",
            "side_effect": "read",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "feishu_upload_image",
            "description": (
                "Upload a PNG/JPG image from the task workspace to a Feishu "
                "doc and return its image_token (so subsequent feishu docx "
                "edits can embed it). Wraps `feishu docx upload-image "
                "<doc_token> --file <path>`. Use after `feishu_publish` "
                "creates the doc and `execute_python` produces a chart PNG "
                "under <task_workspace>/files/output/charts/."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_token": {
                        "type": "string",
                        "description": "Feishu docx token (returned by feishu_publish).",
                    },
                    "image_path": {
                        "type": "string",
                        "description": (
                            "Path relative to <task_workspace>/files/output/, "
                            "e.g. 'charts/T3_forecast.png'. Absolute paths "
                            "outside the task workspace are rejected."
                        ),
                    },
                },
                "required": ["doc_token", "image_path"],
            },
        },
        "_meta": {
            "display_name": "上传图片到飞书",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List every file currently in this task's workspace, including "
                "files the user uploaded (`uploaded`), inputs received from "
                "previous tool calls (`input`), and previous-turn deliverables "
                "you wrote with write_file (`output`). Call this at the start "
                "of a turn whenever the user references 'the file we made', "
                "'上一轮的产物', '刚才那份报告', or any prior artifact you "
                "may have lost from context. Returns id/name/scope/format/size."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["all", "uploaded", "input", "output"],
                        "description": "Filter by scope. Default 'all'.",
                    },
                },
            },
        },
        "_meta": {
            "display_name": "列出工作区文件",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file in this task's workspace. Accepts "
                "either the file's `id` (preferred — get from list_files) or "
                "its `name`. Text formats (.md/.txt/.csv/.tsv/.sql/.py/.json/"
                ".log/.yml/.yaml) return UTF-8 content; binary files return "
                "{is_binary: true} so you can advise the user to open it. Use "
                "this to pick up where a previous turn left off — e.g. read "
                "`query.sql` from last round before refining it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "File id from list_files."},
                    "name": {"type": "string", "description": "Filename, e.g. 'query.sql'."},
                },
            },
        },
        "_meta": {
            "display_name": "读取工作区文件",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "feishu_send_message",
            "description": (
                "Send a Feishu bot message, not a document. Prefer custom bot "
                "webhook delivery for 日报推送 / 发群: pass webhook_url and "
                "optional sign_secret. If webhook_url is omitted, this falls "
                "back to app IM delivery with FEISHU_APP_ID + FEISHU_APP_SECRET "
                "and receive_id. For the 日报推送 agent, webhook_url is required. "
                "Return the Feishu API result; include success/failure in reply."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Card title, e.g. 内容生态数据日报 - 2026-06-03.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Message body in Feishu lark_md markdown. Keep it concise when image_path is provided.",
                    },
                    "image_path": {
                        "type": "string",
                        "description": (
                            "Optional PNG/JPG path relative to <task_workspace>/files/output/, "
                            "e.g. 'daily_report_preview.png'. When provided, the image is "
                            "uploaded as a Feishu message image and embedded in the bot card."
                        ),
                    },
                    "html_url": {
                        "type": "string",
                        "description": (
                            "Optional absolute URL to the HTML report. When provided, the card "
                            "adds a visible link to open the full HTML report."
                        ),
                    },
                    "webhook_url": {
                        "type": "string",
                        "description": (
                            "Feishu custom bot webhook URL, e.g. "
                            "https://open.feishu.cn/open-apis/bot/v2/hook/..."
                        ),
                    },
                    "sign_secret": {
                        "type": "string",
                        "description": (
                            "Optional Feishu custom bot signing secret. Do not echo it back."
                        ),
                    },
                    "receive_id": {
                        "type": "string",
                        "description": (
                            "App IM target id. Optional if FEISHU_DEFAULT_RECEIVE_ID is configured. "
                            "Ignored when webhook_url is provided."
                        ),
                    },
                    "receive_id_type": {
                        "type": "string",
                        "enum": ["chat_id", "open_id", "user_id", "union_id", "email"],
                        "description": (
                            "App IM target id type. Defaults to FEISHU_DEFAULT_RECEIVE_ID_TYPE or chat_id. "
                            "Ignored when webhook_url is provided."
                        ),
                    },
                    "template": {
                        "type": "string",
                        "enum": ["blue", "green", "red", "yellow", "grey", "purple"],
                        "description": "Feishu card header color template. Defaults to blue.",
                    },
                },
                "required": ["title", "content"],
            },
        },
        "_meta": {
            "display_name": "发送飞书消息",
            "side_effect": "network",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "feishu_publish",
            "description": (
                "Publish a markdown document to Feishu (lark) via the bundled "
                "`feishu` CLI. By default lands in the team wiki space "
                "configured in FEISHU_DEFAULT_WIKI_SPACE_ID — every space "
                "member already has read access (no manual permission "
                "request needed). After creation, the task owner + active "
                "collaborators (those with a xiaomi_email on file) are "
                "auto-granted the FEISHU_AUTO_PERM_LEVEL permission; passing "
                "extra `share_to` emails grants them too. Returns the doc URL "
                "on success — INCLUDE the URL in your reply. "
                "图表必须用 PNG（execute_python 出图 → feishu_upload_image 嵌入），"
                "不要在 markdown 里写 ```mermaid``` 块——飞书 PlantUML 渲染未开通，"
                "mermaid 会变成空白画板。返回值若带 content_warnings/hint 字段，"
                "说明文档里有渲染失败的块，按 hint 指引重试。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title."},
                    "markdown": {
                        "type": "string",
                        "description": "Document body in Feishu-flavored markdown.",
                    },
                    "wiki_space": {
                        "type": "string",
                        "description": (
                            "Optional override: place the doc under this wiki "
                            "space root. Defaults to FEISHU_DEFAULT_WIKI_SPACE_ID."
                        ),
                    },
                    "wiki_node": {
                        "type": "string",
                        "description": (
                            "Optional: put the doc under this wiki node "
                            "(token or URL). Mutually exclusive with wiki_space / folder."
                        ),
                    },
                    "folder": {
                        "type": "string",
                        "description": (
                            "Optional: put the doc under this drive folder token. "
                            "Mutually exclusive with wiki_space / wiki_node."
                        ),
                    },
                    "share_to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional Xiaomi office emails (xxx@xiaomi.com / "
                            "@mi.com) to grant explicit perms in addition to "
                            "the task owner + collaborators. Use when sharing "
                            "with a stakeholder who is not yet on the task."
                        ),
                    },
                    "share_perm": {
                        "type": "string",
                        "enum": ["view", "edit", "full_access"],
                        "description": (
                            "Permission level for share_to addresses. "
                            "Defaults to 'edit'. Task owner + collaborators "
                            "always get FEISHU_AUTO_PERM_LEVEL regardless."
                        ),
                    },
                },
                "required": ["title", "markdown"],
            },
        },
        "_meta": {
            "display_name": "发布到飞书文档",
            "side_effect": "network",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_agent_knowledge",
            "description": (
                "Read a file from the current Agent's knowledge base "
                "(agents/<agent_id>/knowledge/<path>). Use this to fetch SQL "
                "templates, event-tracking indexes, page-structure specs, "
                "historical cases, and other reference data that is NOT part "
                "of the always-on system prompt. Start by reading "
                "`index.yaml` to see what's available, then drill in. "
                "Supports text formats (.yaml/.yml/.md/.json/.txt/.sql). "
                "Binary files (.db, images) are rejected — ask the user or "
                "use a different tool. Path must be relative within the "
                "agent's knowledge directory; '..' and absolute paths are "
                "rejected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative path inside knowledge/, e.g. "
                            "'index.yaml', 'metrics/sql_templates/browser_feed.yaml', "
                            "'analysis/cases_and_lessons.yaml'."
                        ),
                    },
                },
                "required": ["path"],
            },
        },
        "_meta": {
            "display_name": "读取 Agent 知识库",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill",
            "description": (
                "Fetch the skill's instruction file. Call this BEFORE executing "
                "an agentic skill (e.g. `kyuubi`, `nl-mapping-table-sql`, "
                "`feishu`, `docx`, `xlsx`, `pptx`, `pdf`) when the user's request "
                "matches its trigger. Default (no `path`) = returns SKILL.md. To "
                "read a sibling reference file that the SKILL.md points you to "
                "(e.g. `reference/browser/table-schema.md`), pass `path` with the "
                "relative path. Pass `path=\"/\"` or `path=\"ls\"` to list all "
                "files in the skill folder. Content is read from the task's own "
                "snapshot when inside a task, so answers are reproducible even if "
                "the global skill is updated later."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "Skill id, e.g. 'nl-mapping-table-sql', 'kyuubi', 'feishu'.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Optional. Relative path inside the skill dir (e.g. 'reference/browser/table-schema.md'). 'ls' or '/' lists all files.",
                    },
                },
                "required": ["skill_id"],
            },
        },
        "_meta": {
            "display_name": "读取 Skill 说明",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
    # ─────────────── v2 agent mechanisms (Claude Code-style) ───────────────
    {
        "type": "function",
        "function": {
            "name": "memory_save",
            "description": (
                "Persist a reusable memory for the current user or for the "
                "current user+agent. Use only for stable preferences, feedback, "
                "project context, or external reference pointers that should "
                "appear in future conversations. Do not save secrets, one-off "
                "facts, or rules already fixed in the system prompt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["user", "agent"]},
                    "slug": {
                        "type": "string",
                        "description": "Stable lowercase id, e.g. 'report-style-preference'.",
                    },
                    "title": {"type": "string"},
                    "hook": {"type": "string", "description": "One-line MEMORY.md retrieval hook."},
                    "type": {
                        "type": "string",
                        "enum": ["user", "feedback", "project", "reference"],
                    },
                    "body": {"type": "string", "description": "Full markdown memory body."},
                },
                "required": ["scope", "slug", "title", "hook", "type", "body"],
            },
        },
        "_meta": {
            "display_name": "保存记忆",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_delete",
            "description": "Delete a stale or incorrect memory and remove it from MEMORY.md.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["user", "agent"]},
                    "slug": {"type": "string"},
                },
                "required": ["scope", "slug"],
            },
        },
        "_meta": {
            "display_name": "删除记忆",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_state_save",
            "description": (
                "Overwrite the current task's STATE.md with a concise markdown "
                "summary of semantic progress: phase, decomposition, pending "
                "items, key decisions, current files, and next steps. Keep it "
                "under about 100 lines."
            ),
            "parameters": {
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        },
        "_meta": {
            "display_name": "保存任务状态",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": (
                "Maintain a live TODO list for the current task so the user can "
                "see your progress. Use this when the task has 3+ distinct steps. "
                "Call with the FULL list every time (replace-all semantics, not "
                "diff-merge). Before you start working on an item, mark it "
                "in_progress. IMMEDIATELY after finishing, mark it completed — "
                "do NOT batch completions. At most ONE item may be in_progress "
                "at a time. If blocked, keep the item in_progress and add a new "
                "pending item describing the blocker."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "The complete todo list.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Imperative form, e.g. 'Write funnel SQL'",
                                },
                                "activeForm": {
                                    "type": "string",
                                    "description": "Present continuous form, e.g. 'Writing funnel SQL'",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                },
                            },
                            "required": ["content", "activeForm", "status"],
                        },
                    },
                },
                "required": ["items"],
            },
        },
        "_meta": {
            "display_name": "更新待办",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": True,  # todo list is plan-scaffolding, not business data
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_input",
            "description": (
                "Pause the current task and ask the user to provide a concrete "
                "decision, correction, approval, or missing business context. "
                "Use this only when continuing without a human answer would be "
                "unsafe, ambiguous, or likely to produce incorrect results. "
                "After calling this tool, stop and wait for the user's response."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short request title."},
                    "message": {"type": "string", "description": "What you need from the user and why."},
                    "fields": {
                        "type": "array",
                        "description": "Optional input fields for the UI.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                                "placeholder": {"type": "string"},
                                "required": {"type": "boolean"},
                            },
                        },
                    },
                    "table": {
                        "type": "object",
                        "description": "Optional rows needing review, e.g. {columns:[...], rows:[{...}]}",
                    },
                    "actions": {
                        "type": "array",
                        "description": "Suggested action buttons.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string"},
                                "kind": {"type": "string", "enum": ["primary", "secondary", "danger"]},
                            },
                        },
                    },
                    "resume_prompt": {
                        "type": "string",
                        "description": "Instruction to follow after the user resolves the request.",
                    },
                },
                "required": ["title", "message"],
            },
        },
        "_meta": {
            "display_name": "请求人工确认",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "exit_plan_mode",
            "description": (
                "Submit the completed plan to the user for approval and STOP "
                "generating. Call this ONLY when you have finished planning and "
                "have a concrete, actionable plan. After you call this tool, do "
                "NOT continue generating text — the user will review, and when "
                "they approve, you will be re-invoked with the green-light to "
                "execute. The plan argument should be a complete markdown "
                "description covering: what will be changed, in which files, "
                "and what verification to run."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "Full plan in markdown. Required.",
                    },
                },
                "required": ["plan"],
            },
        },
        "_meta": {
            "display_name": "提交方案",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": True,  # this is the one way OUT of plan mode
            "subagent_exposable": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_subagent",
            "description": (
                "Delegate a bounded sub-task to a specialized agent. The "
                "sub-agent runs with its own system prompt, tool budget, and "
                "isolated conversation, and returns only its final text answer "
                "(not its full transcript) — protecting your context. Any files "
                "the sub-agent writes (write_file) land in THIS task's "
                "workspace, so the user sees them. Use this to offload research "
                "(e.g. 'spawn data-cleaner to clean users.csv'), long analyses, "
                "or when a different persona is better suited. Cannot be nested "
                "(sub-agents cannot spawn sub-agents)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent to delegate to. Must exist in the agent catalog.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The complete task description for the sub-agent.",
                    },
                    "allowed_tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional whitelist of tool names the sub-agent may use.",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "default": 2048,
                        "description": "Max tokens per LLM call inside the sub-agent.",
                    },
                },
                "required": ["agent_id", "prompt"],
            },
        },
        "_meta": {
            "display_name": "调度子 Agent",
            "side_effect": "write",
            # Each spawn allocates an independent run_id + transcript path +
            # child_ctx, so concurrent calls don't interfere. The ws.py main
            # loop fans out parallel-safe tools via asyncio.gather only when
            # ICE_PARALLEL_TOOLS_ENABLED — leaving this off is the safe
            # default for users who never enable parallel tools.
            "parallel_safe": True,
            "plan_mode_allowed": False,
            "subagent_exposable": False,  # prevents recursion
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_parallel",
            "description": (
                "Run multiple sub-agents in parallel and return all results at "
                "once. Use when you have 2+ independent sub-tasks that can be "
                "executed concurrently (e.g. querying different data while "
                "another agent searches knowledge base). Each sub-task runs "
                "exactly like spawn_subagent but they execute simultaneously, "
                "saving total wall-clock time. Cannot be nested."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent_id": {
                                    "type": "string",
                                    "description": "The agent to delegate to.",
                                },
                                "prompt": {
                                    "type": "string",
                                    "description": "Complete task description for this sub-agent.",
                                },
                            },
                            "required": ["agent_id", "prompt"],
                        },
                        "minItems": 1,
                        "maxItems": 5,
                        "description": "Array of sub-tasks to run in parallel (max 5).",
                    },
                },
                "required": ["tasks"],
            },
        },
        "_meta": {
            "display_name": "并行调度子 Agent",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_scheduled_task",
            "description": (
                "Create a persistent cron schedule for the current task. "
                "Use only after the user has confirmed the schedule, cadence, "
                "and delivery target. The schedule will appear in the task's "
                "Scheduled tab and in the global scheduled task dashboard."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Human-readable schedule name."},
                    "cron": {
                        "type": "string",
                        "description": "Standard 5-field cron expression: minute hour day month weekday.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Full instruction prompt to execute every time the cron fires.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Optional model id for scheduled execution.",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether the schedule is enabled immediately. Defaults to true.",
                    },
                    "todo_list": {
                        "type": "array",
                        "description": "Optional short execution checklist for the scheduled run.",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "cron", "prompt"],
            },
        },
        "_meta": {
            "display_name": "创建定时任务",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_background",
            "description": (
                "Enqueue a long-running task to execute in the background. "
                "Returns immediately with a background job id. When the job "
                "completes, a notification is pushed to the user and any files "
                "the background agent produces land in this task's workspace. "
                "Use for tasks estimated to take >2 minutes or that the user "
                "does not need to watch live."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "prompt": {"type": "string"},
                    "title": {
                        "type": "string",
                        "description": "Short human-readable label shown in notifications.",
                    },
                },
                "required": ["agent_id", "prompt", "title"],
            },
        },
        "_meta": {
            "display_name": "提交后台任务",
            "side_effect": "write",
            "parallel_safe": False,
            "plan_mode_allowed": False,
            "subagent_exposable": False,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "data_platform_call",
            "description": (
                "Call a data-platform-mcp tool. The data platform provides "
                "35 tools across 8 modules: consistency (metric consistency), "
                "metric, dimension, dataset, table, metadata, domain, version. "
                "Pass the MCP tool name and its arguments as a JSON object. "
                "The server proxies the call to "
                "https://data-platform-mcp.mib.miui.com/mcp and returns the "
                "result as structured text. Use this whenever the user asks "
                "about 指标 / 维度 / 数据集 / 数据表 / 业务域 / 元数据 / "
                "版本管理 / 指标一致性检测."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": (
                            "MCP tool name, e.g. 'metadata_config_list', "
                            "'metric_list', 'domain_tree', "
                            "'consistency_overview'. See the data-platform-mcp "
                            "skill for the full list of 35 tools."
                        ),
                    },
                    "arguments": {
                        "type": "object",
                        "description": (
                            "Arguments for the MCP tool. Each tool has its own "
                            "schema; consult the skill docs for details."
                        ),
                    },
                },
                "required": ["tool_name"],
            },
        },
        "_meta": {
            "display_name": "数据平台 MCP 调用",
            "side_effect": "read",
            "parallel_safe": True,
            "plan_mode_allowed": True,
            "subagent_exposable": True,
        },
    },
]


_DEFAULT_META = {
    "display_name": "",
    "side_effect": "read",
    "parallel_safe": False,
    "plan_mode_allowed": False,
    "subagent_exposable": False,
}


def get_tool_meta(tool_name: str) -> dict:
    """Return the _meta dict for a tool, or a safe default if not found."""
    for t in BUILTIN_TOOL_SCHEMAS:
        if t["function"]["name"] == tool_name:
            merged = {**_DEFAULT_META, **(t.get("_meta") or {})}
            return merged
    return dict(_DEFAULT_META)


def get_anthropic_tools(
    *,
    plan_mode: bool = False,
    in_subagent: bool = False,
    feature_flags: dict | None = None,
    tool_whitelist: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    task_skill_ids: list[str] | None = None,
    spawn_targets: list[str] | None = None,
) -> list[dict]:
    """Convert BUILTIN_TOOL_SCHEMAS to Anthropic native tool schema.

    `plan_mode=True` drops tools whose _meta.plan_mode_allowed is False.
    `in_subagent=True` drops tools whose _meta.subagent_exposable is False
    (and thereby prevents sub-agents from spawning further sub-agents).
    `feature_flags` filters out v2 tools whose global flag is off; pass a dict
    like {"todo_write": True, "exit_plan_mode": False, "spawn_subagent": True,
    "run_background": False}. Missing keys default to True (tool stays on).
    `tool_whitelist` (when not None) restricts the output to names in the list;
    sourced from `agent.json.tools` so each agent can declare its own surface.
    None / missing field = no whitelist restriction (every tool stays).
    `disallowed_tools` removes tools after the whitelist is applied.
    `task_skill_ids` (when not None) rewrites the read_skill tool description
    so the LLM only sees the agentic skills bound to the current task — the
    hardcoded example list (kyuubi, nl-mapping-table-sql, ...) is replaced by the actual
    bound ids. Pass [] to advertise "no agentic skills bound". Pass None for
    contexts without a task (admin sandbox, scheduler one-shot completion).
    `spawn_targets` (when not None) constrains spawn_subagent.agent_id to a
    concrete enum of existing published agents the parent may spawn.
    """
    out = []
    whitelist_set = set(tool_whitelist) if tool_whitelist is not None else None
    disallowed_set = set(disallowed_tools or [])
    for t in BUILTIN_TOOL_SCHEMAS:
        fn = t["function"]
        meta = {**_DEFAULT_META, **(t.get("_meta") or {})}
        if fn["name"] in disallowed_set:
            continue
        if plan_mode and not meta["plan_mode_allowed"]:
            continue
        if in_subagent and not meta["subagent_exposable"]:
            continue
        if feature_flags is not None:
            flag = feature_flags.get(fn["name"])
            if flag is False:
                continue
        if fn["name"] == "spawn_subagent" and spawn_targets is not None and not spawn_targets:
            continue
        if whitelist_set is not None and fn["name"] not in whitelist_set:
            continue
        description = fn["description"]
        if task_skill_ids is not None and fn["name"] == "read_skill":
            description = _read_skill_description_for_task(task_skill_ids)
        input_schema = fn["parameters"]
        if fn["name"] == "spawn_subagent" and spawn_targets is not None:
            input_schema = copy.deepcopy(input_schema)
            props = input_schema.setdefault("properties", {})
            agent_prop = props.setdefault("agent_id", {"type": "string"})
            agent_prop["enum"] = list(spawn_targets)
            if spawn_targets:
                agent_prop["description"] = (
                    "The agent to delegate to. Must be one of the listed "
                    "existing spawn targets."
                )
            else:
                agent_prop["description"] = (
                    "No spawn targets are available in this context; do not call this tool."
                )
        out.append(
            {
                "name": fn["name"],
                "description": description,
                "input_schema": input_schema,
            }
        )
    return out


def _read_skill_description_for_task(task_skill_ids: list[str]) -> str:
    """Override the hardcoded example list in read_skill's schema with the
    skills actually bound to the current task. Keeps the call protocol /
    `path` semantics intact — only the example enumeration changes.
    """
    if not task_skill_ids:
        return (
            "Fetch the skill's instruction file. NOTE: this task has NO agentic "
            "skills bound — calling read_skill will return SKILL_NOT_FOUND for "
            "every skill_id. Ask the user to add a skill in the workspace "
            "「🧰 本任务 Skills」 panel first, then retry."
        )
    bound = ", ".join(f"`{sid}`" for sid in task_skill_ids)
    return (
        f"Fetch the skill's instruction file. This task has these agentic "
        f"skills bound: {bound}. Calling read_skill on any OTHER skill id "
        "returns SKILL_NOT_FOUND — only the listed ids are available. "
        "Default (no `path`) = returns SKILL.md. To read a sibling reference "
        "file that the SKILL.md points you to (e.g. `reference/browser/"
        "table-schema.md`), pass `path` with the relative path. Pass "
        "`path=\"/\"` or `path=\"ls\"` to list all files in the skill folder. "
        "Content is read from the task's own snapshot, so answers are "
        "reproducible even if the global skill is updated later."
    )


def get_display_name(tool_name: str) -> str:
    for t in BUILTIN_TOOL_SCHEMAS:
        if t["function"]["name"] == tool_name:
            return t["_meta"]["display_name"]
    return tool_name




# ---------------------------------------------------------------------------
# Tool implementations — extracted to tools/ subpackage for maintainability.
# Each module exports the _tool_* functions with the same signature.
# ---------------------------------------------------------------------------
from .tools.feishu import (  # noqa: F401
    _collect_task_xiaomi_emails,
    _feishu_perm_add,
    _feishu_refresh_user_token,
    _tool_feishu_publish,
    _tool_feishu_send_message,
    _tool_feishu_upload_image,
)
from .tools.file_ops import _tool_list_files, _tool_read_file, _tool_write_file  # noqa: F401
from .tools.knowledge import _tool_read_agent_knowledge, _tool_read_skill  # noqa: F401
from .tools.kyuubi import (  # noqa: F401
    _CONNECTION_MARKERS,
    _PERMISSION_MARKERS,
    _SYNTAX_MARKERS,
    _get_kyuubi_sem,
    _tool_kyuubi,
    classify_kyuubi_stderr,
)
from .tools.memory import _tool_memory_delete, _tool_memory_save, _tool_task_state_save  # noqa: F401
from .tools.misc import _tool_echo, _tool_now  # noqa: F401
from .tools.python_exec import _get_python_sem, _tool_execute_python  # noqa: F401
from .tools.volcano import _tool_volcano_abtest_analyze  # noqa: F401
from .tools.workflow import (  # noqa: F401
    _tool_create_scheduled_task,
    _tool_data_platform_call,
    _tool_exit_plan_mode,
    _tool_request_human_input,
    _tool_run_background,
    _tool_spawn_parallel,
    _tool_spawn_subagent,
    _tool_todo_write,
)

_DISPATCH = {
    "now": _tool_now,
    "echo": _tool_echo,
    "kyuubi_query": _tool_kyuubi,
    "write_file": _tool_write_file,
    "execute_python": _tool_execute_python,
    "list_files": _tool_list_files,
    "read_file": _tool_read_file,
    "feishu_send_message": _tool_feishu_send_message,
    "feishu_publish": _tool_feishu_publish,
    "volcano_abtest_analyze": _tool_volcano_abtest_analyze,
    "feishu_upload_image": _tool_feishu_upload_image,
    "read_skill": _tool_read_skill,
    "read_agent_knowledge": _tool_read_agent_knowledge,
    "memory_save": _tool_memory_save,
    "memory_delete": _tool_memory_delete,
    "task_state_save": _tool_task_state_save,
    "todo_write": _tool_todo_write,
    "request_human_input": _tool_request_human_input,
    "create_scheduled_task": _tool_create_scheduled_task,
    "exit_plan_mode": _tool_exit_plan_mode,
    "spawn_subagent": _tool_spawn_subagent,
    "spawn_parallel": _tool_spawn_parallel,
    "run_background": _tool_run_background,
    "data_platform_call": _tool_data_platform_call,
}


async def execute_tool(name: str, args: dict, ctx: dict | None = None) -> Any:
    """Dispatch a tool by name. Defense-in-depth: re-checks plan_mode and
    subagent constraints at runtime even if the schema filter let this call
    through (e.g. a stale tool_use_id from before mode flipped)."""
    fn = _DISPATCH.get(name)
    if not fn:
        return {"error_code": "TOOL_NOT_FOUND", "message": f"unknown tool: {name}"}
    meta = get_tool_meta(name)
    ctx_d = ctx or {}
    agent_id = (ctx_d.get("agent_id") or "").strip()
    if agent_id:
        from app.services.agent import agents_svc

        if name in agents_svc.get_agent_disallowed_tools(agent_id):
            return {
                "error_code": "TOOL_DISALLOWED",
                "message": f"'{name}' is disallowed by agent '{agent_id}'",
            }
        hook_result = _check_pre_tool_hooks(
            hooks=agents_svc.get_agent_hooks(agent_id),
            tool_name=name,
            args=args,
        )
        if hook_result is not None:
            return hook_result
        permission_result = _check_agent_permission(
            permission_mode=agents_svc.get_agent_permission_mode(agent_id),
            tool_name=name,
            meta=meta,
            ctx=ctx_d,
        )
        if permission_result is not None:
            return permission_result
    if ctx_d.get("plan_mode") and not meta["plan_mode_allowed"]:
        return {
            "error_code": "PLAN_MODE_BLOCKED",
            "message": (
                f"'{name}' has side-effects and is blocked in plan mode. "
                "Call exit_plan_mode once you have a concrete plan."
            ),
        }
    if ctx_d.get("subagent_depth", 0) > 0 and not meta["subagent_exposable"]:
        return {
            "error_code": "NOT_ALLOWED_IN_SUBAGENT",
            "message": f"'{name}' is not available inside a sub-agent",
        }
    result = await fn(args, ctx)
    if agent_id:
        await _emit_post_tool_hook_event(ctx_d, agent_id, name, result)
    return result


def _check_agent_permission(
    *,
    permission_mode: str,
    tool_name: str,
    meta: dict,
    ctx: dict,
) -> dict | None:
    side_effect = meta.get("side_effect") or "read"
    if permission_mode == "default" or side_effect == "read":
        return None
    if permission_mode == "read_only":
        return {
            "error_code": "PERMISSION_DENIED",
            "message": f"Agent permission_mode=read_only blocks '{tool_name}' ({side_effect}).",
        }
    approved = set(ctx.get("approved_side_effects") or [])
    if permission_mode == "confirm_write" and side_effect == "write" and "write" not in approved:
        return {
            "error_code": "PERMISSION_REQUIRED",
            "message": f"'{tool_name}' writes task state/files and requires user confirmation.",
            "side_effect": side_effect,
        }
    if permission_mode == "confirm_network" and side_effect in ("write", "network") and side_effect not in approved:
        return {
            "error_code": "PERMISSION_REQUIRED",
            "message": f"'{tool_name}' has side_effect={side_effect} and requires user confirmation.",
            "side_effect": side_effect,
        }
    return None


def _check_pre_tool_hooks(*, hooks: dict, tool_name: str, args: dict) -> dict | None:
    pre_hooks = hooks.get("pre_tool") or hooks.get("PreToolUse") or []
    if not isinstance(pre_hooks, list):
        return None
    for hook in pre_hooks:
        if not isinstance(hook, dict):
            continue
        pattern = hook.get("tool") or hook.get("tool_name") or hook.get("matcher")
        if pattern not in (None, "*", tool_name):
            continue
        if hook.get("block") is True:
            return {
                "error_code": "HOOK_BLOCKED",
                "message": hook.get("message") or f"pre_tool hook blocked '{tool_name}'",
                "hook": {k: v for k, v in hook.items() if k != "secret"},
            }
        required_args = hook.get("required_args")
        if isinstance(required_args, list):
            missing = [k for k in required_args if isinstance(k, str) and not args.get(k)]
            if missing:
                return {
                    "error_code": "HOOK_BLOCKED",
                    "message": hook.get("message") or f"missing required tool args: {missing}",
                    "missing_args": missing,
                }
    return None


async def _emit_post_tool_hook_event(ctx: dict, agent_id: str, tool_name: str, result: Any) -> None:
    emit = ctx.get("emit_event")
    if not callable(emit):
        return
    try:
        maybe = emit(
            {
                "type": "agent_hook_event",
                "hook": "post_tool",
                "agent_id": agent_id,
                "tool_name": tool_name,
                "success": not (isinstance(result, dict) and result.get("error_code")),
            }
        )
        if asyncio.iscoroutine(maybe):
            await maybe
    except Exception:
        pass
