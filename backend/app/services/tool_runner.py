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
import copy
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from ..core.config import get_settings
from ..core.errors import ErrorCode

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
    for t in BUILTIN_TOOL_SCHEMAS:
        fn = t["function"]
        meta = {**_DEFAULT_META, **(t.get("_meta") or {})}
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


async def _tool_now(_: dict, ctx: dict | None = None) -> Any:
    return {"now": datetime.now(tz=timezone.utc).isoformat()}


async def _tool_echo(args: dict, ctx: dict | None = None) -> Any:
    await asyncio.sleep(0.1)
    return {"echo": args.get("text", "")}


# Semaphore that throttles concurrent Kyuubi CLI invocations even when the
# outer tool loop fires multiple kyuubi_query calls in parallel. Lazy-init so
# `ICE_KYUUBI_CONCURRENCY` from .env takes effect on first use.
_kyuubi_sem: asyncio.Semaphore | None = None


def _get_kyuubi_sem() -> asyncio.Semaphore:
    global _kyuubi_sem
    if _kyuubi_sem is None:
        _kyuubi_sem = asyncio.Semaphore(max(1, get_settings().ICE_KYUUBI_CONCURRENCY))
    return _kyuubi_sem


async def _tool_kyuubi(args: dict, ctx: dict | None = None) -> Any:
    """Run a SQL query through the bundled `kyuubi` CLI.

    The connection context (region / workspace / catalog / engine / token) is
    pinned in server settings so the LLM never has to ask the user about it.
    Caller passes only `sql` (and optional `limit`).

    Records every attempt to sql_audit regardless of outcome.
    """
    import json as _json
    import os
    import shutil
    import time

    from . import sql_audit_svc

    sql = (args.get("sql") or "").strip()
    limit = int(args.get("limit") or 100)
    decision, reason = sql_audit_svc.classify(sql)
    started = time.monotonic()
    s = get_settings()

    conn_ctx = {
        "region": s.KYUUBI_REGION,
        "workspace": s.KYUUBI_WORKSPACE,
        "catalog": s.KYUUBI_CATALOG,
        "engine": s.KYUUBI_ENGINE,
    }

    out: Any
    error_message: str | None = None
    rows_returned: int | None = None

    cli_path = shutil.which("kyuubi")

    if decision == "block":
        out = {"error_code": "SQL_BLOCKED", "message": reason, "context": conn_ctx}
    elif not s.KYUUBI_TOKEN:
        out = {
            "error_code": ErrorCode.KYUUBI_NOT_CONFIGURED,
            "message": "Kyuubi 未配置：请管理员在 .env 设置 KYUUBI_TOKEN",
            "context": conn_ctx,
        }
    elif not cli_path:
        out = {
            "error_code": ErrorCode.KYUUBI_NOT_CONFIGURED,
            "message": (
                "Kyuubi CLI 未安装：请管理员在后端环境安装 `kyuubi` 命令行（pipx install xiaomi-kyuubi-cli）"
            ),
            "context": conn_ctx,
        }
    else:
        try:
            async with _get_kyuubi_sem():
                env = {**os.environ, "KYUUBI_APIKEY": s.KYUUBI_TOKEN}
                cmd = [
                    cli_path, "sql", "query", sql,
                    "--region", conn_ctx["region"],
                    "--workspace", conn_ctx["workspace"],
                    "--catalog", conn_ctx["catalog"],
                    "--engine", conn_ctx["engine"],
                    "--format", "json",
                    "--limit", str(limit),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                try:
                    stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=300.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    error_message = "kyuubi CLI timeout (300s)"
                    out = {"error_code": "KYUUBI_TIMEOUT", "message": error_message, "context": conn_ctx}
                else:
                    stdout_s = stdout_b.decode(errors="replace")
                    stderr_s = stderr_b.decode(errors="replace")
                    if proc.returncode != 0:
                        error_message = (stderr_s.strip() or f"kyuubi exit {proc.returncode}")[:600]
                        out = {
                            "error_code": "KYUUBI_CLI_ERROR",
                            "message": error_message,
                            "context": conn_ctx,
                        }
                    else:
                        try:
                            data = _json.loads(stdout_s)
                        except _json.JSONDecodeError:
                            out = {
                                "columns": [],
                                "rows": [],
                                "row_count": 0,
                                "raw_output": stdout_s.strip()[:4000],
                                "context": conn_ctx,
                                "warning": reason if decision == "warn" else None,
                            }
                        else:
                            cols = data.get("columns") or []
                            col_names = [c.get("name") if isinstance(c, dict) else c for c in cols]
                            rows = data.get("rows") or []
                            rows_returned = len(rows)
                            out = {
                                "columns": col_names,
                                "rows": rows[:limit],
                                "row_count": rows_returned,
                                "context": conn_ctx,
                                "warning": reason if decision == "warn" else None,
                            }
        except Exception as e:
            error_message = str(e)[:300]
            out = {"error_code": "KYUUBI_CLI_ERROR", "message": error_message, "context": conn_ctx}

    # 默认保存 SQL 文本与查询数据到任务工作区，供用户复用与审计。
    # 仅在查询成功且有行返回时保存；失败保存绝不影响主链路。
    if (
        rows_returned and rows_returned > 0
        and (ctx or {}).get("task_id") and (ctx or {}).get("user_id")
        and isinstance(out, dict) and "error_code" not in out
    ):
        try:
            from . import file_svc as _file_svc
            import csv as _csv
            import io as _io
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_uid = uuid.uuid4().hex[:6]
            sql_name = f"query_{ts_str}_{short_uid}.sql"
            csv_name = f"query_{ts_str}_{short_uid}.csv"
            await _file_svc.upload_task_file(
                task_id=ctx["task_id"], owner_id=ctx["user_id"],
                filename=sql_name, data=sql.encode("utf-8"), scope="output",
            )
            buf = _io.StringIO()
            writer = _csv.writer(buf)
            writer.writerow(out.get("columns") or [])
            for row in (out.get("rows") or []):
                writer.writerow(["" if v is None else v for v in row])
            await _file_svc.upload_task_file(
                task_id=ctx["task_id"], owner_id=ctx["user_id"],
                filename=csv_name, data=buf.getvalue().encode("utf-8"), scope="output",
            )
        except Exception:
            pass  # 静默：保存失败绝不阻塞 LLM 主链路

    try:
        await sql_audit_svc.record(
            user_id=(ctx or {}).get("user_id"),
            agent_id=(ctx or {}).get("agent_id"),
            task_id=(ctx or {}).get("task_id"),
            conversation_id=(ctx or {}).get("conversation_id"),
            sql=sql,
            decision=decision,
            block_reason=reason if decision != "allow" else None,
            error_message=error_message,
            rows_returned=rows_returned,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
    except Exception:
        pass
    return out


async def _tool_write_file(args: dict, ctx: dict | None = None) -> Any:
    """Write content into the task's workspace files/output and register it."""
    from . import file_svc

    name = (args.get("name") or "").strip()
    content = args.get("content") or ""
    if not name:
        return {"error_code": "VALIDATION_ERROR", "message": "name is required"}
    if not isinstance(content, str):
        return {"error_code": "VALIDATION_ERROR", "message": "content must be a string"}
    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "write_file is only available in a task context",
        }
    try:
        meta = await file_svc.upload_task_file(
            task_id=task_id,
            owner_id=user_id,
            filename=name,
            data=content.encode("utf-8"),
            scope="output",
        )
    except Exception as e:
        return {"error_code": "WRITE_FILE_FAILED", "message": str(e)[:300]}
    return {
        "saved": True,
        "file_id": meta["id"],
        "name": meta["name"],
        "size_bytes": meta["size_bytes"],
        "scope": "output",
        "path": meta["path"],
        "message": f"已保存到工作区：{meta['name']}（{meta['size_bytes']} bytes）",
    }


_python_sem: asyncio.Semaphore | None = None


def _get_python_sem() -> asyncio.Semaphore:
    global _python_sem
    if _python_sem is None:
        _python_sem = asyncio.Semaphore(
            max(1, get_settings().ICE_PYTHON_SANDBOX_CONCURRENCY)
        )
    return _python_sem


async def _tool_execute_python(args: dict, ctx: dict | None = None) -> Any:
    """Run Python code in the data-analysis sandbox.

    Inputs:
        code: full Python source (required)
        description: free-form audit string
        timeout_sec: optional override (capped at config max)

    Outputs:
        Same shape as SandboxResult.to_dict() plus registered file_ids for
        any new artifact under tasks/{tid}/files/output/. The frontend's
        left-side file panel picks up the registered files automatically.
    """
    from .sandbox import run_python, SandboxStatus
    from . import file_svc
    from ..core.storage.paths import get_paths

    s = get_settings()
    if not s.ICE_PYTHON_SANDBOX_ENABLED:
        return {
            "error_code": "PYTHON_SANDBOX_DISABLED",
            "message": "Python 沙箱已关闭：管理员需在 .env 设 ICE_PYTHON_SANDBOX_ENABLED=true",
        }

    code = args.get("code")
    if not isinstance(code, str) or not code.strip():
        return {"error_code": "VALIDATION_ERROR", "message": "code is required"}

    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "execute_python is only available in a task context",
        }

    timeout_req = args.get("timeout_sec")
    try:
        timeout_sec = int(timeout_req) if timeout_req is not None else s.ICE_PYTHON_SANDBOX_TIMEOUT_SEC
    except (TypeError, ValueError):
        timeout_sec = s.ICE_PYTHON_SANDBOX_TIMEOUT_SEC
    timeout_sec = max(5, min(timeout_sec, s.ICE_PYTHON_SANDBOX_TIMEOUT_SEC))

    paths = get_paths()
    task_dir = paths.task_dir(task_id)
    if not task_dir.exists():
        return {
            "error_code": "TASK_NOT_FOUND",
            "message": f"task workspace missing: {task_dir}",
        }

    try:
        async with _get_python_sem():
            result = await run_python(
                code,
                task_dir=task_dir,
                timeout_sec=timeout_sec,
                # allow_cli=True disables RLIMIT_AS in preexec; Node-based
                # CLIs (feishu / npx) reserve multi-GB virtual address space
                # for V8 + Wasm even when RSS stays small. Wall-clock timeout
                # + RLIMIT_CPU still bound runaway runs.
                memory_mb=s.ICE_PYTHON_SANDBOX_MEMORY_MB,
                fsize_mb=s.ICE_PYTHON_SANDBOX_FSIZE_MB,
                description=str(args.get("description") or "")[:200],
                allow_cli=True,
            )
    except Exception as exc:  # noqa: BLE001 — sandbox shouldn't crash the agent
        return {
            "error_code": "PYTHON_SANDBOX_ERROR",
            "message": str(exc)[:300],
        }

    payload = result.to_dict()

    # Register newly-created files under files/output/ with file_svc so the
    # frontend file panel picks them up. Only files inside files/output/ are
    # registered (the runner reports paths relative to that directory).
    registered: list[dict] = []
    if result.status == SandboxStatus.OK and result.files_created:
        out_root = paths.task_files_output(task_id)
        for f in result.files_created:
            full = out_root / f.relpath
            try:
                if not full.is_file():
                    continue
                data = full.read_bytes()
                # Filename in the registry uses just the basename. Keeping
                # subdir structure (charts/, models/, data/) on disk is fine,
                # but the file_svc registry is flat per task.
                meta = await file_svc.upload_task_file(
                    task_id=task_id,
                    owner_id=user_id,
                    filename=f.relpath.replace(os.sep, "_"),
                    data=data,
                    scope="output",
                )
                registered.append({
                    "relpath": f.relpath,
                    "file_id": meta["id"],
                    "size_bytes": meta["size_bytes"],
                    "kind": f.kind,
                })
            except Exception:  # noqa: BLE001
                # don't fail the whole tool call on file registration error
                continue

    payload["registered_files"] = registered
    return payload


