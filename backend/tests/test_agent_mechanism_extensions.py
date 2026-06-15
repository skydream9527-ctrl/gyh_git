from __future__ import annotations

import pytest

from app.core.storage import append_jsonl, get_paths, write_json
from app.services import (
    agent_inspection_svc,
    agent_prompt_builder,
    agent_workflow_svc,
    agents_svc,
    experience_card_svc,
    skill_svc,
    tool_runner,
)


def _seed_agent(agent_id: str = "mechanic", cfg: dict | None = None) -> str:
    paths = get_paths()
    (paths.agents / agent_id / "prompt").mkdir(parents=True, exist_ok=True)
    (paths.agents / agent_id / "prompt" / "identity.md").write_text("IDENTITY", encoding="utf-8")
    write_json(
        paths.agent_json(agent_id),
        {
            "id": agent_id,
            "name": "Mechanic",
            "description": "test",
            "publish_status": "published",
            "prompt_layout": "v3",
            **(cfg or {}),
        },
    )
    return agent_id


def test_agent_declarative_fields_are_read(isolated_data_root):
    aid = _seed_agent(
        cfg={
            "disallowed_tools": ["write_file"],
            "permission_mode": "read_only",
            "max_turns": 3,
            "effort": "high",
            "initial_prompt": "先复述任务边界。",
            "hooks": {"pre_tool": [{"tool": "write_file", "block": True}]},
        }
    )

    assert agents_svc.get_agent_disallowed_tools(aid) == ["write_file"]
    assert agents_svc.get_agent_permission_mode(aid) == "read_only"
    assert agents_svc.get_agent_max_turns(aid) == 3
    assert agents_svc.get_agent_effort(aid) == "high"
    assert agents_svc.get_agent_initial_prompt(aid) == "先复述任务边界。"
    assert agents_svc.get_agent_hooks(aid)["pre_tool"][0]["block"] is True


def test_get_anthropic_tools_applies_disallowed_tools(isolated_data_root):
    names = {
        t["name"]
        for t in tool_runner.get_anthropic_tools(
            tool_whitelist=["now", "write_file"],
            disallowed_tools=["write_file"],
        )
    }
    assert names == {"now"}


@pytest.mark.asyncio
async def test_permission_mode_read_only_blocks_writes(isolated_data_root):
    aid = _seed_agent(cfg={"permission_mode": "read_only"})
    ctx = {"user_id": "u1", "agent_id": aid, "task_id": "t1"}

    result = await tool_runner.execute_tool(
        "write_file",
        {"name": "x.md", "content": "x"},
        ctx=ctx,
    )

    assert result["error_code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_pre_tool_hook_can_block(isolated_data_root):
    aid = _seed_agent(
        cfg={
            "hooks": {
                "pre_tool": [
                    {"tool": "echo", "block": True, "message": "echo disabled for this agent"}
                ]
            }
        }
    )
    result = await tool_runner.execute_tool(
        "echo",
        {"text": "hi"},
        ctx={"user_id": "u1", "agent_id": aid, "task_id": "t1"},
    )

    assert result["error_code"] == "HOOK_BLOCKED"
    assert "echo disabled" in result["message"]


@pytest.mark.asyncio
async def test_memory_context_selects_relevant_entries(isolated_data_root):
    aid = _seed_agent()
    ctx = {"user_id": "u1", "agent_id": aid, "task_id": "t1"}
    await tool_runner.execute_tool(
        "memory_save",
        {
            "scope": "user",
            "slug": "report-style",
            "title": "报告偏好",
            "hook": "结论先行",
            "type": "feedback",
            "body": "报告要先给结论。",
        },
        ctx=ctx,
    )
    await tool_runner.execute_tool(
        "memory_save",
        {
            "scope": "user",
            "slug": "sql-style",
            "title": "SQL 偏好",
            "hook": "SQL 放附录",
            "type": "feedback",
            "body": "SQL 不要放正文。",
        },
        ctx=ctx,
    )

    prompt = experience_card_svc.merged_system_prompt(
        aid,
        user_id="u1",
        task_id="t1",
        query="帮我写 SQL 附录",
        task_skill_ids=[],
    )

    assert "SQL 不要放正文" in prompt
    assert "报告要先给结论" not in prompt


def test_skill_frontmatter_exposes_trigger_metadata(isolated_data_root):
    d = get_paths().skills / "demo-skill"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\n"
        "name: demo-skill\n"
        "description: Demo\n"
        "when_to_use: 用户要 demo 时\n"
        "paths: '*.sql, reports/*.md'\n"
        "allowed-tools: read_file, write_file\n"
        "agent: data-analysis\n"
        "---\n\nbody",
        encoding="utf-8",
    )

    skill = next(s for s in skill_svc.list_all() if s["id"] == "demo-skill")
    assert skill["when_to_use"] == "用户要 demo 时"
    assert skill["paths"] == ["*.sql", "reports/*.md"]
    assert skill["allowed_tools"] == ["read_file", "write_file"]
    assert skill["agent"] == "data-analysis"


def test_agent_workflows_are_indexed_and_injected(isolated_data_root):
    aid = _seed_agent()
    wf_dir = get_paths().agents / aid / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "review.md").write_text(
        "---\ntitle: Review\ndescription: Review a report\n---\n\n# Body",
        encoding="utf-8",
    )

    workflows = agent_workflow_svc.list_workflows(aid)
    assert workflows[0]["id"] == "review"
    prompt = agent_prompt_builder.build_base_prompt(aid)
    assert "/review" in prompt


def test_agent_inspection_lists_context_and_subagent_runs(isolated_data_root):
    aid = _seed_agent(cfg={"tools": ["now"], "disallowed_tools": ["echo"]})
    paths = get_paths()
    paths.task_dir("t1").mkdir(parents=True, exist_ok=True)
    append_jsonl(
        paths.task_subagent_run("t1", "sub_abc"),
        {
            "event": "spawn",
            "run_id": "sub_abc",
            "agent_id": aid,
            "parent_agent": "general",
            "prompt": "do it",
            "at": "2026-01-01T00:00:00Z",
        },
    )
    append_jsonl(
        paths.task_subagent_run("t1", "sub_abc"),
        {"event": "done", "duration_ms": 12, "tool_count": 1},
    )

    info = agent_inspection_svc.inspect_context(task_id="t1", agent_id=aid, user_id="u1")
    assert info["tools"] == ["now"]
    runs = agent_inspection_svc.list_subagent_runs("t1")
    assert runs[0]["run_id"] == "sub_abc"
    assert runs[0]["last_event"] == "done"
