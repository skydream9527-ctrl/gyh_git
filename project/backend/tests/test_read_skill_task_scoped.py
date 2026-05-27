"""read_skill / get_anthropic_tools 的 task-scope 行为。

用户期望：
- task 内（ctx.task_id 存在）只能看到 task.skill_ids 里的 agentic skill；
  未绑定的 skill 即便存在于全局 skills/ 也返回 SKILL_NOT_FOUND。
- 无 task 上下文（admin 沙盒 / test_run）走全局 fallback，保留原能力。
- get_anthropic_tools(task_skill_ids=...) 改写 read_skill 的 description，
  让 LLM 看到的可调用 skill 列表与任务实际绑定一致。
"""
from __future__ import annotations

import pytest

from app.core.storage import get_paths, write_json
from app.services import agent_snapshot_svc, experience_card_svc, tool_runner


def _seed_global_skill(sid: str) -> None:
    paths = get_paths()
    d = paths.skills / sid
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {sid}\ndescription: test {sid}\n---\n\n# {sid}\n"
        "body content for the test skill, long enough to exceed any size guards."
        * 5
    )


def _make_task_dir(tid: str) -> None:
    paths = get_paths()
    (paths.task_dir(tid) / "conversations").mkdir(parents=True, exist_ok=True)


@pytest.mark.asyncio
async def test_read_skill_returns_bound_skill_from_task_snapshot(isolated_data_root):
    _seed_global_skill("nl-sql")
    _seed_global_skill("docx")
    tid = "t-bound"
    _make_task_dir(tid)
    agent_snapshot_svc.snapshot_skills_into_task(task_id=tid, skill_ids=["nl-sql"])

    result = await tool_runner.execute_tool(
        "read_skill", {"skill_id": "nl-sql"}, ctx={"task_id": tid}
    )
    assert result.get("skill_id") == "nl-sql"
    assert result.get("source") == "task"
    assert "body content" in (result.get("content") or "")


@pytest.mark.asyncio
async def test_read_skill_blocks_unbound_skill_in_task_context(isolated_data_root):
    _seed_global_skill("nl-sql")
    _seed_global_skill("docx")
    tid = "t-blocked"
    _make_task_dir(tid)
    agent_snapshot_svc.snapshot_skills_into_task(task_id=tid, skill_ids=["nl-sql"])

    # docx 存在于全局 skills/，但任务里没绑定 → 必须 SKILL_NOT_FOUND
    result = await tool_runner.execute_tool(
        "read_skill", {"skill_id": "docx"}, ctx={"task_id": tid}
    )
    assert result.get("error_code") == "SKILL_NOT_FOUND"
    assert "未在本任务" in (result.get("message") or "") or "未绑定" in (result.get("message") or "")
    assert result.get("bound_skill_ids") == ["nl-sql"]


@pytest.mark.asyncio
async def test_read_skill_empty_binding_blocks_everything(isolated_data_root):
    _seed_global_skill("nl-sql")
    tid = "t-empty"
    _make_task_dir(tid)
    agent_snapshot_svc.snapshot_skills_into_task(task_id=tid, skill_ids=[])

    result = await tool_runner.execute_tool(
        "read_skill", {"skill_id": "nl-sql"}, ctx={"task_id": tid}
    )
    assert result.get("error_code") == "SKILL_NOT_FOUND"
    assert result.get("bound_skill_ids") == []


@pytest.mark.asyncio
async def test_read_skill_falls_back_to_global_without_task_ctx(isolated_data_root):
    _seed_global_skill("docx")

    # 模拟 admin 沙盒 / test_run：ctx 没有 task_id
    result = await tool_runner.execute_tool(
        "read_skill", {"skill_id": "docx"}, ctx={"user_id": "admin-test"}
    )
    assert result.get("skill_id") == "docx"
    assert result.get("source") == "global"
    assert "body content" in (result.get("content") or "")


def test_get_anthropic_tools_rewrites_read_skill_description_for_bound_task():
    tools = tool_runner.get_anthropic_tools(task_skill_ids=["nl-sql", "kyuubi"])
    by_name = {t["name"]: t for t in tools}
    assert "read_skill" in by_name
    desc = by_name["read_skill"]["description"]
    assert "`nl-sql`" in desc
    assert "`kyuubi`" in desc
    # 老硬编码示例里的 docx 不应该在描述中暴露
    assert "docx" not in desc
    assert "pdf" not in desc


def test_get_anthropic_tools_advertises_no_bindings_when_empty():
    tools = tool_runner.get_anthropic_tools(task_skill_ids=[])
    by_name = {t["name"]: t for t in tools}
    desc = by_name["read_skill"]["description"]
    assert "NO agentic skills bound" in desc


def test_get_anthropic_tools_keeps_default_description_without_task_ctx():
    """No task_skill_ids (None) preserves the original hardcoded description so
    admin sandbox / scheduler / pre-task contexts behave as before."""
    tools = tool_runner.get_anthropic_tools(task_skill_ids=None)
    by_name = {t["name"]: t for t in tools}
    desc = by_name["read_skill"]["description"]
    assert "NO agentic skills bound" not in desc
    # 原描述里枚举了 docx/xlsx/pptx 等，回归保留
    assert "docx" in desc


def _seed_agent(agent_id: str = "test-agent") -> str:
    paths = get_paths()
    adir = paths.agents / agent_id
    (adir / "prompt").mkdir(parents=True, exist_ok=True)
    (adir / "prompt" / "system.md").write_text("you are a test agent\n")
    write_json(paths.agent_json(agent_id), {"id": agent_id, "name": "Test"})
    return agent_id


def test_merged_system_prompt_only_lists_bound_agentic_skills(isolated_data_root):
    _seed_global_skill("nl-sql")
    _seed_global_skill("docx")
    _seed_global_skill("pptx")
    aid = _seed_agent()

    prompt = experience_card_svc.merged_system_prompt(
        aid, task_skill_ids=["nl-sql"]
    )
    # 只有 nl-sql 应该在 system prompt 的 agentic 索引里
    assert "`nl-sql`" in prompt
    # docx / pptx 没绑定，绝对不能出现在 agentic 列表里
    # （这里用 `\`docx\`` 这个完整 token 判定；纯 "docx" 子串可能在自由叙述中出现）
    assert "`docx`" not in prompt
    assert "`pptx`" not in prompt
    # 标题切到任务作用域
    assert "本任务可用 Skill" in prompt
    assert "可用 Skill 全集" not in prompt


def test_merged_system_prompt_empty_binding_announces_no_skills(isolated_data_root):
    _seed_global_skill("nl-sql")
    aid = _seed_agent()

    prompt = experience_card_svc.merged_system_prompt(aid, task_skill_ids=[])
    assert "`nl-sql`" not in prompt
    assert "未绑定任何 agentic skill" in prompt


def test_merged_system_prompt_keeps_full_catalog_when_no_task_ctx(isolated_data_root):
    """admin sandbox / scheduler 等无 task_skill_ids 的场景，回归到全集。"""
    _seed_global_skill("nl-sql")
    _seed_global_skill("docx")
    aid = _seed_agent()

    prompt = experience_card_svc.merged_system_prompt(aid, task_skill_ids=None)
    assert "`nl-sql`" in prompt
    assert "`docx`" in prompt
    assert "可用 Skill 全集" in prompt
