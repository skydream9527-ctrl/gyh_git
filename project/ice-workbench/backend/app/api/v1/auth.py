"""Auth endpoints — dual mode.

Two independent ways to authenticate; either is sufficient:

1. **米盾 (Aegis)** — the proxy injects `X-Proxy-UserDetail` on every request.
   No app-level login flow needed; the browser's `_aegis_cas` cookie handles it.
2. **Password / Feishu OAuth** — classic JWT bearer issued by `/auth/login`
   or `/auth/feishu/oauth/callback`.

`GET /auth/me` works under either path. `POST /auth/logout` returns both a
client-cleared state and the 米盾 logout URL for frontends that want to fully
sign out when behind the proxy.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ...core.config import get_settings
from ...core.deps import client_ip as _client_ip, get_current_user
from ...core.errors import APIError, ErrorCode, ok
from ...core.security import decode_token  # noqa: F401  (kept for tests/back-compat)
from ...schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from ...services import auth_svc, feishu, rate_limit_svc, sysconfig_svc

router = APIRouter()


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    """Password login — issues a JWT. Still available alongside Aegis.

    Per-email and per-IP rate limits are checked before bcrypt to keep the
    cost of a brute-force attempt low. Both clear on a successful login.
    """
    email = (body.email or "").strip()
    ip = _client_ip(request)

    for scope, ident, cfg in (
        ("login_email", email, rate_limit_svc.LOGIN_LIMIT),
        ("login_ip", ip, rate_limit_svc.LOGIN_IP_LIMIT),
    ):
        wait = rate_limit_svc.check(scope, ident, cfg)
        if wait:
            raise APIError(
                429,
                ErrorCode.LOGIN_RATE_LIMITED,
                f"登录尝试过多，请 {int(wait) + 1} 秒后再试",
            )

    try:
        result = await auth_svc.password_login(email, body.password)
    except APIError as e:
        if e.error_code == ErrorCode.INVALID_CREDENTIALS:
            rate_limit_svc.record_failure("login_email", email, rate_limit_svc.LOGIN_LIMIT)
            rate_limit_svc.record_failure("login_ip", ip, rate_limit_svc.LOGIN_IP_LIMIT)
        raise
    rate_limit_svc.clear("login_email", email)
    rate_limit_svc.clear("login_ip", ip)
    return ok(result)


@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    """Open self-service account creation → pending admin approval.

    Gated by sysconfig toggle `enable_open_register` (default off). On success
    returns `{status: "pending", user, message}` — the SPA should show a
    "submitted, waiting for approval" screen. Login only works after an admin
    flips the account status to `active` via /admin/users/{id}/review.

    Rate limited per-IP (3/h) and globally (50/h) to keep the admin-review
    queue from being filled by automated junk. Counted on EVERY attempt —
    a "register every 20 min" attacker is fine; an `xargs -P 100 curl` loop
    is locked out within seconds.
    """
    ip = _client_ip(request)
    for scope, ident, cfg in (
        ("register_ip", ip, rate_limit_svc.REGISTER_IP_LIMIT),
        ("register_global", "all", rate_limit_svc.REGISTER_GLOBAL_LIMIT),
    ):
        wait = rate_limit_svc.check(scope, ident, cfg)
        if wait:
            raise APIError(
                429, ErrorCode.LOGIN_RATE_LIMITED,
                f"注册请求过于频繁，请 {int(wait) + 1} 秒后再试",
            )
    # Each attempt counts (success or failure) — every register hits the
    # admin-review queue, so we must throttle even successful posts.
    rate_limit_svc.record_failure("register_ip", ip, rate_limit_svc.REGISTER_IP_LIMIT)
    rate_limit_svc.record_failure("register_global", "all", rate_limit_svc.REGISTER_GLOBAL_LIMIT)
    result = await auth_svc.register(
        body.email, body.name, body.password, xiaomi_email=body.xiaomi_email or ""
    )
    return ok(result)


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    """Single-use refresh-token rotation. Each refresh consumes the presented
    token's jti and issues a fresh pair. Replaying an already-consumed token
    revokes ALL the user's refresh tokens (assumed compromise)."""
    return ok(await auth_svc.rotate_refresh_token(body.refresh_token))


@router.post("/logout")
async def logout(request: Request):
    """Return the Aegis logout URL (if behind the proxy) so the frontend can
    additionally clear `_aegis_cas`. Bearer JWTs are stateless — frontend
    simply drops the token.
    """
    host = request.headers.get("host", "")
    scheme = request.headers.get("x-forwarded-proto", "https")
    aegis_logout = f"{scheme}://{host}/_aegis/cas/logout" if host else None
    return ok({"logged_out": True, "aegis_logout_url": aegis_logout})


@router.post("/feishu/oauth/start")
async def feishu_start():
    url, state = feishu.build_authorize_url()
    return ok({"auth_url": url, "state": state})


@router.post("/feishu/oauth/callback")
async def feishu_callback(payload: dict):
    code = payload.get("code")
    state = payload.get("state")
    if not code:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "missing code")
    # Backend-side state verification — rejects forged/expired states even
    # if the frontend's sessionStorage check were bypassed (closed tab,
    # phishing redirect, etc.). See feishu.verify_state for details.
    feishu.verify_state(state)
    info = await feishu.exchange_code(code)
    result = await auth_svc.feishu_login(
        feishu_user_id=info["feishu_user_id"],
        email=info.get("email"),
        name=info.get("name"),
        avatar_url=info.get("avatar_url"),
    )
    return ok(result)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return ok(_to_public(user))


@router.get("/methods")
async def methods():
    """Lets the frontend decide which login UIs to show.

    Under 米盾, the browser is already authenticated before it ever hits
    this API — so a frontend can call `/auth/me` directly and skip login UI
    entirely when `aegis_available` is true.
    """
    s = get_settings()
    return ok({
        "aegis_enabled": s.AEGIS_ENABLED and bool(s.aegis_public_keys),
        "password_enabled": True,
        "feishu_oauth_enabled": bool(s.FEISHU_APP_ID and s.FEISHU_APP_SECRET),
        "open_register_enabled": bool(
            sysconfig_svc.get_toggles().get("enable_open_register", False)
        ),
    })


def _to_public(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "display_name": user.get("display_name"),
        "department_name": user.get("department_name"),
        "auth_role": user.get("auth_role", "user"),
        "avatar_url": user.get("avatar_url"),
        "auth_source": user.get("_auth_source"),
    }
