"""M6 测试：沙盒安全 + schema 抽取 + 草稿隔离/复用 + 晋升双门 + 绑定/回滚 + 注入 + API gate。"""
from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATA_ROOT"] = _tmp
os.environ["IDW_SELF_EVOLVE_ENABLED"] = "true"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.storage import paths  # noqa: E402
from app.core.storage.jsonio import read_json, write_json  # noqa: E402
from app.services import (  # noqa: E402
    context_assembler_svc,
    sandbox,
    skill_evolve_svc,
    skill_svc,
)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.services import team_svc, user_svc  # noqa: E402


@pytest.fixture(autouse=True)
def setup_env():
    d = tempfile.mkdtemp()
    os.environ["DATA_ROOT"] = d
    os.environ["IDW_SELF_EVOLVE_ENABLED"] = "true"
    get_settings.cache_clear()
    paths.ensure_top_level()
    yield


def _mk_agent(aid="data-analysis", skills=None):
    write_json(paths.agent_json(aid), {
        "id": aid, "name": "DA", "type": "builtin",
        "skills": skills or ["kyuubi_query"], "version": 1,
    })


class TestSandbox:
    def test_basic_exec(self):
        r = sandbox.run_python("print(1 + 1)", workdir=tempfile.mkdtemp(), wall_timeout=10)
        assert r["ok"] and r["stdout"].strip() == "2"

    def test_params_injection(self):
        r = sandbox.run_python('print(sum(params["xs"]))', params={"xs": [1, 2, 3]},
                               workdir=tempfile.mkdtemp(), wall_timeout=10)
        assert r["ok"] and r["stdout"].strip() == "6"

    def test_network_blocked(self):
        r = sandbox.run_python("import socket; socket.socket()", workdir=tempfile.mkdtemp(), wall_timeout=10)
        assert not r["ok"] and "network access is disabled" in r["stderr"]

    def test_timeout_killed(self):
        r = sandbox.run_python("while True:\n    pass", workdir=tempfile.mkdtemp(),
                               wall_timeout=2, cpu_seconds=2)
        assert r["timed_out"] and r["error_code"] == "SANDBOX_TIMEOUT"

    def test_runtime_error(self):
        r = sandbox.run_python('raise ValueError("boom")', workdir=tempfile.mkdtemp(), wall_timeout=10)
        assert not r["ok"] and r["error_code"] == "SANDBOX_RUNTIME_ERROR" and "ValueError" in r["stderr"]

    def test_file_write_isolated(self):
        wd = tempfile.mkdtemp()
        r = sandbox.run_python('open("out.txt", "w").write("hi")', workdir=wd, wall_timeout=10)
        assert r["ok"] and os.path.exists(os.path.join(wd, "out.txt"))

    def test_disabled_degrades(self):
        os.environ["IDW_SELF_EVOLVE_ENABLED"] = "false"
        get_settings.cache_clear()
        try:
            r = sandbox.run_python("print(1)", workdir=tempfile.mkdtemp())
            assert r["error_code"] == "SANDBOX_NOT_ENABLED"
        finally:
            os.environ["IDW_SELF_EVOLVE_ENABLED"] = "true"
            get_settings.cache_clear()


class TestSchemaExtract:
    def test_python_params(self):
        code = 'a = params["date_range"]\nb = params.get("channel")'
        assert [p["name"] for p in skill_svc.extract_schema(code, "python")] == ["date_range", "channel"]

    def test_sql_params(self):
        sql = "SELECT * FROM t WHERE dt BETWEEN :date_start AND :date_end AND c = :date_start"
        assert [p["name"] for p in skill_svc.extract_schema(sql, "sql")] == ["date_start", "date_end"]

    def test_empty(self):
        assert skill_svc.extract_schema("print(1)", "python") == []


class TestUserSkill:
    def test_create_read(self):
        s = skill_svc.create_user_skill("alice", name="S1", description="d",
                                        runtime="python", code='print("hi")')
        assert s["version"] == 1 and s["scope"] == "by_user"
        assert skill_svc.read_skill_code(skill_svc.get_skill(s["id"], uid="alice")) == 'print("hi")'

    def test_draft_isolated(self):
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code="print(1)")
        assert len(skill_svc.list_user_skills("alice")) == 1
        assert len(skill_svc.list_user_skills("bob")) == 0
        with pytest.raises(Exception):
            skill_svc.get_skill(s["id"], uid="bob")

    def test_test_run_python(self):
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code='print("ok")')
        r = skill_svc.test_run(s["id"], uid="alice")
        assert r["ok"] and skill_svc.get_skill(s["id"], uid="alice")["test_passed"] is True

    def test_test_run_sql_degrades(self):
        s = skill_svc.create_user_skill("alice", name="Q", description="", runtime="sql", code="SELECT :x")
        assert skill_svc.test_run(s["id"], uid="alice")["error_code"] == "KYUUBI_NOT_CONFIGURED"


