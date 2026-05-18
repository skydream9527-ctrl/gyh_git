"""FastAPI dependencies — dual auth: 米盾 (Aegis) OR password JWT.

Per-request resolution order:
  1. `X-Proxy-UserDetail` header present → RSA-verify through Aegis. If the
     header exists but verifies bad, we 401 immediately (don't fall through —
     a tampered header shouldn't be silently ignored).
  2. `Authorization: Bearer <jwt>` header present → decode JWT and load user
     from the local users index.
  3. Dev escape hatch: `AEGIS_DEV_BYPASS_EMAIL` set AND the request opts in
     by sending `X-Dev-Bypass: 1` → synthesize that user. Without the
     header the bypass is INERT — that prevents the SPA's bootstrapMe()
     from silently auto-logging anyone in as the bypass account, which would
     defeat the password gate on /auth/login.
  4. Neither → 401.

Either path is optional; admins choose per deployment (米盾-only prod, mixed,
or standalone dev/test). The handler never sees which path authenticated —
both paths produce the same user dict shape.
"""
from __future__ import annotations

import enum
import logging

from fastapi import Depends, Header, Query, WebSocket

from ..services.auth_svc import ensure_user_for_email, load_user_by_id
from .aegis import AegisUser, AegisVerifyError, verify
from .config import get_settings
from .errors import APIError, ErrorCode
from .security import decode_token
from .storage import get_paths, read_json

log = logging.getLogger(__name__)

_AEGIS_HEADER = "X-Proxy-UserDetail"


async def _user_from_aegis(info: AegisUser) -> dict:
    """Build the handler-visible user dict from an Aegis payload.

    Resolves the email to the canonical user record in the local users
    registry — `user["id"]` is therefore the same uuid that password-login
    issues, NOT the email. This guarantees task ownership and per-user data
    directories are stable regardless of which auth path the user enters
    through. First-time Aegis visitors get auto-provisioned.
    """
    settings = get_settings()
    email = (info.email or info.user or "").lower()
    if not email:
        raise APIError(401, ErrorCode.TOKEN_INVALID, "aegis payload missing email")
    role = "super_admin" if email in settings.aegis_admin_emails else "user"
    profile = await ensure_user_for_email(
        email,
        name=info.name or info.display_name or email.split("@")[0],
        auth_role=role,
    )
    out = dict(profile)
    out.update(
        {
            "auth_role": profile.get("auth_role", role),
            "display_name": info.display_name,
            "department_name": info.department_name,
            "avatar_url": info.avatar or profile.get("avatar_url"),
            "mi_id": info.mi_id,
            "uid": info.uid,
            "user": info.user,
            "type": info.type,
            "_auth_source": "aegis",
        }
    )
    return out


async def _dev_bypass_user(email: str) -> dict:
    settings = get_settings()
    email = email.lower()
    role = "super_admin" if email in settings.aegis_admin_emails else "user"
    profile = await ensure_user_for_email(email, auth_role=role)
    out = dict(profile)
    out.update(
        {
            "auth_role": profile.get("auth_role", role),
            "display_name": profile.get("name") or email.split("@")[0],
            "department_name": None,
            "mi_id": None,
            "uid": None,
            "user": email.split("@")[0],
            "type": "employee",
            "_auth_source": "dev_bypass",
        }
    )
    return out


async def _try_aegis(header_value: str | None) -> dict | None:
    """None = header absent. dict = verified user. Raises APIError on tampered header."""
    settings = get_settings()
    if not settings.AEGIS_ENABLED:
        return None
    if not header_value:
        return None
    if not settings.aegis_public_keys:
        # Header present but we have no key configured — treat as absent rather
        # than 401, so mixed deployments (dev laptop behind staging Aegis but
        # without the prod key) can still log in via password.
        log.warning("aegis: X-Proxy-UserDetail seen but AEGIS_PUBLIC_KEY unset — ignoring")
        return None
    try:
        info = verify(header_value, settings.aegis_public_keys)
    except AegisVerifyError as e:
        log.warning("aegis verify failed: %s", e)
        raise APIError(401, ErrorCode.TOKEN_INVALID, f"aegis verify failed: {e}") from e
    return await _user_from_aegis(info)


async def _try_bearer(authorization: str | None) -> dict | None:
    """None = header absent. dict = valid JWT + user found. Raises APIError on bad JWT."""
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    payload = decode_token(token, expect="access")  # raises APIError on bad token
    user = await load_user_by_id(payload["sub"])
    if not user:
        raise APIError(401, ErrorCode.TOKEN_INVALID, "user not found")
    if user.get("status") == "disabled":
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "account disabled")
    user["_auth_source"] = "password"
    return user


