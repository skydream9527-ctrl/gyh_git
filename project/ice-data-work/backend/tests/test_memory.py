"""M3 测试：记忆候选/晋升、5 scope 路由、隔离/复用矩阵、原子性、HITL。"""
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
    context_assembler_svc,
    hitl_svc,
    memory_retrieval,
    memory_svc,
    task_svc,
)


@pytest.fixture(autouse=True)
def setup_env():
    # 每个用例独立 DATA_ROOT，避免记忆跨用例累积污染
    d = tempfile.mkdtemp()
    os.environ["DATA_ROOT"] = d
    get_settings.cache_clear()
    paths.ensure_top_level()
    yield


def _new_task(**kw):
    return task_svc.create_task(
        title=kw.get("title", "记忆测试"),
        project_id=kw.get("project_id", "p_growth"),
        created_by=kw.get("created_by", "alice"),
        task_type=kw.get("task_type", "data"),
    )


class TestCandidate:
    def test_propose_and_list(self):
        t = _new_task()
        cand = memory_svc.propose_candidate(t["id"], content="表格优先", scope="user_preference", proposer="twin-alice")
        assert cand["status"] == "pending"
        assert not cand["needs_review"]  # user_preference 不需审核

        cands = memory_svc.list_candidates(t["id"])
        assert len(cands) == 1
        assert cands[0]["content"] == "表格优先"

    def test_agent_team_needs_review(self):
        t = _new_task()
        cand = memory_svc.propose_candidate(t["id"], content="DAU 先查冷启动", scope="agent_team")
        assert cand["needs_review"]  # 共享空间需审核

    def test_invalid_scope(self):
        t = _new_task()
        with pytest.raises(Exception):
            memory_svc.propose_candidate(t["id"], content="x", scope="bogus")

    def test_empty_content(self):
        t = _new_task()
        with pytest.raises(Exception):
            memory_svc.propose_candidate(t["id"], content="  ", scope="agent_user")


class TestPromotion:
    def test_promote_user_preference(self):
        t = _new_task(created_by="alice")
        cand = memory_svc.propose_candidate(t["id"], content="先结论后细节", scope="user_preference", proposer="twin-alice")
        result = memory_svc.promote(t["id"], cand["id"], decided_by="alice", uid="alice")
        assert result["mem_id"].startswith("MEM-")
        assert result["scope"] == "user_preference"

        # 写入了 users/alice/twin/memory/preferences.memory.md
        entries = memory_svc.list_scope_memory("user_preference", uid="alice")
        assert len(entries) == 1
        assert "先结论后细节" in entries[0]["content"]
        assert entries[0]["mem_id"] == result["mem_id"]

    def test_promote_agent_user(self):
        t = _new_task(created_by="alice")
        cand = memory_svc.propose_candidate(t["id"], content="alice 偏好分渠道看", scope="agent_user")
        memory_svc.promote(t["id"], cand["id"], decided_by="alice", aid="data-analysis", uid="alice")
        entries = memory_svc.list_scope_memory("agent_user", aid="data-analysis", uid="alice")
        assert len(entries) == 1

    def test_promote_agent_team(self):
        t = _new_task()
        cand = memory_svc.propose_candidate(t["id"], content="团队口径：DAU 去重", scope="agent_team")
        memory_svc.promote(t["id"], cand["id"], decided_by="admin", aid="data-analysis", tid="t_growth")
        entries = memory_svc.list_scope_memory("agent_team", aid="data-analysis", tid="t_growth")
        assert len(entries) == 1

    def test_promote_marks_candidate_approved(self):
        t = _new_task(created_by="alice")
        cand = memory_svc.propose_candidate(t["id"], content="x", scope="user_preference")
        memory_svc.promote(t["id"], cand["id"], decided_by="alice", uid="alice")
        updated = memory_svc.get_candidate(t["id"], cand["id"])
        assert updated["status"] == "approved"

    def test_double_promote_rejected(self):
        t = _new_task(created_by="alice")
        cand = memory_svc.propose_candidate(t["id"], content="x", scope="user_preference")
        memory_svc.promote(t["id"], cand["id"], decided_by="alice", uid="alice")
        with pytest.raises(Exception):
            memory_svc.promote(t["id"], cand["id"], decided_by="alice", uid="alice")

    def test_reject(self):
        t = _new_task()
        cand = memory_svc.propose_candidate(t["id"], content="x", scope="agent_team")
        memory_svc.reject(t["id"], cand["id"], decided_by="admin", reason="不通用")
        updated = memory_svc.get_candidate(t["id"], cand["id"])
        assert updated["status"] == "rejected"

    def test_multiple_entries_accumulate(self):
        t = _new_task(created_by="bob")
        for i in range(3):
            c = memory_svc.propose_candidate(t["id"], content=f"偏好{i}", scope="user_preference")
            memory_svc.promote(t["id"], c["id"], decided_by="bob", uid="bob")
        entries = memory_svc.list_scope_memory("user_preference", uid="bob")
        assert len(entries) == 3