_VOLCANO_MEDIA_ALIASES = {
    "浏览器": "browser",
    "browser": "browser",
    "内容中心": "newhome",
    "桌面内容中心": "newhome",
    "newhome": "newhome",
    "nh": "newhome",
    "mcc": "newhome",
}


async def _tool_volcano_abtest_analyze(args: dict, ctx: dict | None = None) -> Any:
    """Run agents/volcano-abtest/scripts/analyze.py via the host `datum` CLI.

    Parameters are validated and forwarded as `-m / -e / -s / -d` args.
    The script's stdout (markdown report) is captured. On success the report
    is saved to the task's files/output/ so it appears in the file panel.

    Failure modes (returned as error_code envelopes — never raises):
      DATUM_NOT_INSTALLED   — datum CLI not on PATH
      ANALYZE_SCRIPT_MISSING — analyze.py not found under agents/volcano-abtest
      VALIDATION_ERROR       — bad params
      VOLCANO_ABTEST_TIMEOUT — script exceeded 320s
      VOLCANO_ABTEST_FAILED  — non-zero exit; stderr returned in `message`
    """
    import os
    import shutil
    import sys

    from . import file_svc
    from ..core.storage.paths import get_paths

    media_raw = (args.get("media") or "").strip()
    exp_id = (args.get("exp_id") or "").strip()
    start_date = (args.get("start_date") or "").strip()
    end_date = (args.get("end_date") or "").strip()
    if not (media_raw and exp_id and start_date and end_date):
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "media, exp_id, start_date, end_date are all required",
        }
    media = _VOLCANO_MEDIA_ALIASES.get(media_raw, media_raw.lower())
    if media not in ("browser", "newhome"):
        return {
            "error_code": "VALIDATION_ERROR",
            "message": (
                f"未知 media '{media_raw}'，可选：浏览器/browser、"
                "内容中心/桌面内容中心/newhome/nh/mcc"
            ),
        }
    if not exp_id.isdigit():
        return {
            "error_code": "VALIDATION_ERROR",
            "message": f"exp_id 必须为纯数字，收到 '{exp_id}'",
        }

    if not shutil.which("datum"):
        return {
            "error_code": "DATUM_NOT_INSTALLED",
            "message": (
                "datum CLI 未安装：请管理员在后端环境安装 datum 命令行（参见 skills/datum-cli/SKILL.md）"
            ),
        }

    paths = get_paths()
    script = paths.agents / "volcano-abtest" / "scripts" / "analyze.py"
    if not script.is_file():
        return {
            "error_code": "ANALYZE_SCRIPT_MISSING",
            "message": f"未找到分析脚本：{script}",
        }

    cmd = [
        sys.executable, str(script),
        "-m", media,
        "-e", exp_id,
        "-s", start_date,
        "-d", end_date,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=320.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "error_code": "VOLCANO_ABTEST_TIMEOUT",
                "message": "analyze.py 超时（320s），通常是 datum 查询排队或权限问题",
            }
    except FileNotFoundError as exc:
        return {"error_code": "VOLCANO_ABTEST_FAILED", "message": str(exc)[:300]}

    stdout_s = stdout_b.decode(errors="replace")
    stderr_s = stderr_b.decode(errors="replace")
    if proc.returncode != 0:
        return {
            "error_code": "VOLCANO_ABTEST_FAILED",
            "message": (stderr_s.strip() or f"analyze.py exit {proc.returncode}")[:1200],
            "exit_code": proc.returncode,
        }

    report_md = stdout_s.strip()
    if not report_md:
        return {
            "error_code": "VOLCANO_ABTEST_EMPTY",
            "message": "脚本未输出报告内容（可能查询无数据）",
            "stderr": stderr_s.strip()[:600],
        }

    # 落盘到任务工作区，与 kyuubi_query 的行为一致。
    saved_meta: dict | None = None
    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if task_id and user_id:
        try:
            fname = f"abtest_{media}_{exp_id}_{start_date}-{end_date}.md"
            saved_meta = await file_svc.upload_task_file(
                task_id=task_id,
                owner_id=user_id,
                filename=fname,
                data=report_md.encode("utf-8"),
                scope="output",
            )
        except Exception:
            saved_meta = None

    return {
        "report_md": report_md,
        "media": media,
        "exp_id": exp_id,
        "start_date": start_date,
        "end_date": end_date,
        "file_id": (saved_meta or {}).get("id"),
        "file_name": (saved_meta or {}).get("name"),
        "stderr_tail": stderr_s.strip()[-400:] if stderr_s else "",
    }


