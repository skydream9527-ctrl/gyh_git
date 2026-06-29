from __future__ import annotations

import pytest

from app.core.storage import get_paths, write_json
from app.services import agent_prompt_builder, experience_card_svc, tool_runner


def _make_v3_agent(agent_id: str = "analyst") -> None:
    paths = get_paths()
    (paths.agents / agent_id / "prompt").mkdir(parents=True, exist_ok=True)
    (paths.agents / agent_id / "prompt" / "identity.md").write_text("IDENTITY", encoding="utf-8")
    write_json(
        paths.agent_json(agent_id),
        {
            "id": agent_id,
            "name": "Analyst",
            "description": "test agent",
            "publish_status": "published",
            "prompt_layout": "v3",
            "features": {"exit_plan_mode": True},
        },
    )


def test_v3_prompt_includes_shared_context_protocol(isolated_data_root):
    paths = get_paths()
    _make_v3_agent()
    (paths.agents / "_shared").mkdir(parents=True, exist_ok=True)
    (paths.agents / "_shared" / "context-protocol.md").write_text(
        "# Agent Context Protocol\nprotocol-body",
        encoding="utf-8",
    )

    out = agent_prompt_builder.build_base_prompt("analyst")

    assert "IDENTITY" in out
    assert "Agent Context Protocol" in out
    assert "protocol-body" in out


@pytest.mark.asyncio
async def test_memory_and_task_state_tools_feed_runtime_context(isolated_data_root):
    _make_v3_agent()
    ctx = {
        "user_id": "u1",
        "agent_id": "analyst",
        "task_id": "t1",
        "conversation_id": "c1",
    }

    saved = await tool_runner.execute_tool(
        "memory_save",
        {
            "scope": "user",
            "slug": "report-style",
            "title": "报告风格",
            "hook": "结论先行",
            "type": "feedback",
            "body": "用户偏好：先给结论，再给证据。",
        },
        ctx=ctx,
    )
    assert saved["saved"] is True

    saved_agent = await tool_runner.execute_tool(
        "memory_save",
        {
            "scope": "agent",
            "slug": "metric-window",
            "title": "指标窗口",
            "hook": "常用 14 天窗口",
            "type": "project",
            "body": "本 agent 给该用户做指标分析时默认先看 14 天。",
        },
        ctx=ctx,
    )
    assert saved_agent["saved"] is True

    state = await tool_runner.execute_tool(
        "task_state_save",
        {"content": "# Task State\n\n- **Phase**: 2\n- **Pending**: 补 SQL"},
        ctx=ctx,
    )
    assert state["saved"] is True

    prompt = experience_card_svc.merged_system_prompt(
        "analyst",
        user_id="u1",
        task_id="t1",
        task_skill_ids=[],
    )
    assert "# Runtime Context" in prompt
    assert "用户偏好：先给结论" in prompt
    assert "默认先看 14 天" in prompt
    assert "**Phase**: 2" in prompt


@pytest.mark.asyncio
async def test_memory_delete_removes_index_entry(isolated_data_root):
    _make_v3_agent()
    ctx = {"user_id": "u1", "agent_id": "analyst", "task_id": "t1"}
    await tool_runner.execute_tool(
        "memory_save",
        {
            "scope": "user",
            "slug": "obsolete",
            "title": "过期信息",
            "hook": "待删",
            "type": "reference",
            "body": "old",
        },
        ctx=ctx,
    )
    deleted = await tool_runner.execute_tool(
        "memory_delete",
        {"scope": "user", "slug": "obsolete"},
        ctx=ctx,
    )
    assert deleted["deleted"] is True
    index_text = get_paths().user_memory_index("u1").read_text(encoding="utf-8")
    assert "obsolete.md" not in index_text
