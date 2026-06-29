"""M7 测试：有界多跳 A2A 编排（T01）+ 转交协议/工具（T02）+ 落盘（T03）+ A2A 上下文（T04）。

重点（DEV_PLAN §11.D 收口）：编排防环 / 预算 / Twin 仲裁不盲从。
开关 IDW_A2A_ENABLED 默认关——本文件用 a2a_on fixture 显式开启并在结束后还原，避免泄漏到其它用例。
"""
from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATA_ROOT"] = _tmp

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.storage import paths  # noqa: E402
from app.services import (  # noqa: E402
    agent_runtime,
    context_assembler_svc,
    conversation_svc,
    llm_gateway,
    orchestrator_svc,
    task_svc,
)
from app.services.tools import run_tool  # noqa: E402


@pytest.fixture(autouse=True)
def setup_env():
    paths.ensure_top_level()
    yield


@pytest.fixture
def a2a_on():
    """开启 A2A 多跳；结束后还原并清缓存，确保不影响其它用例。"""
    os.environ["IDW_A2A_ENABLED"] = "true"
    get_settings.cache_clear()
    yield
    os.environ.pop("IDW_A2A_ENABLED", None)
    get_settings.cache_clear()


class _ScriptedLLM:
    """按调用次序产出脚本文本（模拟不同 speaker 的输出，可含转交指令）。"""

    def __init__(self, scripts: list[str]):
        self.scripts = scripts
        self.i = 0

    def __call__(self, messages, *, model="claude-sonnet-4", temperature=0.7, max_tokens=4096):
        text = self.scripts[min(self.i, len(self.scripts) - 1)]
        self.i += 1
        yield {"type": "text", "delta": text}
        yield {"type": "done", "content": text, "usage": {"mock": True}}


def _two_agent_task(a="data-analysis", b="report-writer"):
    t = task_svc.create_task(title="多跳协作", project_id="p_x", created_by="admin")
    task_svc.add_participant(t["id"], "agent", a, role="tool")
    task_svc.add_participant(t["id"], "agent", b, role="tool")
    return t


# ─────────────────── T01/T02 纯函数 ───────────────────

class TestDirectiveParsing:
    def test_parse_handoff(self):
        d = orchestrator_svc.parse_directive("好的，我先看下。[[handoff:report-writer|请基于结论写报告]]")
        assert d == {"action": "handoff", "to": "report-writer", "reason": "请基于结论写报告"}

    def test_parse_ask(self):
        d = orchestrator_svc.parse_directive("[[ask:data-analysis|上周 DAU 是多少]]")
        assert d["action"] == "ask"
        assert d["to"] == "data-analysis"

    def test_parse_none(self):
        assert orchestrator_svc.parse_directive("普通回复，无转交。") is None
        assert orchestrator_svc.parse_directive("") is None

    def test_parse_last_wins(self):
        text = "[[handoff:a|先]] 再想想 [[handoff:b|最终决定]]"
        d = orchestrator_svc.parse_directive(text)
        assert d["to"] == "b"

    def test_strip_directives(self):
        text = "结论如下。[[handoff:report-writer|写报告]]"
        assert orchestrator_svc.strip_directives(text) == "结论如下。"


