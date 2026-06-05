"""Tests for the v2 tool-runner additions — metadata, schema filters, gates,
todo tool, and exit_plan_mode tool behaviour."""
from __future__ import annotations

import asyncio
import json

import pytest

from app.core.storage import get_paths
from app.services import tool_runner


def _tool_names(schemas: list[dict]) -> set[str]:
    return {t["name"] for t in schemas}


def test_all_tools_have_meta():
    """Every registered tool exposes the v2 metadata keys."""
    for t in tool_runner.BUILTIN_TOOL_SCHEMAS:
        meta = t.get("_meta") or {}
        name = t["function"]["name"]
        assert meta, f"{name} missing _meta"
        for key in ("display_name", "side_effect", "parallel_safe",
                    "plan_mode_allowed", "subagent_exposable"):
            assert key in meta, f"{name}._meta missing {key}"
        assert meta["side_effect"] in ("read", "write", "network"), name


def test_get_anthropic_tools_filters_plan_mode():
    """plan_mode=True drops every tool whose _meta.plan_mode_allowed is False."""
    all_names = _tool_names(tool_runner.get_anthropic_tools())
    plan_names = _tool_names(tool_runner.get_anthropic_tools(plan_mode=True))
    # Write-side tools must be gone.
    assert "write_file" not in plan_names
    assert "feishu_publish" not in plan_names
    assert "spawn_subagent" not in plan_names
    assert "run_background" not in plan_names
    # Read-side + exit_plan_mode + todo_write survive.
    assert "list_files" in plan_names
    assert "read_file" in plan_names
    assert "todo_write" in plan_names
    assert "exit_plan_mode" in plan_names
    # Non-plan mode keeps writes.
    assert "write_file" in all_names


def test_get_anthropic_tools_filters_subagent():
    """in_subagent=True drops tools that can't appear inside a sub-agent —
    crucially including spawn_subagent itself (prevents recursion)."""
    names = _tool_names(tool_runner.get_anthropic_tools(in_subagent=True))
    assert "spawn_subagent" not in names
    assert "run_background" not in names
    assert "feishu_publish" not in names
    assert "exit_plan_mode" not in names
    # write_file stays: sub-agent products land in parent workspace.
    assert "write_file" in names


def test_get_anthropic_tools_feature_flags():
    """feature_flags dict with a False value removes that tool only."""
    names = _tool_names(
        tool_runner.get_anthropic_tools(feature_flags={"todo_write": False})
    )
    assert "todo_write" not in names
    assert "write_file" in names


def test_feishu_send_message_schema_supports_webhook():
    schema = next(
        t["function"]["parameters"]
        for t in tool_runner.BUILTIN_TOOL_SCHEMAS
        if t["function"]["name"] == "feishu_send_message"
    )
    props = schema["properties"]
    assert "webhook_url" in props
    assert "sign_secret" in props


@pytest.mark.asyncio
async def test_daily_report_requires_feishu_webhook():
    r = await tool_runner._tool_feishu_send_message(
        {"title": "日报", "content": "hello"},
        ctx={"agent_id": "djy-daily-report"},
    )
    assert r["error_code"] == "FEISHU_WEBHOOK_REQUIRED"


@pytest.mark.asyncio
async def test_execute_tool_plan_mode_blocks_writes(isolated_data_root):
    """ctx.plan_mode=True blocks any tool whose _meta.plan_mode_allowed=False."""
    ctx = {
        "task_id": "t1",
        "user_id": "u1",
        "agent_id": "biz-insight",
        "conversation_id": "c1",
        "plan_mode": True,
    }
    r = await tool_runner.execute_tool("write_file", {"name": "a.md", "content": "x"}, ctx=ctx)
    assert isinstance(r, dict)
    assert r.get("error_code") == "PLAN_MODE_BLOCKED"


@pytest.mark.asyncio
async def test_execute_tool_plan_mode_allows_reads(isolated_data_root):
    """plan_mode=True does NOT block list_files (read side)."""
    ctx = {
        "task_id": "t1",
        "user_id": "u1",
        "agent_id": "biz-insight",
        "conversation_id": "c1",
        "plan_mode": True,
    }
    # list_files needs the task dir; make one.
    get_paths().task_dir("t1").mkdir(parents=True, exist_ok=True)
    r = await tool_runner.execute_tool("list_files", {}, ctx=ctx)
    # Either succeeds (returns {files, total, scope}) or returns task-related
    # error — but NOT a plan-mode block.
    assert r.get("error_code") != "PLAN_MODE_BLOCKED"


