"""Tests for the monthly budget config + migration + enforce toggle."""
from __future__ import annotations

import pytest

from app.core.storage import get_paths, read_json, write_json
from app.services import sysconfig_svc


def test_default_budget_is_2000(isolated_data_root):
    """Fresh install: default monthly budget is $2000 USD."""
    assert sysconfig_svc.DEFAULTS["llm"]["budget_monthly_usd"] == 2000.0


def test_fresh_read_returns_2000(isolated_data_root):
    """On a blank install, get_llm_config() returns the new $2000 default
    and does NOT carry an enforce_budget_cap field (budget is notify-only)."""
    cfg = sysconfig_svc.get_llm_config()
    assert cfg["budget_monthly_usd"] == 2000.0
    assert "enforce_budget_cap" not in cfg


def test_migration_bumps_old_default_200(isolated_data_root):
    """Legacy install: system-config.json has budget=200. _read() bumps to 2000."""
    p = get_paths().cache / "system-config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        p,
        {
            "toggles": {},
            "system_params": {},
            "llm": {
                "budget_monthly_usd": 200.0,
                "budget_alert_threshold": 0.8,
                "models": [],
            },
            "announcements": [],
        },
    )
    cfg = sysconfig_svc.get_llm_config()
    assert cfg["budget_monthly_usd"] == 2000.0
    on_disk = read_json(p)
    assert on_disk["llm"]["budget_monthly_usd"] == 2000.0


def test_migration_preserves_custom_budget(isolated_data_root):
    """An admin-set budget (anything other than the old $200) is left alone."""
    p = get_paths().cache / "system-config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        p,
        {
            "toggles": {},
            "system_params": {},
            "llm": {
                "budget_monthly_usd": 500.0,
                "budget_alert_threshold": 0.9,
                "models": [],
            },
            "announcements": [],
        },
    )
    cfg = sysconfig_svc.get_llm_config()
    assert cfg["budget_monthly_usd"] == 500.0
    assert cfg["budget_alert_threshold"] == 0.9


def test_migration_strips_stale_enforce_key(isolated_data_root):
    """Installs that ran an earlier hard-cap migration carry
    `enforce_budget_cap: true` on disk — _read() now removes it since the
    feature is gone (budget is notify-only)."""
    p = get_paths().cache / "system-config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        p,
        {
            "toggles": {},
            "system_params": {},
            "llm": {
                "budget_monthly_usd": 2000.0,
                "budget_alert_threshold": 0.8,
                "enforce_budget_cap": True,
                "models": [],
            },
            "announcements": [],
        },
    )
    cfg = sysconfig_svc.get_llm_config()
    assert "enforce_budget_cap" not in cfg
    on_disk = read_json(p)
    assert "enforce_budget_cap" not in on_disk["llm"]


def test_admin_can_set_low_budget(isolated_data_root):
    """Admin can lower the budget below the 2000 default without being
    overwritten on next read."""
    sysconfig_svc.update_llm_budget(
        budget_monthly_usd=100.0, budget_alert_threshold=0.8
    )
    cfg = sysconfig_svc.get_llm_config()
    assert cfg["budget_monthly_usd"] == 100.0


def test_month_summary_exceeded_at_budget(isolated_data_root, monkeypatch):
    """Inject a spend >= budget; month_summary should report state=exceeded."""
    import asyncio
    from app.services import usage_svc

    async def run():
        await usage_svc._ensure_table()  # noqa: SLF001 — test setup
        from app.core.storage import get_index_db

        db = get_index_db()
        await db.upsert(
            "llm_usage",
            {
                "id": "rec1",
                "user_id": "u1",
                "agent_id": "a",
                "task_id": "t",
                "conversation_id": "c",
                "model": "ppio/pa/claude-opus-4-7",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost_usd": 3000.0,  # well over the $2000 default
                "success": 1,
                "created_at": usage_svc._now().isoformat(),  # noqa: SLF001
                "day": usage_svc._day(usage_svc._now()),  # noqa: SLF001 — YYYY-MM-DD
            },
        )
        return await usage_svc.month_summary()

    summary = asyncio.run(run())
    assert summary["budget_usd"] == 2000.0
    assert summary["cost_usd"] >= 3000.0
    assert summary["budget_state"] == "exceeded"