_VALID_PERM_LEVELS = {"view", "edit", "full_access"}


async def _feishu_perm_add(
    cli: str, doc_token: str, email: str, perm: str
) -> tuple[bool, str]:
    """Run `feishu perm add` for a single email. Returns (ok, message)."""
    proc = await asyncio.create_subprocess_exec(
        cli, "perm", "add", doc_token,
        "--type", "docx",
        "--member-type", "email",
        "--member-id", email,
        "--perm", perm,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=20.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, f"timeout (20s) for {email}"
    err_s = err_b.decode(errors="replace").strip()
    if proc.returncode == 0:
        return True, ""
    return False, (err_s or f"exit {proc.returncode}")[:200]


def _collect_task_xiaomi_emails(task_id: str) -> list[str]:
    """Pull the task owner's + active collaborators' xiaomi_email values.

    Returns deduped lowercase list. Silent on missing fields — users without
    a xiaomi_email simply skip auto-perm and the report stays inaccessible
    to them via this channel (the AccountModal banner nudges them to add it).
    """
    from ..core.storage import read_json as _read_json
    from ..core.storage.paths import get_paths as _gp

    paths = _gp()
    meta = _read_json(paths.task_meta(task_id)) or {}
    collabs = _read_json(paths.task_collaborators(task_id)) or []

    user_ids: list[str] = []
    owner_id = meta.get("owner_id") or meta.get("user_id")
    if owner_id:
        user_ids.append(owner_id)
    for c in collabs:
        if isinstance(c, dict) and c.get("status") == "active" and c.get("user_id"):
            user_ids.append(c["user_id"])

    seen: set[str] = set()
    emails: list[str] = []
    for uid in user_ids:
        if uid in seen:
            continue
        seen.add(uid)
        prof = _read_json(paths.user_profile(uid)) or {}
        xe = (prof.get("xiaomi_email") or "").strip().lower()
        if xe and xe not in emails:
            emails.append(xe)
    return emails


async def _tool_feishu_publish(args: dict, ctx: dict | None = None) -> Any:
    """Create a Feishu doc via the bundled `feishu` CLI.

    Three layers of access provisioning, applied in order:
      A. Default location → team wiki space (FEISHU_DEFAULT_WIKI_SPACE_ID),
         so every space member has read perms by default.
      B. After create, perm-add the task owner + active collaborators
         (their xiaomi_email) at FEISHU_AUTO_PERM_LEVEL.
      C. Anything in `share_to` gets perm-add at `share_perm` (default edit).

    Per-call args can override the location (wiki_space / wiki_node / folder).
    Perm-add failures are warnings, never fatal — the doc stays usable.
    """
    import json as _json
    import shutil
    import tempfile
    from pathlib import Path

    title = (args.get("title") or "").strip()
    markdown = args.get("markdown") or ""
    if not title:
        return {"error_code": "VALIDATION_ERROR", "message": "title is required"}
    cli = shutil.which("feishu")
    if not cli:
        return {
            "error_code": "FEISHU_CLI_NOT_INSTALLED",
            "message": "feishu CLI 未安装；请管理员在后端环境安装 feishu 命令行",
        }

    settings = get_settings()
    # Resolve location: per-call > env default. Three options are mutually
    # exclusive — first truthy wins.
    wiki_space = (args.get("wiki_space") or "").strip()
    wiki_node = (args.get("wiki_node") or "").strip()
    folder_token = (args.get("folder") or "").strip()
    if not (wiki_space or wiki_node or folder_token):
        wiki_space = (settings.FEISHU_DEFAULT_WIKI_SPACE_ID or "").strip()
        if not wiki_space:
            folder_token = (settings.FEISHU_DEFAULT_FOLDER_TOKEN or "").strip()

    extra_args: list[str] = []
    if wiki_node:
        extra_args = ["--wiki-node", wiki_node]
    elif wiki_space:
        extra_args = ["--wiki-space", wiki_space]
    elif folder_token:
        extra_args = ["--folder", folder_token]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(markdown)
        tmp_path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            cli, "docx", "create", title, "-f", tmp_path, *extra_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=90.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"error_code": "FEISHU_CLI_TIMEOUT", "message": "feishu CLI timeout (90s)"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    out_s = out_b.decode(errors="replace")
    err_s = err_b.decode(errors="replace")
    # Reference impl: rc 0/2/3 all carry a usable doc_token; 2/3 = warnings only.
    if proc.returncode not in (0, 2, 3):
        return {
            "error_code": "FEISHU_CLI_ERROR",
            "message": (err_s.strip() or f"feishu exit {proc.returncode}")[:600],
        }
    try:
        data = _json.loads(out_s)
    except _json.JSONDecodeError:
        return {"raw_output": out_s.strip()[:2000]}

    doc_token = data.get("doc_token", "")
    location = (
        f"wiki_space={wiki_space}" if wiki_space
        else f"wiki_node={wiki_node}" if wiki_node
        else f"folder={folder_token}" if folder_token
        else "personal"
    )

    # ----- Auto-permission step (A's tail-end + B + C) -----
    perm_results: list[dict] = []
    perm_warnings: list[str] = []
    if doc_token:
        task_id = (ctx or {}).get("task_id")
        # B: task owner + active collaborators (deduped)
        auto_level = (settings.FEISHU_AUTO_PERM_LEVEL or "").strip().lower()
        auto_emails: list[str] = []
        if task_id and auto_level in _VALID_PERM_LEVELS:
            try:
                auto_emails = _collect_task_xiaomi_emails(task_id)
            except Exception as exc:
                perm_warnings.append(f"collect collaborators failed: {exc!s}"[:200])

        # C: explicit share_to from the caller
        share_perm_raw = (args.get("share_perm") or "edit").strip().lower()
        share_perm = share_perm_raw if share_perm_raw in _VALID_PERM_LEVELS else "edit"
        share_to_raw = args.get("share_to") or []
        share_to: list[str] = []
        if isinstance(share_to_raw, list):
            for x in share_to_raw:
                if isinstance(x, str):
                    e = x.strip().lower()
                    if e and e not in share_to:
                        share_to.append(e)

        # Run sequentially — perm add is fast (<1s typical) and tiny per
        # team, but parallel would mean N concurrent CLI procs spawning
        # subprocesses on the host; not worth the variance.
        targets: list[tuple[str, str]] = []  # (email, perm)
        for em in auto_emails:
            targets.append((em, auto_level))
        for em in share_to:
            if not any(em == e for e, _ in targets):
                targets.append((em, share_perm))

        for em, p in targets:
            ok, msg = await _feishu_perm_add(cli, doc_token, em, p)
            perm_results.append({"email": em, "perm": p, "ok": ok, "error": msg or None})
            if not ok:
                perm_warnings.append(f"{em} ({p}): {msg}"[:200])

    # Surface CLI's content-write warnings (e.g. "Whiteboard write failed: 404"
    # when Feishu app lacks PlantUML scope — produces empty 「空白画板」 in the doc).
    # Without this, the agent flies blind and can't retry with PNG charts.
    cli_warnings = data.get("warnings") or []
    if not isinstance(cli_warnings, list):
        cli_warnings = [str(cli_warnings)]

    hint: str | None = None
    if any("Whiteboard write failed" in w for w in cli_warnings):
        hint = (
            "飞书 mermaid 渲染失败（whiteboard PlantUML scope 未开通），文档里 "
            "mermaid block 全部是空白画板。请用 execute_python 出 PNG 图表落到 "
            "files/output/charts/，再调 feishu_upload_image 嵌入；不要在 markdown "
            "里写 ```mermaid``` 块。"
        )

    return {
        "url": data.get("url", ""),
        "doc_token": doc_token,
        "title": title,
        "location": location,
        "blocks_added": data.get("blocks_added"),
        "images_processed": data.get("images_processed"),
        "whiteboards_created": data.get("whiteboards_created"),
        "content_warnings": cli_warnings or None,
        "hint": hint,
        "perm_grants": perm_results,
        "perm_warnings": perm_warnings or None,
        "warning": err_s.strip() if proc.returncode in (2, 3) else None,
    }


async def _tool_feishu_upload_image(args: dict, ctx: dict | None = None) -> Any:
    """Upload a PNG/JPG from the task workspace to a Feishu doc.

    Wraps `feishu docx upload-image <doc_token> --file <path>`.
    Path must resolve under <task_workspace>/files/output/ — absolute escapes
    are rejected. Returns image_token (used for embedding) + raw stdout.
    """
    import json as _json
    import shutil
    from pathlib import Path

    from ..core.storage.paths import get_paths

    doc_token = (args.get("doc_token") or "").strip()
    rel = (args.get("image_path") or "").strip()
    if not doc_token or not rel:
        return {"error_code": "VALIDATION_ERROR", "message": "doc_token and image_path are required"}
    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "feishu_upload_image needs a task context"}

    cli = shutil.which("feishu")
    if not cli:
        return {
            "error_code": "FEISHU_CLI_NOT_INSTALLED",
            "message": "feishu CLI 未安装；请管理员在后端环境安装 feishu 命令行",
        }

    # Resolve image_path against task output dir; reject escapes.
    paths = get_paths()
    out_root = paths.task_files_output(task_id).resolve()
    candidate = (out_root / rel).resolve()
    try:
        candidate.relative_to(out_root)
    except ValueError:
        return {
            "error_code": "PATH_OUTSIDE_TASK_WORKSPACE",
            "message": f"image_path must be under {out_root}",
        }
    if not candidate.is_file():
        return {
            "error_code": "FILE_NOT_FOUND",
            "message": f"image not found: {rel}",
        }
    if candidate.stat().st_size > 10 * 1024 * 1024:
        return {
            "error_code": "IMAGE_TOO_LARGE",
            "message": f"image > 10MB: {rel}",
        }

    proc = await asyncio.create_subprocess_exec(
        cli, "docx", "upload-image", doc_token, "--file", str(candidate),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=60.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"error_code": "FEISHU_CLI_TIMEOUT", "message": "feishu upload-image timeout (60s)"}

    out_s = out_b.decode(errors="replace")
    err_s = err_b.decode(errors="replace")
    if proc.returncode != 0:
        return {
            "error_code": "FEISHU_CLI_ERROR",
            "message": (err_s.strip() or f"feishu exit {proc.returncode}")[:600],
        }
    try:
        data = _json.loads(out_s)
    except _json.JSONDecodeError:
        # CLI may print plain token; normalize
        token = out_s.strip().split()[-1] if out_s.strip() else ""
        return {"image_token": token, "raw_output": out_s.strip()[:600]}
    return {
        "image_token": data.get("image_token") or data.get("token") or "",
        "doc_token": doc_token,
        "image_path": rel,
        "raw": data,
    }