class TestArbitration:
    def _state(self):
        return orchestrator_svc.HopState(max_hops=3, hard_cap=6)

    def test_honor_valid(self):
        d = orchestrator_svc.arbitrate_handoff(
            request={"to": "report-writer", "reason": "r"},
            current_speaker={"type": "agent", "id": "data-analysis"},
            state=self._state(),
            participant_agent_ids={"data-analysis", "report-writer"},
            known_agent_ids=set(),
        )
        assert d["honor"] and d["target"] == {"type": "agent", "id": "report-writer"}

    def test_deny_self_handoff(self):
        d = orchestrator_svc.arbitrate_handoff(
            request={"to": "a"}, current_speaker={"type": "agent", "id": "a"},
            state=self._state(), participant_agent_ids={"a"}, known_agent_ids=set(),
        )
        assert not d["honor"]

    def test_deny_unknown_target(self):
        d = orchestrator_svc.arbitrate_handoff(
            request={"to": "ghost"}, current_speaker={"type": "agent", "id": "a"},
            state=self._state(), participant_agent_ids={"a"}, known_agent_ids=set(),
        )
        assert not d["honor"]
        assert "不存在" in d["reason"]

    def test_deny_budget_exhausted(self):
        st = orchestrator_svc.HopState(hops=3, max_hops=3, hard_cap=6)
        d = orchestrator_svc.arbitrate_handoff(
            request={"to": "b"}, current_speaker={"type": "agent", "id": "a"},
            state=st, participant_agent_ids={"a", "b"}, known_agent_ids=set(),
        )
        assert not d["honor"]
        assert "预算" in d["reason"]

    def test_deny_pingpong(self):
        st = orchestrator_svc.HopState(max_hops=3, hard_cap=6)
        orchestrator_svc.record_hop(st, from_speaker={"id": "a"}, target={"type": "agent", "id": "b"})
        # b 想转回 a → A↔B 乒乓
        d = orchestrator_svc.arbitrate_handoff(
            request={"to": "a"}, current_speaker={"type": "agent", "id": "b"},
            state=st, participant_agent_ids={"a", "b"}, known_agent_ids=set(),
        )
        assert not d["honor"]
        assert "循环" in d["reason"]

    def test_auto_join_for_known_nonparticipant(self):
        d = orchestrator_svc.arbitrate_handoff(
            request={"to": "k"}, current_speaker={"type": "agent", "id": "a"},
            state=self._state(), participant_agent_ids={"a"}, known_agent_ids={"k"},
        )
        assert d["honor"] and d["auto_join"]

    def test_effective_max_clamps_to_hard_cap(self):
        st = orchestrator_svc.HopState(max_hops=99, hard_cap=6)
        assert st.effective_max == 6


# ─────────────────── T01/T03 多跳集成 ───────────────────

class TestMultiHopOrchestration:
    def test_relay_handoff(self, a2a_on, monkeypatch):
        t = _two_agent_task()
        monkeypatch.setattr(llm_gateway, "stream_chat", _ScriptedLLM([
            "分析完成。[[handoff:report-writer|请基于结论写报告]]",
            "报告已写好。",
        ]))
        events = list(agent_runtime.run_agent_turn(
            t["id"], user_message="帮我分析并写报告", acting_user_id="admin",
        ))
        types = [e["type"] for e in events]
        # 两个 speaker 各一次 turn_start
        assert types.count("turn_start") == 2
        # 有一次成功转交
        handoffs = [e for e in events if e["type"] == "handoff"]
        assert len(handoffs) == 1
        assert handoffs[0]["honored"] is True
        assert handoffs[0]["from"]["id"] == "data-analysis"
        assert handoffs[0]["to"]["id"] == "report-writer"
        # 落盘：B 的回合带 handoff 元信息
        turns = conversation_svc.get_conversation(t["id"])
        b_turns = [x for x in turns if x["speaker"]["id"] == "report-writer"]
        assert b_turns and b_turns[-1].get("handoff", {}).get("from") == "data-analysis"
        # 展示文本已清洗指令标记
        a_turns = [x for x in turns if x["speaker"]["id"] == "data-analysis"]
        assert "[[handoff" not in a_turns[-1]["content"]

    def test_pingpong_blocked(self, a2a_on, monkeypatch):
        t = _two_agent_task()
        monkeypatch.setattr(llm_gateway, "stream_chat", _ScriptedLLM([
            "我来起头。[[handoff:report-writer|你来写]]",
            "我觉得该退回去。[[handoff:data-analysis|你再算算]]",
            "不应到这里",
        ]))
        events = list(agent_runtime.run_agent_turn(
            t["id"], user_message="开始", acting_user_id="admin",
        ))
        handoffs = [e for e in events if e["type"] == "handoff"]
        # 第一次转交成功，第二次（B→A）被防环拦截
        assert handoffs[0]["honored"] is True
        assert handoffs[1]["honored"] is False
        assert "循环" in handoffs[1]["note"]
        # 只有 2 个 speaker 真正发言（A、B），未回到 A
        assert [e["type"] for e in events].count("turn_start") == 2

    def test_budget_caps_hops(self, a2a_on, monkeypatch):
        # max_hops=1：第一次转交后即达上限，后续转交被预算拦截
        os.environ["IDW_A2A_MAX_HOPS"] = "1"
        get_settings.cache_clear()
        try:
            t = _two_agent_task("a1", "a2")
            task_svc.add_participant(t["id"], "agent", "a3", role="tool")
            monkeypatch.setattr(llm_gateway, "stream_chat", _ScriptedLLM([
                "[[handoff:a2|交给你]]",
                "[[handoff:a3|再交给你]]",
                "末端",
            ]))
            events = list(agent_runtime.run_agent_turn(
                t["id"], user_message="走", acting_user_id="admin",
            ))
            handoffs = [e for e in events if e["type"] == "handoff"]
            assert handoffs[0]["honored"] is True
            assert handoffs[1]["honored"] is False
            assert "预算" in handoffs[1]["note"]
        finally:
            os.environ.pop("IDW_A2A_MAX_HOPS", None)
            get_settings.cache_clear()

    def test_a2a_off_is_single_hop(self, monkeypatch):
        """开关关：即便输出带转交指令，也只跑单跳、无 handoff 事件（保持 v1 行为）。"""
        get_settings.cache_clear()
        t = _two_agent_task()
        monkeypatch.setattr(llm_gateway, "stream_chat", _ScriptedLLM([
            "分析完成。[[handoff:report-writer|写报告]]",
            "不应到这里",
        ]))
        events = list(agent_runtime.run_agent_turn(
            t["id"], user_message="走", acting_user_id="admin",
        ))
        types = [e["type"] for e in events]
        assert types.count("turn_start") == 1
        assert not any(e["type"] == "handoff" for e in events)