class TestIsolationReuse:
    """隔离/复用矩阵（D-06）：by-user 默认隔离，by-team 显式共享后复用。"""

    def test_agent_user_isolation(self):
        """alice 给 data-analysis 的 agent_user 记忆，bob 读不到。"""
        t = _new_task(created_by="alice")
        c = memory_svc.propose_candidate(t["id"], content="alice 私有经验", scope="agent_user")
        memory_svc.promote(t["id"], c["id"], decided_by="alice", aid="data-analysis", uid="alice")

        alice_mem = memory_svc.list_scope_memory("agent_user", aid="data-analysis", uid="alice")
        bob_mem = memory_svc.list_scope_memory("agent_user", aid="data-analysis", uid="bob")
        assert len(alice_mem) == 1
        assert len(bob_mem) == 0  # 隔离：bob 读不到 alice 的

    def test_agent_team_reuse(self):
        """贡献给团队后，同团队不同用户都能复用。"""
        t = _new_task()
        c = memory_svc.propose_candidate(t["id"], content="团队共享口径", scope="agent_team")
        memory_svc.promote(t["id"], c["id"], decided_by="admin", aid="data-analysis", tid="t_growth")

        team_mem = memory_svc.list_scope_memory("agent_team", aid="data-analysis", tid="t_growth")
        assert len(team_mem) == 1  # 团队级共享，全团队可读

    def test_context_assembler_access_boundary(self):
        """ContextAssembler 只注入当前用户的 by-user 记忆，不越界。"""
        # alice 与 bob 各有 data-analysis 的 by-user 记忆
        t1 = _new_task(created_by="alice")
        c1 = memory_svc.propose_candidate(t1["id"], content="DAU 渠道分析经验", scope="agent_user")
        memory_svc.promote(t1["id"], c1["id"], decided_by="alice", aid="data-analysis", uid="alice")

        t2 = _new_task(created_by="bob")
        c2 = memory_svc.propose_candidate(t2["id"], content="bob 的留存分析经验", scope="agent_user")
        memory_svc.promote(t2["id"], c2["id"], decided_by="bob", aid="data-analysis", uid="bob")

        # 组装 alice 的任务上下文，邀请 data-analysis
        task_svc.add_participant(t1["id"], "agent", "data-analysis", role="tool")
        meta = task_svc.get_task(t1["id"])
        msgs = context_assembler_svc.assemble_context(
            meta, speaker={"type": "agent", "id": "data-analysis"}, acting_user_id="alice",
        )
        all_text = "\n".join(m["content"] for m in msgs)
        # 注入了 alice 的经验，绝不能注入 bob 的
        assert "渠道分析经验" in all_text or "DAU" in all_text
        assert "bob 的留存分析经验" not in all_text


class TestRetrieval:
    def test_keyword_retrieve_topk(self):
        entries = [
            {"mem_id": "MEM-1", "content": "DAU 下滑先看版本冷启动耗时", "tags": ["DAU"], "confidence": "high"},
            {"mem_id": "MEM-2", "content": "用户偏好表格输出", "tags": ["格式"], "confidence": "medium"},
            {"mem_id": "MEM-3", "content": "渠道新增归因方法", "tags": ["渠道"], "confidence": "medium"},
        ]
        hits = memory_retrieval.retrieve(entries, "DAU 为什么下滑", k=2)
        assert len(hits) <= 2
        # 最相关的应是 MEM-1
        assert hits[0]["mem_id"] == "MEM-1"

    def test_empty_query_returns_head(self):
        entries = [{"mem_id": f"MEM-{i}", "content": f"c{i}", "tags": []} for i in range(10)]
        hits = memory_retrieval.retrieve(entries, "", k=3)
        assert len(hits) == 3

    def test_empty_entries(self):
        assert memory_retrieval.retrieve([], "anything", k=5) == []


class TestHITL:
    def test_create_and_list_approval(self):
        t = _new_task(created_by="alice")
        appr = hitl_svc.create_approval(t["id"], action_type="write_file", summary="写报告", requester="data-analysis")
        assert appr["status"] == "pending"
        pending = hitl_svc.list_approvals(t["id"], status="pending")
        assert len(pending) == 1

    def test_decide_approve(self):
        t = _new_task(created_by="alice")
        appr = hitl_svc.create_approval(t["id"], action_type="x", summary="y")
        hitl_svc.decide(t["id"], appr["id"], approved=True, decided_by="alice")
        updated = hitl_svc.get_approval(t["id"], appr["id"])
        assert updated["status"] == "approved"

    def test_double_decide_rejected(self):
        t = _new_task(created_by="alice")
        appr = hitl_svc.create_approval(t["id"], action_type="x", summary="y")
        hitl_svc.decide(t["id"], appr["id"], approved=True, decided_by="alice")
        with pytest.raises(Exception):
            hitl_svc.decide(t["id"], appr["id"], approved=False, decided_by="alice")

    def test_list_pending_for_user(self):
        t = _new_task(created_by="alice")
        hitl_svc.create_approval(t["id"], action_type="x", summary="待确认项")
        pending = hitl_svc.list_pending_for_user("alice")
        assert len(pending) >= 1
        assert pending[0]["task_title"] == t["title"]


class TestMemoryFormat:
    def test_roundtrip_parse(self):
        """晋升写入后能正确解析回条目。"""
        t = _new_task(created_by="alice")
        c = memory_svc.propose_candidate(
            t["id"], content="多行内容\n第二行", scope="user_preference",
            proposer="twin-alice", tags=["a", "b"],
        )
        result = memory_svc.promote(t["id"], c["id"], decided_by="alice", uid="alice")
        entries = memory_svc.list_scope_memory("user_preference", uid="alice")
        assert len(entries) == 1
        e = entries[0]
        assert e["mem_id"] == result["mem_id"]
        assert "多行内容" in e["content"]
        assert "a" in e["tags"] and "b" in e["tags"]