async def _tool_list_files(args: dict, ctx: dict | None = None) -> Any:
    """List every file in the current task workspace."""
    from . import file_svc

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "list_files needs a task context"}
    scope = (args.get("scope") or "all").lower()
    if scope not in ("all", "uploaded", "input", "output"):
        return {"error_code": "VALIDATION_ERROR", "message": f"invalid scope: {scope}"}
    items = await file_svc.list_task_files(task_id)
    if scope != "all":
        items = [m for m in items if m.get("scope") == scope]
    out = [
        {
            "id": m["id"],
            "name": m["name"],
            "scope": m.get("scope"),
            "format": m.get("format"),
            "size_bytes": m.get("size_bytes"),
            "created_at": m.get("created_at"),
        }
        for m in items
    ]
    return {"files": out, "total": len(out), "scope": scope}


async def _tool_read_file(args: dict, ctx: dict | None = None) -> Any:
    """Read a workspace file by id or name."""
    from . import file_svc
    from ..core.errors import APIError

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "read_file needs a task context"}

    file_id = (args.get("id") or "").strip()
    name = (args.get("name") or "").strip()
    if not file_id and not name:
        return {"error_code": "VALIDATION_ERROR", "message": "id 或 name 至少给一个"}

    if not file_id:
        items = await file_svc.list_task_files(task_id)
        # 同名按时间倒序，取最新（list_task_files 已按 created_at desc）
        match = next((m for m in items if m.get("name") == name), None)
        if not match:
            return {
                "error_code": "FILE_NOT_FOUND",
                "message": f"工作区里没有名为 `{name}` 的文件，请先用 list_files 查看。",
            }
        file_id = match["id"]

    try:
        result = await file_svc.read_file_text(task_id, file_id)
    except APIError as e:
        return {"error_code": e.error_code, "message": e.message}

    meta = result.get("meta") or {}
    if result.get("binary"):
        return {
            "id": file_id,
            "name": meta.get("name"),
            "scope": meta.get("scope"),
            "format": meta.get("format"),
            "is_binary": True,
            "size_bytes": meta.get("size_bytes"),
            "message": "二进制文件，无法以文本形式返回。",
        }
    return {
        "id": file_id,
        "name": meta.get("name"),
        "scope": meta.get("scope"),
        "format": meta.get("format"),
        "size_bytes": meta.get("size_bytes"),
        "content": result.get("content") or "",
    }


