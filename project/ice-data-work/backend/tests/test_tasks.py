"""M2 测试：任务状态机 + 参与者 + 会话 + 上下文组装 + 产物 + Agent 运行时。"""
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
    artifact_svc,
    context_assembler_svc,
    conversation_svc,
    task_svc,
)


@pytest.fixture(autouse=True)
def setup_env():
    paths.ensure_top_level()
    yield


class TestStateMachine:
    def test_valid_transitions(self):
        assert task_svc.can_transition("todo", "doing")
        assert task_svc.can_transition("doing", "await")
        assert task_svc.can_transition("doing", "done")
        assert task_svc.can_transition("doing", "error")
        assert task_svc.can_transition("await", "done")
        assert task_svc.can_transition("paused", "doing")

    def test_invalid_transitions(self):
        assert not task_svc.can_transition("todo", "done")
        assert not task_svc.can_transition("done", "await")
        assert not task_svc.can_transition("todo", "nonexistent")

    def test_set_status_enforces_machine(self):
        t = task_svc.create_task(title="测试任务", project_id="p_x", created_by="admin")
        assert t["status"] == "todo"

        task_svc.set_status(t["id"], "doing")
        assert task_svc.get_task(t["id"])["status"] == "doing"

        # 非法流转：todo 直接到 done 不允许
        t2 = task_svc.create_task(title="测试任务2", project_id="p_x", created_by="admin")
        with pytest.raises(Exception):
            task_svc.set_status(t2["id"], "done")  # todo->done 非法

    def test_error_records_reason(self):
        t = task_svc.create_task(title="错误任务", project_id="p_x", created_by="admin")
        task_svc.set_status(t["id"], "doing")
        task_svc.set_status(t["id"], "error", reason="kyuubi 超时")
        meta = task_svc.get_task(t["id"])
        assert meta["status"] == "error"
        assert meta["error_reason"] == "kyuubi 超时"

    def test_pause_records_origin(self):
        t = task_svc.create_task(title="暂停任务", project_id="p_x", created_by="admin")
        task_svc.set_status(t["id"], "doing")
        task_svc.set_status(t["id"], "paused")
        meta = task_svc.get_task(t["id"])
        assert meta["status"] == "paused"
        assert meta["paused_from"] == "doing"


class TestTaskCRUD:
    def test_create_task_owner_participant(self):
        t = task_svc.create_task(title="归因", project_id="p_growth", created_by="alice")
        owners = [p for p in t["participants"] if p["role"] == "owner"]
        assert len(owners) == 1
        assert owners[0]["ref_id"] == "alice"

    def test_create_task_empty_title(self):
        with pytest.raises(Exception):
            task_svc.create_task(title="  ", project_id="p_x", created_by="admin")

    def test_list_tasks_by_project(self):
        task_svc.create_task(title="A", project_id="p_alpha", created_by="admin")
        task_svc.create_task(title="B", project_id="p_beta", created_by="admin")
        alpha = task_svc.list_tasks(project_id="p_alpha")
        assert all(t["project_id"] == "p_alpha" for t in alpha)
        assert len(alpha) >= 1

    def test_list_tasks_by_user(self):
        task_svc.create_task(title="C", project_id="p_x", created_by="bob")
        bob_tasks = task_svc.list_tasks(user_id="bob")
        assert len(bob_tasks) >= 1
        nobody = task_svc.list_tasks(user_id="nobody_xyz")
        assert len(nobody) == 0


class TestParticipants:
    def test_add_remove_participant(self):
        t = task_svc.create_task(title="协作", project_id="p_x", created_by="admin")
        task_svc.add_participant(t["id"], "agent", "data-analysis", role="tool")
        parts = task_svc.list_participants(t["id"])
        assert any(p["ref_id"] == "data-analysis" for p in parts)

        task_svc.remove_participant(t["id"], "agent", "data-analysis")
        parts = task_svc.list_participants(t["id"])
        assert not any(p["ref_id"] == "data-analysis" for p in parts)

    def test_cannot_remove_owner(self):
        t = task_svc.create_task(title="x", project_id="p_x", created_by="admin")
        with pytest.raises(Exception):
            task_svc.remove_participant(t["id"], "user", "admin")

    def test_duplicate_participant(self):
        t = task_svc.create_task(title="x", project_id="p_x", created_by="admin")
        task_svc.add_participant(t["id"], "agent", "ag1")
        with pytest.raises(Exception):
            task_svc.add_participant(t["id"], "agent", "ag1")


class TestConversation:
    def test_append_and_read_turns(self):
        t = task_svc.create_task(title="对话", project_id="p_x", created_by="admin")
        conversation_svc.append_turn(t["id"], speaker_type="user", speaker_id="admin", content="你好")
        conversation_svc.append_turn(t["id"], speaker_type="agent", speaker_id="data-analysis", content="收到")
        turns = conversation_svc.get_conversation(t["id"])
        assert len(turns) == 2
        assert turns[0]["speaker"]["type"] == "user"
        assert turns[1]["speaker"]["type"] == "agent"

    def test_recent_turns_limit(self):
        t = task_svc.create_task(title="多轮", project_id="p_x", created_by="admin")
        for i in range(20):
            conversation_svc.append_turn(t["id"], speaker_type="user", speaker_id="admin", content=f"msg{i}")
        recent = conversation_svc.get_conversation(t["id"], limit=5)
        assert len(recent) == 5
        assert recent[-1]["content"] == "msg19"

    def test_tool_call_log(self):
        t = task_svc.create_task(title="工具", project_id="p_x", created_by="admin")
        conversation_svc.append_tool_call(t["id"], tool="now", args={}, result={"ok": True})
        calls = conversation_svc.get_tool_calls(t["id"])
        assert len(calls) == 1
        assert calls[0]["tool"] == "now"


