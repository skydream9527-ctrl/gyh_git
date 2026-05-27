"""Regression tests for the dev_bypass tightening.

The bug: with `AEGIS_DEV_BYPASS_EMAIL=admin` set in `.env`, every request
without other auth got resolved as the bypass account — so the SPA's
`/auth/me` call after a wrong-password "login" auto-promoted the user to
admin. The fix gates dev_bypass behind an explicit `X-Dev-Bypass: 1` header.

These tests assert:

1. /auth/login still rejects wrong passwords with 401 (it always did, but we
   prove it's still correct now).
2. /auth/me with no Bearer and no X-Dev-Bypass header → 401 (no silent
   auto-login, even when AEGIS_DEV_BYPASS_EMAIL is set).
3. /auth/me with X-Dev-Bypass: 1 → 200 + dev_bypass user (the escape hatch
   still works for explicit dev clients like curl).
4. Issued JWT continues to work normally.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.seed.runner import bootstrap


@pytest.fixture
def dev_bypass_env(monkeypatch):
    """Pretend the dev's .env has AEGIS_DEV_BYPASS_EMAIL=admin."""
    monkeypatch.setenv("AEGIS_DEV_BYPASS_EMAIL", "admin")
    monkeypatch.setenv("AEGIS_ENABLED", "true")
    from app.core import config as cfg

    cfg.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_with_wrong_password_rejected(isolated_data_root, dev_bypass_env):
    await bootstrap()
    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/auth/login", json={"email": "admin", "password": "totally-wrong"}
    )
    assert r.status_code == 401
    body = r.json()
    assert body["error_code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_me_without_auth_returns_401_even_when_bypass_email_set(
    isolated_data_root, dev_bypass_env
):
    """Core bug fix: previously /auth/me with no auth would dev_bypass into
    admin, letting wrong-password 'logins' silently succeed downstream."""
    await bootstrap()
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error_code"] == "TOKEN_INVALID"


@pytest.mark.asyncio
async def test_me_with_dev_bypass_header_succeeds(isolated_data_root, dev_bypass_env):
    """Explicit opt-in still works for curl/dev tooling."""
    await bootstrap()
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/auth/me", headers={"X-Dev-Bypass": "1"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["email"] == "admin"
    assert body["auth_role"] == "super_admin"
    assert body["auth_source"] == "dev_bypass"


@pytest.mark.asyncio
async def test_me_with_bypass_header_zero_or_empty_does_not_bypass(
    isolated_data_root, dev_bypass_env
):
    """`X-Dev-Bypass: 0` / empty / `false` should NOT activate the bypass —
    only truthy values do."""
    await bootstrap()
    from app.main import app

    client = TestClient(app)
    for falsy in ("0", "", "false"):
        r = client.get("/api/v1/auth/me", headers={"X-Dev-Bypass": falsy})
        assert r.status_code == 401, f"falsy header value `{falsy}` should not bypass"


@pytest.mark.asyncio
async def test_me_with_jwt_works(isolated_data_root, dev_bypass_env):
    """A real password login + JWT still authenticates /auth/me regardless
    of dev_bypass settings."""
    from app.services import auth_svc

    await bootstrap()
    from app.main import app

    creds = await auth_svc.password_login("admin", "Test-Admin-Pw-2026!")
    token = creds["tokens"]["access_token"]
    client = TestClient(app)
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["auth_source"] == "password"


@pytest.mark.asyncio
async def test_login_with_correct_password_still_works(
    isolated_data_root, dev_bypass_env
):
    await bootstrap()
    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/auth/login", json={"email": "admin", "password": "Test-Admin-Pw-2026!"}
    )
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["user"]["email"] == "admin"
    assert body["tokens"]["access_token"]