_KNOWLEDGE_TEXT_EXTS = {".yaml", ".yml", ".md", ".json", ".txt", ".sql"}
_KNOWLEDGE_MAX_BYTES = 200 * 1024  # 200KB


async def _tool_read_agent_knowledge(args: dict, ctx: dict | None = None) -> Any:
    """Read a file from agents/<agent_id>/knowledge/<path>.

    Security: rejects absolute paths, traversal ('..'), and anything resolving
    outside the agent's knowledge directory. Rejects binary extensions; caps
    size at 200KB.
    """
    from ..core.storage import get_paths

    agent_id = (ctx or {}).get("agent_id")
    if not agent_id:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "read_agent_knowledge needs an agent context",
        }

    raw = (args.get("path") or "").strip()
    if not raw:
        return {"error_code": "VALIDATION_ERROR", "message": "path is required"}

    from pathlib import Path, PurePosixPath

    pp = PurePosixPath(raw)
    if pp.is_absolute() or any(part == ".." for part in pp.parts):
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "path must be relative and must not contain '..'",
        }

    base = (get_paths().agents / agent_id / "knowledge").resolve()
    if not base.exists():
        return {
            "error_code": "KNOWLEDGE_NOT_FOUND",
            "message": f"agent '{agent_id}' has no knowledge/ directory",
        }

    target = (base / raw).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return {
            "error_code": "VALIDATION_ERROR",
            "message": "path escapes the knowledge directory",
        }

    if not target.exists() or not target.is_file():
        return {
            "error_code": "FILE_NOT_FOUND",
            "message": f"knowledge file not found: {raw}",
        }

    ext = target.suffix.lower()
    if ext not in _KNOWLEDGE_TEXT_EXTS:
        return {
            "error_code": "UNSUPPORTED_FORMAT",
            "message": (
                f"binary/unsupported extension: {ext}. "
                f"Supported: {sorted(_KNOWLEDGE_TEXT_EXTS)}"
            ),
        }

    size = target.stat().st_size
    if size > _KNOWLEDGE_MAX_BYTES:
        return {
            "error_code": "FILE_TOO_LARGE",
            "message": f"{raw} is {size} bytes (limit {_KNOWLEDGE_MAX_BYTES})",
        }

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "error_code": "ENCODING_ERROR",
            "message": f"{raw} is not valid UTF-8",
        }
    except OSError as e:
        return {"error_code": "READ_FAILED", "message": str(e)[:300]}

    return {
        "agent_id": agent_id,
        "path": raw,
        "size_bytes": size,
        "content": content,
    }


