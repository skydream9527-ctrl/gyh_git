"""Tests for usage_svc.by_dimension's per-user / per-task label resolution.

Seeds synthetic llm_usage rows + users_index + tasks_index rows, then asserts
that by_dimension returns human-readable labels alongside the raw keys.
Fallback behavior (missing row → label = key) is also verified.
"""
from __future__ import annotations

import pytest

from app.core.storage import get_index_db
from app.services import agents_svc, usage_svc


async def _seed_usage(**overrides):
    """Insert one llm_usage row with the current day so it falls within the
    default 30-day window."""
    await usage_svc._ensure_table()  # noqa: SLF001
    db = get_index_db()
    row = {
        "id": overrides.get("id", "rec"),
        "user_id": overrides.get("user_id"),
        "agent_id": overrides.get("agent_id"),
        "task_id": overrides.get("task_id"),
        "conversation_id": "c1",
        "model": overrides.get("model", "ppio/pa/claude-opus-4-7"),
        "input_tokens": overrides.get("input_tokens", 100),
        "output_tokens": overrides.get("output_tokens", 50),
        "cost_usd": overrides.get("cost_usd", 0.005),
        "success": 1,
        "created_at": usage_svc._now().isoformat(),  # noqa: SLF001
        "day": usage_svc._day(usage_svc._now()),  # noqa: SLF001
    }
    await db.upsert("llm_usage", row)


@pytest.mark.asyncio
async def test_by_user_resolves_name(isolated_data_root):
    """user_id dimension should surface users_index.name."""
    db = get_index_db()
    await db.init()
    await db.upsert(
        "users_index",
        {
            "id": "u-alice",
            "email": "alice@example.com",
            "name": "Alice Smith",
            "auth_role": "user",
            "status": "active",
            "feishu_user_id": None,
            "last_login_at": None,
            "password_hash": None,
            "created_at": "2026-01-01",
        },
    )
    await _seed_usage(user_id="u-alice", id="r1")
    items = await usage_svc.by_dimension(dimension="user_id", days=30, limit=10)
    assert len(items) == 1
    assert items[0]["key"] == "u-alice"
    assert items[0]["label"] == "Alice Smith"


@pytest.mark.asyncio
async def test_by_user_falls_back_to_email(isolated_data_root):
    """Users without a `name` fall back to their email (COALESCE order)."""
    db = get_index_db()
    await db.init()
    await db.upsert(
        "users_index",
        {
            "id": "u-bob",
            "email": "bob@example.com",
            "name": None,
            "auth_role": "user",
            "status": "active",
            "feishu_user_id": None,
            "last_login_at": None,
            "password_hash": None,
            "created_at": "2026-01-01",
        },
    )
    await _seed_usage(user_id="u-bob", id="r1")
    items = await usage_svc.by_dimension(dimension="user_id", days=30, limit=10)
    assert items[0]["label"] == "bob@example.com"


@pytest.mark.asyncio
async def test_by_user_missing_falls_back_to_key(isolated_data_root):
    """Unknown user_id (e.g. deleted account) → label equals the raw key."""
    db = get_index_db()
    await db.init()
    await _seed_usage(user_id="u-ghost", id="r1")
    items = await usage_svc.by_dimension(dimension="user_id", days=30, limit=10)
    assert items[0]["label"] == "u-ghost"


@pytest.mark.asyncio
async def test_by_task_resolves_name(isolated_data_root):
    db = get_index_db()
    await db.init()
    await db.upsert(
        "tasks_index",
        {
            "id": "t-funnel",
            "owner_id": "u1",
            "name": "Q2 漏斗分析",
            "paradigm": "biz",
            "agent_id": "biz-insight",
            "status": "active",
            "visibility": "private",
            "publish_status": "draft",
            "file_count": 0,
            "last_message_preview": None,
            "updated_at": "2026-01-01",
            "created_at": "2026-01-01",
        },
    )
    await _seed_usage(task_id="t-funnel", id="r1")
    items = await usage_svc.by_dimension(dimension="task_id", days=30, limit=10)
    assert items[0]["key"] == "t-funnel"
    assert items[0]["label"] == "Q2 漏斗分析"


@pytest.mark.asyncio
async def test_by_agent_resolves_name(isolated_data_root):
    """agent_id dimension reads agents/<id>/agent.json.name."""
    db = get_index_db()
    await db.init()
    agents_svc.create_agent(
        agent_id="my-analyst", name="数据分析师自建", paradigm="custom"
    )
    await _seed_usage(agent_id="my-analyst", id="r1")
    items = await usage_svc.by_dimension(dimension="agent_id", days=30, limit=10)
    assert items[0]["label"] == "数据分析师自建"


@pytest.mark.asyncio
async def test_by_model_leaves_label_equal_key(isolated_data_root):
    """model strings are already human-readable — no resolution, label==key."""
    db = get_index_db()
    await db.init()
    await _seed_usage(
        user_id="u1", id="r1", model="ppio/pa/claude-opus-4-7"
    )
    items = await usage_svc.by_dimension(dimension="model", days=30, limit=10)
    assert items[0]["key"] == "ppio/pa/claude-opus-4-7"
    assert items[0]["label"] == "ppio/pa/claude-opus-4-7"


@pytest.mark.asyncio
async def test_multiple_users_aggregated_and_sorted(isolated_data_root):
    """Two users with different spend — by_dimension aggregates per user and
    sorts DESC by cost."""
    db = get_index_db()
    await db.init()
    for uid, name, cost in [
        ("u1", "User One", 0.5),
        ("u2", "User Two", 2.0),
        ("u1", "User One", 0.25),
    ]:
        await db.upsert(
            "users_index",
            {
                "id": uid,
                "email": f"{uid}@x.com",
                "name": name,
                "auth_role": "user",
                "status": "active",
                "feishu_user_id": None,
                "last_login_at": None,
                "password_hash": None,
                "created_at": "2026-01-01",
            },
        )
    await _seed_usage(user_id="u1", id="a", cost_usd=0.5)
    await _seed_usage(user_id="u2", id="b", cost_usd=2.0)
    await _seed_usage(user_id="u1", id="c", cost_usd=0.25)
    items = await usage_svc.by_dimension(dimension="user_id", days=30, limit=10)
    assert [it["key"] for it in items] == ["u2", "u1"]  # DESC by cost
    u1 = next(it for it in items if it["key"] == "u1")
    assert abs(u1["cost_usd"] - 0.75) < 1e-6
    assert u1["calls"] == 2
