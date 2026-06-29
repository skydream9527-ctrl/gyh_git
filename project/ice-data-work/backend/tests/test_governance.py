"""M4 测试：审计、一键暂停、失败复盘、共享空间隔离、用量、admin。"""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def setup_env():
    d = tempfile.mkdtemp()
    os.environ["DATA_ROOT"] = d
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core.storage import paths
    paths.ensure_top_level()
    yield


def _svcs():
    from app.services import (
        audit_svc, control_svc, error_classifier, shared_svc, usage_svc, task_svc,
    )
    return audit_svc, control_svc, error_classifier, shared_svc, usage_svc, task_svc


class TestAudit:
    def test_record_and_read_task_audit(self):
        audit_svc, _, _, _, _, task_svc = _svcs()
        t = task_svc.create_task(title="审计", project_id="p_x", created_by="alice")
        audit_svc.record(actor="alice", action="tool_call", task_id=t["id"], tool="now", summary="取时间")
        events = audit_svc.list_task_audit(t["id"])
        assert len(events) == 1
        assert events[0]["tool"] == "now"

    def test_blocked_cross_space_recorded(self):
        audit_svc, _, _, _, _, task_svc = _svcs()
        t = task_svc.create_task(title="越权", project_id="p_x", created_by="alice")
        ev = audit_svc.record_blocked_cross_space("alice", "users/bob/twin", task_id=t["id"])
        assert ev["result"] == "blocked"
        events = audit_svc.list_task_audit(t["id"])
        assert any(e["action"] == "cross_space_read" and e["result"] == "blocked" for e in events)

    def test_recent_for_user_aggregates(self):
        audit_svc, _, _, _, _, task_svc = _svcs()
        t = task_svc.create_task(title="聚合", project_id="p_x", created_by="alice")
        audit_svc.record(actor="alice", action="agent_turn", task_id=t["id"], summary="x")
        recent = audit_svc.list_recent_for_user("alice")
        assert len(recent) >= 1
        assert recent[0]["task_title"] == "聚合"


class TestPause:
    def test_pause_resume(self):
        _, control_svc, _, _, _, _ = _svcs()
        assert not control_svc.is_paused()
        control_svc.pause_all("admin")
        assert control_svc.is_paused()
        control_svc.resume_all("admin")
        assert not control_svc.is_paused()

    def test_runtime_blocked_when_paused(self):
        _, control_svc, _, _, _, task_svc = _svcs()
        from app.services import agent_runtime
        t = task_svc.create_task(title="暂停拦截", project_id="p_x", created_by="alice")
        control_svc.pause_all("admin")
        events = list(agent_runtime.run_agent_turn(t["id"], user_message="hi", acting_user_id="alice"))
        assert any(e["type"] == "error" and "暂停" in e["message"] for e in events)


class TestErrorClassifier:
    def test_timeout(self):
        _, _, error_classifier, _, _, _ = _svcs()
        r = error_classifier.classify("kyuubi query timed out after 60s")
        assert r["error_type"] == "timeout"
        assert r["recoverable"] is True

    def test_kyuubi_not_configured(self):
        _, _, error_classifier, _, _, _ = _svcs()
        r = error_classifier.classify("", error_code="KYUUBI_NOT_CONFIGURED")
        assert r["error_type"] == "integration_unavailable"
        assert r["recoverable"] is False

    def test_permission_denied(self):
        _, _, error_classifier, _, _, _ = _svcs()
        r = error_classifier.classify("CROSS_SPACE_DENIED: 越权读取")
        assert r["error_type"] == "permission_denied"

    def test_unknown_default(self):
        _, _, error_classifier, _, _, _ = _svcs()
        r = error_classifier.classify("某种没见过的错误")
        assert r["error_type"] == "unknown"
        assert r["recoverable"] is True