async def _tool_read_skill(args: dict, ctx: dict | None = None) -> Any:
    """Return skill content. Resolution rule:
      - inside a task (ctx.task_id present): ONLY tasks/<task_id>/skills/<sid>/.
        Skills not bound to the task are invisible — call returns SKILL_NOT_FOUND
        even if the same skill exists in the global catalog.
      - outside a task (admin sandbox / test_run): falls back to global skills/<sid>/.

    Supports `path` arg:
      - omitted or empty → SKILL.md
      - 'ls' / '/' → list files in the skill dir
      - otherwise → the relative file (e.g. 'reference/browser/table-schema.md')

    Path traversal (..), absolute paths, and symlinks outside the skill dir
    are rejected.
    """
    from pathlib import Path
    from ..core.storage import get_paths

    sid = (args.get("skill_id") or "").strip()
    if not sid:
        return {"error_code": "VALIDATION_ERROR", "message": "skill_id is required"}
    rel = (args.get("path") or "").strip().lstrip("/")

    task_id = (ctx or {}).get("task_id")
    paths = get_paths()

    base: Path | None = None
    source: str
    if task_id:
        candidate = paths.task_skills_dir(task_id) / sid
        source = "task"
        if candidate.exists() and candidate.is_dir():
            base = candidate.resolve()
    else:
        candidate = paths.skills / sid
        source = "global"
        if candidate.exists() and candidate.is_dir():
            base = candidate.resolve()

    if base is None:
        if task_id:
            bound: list[str] = []
            skills_root = paths.task_skills_dir(task_id)
            if skills_root.exists():
                bound = sorted(p.name for p in skills_root.iterdir() if p.is_dir())
            hint = (
                f"未在本任务的 Skills 列表里找到 '{sid}'。"
                f"已绑定的 skill：{bound or '（无）'}。"
                "如需使用，请在工作区右栏「🧰 本任务 Skills」点击 +添加。"
            )
            return {
                "error_code": "SKILL_NOT_FOUND",
                "message": hint,
                "bound_skill_ids": bound,
            }
        return {
            "error_code": "SKILL_NOT_FOUND",
            "message": f"skill '{sid}' not found in global catalog",
        }

    # "ls" or "/" → directory listing
    if rel in ("", "ls", "/") and (args.get("path") in ("ls", "/")):
        entries = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rp = p.relative_to(base).as_posix()
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            entries.append({"path": rp, "size": sz})
        return {
            "skill_id": sid,
            "source": source,
            "files": entries,
            "total": len(entries),
        }

    # No path → SKILL.md (legacy behavior)
    target_rel = rel or "SKILL.md"
    if ".." in target_rel.split("/") or target_rel.startswith("/"):
        return {"error_code": "VALIDATION_ERROR", "message": "path 非法"}
    target = (base / target_rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return {"error_code": "VALIDATION_ERROR", "message": "path 越界"}
    if not target.exists() or not target.is_file():
        return {
            "error_code": "SKILL_FILE_NOT_FOUND",
            "message": f"skill '{sid}' 内无文件 '{target_rel}'（试试 path=ls 看全部）",
        }
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error_code": "SKILL_BINARY", "message": f"'{target_rel}' 是二进制文件"}
    except OSError as e:
        return {"error_code": "SKILL_READ_FAILED", "message": str(e)[:300]}
    return {
        "skill_id": sid,
        "source": source,
        "path": target_rel,
        "size_bytes": len(text.encode("utf-8")),
        "content": text,
    }


# ──────────────────────── v2 tool dispatches ─────────────────────────────


async def _tool_todo_write(args: dict, ctx: dict | None = None) -> Any:
    """Replace-all write of the task-level todo list. Sends a WS `todos_updated`
    event to the caller when a send_event callback is present in ctx."""
    from ..core.storage import file_transaction, get_paths

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "todo_write needs a task context"}

    raw_items = args.get("items")
    # Compatibility for older prompts / model slips that send
    # {"todos": "[...]"} or {"todos": [...]} even though the schema says
    # `items`. Keeping this here makes the progress panel resilient without
    # broadening the advertised contract.
    if raw_items is None and "todos" in args:
        raw_items = args.get("todos")
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except json.JSONDecodeError:
                return {"error_code": "VALIDATION_ERROR", "message": "todos must be valid JSON array"}
    if not isinstance(raw_items, list):
        return {"error_code": "VALIDATION_ERROR", "message": "items must be an array"}

    normalized: list[dict] = []
    seen_in_progress = 0
    for idx, it in enumerate(raw_items):
        if not isinstance(it, dict):
            return {"error_code": "VALIDATION_ERROR", "message": f"items[{idx}] must be an object"}
        content = (it.get("content") or "").strip()
        active = (it.get("activeForm") or "").strip()
        status = (it.get("status") or "pending").strip()
        if not content:
            return {"error_code": "VALIDATION_ERROR", "message": f"items[{idx}].content required"}
        if status not in ("pending", "in_progress", "completed"):
            return {"error_code": "VALIDATION_ERROR", "message": f"items[{idx}].status invalid"}
        if status == "in_progress":
            seen_in_progress += 1
        normalized.append(
            {
                "id": it.get("id") or f"t{idx + 1}",
                "content": content,
                "activeForm": active or content,
                "status": status,
            }
        )

    now_iso = datetime.now(tz=timezone.utc).isoformat()
    payload = {
        "task_id": task_id,
        "updated_at": now_iso,
        "updated_by_conv_id": (ctx or {}).get("conversation_id"),
        "items": normalized,
    }
    paths = get_paths()
    todo_path = paths.task_todos(task_id)
    todo_path.parent.mkdir(parents=True, exist_ok=True)
    with file_transaction([todo_path]) as tx:
        tx.write_json(todo_path, payload)

    # Notify the WS if the handler wired an emit callback into ctx.
    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit(
                {
                    "type": "todos_updated",
                    "task_id": task_id,
                    "items": normalized,
                    "updated_at": now_iso,
                }
            )
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass

    return {
        "updated": True,
        "count": len(normalized),
        "in_progress": seen_in_progress,
        "updated_at": now_iso,
    }


