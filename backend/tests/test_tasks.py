from __future__ import annotations

import pytest

from app.services import hitl_svc, scheduler_svc, task_svc


async def _make_user_task(uid: str = "u1", name: str = "Task") -> dict:
    from app.core.storage import get_index_db, get_paths

    await get_index_db().init()
    (get_paths().users / uid / "tasks").mkdir(parents=True, exist_ok=True)
    return await task_svc.create_task(name=name, paradigm="biz", owner_id=uid)


@pytest.mark.asyncio
async def test_create_and_list_task(isolated_data_root):
    uid = "u1"
    task = await _make_user_task(uid, name="Demo Q2 复盘")
    assert task["id"]
    items = await task_svc.list_user_tasks(uid)
    assert any(t["id"] == task["id"] for t in items)
    detail = await task_svc.get_task(task["id"], uid)
    assert detail["name"] == "Demo Q2 复盘"


@pytest.mark.asyncio
async def test_update_task_and_run_events(isolated_data_root):
    uid = "u1"
    task = await _make_user_task(uid, name="Old")

    updated = await task_svc.update_task(task["id"], uid, {"name": "New", "status": "running"})
    assert updated["name"] == "New"
    assert updated["status"] == "running"
    listed = await task_svc.list_user_tasks(uid)
    assert any(t["id"] == task["id"] and t["name"] == "New" for t in listed)

    cid = await task_svc.get_or_create_default_conversation(task["id"])
    task_svc.append_run_event(task["id"], cid, {"run_id": "r1", "label": "start"})
    assert task_svc.list_run_events(task["id"], cid)[0]["run_id"] == "r1"


@pytest.mark.asyncio
async def test_hitl_request_resolve_updates_status(isolated_data_root):
    uid = "u1"
    task = await _make_user_task(uid, name="HITL")
    cid = await task_svc.get_or_create_default_conversation(task["id"])

    req = await hitl_svc.create_request(
        task_id=task["id"],
        conv_id=cid,
        created_by=uid,
        title="确认口径",
        message="请选择异常值处理方式",
    )
    paused = await task_svc.get_task(task["id"], uid)
    assert paused["status"] == "paused"
    assert (await hitl_svc.list_requests(task["id"], status="pending"))[0]["id"] == req["id"]

    resolved = await hitl_svc.resolve_request(
        task_id=task["id"],
        request_id=req["id"],
        user_id=uid,
        decision="continue",
        payload={"note": "剔除异常"},
    )
    assert resolved["status"] == "resolved"
    active = await task_svc.get_task(task["id"], uid)
    assert active["status"] == "active"


def test_scheduler_summary_counts_recent_failures(isolated_data_root):
    from app.core.storage import append_jsonl, get_paths, write_json

    paths = get_paths()
    (paths.users / "u1" / "tasks").mkdir(parents=True)
    (paths.tasks / "t1").mkdir(parents=True)
    write_json(paths.user_tasks_index("u1"), [{"task_id": "t1", "name": "T"}])
    write_json(
        paths.task_dir("t1") / "scheduled.json",
        [
            {
                "id": "s1",
                "task_id": "t1",
                "name": "S",
                "enabled": True,
                "cron": "0 9 * * *",
            }
        ],
    )
    append_jsonl(
        paths.task_dir("t1") / "scheduled_runs" / "s1.jsonl",
        {
            "id": "r1",
            "scheduled_id": "s1",
            "task_id": "t1",
            "status": "failed",
            "started_at": scheduler_svc._now_iso(),
        },
    )
    summary = scheduler_svc.summary_for_user("u1")
    assert summary["enabled"] == 1
    assert summary["failed_7d"] == 1
