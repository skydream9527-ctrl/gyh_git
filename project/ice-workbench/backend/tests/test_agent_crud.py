"""Tests for Agent CRUD additions — create, delete, guards."""
from __future__ import annotations

import pytest

from app.core.errors import APIError
from app.core.storage import get_paths, write_json
from app.services import agents_svc


@pytest.mark.asyncio
async def test_create_agent_writes_files(isolated_data_root):
    cfg = agents_svc.create_agent(
        agent_id="my-analyst",
        name="我的分析师",
        paradigm="custom",
        icon="🧮",
        color="#abcdef",
        description="自建",
        system_prompt="你好",
    )
    assert cfg["id"] == "my-analyst"
    paths = get_paths()
    assert (paths.agents / "my-analyst" / "agent.json").exists()
    assert (paths.agents / "my-analyst" / "prompt" / "system.md").read_text() == "你好"
    assert (paths.agents / "my-analyst" / "prompt" / "cards.md").exists()


def test_create_agent_rejects_bad_id(isolated_data_root):
    for bad in ("Bad", "1starts-with-digit", "sh", "has_underscore", "a" * 50):
        with pytest.raises(APIError) as exc:
            agents_svc.create_agent(agent_id=bad, name="x", paradigm="custom")
        assert exc.value.error_code == "VALIDATION_ERROR"


def test_create_agent_rejects_duplicate(isolated_data_root):
    agents_svc.create_agent(agent_id="dup", name="x", paradigm="custom")
    with pytest.raises(APIError) as exc:
        agents_svc.create_agent(agent_id="dup", name="x", paradigm="custom")
    assert exc.value.status_code == 409


def test_create_agent_defaults_icon_and_color(isolated_data_root):
    cfg = agents_svc.create_agent(agent_id="minimal", name="简", paradigm="custom")
    assert cfg["icon"] == "🤖"
    assert cfg["color"] == "#7bafd4"
    assert cfg["publish_status"] == "draft"


@pytest.mark.asyncio
async def test_delete_agent_removes_dir(isolated_data_root):
    from app.core.storage import get_index_db

    await get_index_db().init()  # bootstrap the tasks_index table for this test
    agents_svc.create_agent(agent_id="todelete", name="待删", paradigm="custom")
    paths = get_paths()
    assert (paths.agents / "todelete").exists()
    result = await agents_svc.delete_agent(agent_id="todelete")
    assert result["removed"] is True
    assert result["tasks_orphaned"] == 0
    assert not (paths.agents / "todelete").exists()


@pytest.mark.asyncio
async def test_delete_agent_rejects_protected_seed(isolated_data_root):
    """Seed agents (biz-insight, ab-experiment, etc.) cannot be deleted — the
    seed loop would recreate them and the audit trail would be misleading."""
    agents_svc.list_agents()  # triggers _ensure_seed_agents()
    with pytest.raises(APIError) as exc:
        await agents_svc.delete_agent(agent_id="biz-insight")
    assert exc.value.error_code == "VALIDATION_ERROR"
    assert "预置" in exc.value.message


@pytest.mark.asyncio
async def test_delete_agent_refuses_when_in_use(isolated_data_root):
    """If any task references the agent, delete refuses unless force=True."""
    from app.core.storage import get_index_db

    db = get_index_db()
    await db.init()
    agents_svc.create_agent(agent_id="in-use", name="x", paradigm="custom")
    await db.upsert(
        "tasks_index",
        {
            "id": "t1",
            "owner_id": "u1",
            "name": "测试",
            "paradigm": "custom",
            "agent_id": "in-use",
            "status": "active",
            "visibility": "private",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        },
    )
    with pytest.raises(APIError) as exc:
        await agents_svc.delete_agent(agent_id="in-use")
    assert exc.value.status_code == 409
    assert "1 个任务" in exc.value.message

    # force=True should succeed and report the orphaned count.
    result = await agents_svc.delete_agent(agent_id="in-use", force=True)
    assert result["removed"] is True
    assert result["tasks_orphaned"] == 1


@pytest.mark.asyncio
async def test_delete_agent_missing(isolated_data_root):
    with pytest.raises(APIError) as exc:
        await agents_svc.delete_agent(agent_id="does-not-exist")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_created_agent_shows_in_list(isolated_data_root):
    agents_svc.create_agent(agent_id="visible", name="可见", paradigm="custom")
    ids = [a["id"] for a in agents_svc.list_agents()]
    assert "visible" in ids