async def _tool_exit_plan_mode(args: dict, ctx: dict | None = None) -> Any:
    """Emit the proposed plan and flag the current round for termination.

    The actual plan_mode → live-mode transition happens in ws.py when the user
    approves via the frontend modal; here we just persist the plan_id and emit
    a `plan_proposed` event. The outer round loop checks a flag set on ctx to
    break without re-invoking the LLM.
    """
    import uuid

    plan = (args.get("plan") or "").strip()
    if not plan:
        return {"error_code": "VALIDATION_ERROR", "message": "plan is required"}

    task_id = (ctx or {}).get("task_id")
    conv_id = (ctx or {}).get("conversation_id")
    if not task_id or not conv_id:
        return {"error_code": "VALIDATION_ERROR", "message": "exit_plan_mode needs a conv context"}

    plan_id = f"p_{uuid.uuid4().hex[:12]}"

    # Persist plan_id onto the conversation meta via conversation_svc (lazy import).
    try:
        from . import conversation_svc

        await conversation_svc.set_pending_plan(task_id=task_id, conv_id=conv_id, plan_id=plan_id, plan_text=plan)
    except Exception as exc:
        return {"error_code": "PLAN_PERSIST_FAILED", "message": str(exc)[:300]}

    # Ask the round loop to break (the ws.py handler checks this key).
    if ctx is not None:
        ctx["_plan_proposed"] = {"plan_id": plan_id, "plan_text": plan}

    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit(
                {
                    "type": "plan_proposed",
                    "plan_id": plan_id,
                    "plan_text": plan,
                }
            )
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass

    return {"waiting_for_approval": True, "plan_id": plan_id}


async def _tool_request_human_input(args: dict, ctx: dict | None = None) -> Any:
    from . import hitl_svc

    task_id = (ctx or {}).get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "request_human_input needs a task context"}
    title = (args.get("title") or "").strip()
    message = (args.get("message") or "").strip()
    if not title or not message:
        return {"error_code": "VALIDATION_ERROR", "message": "title and message are required"}

    req = await hitl_svc.create_request(
        task_id=task_id,
        conv_id=(ctx or {}).get("conversation_id"),
        created_by=(ctx or {}).get("user_id"),
        title=title,
        message=message,
        fields=args.get("fields") if isinstance(args.get("fields"), list) else None,
        table=args.get("table") if isinstance(args.get("table"), dict) else None,
        actions=args.get("actions") if isinstance(args.get("actions"), list) else None,
        resume_prompt=args.get("resume_prompt"),
        source="tool",
    )

    emit = (ctx or {}).get("emit_event")
    if callable(emit):
        try:
            maybe = emit({"type": "hitl_requested", "request": req})
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass
    return {"waiting_for_human": True, "request": req}


