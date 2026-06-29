"""M7 测试：任务计划模型（T06）+ 计划编排拆解/推进（T07）+ 目标/DoD 门控（T08）。"""
from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATA_ROOT"] = _tmp

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.storage import paths  # noqa: E402
from app.services import plan_svc, task_svc  # noqa: E402


@pytest.fixture(autouse=True)
def setup_env():
    paths.ensure_top_level()
    yield


def _task(**kw):
    return task_svc.create_task(title=kw.pop("title", "计划任务"),
                                project_id="p_x", created_by="admin", **kw)


# ─────────────────── T06 计划模型 ───────────────────

class TestPlanModel:
    def test_ensure_and_add_step(self):
        t = _task()
        plan_svc.ensure_plan(t["id"], goal="做归因")
        assert plan_svc.get_plan(t["id"])["goal"] == "做归因"
        s = plan_svc.add_step(t["id"], title="取数", owner_agent="data-analysis")
        assert s["status"] == "todo"
        assert plan_svc.get_plan(t["id"])["steps"][0]["title"] == "取数"

    def test_step_status_and_progress(self):
        t = _task()
        plan_svc.ensure_plan(t["id"])
        s1 = plan_svc.add_step(t["id"], title="一", owner_agent="a")
        plan_svc.add_step(t["id"], title="二", owner_agent="b")
        prog0 = plan_svc.progress(t["id"])
        assert prog0 == {"total": 2, "done": 0, "current_index": 0, "current_title": ""}
        plan_svc.update_step(t["id"], s1["id"], status="done")
        prog1 = plan_svc.progress(t["id"])
        assert prog1["done"] == 1 and prog1["total"] == 2
        # 完成第一步后 current 推进到第二步
        cur = plan_svc.current_step(t["id"])
        assert cur and cur["title"] == "二"

    def test_invalid_step_status(self):
        t = _task()
        plan_svc.ensure_plan(t["id"])
        s = plan_svc.add_step(t["id"], title="x")
        with pytest.raises(Exception):
            plan_svc.update_step(t["id"], s["id"], status="bogus")

    def test_depends_on_gating(self):
        t = _task()
        plan_svc.replace_steps(t["id"], [
            {"title": "A", "owner_agent": "a"},
            {"title": "B", "owner_agent": "b"},
        ])
        plan = plan_svc.get_plan(t["id"])
        a_id, b_id = plan["steps"][0]["id"], plan["steps"][1]["id"]
        # B 依赖 A：A 未完成时 next_ready 仍是 A
        plan_svc.update_step(t["id"], b_id, title="B")  # 不改状态
        # 手动设 B 依赖 A
        with_dep = plan_svc.get_plan(t["id"])
        with_dep["steps"][1]["depends_on"] = [a_id]
        from app.core.storage.jsonio import write_json
        write_json(paths.task_plan(t["id"]), with_dep)
        nxt = plan_svc.next_ready_step(t["id"])
        assert nxt["id"] == a_id
        plan_svc.update_step(t["id"], a_id, status="done")
        nxt2 = plan_svc.next_ready_step(t["id"])
        assert nxt2["id"] == b_id

    def test_is_plan_complete(self):
        t = _task()
        plan_svc.ensure_plan(t["id"])
        assert plan_svc.is_plan_complete(t["id"]) is False  # 空计划不算完成
        s = plan_svc.add_step(t["id"], title="只有一步")
        assert plan_svc.is_plan_complete(t["id"]) is False
        plan_svc.update_step(t["id"], s["id"], status="done")
        assert plan_svc.is_plan_complete(t["id"]) is True

    def test_start_next(self):
        t = _task()
        plan_svc.replace_steps(t["id"], [{"title": "一", "owner_agent": "a"}])
        nxt = plan_svc.start_next(t["id"])
        assert nxt["status"] == "doing"
        assert plan_svc.current_step(t["id"])["id"] == nxt["id"]


# ─────────────────── T07 拆解/推进 ───────────────────

class TestPlanOrchestration:
    def test_decompose_splits_clauses(self):
        steps = plan_svc.decompose_goal("取数；清洗；建模。出报告", ["a", "b"])
        assert [s["title"] for s in steps] == ["取数", "清洗", "建模", "出报告"]
        # owner 轮转
        assert steps[0]["owner_agent"] == "a"
        assert steps[1]["owner_agent"] == "b"
        assert steps[2]["owner_agent"] == "a"

    def test_decompose_numbered_list(self):
        steps = plan_svc.decompose_goal("1. 拉新增 2. 看留存 3. 给结论", [])
        assert [s["title"] for s in steps] == ["拉新增", "看留存", "给结论"]

    def test_decompose_fallback_single(self):
        steps = plan_svc.decompose_goal("分析 DAU 异动", [])
        assert len(steps) == 1
        assert "DAU" in steps[0]["title"]

    def test_advance_success(self):
        t = _task()
        plan_svc.replace_steps(t["id"], [{"title": "一", "owner_agent": "a"},
                                         {"title": "二", "owner_agent": "b"}])
        plan_svc.start_next(t["id"])  # 一 → doing
        r = plan_svc.plan_advance_after_turn(t["id"])
        assert r["current"]["title"] == "一"
        assert r["next"]["title"] == "二"
        assert r["failed"] is None

    def test_advance_failure_attaches_suggestion(self):
        t = _task()
        plan_svc.replace_steps(t["id"], [{"title": "查库", "owner_agent": "a"}])
        plan_svc.start_next(t["id"])
        r = plan_svc.plan_advance_after_turn(t["id"], errored=True, error_message="kyuubi 连接超时 timeout")
        assert r["failed"]["title"] == "查库"
        assert r["suggestion"] is not None
        # 失败步保持 error，未推进
        assert plan_svc.get_plan(t["id"])["steps"][0]["status"] == "error"


# ─────────────────── T08 目标/DoD 门控 ───────────────────

class TestDoDGate:
    def test_no_dod_done_freely(self):
        t = _task()
        task_svc.set_status(t["id"], "doing")
        meta = task_svc.set_status(t["id"], "done")  # 无 DoD，自由完成
        assert meta["status"] == "done"

    def test_dod_blocks_without_confirm(self):
        t = _task(definition_of_done="报告需评审通过")
        task_svc.set_status(t["id"], "doing")
        with pytest.raises(Exception) as e:
            task_svc.set_status(t["id"], "done")
        assert "DoD" in str(e.value) or "完成判据" in str(e.value)

    def test_dod_allows_with_confirm(self):
        t = _task(definition_of_done="报告需评审通过")
        task_svc.set_status(t["id"], "doing")
        meta = task_svc.set_status(t["id"], "done", confirm=True)
        assert meta["status"] == "done"
        assert "completed_at" in meta

    def test_dod_allows_when_plan_complete(self):
        t = _task(definition_of_done="所有步骤完成")
        plan_svc.ensure_plan(t["id"])
        s = plan_svc.add_step(t["id"], title="唯一步")
        plan_svc.update_step(t["id"], s["id"], status="done")
        task_svc.set_status(t["id"], "doing")
        meta = task_svc.set_status(t["id"], "done")  # 计划已完成，无需 confirm
        assert meta["status"] == "done"

    def test_goal_dod_in_summary(self):
        _task(title="带目标", goal="G", definition_of_done="D")
        tasks = task_svc.list_tasks(project_id="p_x")
        target = next(t for t in tasks if t["title"] == "带目标")
        assert target["goal"] == "G"
        assert target["has_dod"] is True