@pytest.mark.asyncio
async def test_todo_write_persists_and_emits(isolated_data_root):
    """todo_write stores the list to tasks/{tid}/todos.json and fires
    emit_event when the WS callback is provided."""
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    ctx = {
        "task_id": "t-todo",
        "user_id": "u1",
        "agent_id": "biz-insight",
        "conversation_id": "c1",
        "emit_event": emit,
    }
    r = await tool_runner._tool_todo_write(
        {
            "items": [
                {"content": "写 SQL", "activeForm": "正在写 SQL", "status": "in_progress"},
                {"content": "自测", "activeForm": "正在自测", "status": "pending"},
            ]
        },
        ctx=ctx,
    )
    assert r["updated"] is True
    assert r["count"] == 2
    assert r["in_progress"] == 1

    # File was written with normalized structure.
    todo_path = get_paths().task_todos("t-todo")
    assert todo_path.exists()
    data = json.loads(todo_path.read_text())
    assert data["task_id"] == "t-todo"
    assert len(data["items"]) == 2
    assert data["items"][0]["status"] == "in_progress"

    # WS event was pushed.
    assert len(events) == 1
    assert events[0]["type"] == "todos_updated"
    assert events[0]["task_id"] == "t-todo"
    assert len(events[0]["items"]) == 2


@pytest.mark.asyncio
async def test_todo_write_accepts_legacy_todos_json_string(isolated_data_root):
    """Older prompts sometimes sent todos as a JSON string; keep progress live."""
    ctx = {"task_id": "t-todo-legacy", "user_id": "u1", "agent_id": "x", "conversation_id": "c"}
    r = await tool_runner._tool_todo_write(
        {
            "todos": json.dumps(
                [
                    {"content": "查数", "activeForm": "正在查数", "status": "in_progress"},
                    {"content": "写报告", "activeForm": "正在写报告", "status": "pending"},
                ],
                ensure_ascii=False,
            )
        },
        ctx=ctx,
    )
    assert r["updated"] is True
    assert r["count"] == 2
    data = json.loads(get_paths().task_todos("t-todo-legacy").read_text())
    assert data["items"][0]["content"] == "查数"


@pytest.mark.asyncio
async def test_todo_write_replace_all_semantics(isolated_data_root):
    """Second todo_write fully replaces the first — no diff-merge."""
    ctx = {"task_id": "t-r", "user_id": "u1", "agent_id": "x", "conversation_id": "c"}
    get_paths().task_dir("t-r").mkdir(parents=True, exist_ok=True)

    await tool_runner._tool_todo_write(
        {"items": [{"content": "一", "activeForm": "一中", "status": "pending"}]},
        ctx=ctx,
    )
    await tool_runner._tool_todo_write(
        {
            "items": [
                {"content": "二", "activeForm": "二中", "status": "in_progress"},
                {"content": "三", "activeForm": "三中", "status": "pending"},
            ]
        },
        ctx=ctx,
    )

    data = json.loads(get_paths().task_todos("t-r").read_text())
    assert [it["content"] for it in data["items"]] == ["二", "三"]


@pytest.mark.asyncio
async def test_todo_write_rejects_invalid_status(isolated_data_root):
    ctx = {"task_id": "t-v", "user_id": "u1", "agent_id": "x", "conversation_id": "c"}
    r = await tool_runner._tool_todo_write(
        {"items": [{"content": "x", "activeForm": "y", "status": "bogus"}]},
        ctx=ctx,
    )
    assert r.get("error_code") == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_exit_plan_mode_persists_and_emits(isolated_data_root):
    """exit_plan_mode stores plan_id on the conversation index and fires a
    plan_proposed WS event.

    We avoid conversation_svc.create_conversation here because it consults a
    users_index SQLite cache that the test fixture doesn't seed. Writing the
    INDEX.json directly keeps the test focused on plan persistence.
    """
    from app.core.storage import write_json
    from app.services import conversation_svc

    paths = get_paths()
    idx_path = paths.task_conversations_index("t-p")
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        idx_path,
        [
            {
                "id": "cv1",
                "title": "c",
                "created_by": "u1",
                "created_at": "2026-01-01T00:00:00Z",
                "last_message_at": "2026-01-01T00:00:00Z",
                "message_count": 0,
            }
        ],
    )

    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    ctx = {
        "task_id": "t-p",
        "conversation_id": "cv1",
        "user_id": "u1",
        "agent_id": "x",
        "emit_event": emit,
    }
    r = await tool_runner._tool_exit_plan_mode({"plan": "# step 1\n- do x"}, ctx=ctx)
    assert r["waiting_for_approval"] is True
    plan_id = r["plan_id"]
    assert plan_id.startswith("p_")

    # Conversation meta carries the plan.
    state = await conversation_svc.get_plan_mode(task_id="t-p", conv_id="cv1")
    assert state["plan_mode"] is True
    assert state["pending_plan_id"] == plan_id
    assert "step 1" in state["pending_plan_text"]

    # WS event fired.
    assert any(e.get("type") == "plan_proposed" and e.get("plan_id") == plan_id for e in events)

    # ctx gets an internal marker used by ws.py to break the round loop.
    assert ctx["_plan_proposed"]["plan_id"] == plan_id