class TestMaterialize:
    def test_by_user(self):
        _mk_agent()
        cand = skill_svc.propose_skill_candidate("t1", name="DAU", description="", runtime="python",
                                                 code='print(params.get("ch"))', proposer="alice",
                                                 scope="by_user", agent_id="data-analysis", knowledge="查 DAU")
        res = skill_evolve_svc.materialize_candidate("t1", cand["id"], decided_by="alice", uid="alice")
        assert res["immediately_usable"] and res["bound_agent"] == "data-analysis" and res["needs_review"] is False
        assert skill_svc.get_skill_candidate("t1", cand["id"])["status"] == "approved"

    def test_by_team_creates_approval(self):
        _mk_agent()
        cand = skill_svc.propose_skill_candidate("t1", name="DAU", description="", runtime="python",
                                                 code="print(1)", proposer="alice",
                                                 scope="by_team", agent_id="data-analysis")
        res = skill_evolve_svc.materialize_candidate("t1", cand["id"], decided_by="alice", uid="alice")
        assert res["needs_review"] is True and res.get("promotion_approval_id")


class TestPromoteDoubleGate:
    def test_gate1_requires_test_run(self):
        _mk_agent()
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code='print("ok")')
        with pytest.raises(Exception):  # 门1：未 test-run
            skill_evolve_svc.promote_to_team(s["id"], uid="alice", tid="t_growth", decided_by="admin")

    def test_promote_after_test_run(self):
        _mk_agent()
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code='print("ok")')
        skill_svc.test_run(s["id"], uid="alice")
        res = skill_evolve_svc.promote_to_team(s["id"], uid="alice", tid="t_growth",
                                               decided_by="admin", agent_id="data-analysis")
        assert res["scope"] == "by_team"
        agent = read_json(paths.agent_json("data-analysis"))
        assert agent["version"] == 2 and s["id"] in agent["skills"]


class TestBindRollback:
    def test_rollback_new_version(self):
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code='print("v1")')
        skill_svc.save_new_version(skill_svc.get_skill(s["id"], uid="alice"), 'print("v2")', note="edit")
        rb = skill_evolve_svc.rollback_skill(s["id"], 1, uid="alice")
        assert rb["rolled_back_to"] == 1 and rb["version"] == 3
        cur = skill_svc.get_skill(s["id"], uid="alice")
        assert skill_svc.read_skill_code(cur) == 'print("v1")'
        assert [m["version"] for m in skill_svc.list_versions(cur)] == [1, 2, 3]

    def test_user_binding_isolated(self):
        _mk_agent()
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code="print(1)")
        skill_evolve_svc.bind_to_agent("data-analysis", s["id"], uid="alice", team=False)
        assert len(skill_evolve_svc.list_agent_bindings("data-analysis", uid="alice")["user_skills"]) == 1
        assert len(skill_evolve_svc.list_agent_bindings("data-analysis", uid="bob")["user_skills"]) == 0


class TestContextInjection:
    def _task(self):
        return {"id": "t_inj", "title": "x", "type": "data", "status": "doing", "project_id": "",
                "participants": [{"ref_type": "agent", "ref_id": "data-analysis", "role": "tool"}]}

    def _text(self, uid):
        msgs = context_assembler_svc.assemble_context(
            self._task(), speaker={"type": "agent", "id": "data-analysis"}, acting_user_id=uid)
        return "\n".join(m["content"] for m in msgs)

    def test_owner_sees_skill(self):
        _mk_agent()
        s = skill_svc.create_user_skill("alice", name="XX_DAU_SKILL", description="",
                                        runtime="python", code='print(params.get("ch"))', knowledge="查 XX DAU")
        skill_evolve_svc.bind_to_agent("data-analysis", s["id"], uid="alice", team=False, knowledge="查 XX DAU")
        assert "XX_DAU_SKILL" in self._text("alice")

    def test_other_user_not_injected(self):
        _mk_agent()
        s = skill_svc.create_user_skill("alice", name="ALICE_SECRET", description="", runtime="python", code="print(1)")
        skill_evolve_svc.bind_to_agent("data-analysis", s["id"], uid="alice", team=False)
        assert "ALICE_SECRET" not in self._text("bob")


class TestPromoteApiGate:
    """门2 端到端（HTTP）：团队晋升需 owner/admin。promote 路由 = POST /skills/promote/{tid}。"""

    def _hdr(self, uid):
        user_svc.ensure_user(uid)  # platform_role 默认 user
        return {"Authorization": f"Bearer {create_access_token(uid)}"}

    def test_owner_can_promote(self):
        _mk_agent()
        hdr = self._hdr("alice")
        team_svc.create_team("t_test", name="T", owner_id="alice")
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code='print("ok")')
        skill_svc.test_run(s["id"], uid="alice")  # 门1
        r = TestClient(app).post("/api/v1/skills/promote/t_test",
                                 json={"skill_id": s["id"], "agent_id": "data-analysis"}, headers=hdr)
        assert r.status_code == 200 and r.json()["data"]["scope"] == "by_team"

    def test_non_member_blocked(self):
        hdr_bob = self._hdr("bob")
        self._hdr("alice")
        team_svc.create_team("t_test", name="T", owner_id="alice")
        s = skill_svc.create_user_skill("bob", name="S", description="", runtime="python", code="print(1)")
        r = TestClient(app).post("/api/v1/skills/promote/t_test",
                                 json={"skill_id": s["id"]}, headers=hdr_bob)
        assert r.status_code == 403

    def test_gate1_blocks_without_testrun(self):
        hdr = self._hdr("alice")
        team_svc.create_team("t_test", name="T", owner_id="alice")
        s = skill_svc.create_user_skill("alice", name="S", description="", runtime="python", code="print(1)")
        r = TestClient(app).post("/api/v1/skills/promote/t_test", json={"skill_id": s["id"]}, headers=hdr)
        assert r.status_code == 409  # 门1：未 test-run