async def _tool_spawn_subagent(args: dict, ctx: dict | None = None) -> Any:
    """Run a bounded sub-agent and return only its final text."""
    import uuid

    from . import agent_runtime, agents_svc, experience_card_svc
    from ..core.storage import append_jsonl, get_paths

    agent_id = (args.get("agent_id") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    if not agent_id or not prompt:
        return {"error_code": "VALIDATION_ERROR", "message": "agent_id and prompt are required"}

    s = get_settings()
    if not s.ICE_SUBAGENT_ENABLED:
        return {"error_code": "SUBAGENT_DISABLED", "message": "sub-agent delegation is not enabled"}

    parent_ctx = ctx or {}
    depth = int(parent_ctx.get("subagent_depth") or 0)
    if depth >= s.ICE_SUBAGENT_MAX_DEPTH:
        return {
            "error_code": "SUBAGENT_DEPTH_EXCEEDED",
            "message": f"sub-agent depth limit is {s.ICE_SUBAGENT_MAX_DEPTH}",
        }

    task_id = parent_ctx.get("task_id")
    if not task_id:
        return {"error_code": "VALIDATION_ERROR", "message": "spawn_subagent needs a task context"}

    # Verify the target agent exists. (get_agent is sync — earlier code awaited
    # it and the resulting TypeError got swallowed, so the check was dead.)
    if not agents_svc.get_agent(agent_id):
        return {"error_code": "AGENT_NOT_FOUND", "message": f"agent '{agent_id}' not found"}
    parent_agent_id = (parent_ctx.get("agent_id") or "").strip()
    if parent_agent_id:
        allowed_targets = agents_svc.list_spawnable_agent_ids(parent_agent_id)
        if agent_id not in allowed_targets:
            return {
                "error_code": "AGENT_NOT_ALLOWED",
                "message": f"agent '{agent_id}' is not an allowed spawn target for '{parent_agent_id}'",
                "allowed_targets": allowed_targets,
            }

    run_id = f"sub_{uuid.uuid4().hex[:12]}"
    paths = get_paths()
    transcript_path = paths.task_subagent_run(task_id, run_id)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    async def _emit_subagent_event(
        *,
        label: str,
        status: str = "running",
        detail: str | None = None,
    ) -> None:
        emit = parent_ctx.get("emit_event")
        if not callable(emit):
            return
        try:
            maybe = emit(
                {
                    "type": "run_event",
                    "run_id": run_id,
                    "stage": "subagent",
                    "label": label,
                    "status": status,
                    "detail": detail,
                    "payload": {"agent_id": agent_id},
                    "created_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            )
            if asyncio.iscoroutine(maybe):
                await maybe
        except Exception:
            pass

    from ..core.storage import read_json as _read_json
    parent_meta = _read_json(paths.task_meta(task_id)) or {}
    parent_skill_ids = list(parent_meta.get("skill_ids") or [])
    # Effective tool whitelist for the child = intersection of:
    #   1. the child agent's own `agent.json.tools` (None if unrestricted)
    #   2. parent-passed `allowed_tools` arg (LLM's runtime choice)
    # Both None ⇒ no whitelist (the child gets every subagent-exposable tool).
    child_whitelist = agents_svc.get_agent_tools(agent_id)
    parent_allowed = args.get("allowed_tools") if isinstance(args.get("allowed_tools"), list) else None
    if child_whitelist is not None and parent_allowed is not None:
        effective_whitelist = [t for t in child_whitelist if t in parent_allowed]
    else:
        effective_whitelist = child_whitelist if child_whitelist is not None else parent_allowed
    tools = get_anthropic_tools(
        in_subagent=True,
        tool_whitelist=effective_whitelist,
        task_skill_ids=parent_skill_ids,
    )
    system_prompt = experience_card_svc.merged_system_prompt(
        agent_id,
        task_skill_ids=parent_skill_ids,
        callable_tool_names=[t["name"] for t in tools],
    )

    child_ctx = {
        "user_id": parent_ctx.get("user_id"),
        "agent_id": agent_id,
        "task_id": task_id,
        "conversation_id": f"{parent_ctx.get('conversation_id', 'main')}::{run_id}",
        "subagent_depth": depth + 1,
        "plan_mode": False,
    }

    append_jsonl(
        transcript_path,
        {
            "event": "spawn",
            "run_id": run_id,
            "parent_conv": parent_ctx.get("conversation_id"),
            "parent_agent": parent_ctx.get("agent_id"),
            "agent_id": agent_id,
            "prompt": prompt,
            "at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )

    started = datetime.now(tz=timezone.utc)
    # Per-message arg > child agent's agent.json.model > runtime default.
    child_model = args.get("model") or agents_svc.get_agent_model(agent_id)
    try:
        await _emit_subagent_event(label=f"子 Agent {agent_id} 开始执行")
        result = await asyncio.wait_for(
            agent_runtime.run_agent_turn(
                system_prompt=system_prompt,
                initial_messages=[{"role": "user", "content": prompt}],
                tools=tools,
                ctx=child_ctx,
                max_rounds=s.ICE_SUBAGENT_MAX_TOOL_ROUNDS,
                model=child_model,
                max_tokens=int(args.get("max_tokens") or 2048),
                transcript_sink=transcript_path,
            ),
            timeout=s.ICE_SUBAGENT_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        append_jsonl(transcript_path, {"event": "timeout", "at": datetime.now(tz=timezone.utc).isoformat()})
        await _emit_subagent_event(
            label=f"子 Agent {agent_id} 执行超时",
            status="error",
            detail=f"{s.ICE_SUBAGENT_TIMEOUT_SEC}s",
        )
        return {
            "error_code": "SUBAGENT_TIMEOUT",
            "message": f"sub-agent exceeded {s.ICE_SUBAGENT_TIMEOUT_SEC}s",
            "run_id": run_id,
        }
    except Exception as exc:
        append_jsonl(transcript_path, {"event": "error", "message": str(exc)[:500]})
        await _emit_subagent_event(
            label=f"子 Agent {agent_id} 执行失败",
            status="error",
            detail=str(exc)[:160],
        )
        return {"error_code": "SUBAGENT_FAILED", "message": str(exc)[:300], "run_id": run_id}

    duration_ms = int((datetime.now(tz=timezone.utc) - started).total_seconds() * 1000)
    append_jsonl(
        transcript_path,
        {
            "event": "done",
            "at": datetime.now(tz=timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "tool_count": len(result.get("tool_uses_log") or []),
        },
    )
    await _emit_subagent_event(
        label=f"子 Agent {agent_id} 执行完成",
        status="done",
        detail=f"{len(result.get('tool_uses_log') or [])} 个工具 · {duration_ms}ms",
    )
    return {
        "final_text": result.get("final_text", ""),
        "run_id": run_id,
        "tool_count": len(result.get("tool_uses_log") or []),
        "duration_ms": duration_ms,
    }


async def _tool_run_background(args: dict, ctx: dict | None = None) -> Any:
    """Enqueue a background job. Returns immediately; completion fires a
    notification to the user and drops any produced files into the task
    workspace."""
    from . import bg_task_svc

    s = get_settings()
    if not s.ICE_BG_TASK_ENABLED:
        return {"error_code": "BG_TASK_DISABLED", "message": "background tasks are not enabled"}

    agent_id = (args.get("agent_id") or "").strip()
    prompt = (args.get("prompt") or "").strip()
    title = (args.get("title") or "").strip()
    if not (agent_id and prompt and title):
        return {"error_code": "VALIDATION_ERROR", "message": "agent_id, prompt, title all required"}

    task_id = (ctx or {}).get("task_id")
    user_id = (ctx or {}).get("user_id")
    if not task_id or not user_id:
        return {"error_code": "VALIDATION_ERROR", "message": "run_background needs task + user"}

    try:
        job = await bg_task_svc.enqueue(
            task_id=task_id,
            user_id=user_id,
            agent_id=agent_id,
            title=title,
            prompt=prompt,
            source_conv_id=(ctx or {}).get("conversation_id"),
        )
    except Exception as exc:
        return {"error_code": "BG_TASK_ENQUEUE_FAILED", "message": str(exc)[:300]}
    return {"job_id": job["id"], "status": job["status"], "title": title}


_DISPATCH = {
    "now": _tool_now,
    "echo": _tool_echo,
    "kyuubi_query": _tool_kyuubi,
    "write_file": _tool_write_file,
    "execute_python": _tool_execute_python,
    "list_files": _tool_list_files,
    "read_file": _tool_read_file,
    "feishu_publish": _tool_feishu_publish,
    "volcano_abtest_analyze": _tool_volcano_abtest_analyze,
    "feishu_upload_image": _tool_feishu_upload_image,
    "read_skill": _tool_read_skill,
    "read_agent_knowledge": _tool_read_agent_knowledge,
    "todo_write": _tool_todo_write,
    "request_human_input": _tool_request_human_input,
    "exit_plan_mode": _tool_exit_plan_mode,
    "spawn_subagent": _tool_spawn_subagent,
    "run_background": _tool_run_background,
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
    return await fn(args, ctx)
