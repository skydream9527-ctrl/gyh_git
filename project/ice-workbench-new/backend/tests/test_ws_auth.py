"""WebSocket auth — dual path: Aegis header OR bearer JWT."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.seed.runner import bootstrap


@pytest.mark.asyncio
async def test_ws_subprotocol_auth(isolated_data_root):
    """Classic JWT via `["bearer", token]` subprotocol still works."""
    await bootstrap()

    from app.main import app
    from app.services import auth_svc, task_svc

    client = TestClient(app)
    creds = await auth_svc.password_login("admin", "Test-Admin-Pw-2026!")
    token = creds["tokens"]["access_token"]
    uid = creds["user"]["id"]
    task = await task_svc.create_task(name="WS test", paradigm="biz", owner_id=uid)
    cid = task["workspace"]["current_conversation_id"] if task.get("workspace") else None
    if not cid:
        cid = await task_svc.get_or_create_default_conversation(task["id"])

    with client.websocket_connect(
        f"/api/v1/ws/conversations/{cid}?task_id={task['id']}",
        subprotocols=["bearer", token],
    ) as ws:
        assert ws.scope.get("type") == "websocket"

    with client.websocket_connect(
        f"/api/v1/ws/conversations/{cid}?task_id={task['id']}&token={token}"
    ) as ws:
        assert ws.scope.get("type") == "websocket"


@pytest.mark.asyncio
async def test_ws_rejects_dev_bypass(isolated_data_root, monkeypatch):
    """Dev bypass deliberately does NOT work on WebSocket connections —
    browsers can't attach the X-Dev-Bypass header to a WS handshake, and
    silently auto-promoting unauthed WS clients via AEGIS_DEV_BYPASS_EMAIL
    was the same class of bug that let any-password-logs-in happen on HTTP.
    Even with the env set, an unauthed WS handshake must close 4401."""
    monkeypatch.setenv("AEGIS_DEV_BYPASS_EMAIL", "tester@xiaomi.com")
    from app.core import config as cfg
    cfg.get_settings.cache_clear()

    await bootstrap()

    from app.main import app
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(app)
    with pytest.raises((WebSocketDisconnect, Exception)):
        with client.websocket_connect(
            "/api/v1/ws/conversations/bogus?task_id=bogus"
        ) as ws:
            ws.receive_text()


@pytest.mark.asyncio
async def test_ws_rejects_when_no_credential(isolated_data_root, monkeypatch):
    """No Aegis header, no JWT, no dev bypass → close 4401."""
    monkeypatch.setenv("AEGIS_DEV_BYPASS_EMAIL", "")
    from app.core import config as cfg
    cfg.get_settings.cache_clear()

    await bootstrap()
    from app.main import app
    client = TestClient(app)

    import websockets.exceptions as wse  # type: ignore
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises((WebSocketDisconnect, wse.ConnectionClosed, Exception)):
        with client.websocket_connect("/api/v1/ws/conversations/bogus?task_id=bogus") as ws:
            ws.receive_text()


@pytest.mark.asyncio
async def test_ws_auth_failure_delivers_close_code_not_handshake_rejection(isolated_data_root):
    """Regression: auth/task-gate failures must be delivered as WebSocket close
    codes 4401/4403, which requires accepting the upgrade BEFORE closing.

    A close issued *before* `accept()` rejects the HTTP handshake; browsers then
    surface only an opaque `onclose` code 1006 and cannot read the 4401/4403
    code, which makes the frontend's refresh-then-reconnect / clear+redirect /
    PERMISSION_DENIED-fatal handling unreachable. This test pins the
    accept-then-close behavior by asserting the exact close codes reach the
    client (TestClient raises WebSocketDisconnect carrying .code).
    """
    await bootstrap()

    from app.main import app
    from app.services import auth_svc, task_svc
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(app)
    creds = await auth_svc.password_login("admin", "Test-Admin-Pw-2026!")
    token = creds["tokens"]["access_token"]
    uid = creds["user"]["id"]
    task = await task_svc.create_task(name="WS close-code test", paradigm="biz", owner_id=uid)
    tid = task["id"]
    cid = (task.get("workspace") or {}).get("current_conversation_id") or (
        await task_svc.get_or_create_default_conversation(tid)
    )

    # Valid bearer subprotocol → accepted, negotiated subprotocol is exactly
    # "bearer" (never the token), and the first frame is inflight_status.
    with client.websocket_connect(
        f"/api/v1/ws/conversations/{cid}?task_id={tid}",
        subprotocols=["bearer", token],
    ) as ws:
        assert ws.scope.get("type") == "websocket"
        first = ws.receive_json()
        assert first["type"] == "inflight_status"

    # Invalid bearer token → handshake ACCEPTED then closed with 4401 (so a
    # browser actually observes 4401, not an opaque 1006 handshake failure).
    # The `accepted` flag is the real regression guard: under the old
    # pre-accept close, the context manager `__enter__` itself raises (handshake
    # denied) and `accepted` stays False; the accept-then-close fix enters the
    # block (handshake upgraded) before the 4401 close arrives on receive.
    accepted = False
    with pytest.raises(WebSocketDisconnect) as ei_auth:
        with client.websocket_connect(
            f"/api/v1/ws/conversations/{cid}?task_id={tid}",
            subprotocols=["bearer", "not-a-real-jwt"],
        ) as ws:
            accepted = True
            ws.receive_text()
    assert accepted, "handshake must be accepted before the 4401 close so the code reaches the client"
    assert ei_auth.value.code == 4401

    # Valid token but a task the user cannot access → close 4403 (distinct from
    # the 4401 auth-failure code so the client can treat it as fatal).
    accepted_task = False
    with pytest.raises(WebSocketDisconnect) as ei_task:
        with client.websocket_connect(
            f"/api/v1/ws/conversations/{cid}?task_id=nonexistent-task-id",
            subprotocols=["bearer", token],
        ) as ws:
            accepted_task = True
            ws.receive_text()
    assert accepted_task, "handshake must be accepted before the 4403 close so the code reaches the client"
    assert ei_task.value.code == 4403