class TestSharedSpace:
    def test_team_write_read_list(self):
        _, _, _, shared_svc, _, _ = _svcs()
        shared_svc.write_item("team", "knowledge", "口径.md", "# DAU 口径\n去重日活", tid="t_growth")
        items = shared_svc.list_items("team", "knowledge", tid="t_growth")
        assert len(items) == 1
        assert items[0]["name"] == "口径.md"
        content = shared_svc.read_item("team", "knowledge", "口径.md", tid="t_growth")
        assert "去重日活" in content["content"]

    def test_project_team_isolation(self):
        """项目级与团队级共享相互隔离。"""
        _, _, _, shared_svc, _, _ = _svcs()
        shared_svc.write_item("team", "files", "团队文件.txt", "team", tid="t_growth")
        shared_svc.write_item("project", "files", "项目文件.txt", "proj", tid="t_growth", pid="p_growth")

        team_items = shared_svc.list_items("team", "files", tid="t_growth")
        proj_items = shared_svc.list_items("project", "files", tid="t_growth", pid="p_growth")
        assert [i["name"] for i in team_items] == ["团队文件.txt"]
        assert [i["name"] for i in proj_items] == ["项目文件.txt"]

    def test_invalid_kind(self):
        _, _, _, shared_svc, _, _ = _svcs()
        with pytest.raises(Exception):
            shared_svc.list_items("team", "bogus", tid="t_growth")

    def test_path_traversal_blocked(self):
        _, _, _, shared_svc, _, _ = _svcs()
        with pytest.raises(Exception):
            shared_svc.write_item("team", "files", "../escape.txt", "x", tid="t_growth")

    def test_assets_aggregation(self):
        _, _, _, shared_svc, _, _ = _svcs()
        shared_svc.write_item("team", "knowledge", "t.md", "team", tid="t_growth")
        shared_svc.write_item("project", "artifacts", "p.md", "proj", tid="t_growth", pid="p_growth")
        assets = shared_svc.list_all_for_project("t_growth", "p_growth")
        assert len(assets["team"]["knowledge"]) == 1
        assert len(assets["project"]["artifacts"]) == 1


class TestUsage:
    def test_record_and_summary(self):
        _, _, _, _, usage_svc, _ = _svcs()
        usage_svc.record_usage(model="claude-sonnet-4", input_tokens=1000, output_tokens=500, user_id="alice")
        usage_svc.record_usage(model="claude-sonnet-4", input_tokens=2000, output_tokens=1000, user_id="alice")
        s = usage_svc.summary()
        assert s["total_calls"] == 2
        assert s["total_tokens"] == 4500
        assert s["total_cost_usd"] > 0

    def test_mock_zero_cost(self):
        _, _, _, _, usage_svc, _ = _svcs()
        usage_svc.record_usage(model="claude-sonnet-4", output_tokens=100, mock=True)
        s = usage_svc.summary()
        assert s["total_calls"] == 1
        assert s["total_cost_usd"] == 0.0

    def test_csv_export(self):
        _, _, _, _, usage_svc, _ = _svcs()
        usage_svc.record_usage(model="claude-sonnet-4", input_tokens=100, output_tokens=50)
        csv_text = usage_svc.export_csv()
        assert "model" in csv_text
        assert "claude-sonnet-4" in csv_text


class TestAdminApi:
    def test_overview_requires_admin(self):
        """普通用户访问 admin overview 应被拒。"""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        # 注册普通用户
        from app.services import auth_svc
        reg = auth_svc.register("normaluser", "pw123", "普通")
        token = reg["token"]
        r = client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {token}"})
        body = r.json()
        assert body["error_code"] == "FORBIDDEN"

    def test_overview_admin_ok(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        from app.services import user_svc
        user_svc.create_user("adminx", name="Admin X", password="pw", platform_role="super_admin")
        from app.services import auth_svc
        login = auth_svc.login("adminx", "pw")
        token = login["token"]
        r = client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {token}"})
        body = r.json()
        assert body["error_code"] == "OK"
        assert "users" in body["data"]
