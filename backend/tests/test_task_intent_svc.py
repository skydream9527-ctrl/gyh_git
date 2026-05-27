from __future__ import annotations

from app.services import task_intent_svc, tool_runner


def test_parse_compact_tag_and_chinese_date(monkeypatch):
    monkeypatch.setattr(
        task_intent_svc.agents_svc,
        "get_agent",
        lambda agent_id: {"id": agent_id} if agent_id == "data-analysis" else None,
    )
    intent = task_intent_svc.parse_message_intent(
        "1.13.c.126年5.26实时曝光环比前一条同时间段下降10%，下钻查下原因",
        task_name="c.1广告曝光下降问题",
    )

    assert intent.domain == "ad_data"
    assert intent.tag_id == "1.13.c.1"
    assert intent.date_text == "26年5月26日"
    assert intent.route_agent_id == "data-analysis"
    assert "tag_id=`1.13.c.1`" in (intent.prompt_hint or "")
    assert "不要把完整连写片段误判成实验 ID" in (intent.prompt_hint or "")
    assert "必须先说明能力边界" in (intent.prompt_hint or "")


def test_choose_agent_routes_generic_ad_diagnosis_to_data_agent(monkeypatch):
    monkeypatch.setattr(
        task_intent_svc.agents_svc,
        "get_agent",
        lambda agent_id: {"id": agent_id} if agent_id == "data-analysis" else None,
    )
    agent_id, intent = task_intent_svc.choose_agent_for_task(
        name="c.1广告曝光下降问题",
        requested_agent_id="general",
        initial_prompt="1.13.c.126年5.26实时曝光环比下降10%，下钻查原因",
    )

    assert agent_id == "data-analysis"
    assert intent.route_reason == "ad_data_diagnosis"
    assert intent.tag_id == "1.13.c.1"


def test_spawn_subagent_schema_uses_concrete_target_enum():
    tools = tool_runner.get_anthropic_tools(spawn_targets=["data-analysis", "know"])
    spawn = next(t for t in tools if t["name"] == "spawn_subagent")

    agent_schema = spawn["input_schema"]["properties"]["agent_id"]
    assert agent_schema["enum"] == ["data-analysis", "know"]


def test_spawn_subagent_hidden_when_no_targets():
    names = {t["name"] for t in tool_runner.get_anthropic_tools(spawn_targets=[])}
    assert "spawn_subagent" not in names