async def _resolve_user(
    aegis_header: str | None,
    authorization: str | None,
    *,
    dev_bypass_opt_in: bool = False,
) -> dict:
    settings = get_settings()
    u = await _try_aegis(aegis_header)
    if u:
        return u
    u = await _try_bearer(authorization)
    if u:
        return u
    # Dev bypass: only fire when the request EXPLICITLY opts in via the
    # X-Dev-Bypass header. Without that, bootstrapMe() / /auth/me without a
    # valid Bearer must 401 — otherwise wrong-password "logins" silently
    # succeed because the frontend's follow-up /auth/me hits dev_bypass.
    if settings.AEGIS_DEV_BYPASS_EMAIL and dev_bypass_opt_in:
        log.debug("aegis: dev bypass active as %s", settings.AEGIS_DEV_BYPASS_EMAIL)
        return await _dev_bypass_user(settings.AEGIS_DEV_BYPASS_EMAIL)
    raise APIError(
        401,
        ErrorCode.TOKEN_INVALID,
        "missing credentials: neither X-Proxy-UserDetail nor Bearer token present",
    )


# Public helper for non-Depends callers (WebSocket handler).
# Browsers can't attach custom headers to a WS handshake, so dev_bypass is
# never available on WS. WS clients must always present a real Bearer token
# (or come in via the Aegis proxy).
async def resolve_user(aegis_header: str | None, authorization: str | None) -> dict:
    return await _resolve_user(aegis_header, authorization, dev_bypass_opt_in=False)


async def get_current_user(
    x_proxy_user_detail: str | None = Header(default=None, alias=_AEGIS_HEADER),
    authorization: str | None = Header(default=None),
    x_dev_bypass: str | None = Header(default=None, alias="X-Dev-Bypass"),
) -> dict:
    return await _resolve_user(
        x_proxy_user_detail,
        authorization,
        dev_bypass_opt_in=bool(x_dev_bypass and x_dev_bypass.strip() not in ("", "0", "false")),
    )


async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> dict:
    """WebSocket: try Aegis header first; then bearer (from subprotocol or `?token=`)."""
    aegis = websocket.headers.get(_AEGIS_HEADER)
    # Bearer can arrive via subprotocol `["bearer", "<jwt>"]` or legacy ?token=
    offered = (websocket.headers.get("sec-websocket-protocol") or "").split(",")
    offered = [p.strip() for p in offered if p.strip()]
    sub_token: str | None = None
    if "bearer" in offered:
        for p in offered:
            if p != "bearer":
                sub_token = p
                break
    bearer = sub_token or token
    auth_header = f"Bearer {bearer}" if bearer else None
    return await _resolve_user(aegis, auth_header)


def require_role(*roles: str):
    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user["auth_role"] not in roles:
            raise APIError(403, ErrorCode.PERMISSION_DENIED, "role required: " + "/".join(roles))
        return user

    return _checker


require_admin = require_role("admin", "super_admin")
require_super_admin = require_role("super_admin")


class TaskRole(str, enum.Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    ADMIN = "admin"  # cross-cutting: admin gets owner-equivalent access


def derive_task_role(
    task_meta: dict, collaborators: list[dict], *, user_id: str, is_admin: bool
) -> TaskRole | None:
    if is_admin:
        return TaskRole.ADMIN
    if task_meta.get("owner_id") == user_id:
        return TaskRole.OWNER
    for c in collaborators:
        if c.get("user_id") == user_id and c.get("status") == "active":
            role = c.get("role")
            if role == "owner":
                return TaskRole.OWNER
            if role == "editor":
                return TaskRole.EDITOR
    if (
        task_meta.get("visibility") == "public"
        and task_meta.get("publish_status") == "published"
    ):
        return TaskRole.VIEWER
    return None


async def get_task_role(task_id: str, user: dict = Depends(get_current_user)) -> TaskRole:
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    collabs = read_json(paths.task_collaborators(task_id), default=[]) or []
    role = derive_task_role(meta, collabs, user_id=user["id"], is_admin=bool(user.get("is_admin")))
    if role is None:
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "无权访问该任务")
    return role


def require_task_role(*allowed: TaskRole):
    """Handler-side gate factory. Usage: Depends(require_task_role(TaskRole.EDITOR, TaskRole.OWNER, TaskRole.ADMIN))."""

    async def checker(role: TaskRole = Depends(get_task_role)) -> TaskRole:
        if role not in allowed:
            raise APIError(403, ErrorCode.PERMISSION_DENIED, "当前身份无此权限")
        return role

    return checker