class TestContextAssembler:
    def test_assemble_includes_task_layer(self):
        t = task_svc.create_task(title="DAU 归因", project_id="p_growth", created_by="admin")
        msgs = context_assembler_svc.assemble_context(
            t, speaker={"type": "agent", "id": "data-analysis"}, acting_user_id="admin",
        )
        # 任务层一定存在
        task_layers = [m for m in msgs if m.get("_layer") == "task"]
        assert len(task_layers) >= 1
        assert any("DAU 归因" in m["content"] for m in task_layers)

    def test_budget_clamp_keeps_task_layer(self):
        t = task_svc.create_task(title="预算", project_id="p_x", created_by="admin")
        msgs = context_assembler_svc.assemble_context(
            t, speaker={"type": "agent", "id": "x"}, acting_user_id="admin", char_budget=100,
        )
        # 即使预算极小，任务层不丢
        assert any(m.get("_layer") == "task" for m in msgs)

    def test_strip_meta(self):
        t = task_svc.create_task(title="x", project_id="p_x", created_by="admin")
        msgs = context_assembler_svc.assemble_context(
            t, speaker={"type": "agent", "id": "x"}, acting_user_id="admin",
        )
        clean = context_assembler_svc.strip_meta(msgs)
        assert all(set(m.keys()) == {"role", "content"} for m in clean)


class TestArtifacts:
    def test_create_and_get_artifact(self):
        t = task_svc.create_task(title="产物", project_id="p_x", created_by="admin")
        art = artifact_svc.create_artifact(t["id"], title="报告", kind="report", content="# 标题\n内容")
        assert art["status"] == "draft"

        full = artifact_svc.get_artifact_content(t["id"], art["id"])
        assert "内容" in full["content"]

    def test_artifact_status_transition(self):
        t = task_svc.create_task(title="产物2", project_id="p_x", created_by="admin")
        art = artifact_svc.create_artifact(t["id"], title="x", kind="doc")
        artifact_svc.set_status(t["id"], art["id"], "published")
        arts = artifact_svc.list_artifacts(t["id"])
        assert arts[0]["status"] == "published"


class TestAgentRuntime:
    def test_run_turn_mock_llm(self):
        """无 LLM key 时走 mock 流，验证端到端回合可跑通。"""
        t = task_svc.create_task(title="运行时", project_id="p_x", created_by="admin")
        task_svc.add_participant(t["id"], "agent", "data-analysis", role="tool")

        events = list(agent_runtime.run_agent_turn(
            t["id"], user_message="帮我分析 DAU", acting_user_id="admin",
        ))
        types = [e["type"] for e in events]
        assert "turn_start" in types
        assert "turn_done" in types
        # 所有事件带 speaker
        assert all("speaker" in e for e in events if e["type"] != "error")

        # 会话已落盘：用户 + speaker 两条
        turns = conversation_svc.get_conversation(t["id"])
        assert len(turns) >= 2

    def test_resolve_speaker_twin_priority(self):
        t = task_svc.create_task(title="编排", project_id="p_x", created_by="admin")
        task_svc.add_participant(t["id"], "twin", "twin-admin", role="collaborator")
        task_svc.add_participant(t["id"], "agent", "data-analysis", role="tool")
        meta = task_svc.get_task(t["id"])
        speaker = agent_runtime.resolve_speaker(meta)
        assert speaker["type"] == "twin"

    def test_resolve_speaker_mention(self):
        t = task_svc.create_task(title="定向", project_id="p_x", created_by="admin")
        task_svc.add_participant(t["id"], "twin", "twin-admin")
        task_svc.add_participant(t["id"], "agent", "data-analysis")
        meta = task_svc.get_task(t["id"])
        speaker = agent_runtime.resolve_speaker(meta, mentioned="data-analysis")
        assert speaker["id"] == "data-analysis"


class TestTools:
    def test_now_tool(self):
        from app.services.tools import run_tool
        result = run_tool("now", {})
        assert result["ok"]
        assert "now" in result["data"]

    def test_high_risk_requires_approval(self):
        from app.services.tools import run_tool
        result = run_tool("write_file", {"path": "x.md", "content": "y"}, context={"task_id": "t1"})
        assert not result["ok"]
        assert result["error_code"] == "APPROVAL_REQUIRED"

    def test_kyuubi_degraded(self):
        from app.services.tools import run_tool
        result = run_tool("kyuubi_query", {"sql": "select 1"})
        assert not result["ok"]
        assert result["error_code"] == "KYUUBI_NOT_CONFIGURED"

    def test_propose_memory(self):
        t = task_svc.create_task(title="记忆", project_id="p_x", created_by="admin")
        from app.services.tools import run_tool
        result = run_tool(
            "propose_memory", {"content": "用户偏好表格", "scope": "user_preference"},
            context={"task_id": t["id"], "speaker_id": "twin-admin", "approved": True},
        )
        assert result["ok"]
        assert "candidate_id" in result["data"]