# ─────────────────── T04 A2A 上下文层 ───────────────────

class TestA2AContext:
    def test_handoff_layer_injected(self):
        t = _two_agent_task()
        conversation_svc.append_turn(
            t["id"], speaker_type="agent", speaker_id="data-analysis",
            content="DAU 环比下降 8%，主因新增渠道质量下滑。",
        )
        msgs = context_assembler_svc.assemble_context(
            task_svc.get_task(t["id"]),
            speaker={"type": "agent", "id": "report-writer"}, acting_user_id="admin",
            handoff={"from": "data-analysis", "to": "report-writer", "reason": "写报告"},
        )
        a2a = [m for m in msgs if m.get("_layer") == "a2a"]
        assert len(a2a) == 1
        assert "data-analysis" in a2a[0]["content"]
        assert "写报告" in a2a[0]["content"]
        # 注入了前序产出摘要
        assert "环比下降" in a2a[0]["content"]

    def test_no_handoff_no_a2a_layer(self):
        t = _two_agent_task()
        msgs = context_assembler_svc.assemble_context(
            task_svc.get_task(t["id"]),
            speaker={"type": "agent", "id": "data-analysis"}, acting_user_id="admin",
        )
        assert not any(m.get("_layer") == "a2a" for m in msgs)

    def test_a2a_layer_survives_tiny_budget(self):
        t = _two_agent_task()
        msgs = context_assembler_svc.assemble_context(
            task_svc.get_task(t["id"]),
            speaker={"type": "agent", "id": "report-writer"}, acting_user_id="admin",
            char_budget=50, handoff={"from": "data-analysis", "to": "report-writer", "reason": "x"},
        )
        # 预算极小，a2a 接手层与任务层都不丢
        assert any(m.get("_layer") == "a2a" for m in msgs)
        assert any(m.get("_layer") == "task" for m in msgs)


# ─────────────────── T02 转交工具 ───────────────────

class TestHandoffTools:
    def test_handoff_to_agent_valid(self):
        t = _two_agent_task()
        r = run_tool("handoff_to_agent", {"to": "report-writer", "reason": "写报告"},
                     context={"task_id": t["id"], "speaker_id": "data-analysis"})
        assert r["ok"]
        assert r["data"]["action"] == "handoff"
        assert r["data"]["to"] == "report-writer"

    def test_handoff_to_unknown(self):
        t = _two_agent_task()
        r = run_tool("handoff_to_agent", {"to": "ghost"},
                     context={"task_id": t["id"], "speaker_id": "data-analysis"})
        assert not r["ok"]
        assert r["error_code"] == "NOT_FOUND"

    def test_ask_agent_valid(self):
        t = _two_agent_task()
        r = run_tool("ask_agent", {"to": "data-analysis", "question": "DAU?"},
                     context={"task_id": t["id"], "speaker_id": "report-writer"})
        assert r["ok"]
        assert r["data"]["action"] == "ask"
