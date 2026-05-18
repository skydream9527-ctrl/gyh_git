"""Auth service. Source of truth = users/{uid}/profile.json; index in cache."""
from __future__ import annotations

from datetime import datetime, timezone

from ..core.config import get_settings
from ..core.errors import APIError, ErrorCode
from ..core.security import create_access_token, create_refresh_token, verify_password
from ..core.storage import file_transaction, get_index_db, get_paths, read_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def load_user_by_id(user_id: str) -> dict | None:
    p = get_paths().user_profile(user_id)
    return read_json(p) or None


async def load_user_by_email(email: str) -> dict | None:
    db = get_index_db()
    row = await db.fetchone(
        "SELECT id FROM users_index WHERE email = ? COLLATE NOCASE LIMIT 1", [email]
    )
    if not row:
        return None
    return await load_user_by_id(row["id"])


async def ensure_user_for_email(
    email: str,
    *,
    name: str | None = None,
    auth_role: str = "user",
) -> dict:
    """Resolve an email to the canonical (uuid-keyed) user profile.

    Used by Aegis / dev_bypass auth paths so that the same person who shows up
    via the proxy gets the SAME ``user.id`` as if they had registered through
    the password flow. Without this, tasks owned by ``id="email"`` and
    ``id="<uuid>"`` get split across two directories and the user appears to
    "lose" their data when the auth path changes.

    If the user does not yet exist, create them as ``status="active"`` with
    the supplied role so first-time visits via Aegis don't get a 401 loop.
    """
    import uuid as _uuid

    email_clean = (email or "").strip().lower()
    if not email_clean:
        raise APIError(401, ErrorCode.TOKEN_INVALID, "missing email for user resolution")

    existing = await load_user_by_email(email_clean)
    if existing:
        # Don't downgrade an existing super_admin / admin role just because
        # the auth path passed a generic "user".
        return existing

    paths = get_paths()
    db = get_index_db()
    uid = _uuid.uuid4().hex
    created_at = _now()
    profile = {
        "id": uid,
        "email": email_clean,
        "name": (name or email_clean.split("@")[0])[:60] or email_clean,
        "auth_role": auth_role,
        "status": "active",
        "password_hash": None,
        "feishu_user_id": None,
        "team": None,
        "title": None,
        "avatar_url": None,
        "created_at": created_at,
        "last_login_at": created_at,
        "self_registered": False,
    }
    with file_transaction([paths.user_profile(uid), paths.user_tasks_index(uid)]) as tx:
        tx.makedirs(
            [
                paths.user_dir(uid) / "tasks",
                paths.user_dir(uid) / "notifications",
                paths.user_dir(uid) / "audit",
            ]
        )
        tx.write_json(paths.user_profile(uid), profile)
        tx.write_json(paths.user_tasks_index(uid), [])
        tx.write_json(paths.user_settings(uid), {"theme": "dark"})
    await db.upsert(
        "users_index",
        {
            "id": uid,
            "email": profile["email"],
            "name": profile["name"],
            "auth_role": auth_role,
            "status": "active",
            "feishu_user_id": None,
            "last_login_at": created_at,
            "password_hash": None,
            "created_at": created_at,
        },
    )
    return profile


async def register(email: str, name: str, password: str) -> dict:
    """Self-service registration — now goes through admin approval.

    Gated by sysconfig toggle `enable_open_register`. Validates input, checks
    email uniqueness, stores a bcrypt-hashed password, and creates the user
    with `status="pending"`. **No tokens are issued** — the user must wait for
    an admin to approve via /admin/users before they can log in.

    Returns the public user summary so the frontend can show "submitted, wait
    for approval" rather than redirecting to dashboard.
    """
    from . import sysconfig_svc

    if not sysconfig_svc.get_toggles().get("enable_open_register", False):
        raise APIError(
            403,
            ErrorCode.OPEN_REGISTER_DISABLED,
            "账号注册已关闭，请联系管理员开通",
        )

    email_clean = (email or "").strip()
    name_clean = (name or "").strip()
    if not email_clean or not name_clean:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "账号和姓名不能为空")
    if len(email_clean) > 120 or len(name_clean) > 60:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "账号或姓名过长")
    if any(c.isspace() for c in email_clean):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "账号不能包含空格")
    if password is None or len(password) < 6:
        raise APIError(400, ErrorCode.WEAK_PASSWORD, "密码至少 6 位")
    if len(password) > 128:
        raise APIError(400, ErrorCode.WEAK_PASSWORD, "密码最长 128 位")

    existing = await load_user_by_email(email_clean)
    if existing:
        # Surface pending/rejected history so the frontend can show a helpful
        # message instead of "email taken" when the user is re-submitting.
        status_now = existing.get("status")
        if status_now == "pending":
            raise APIError(
                409,
                ErrorCode.ACCOUNT_PENDING_APPROVAL,
                "该账号已提交申请，正在等待管理员审批",
            )
        if status_now == "rejected":
            raise APIError(
                409,
                ErrorCode.ACCOUNT_REJECTED,
                "该账号申请已被驳回；如需重新申请请联系管理员",
            )
        raise APIError(409, ErrorCode.EMAIL_ALREADY_EXISTS, "该账号已被注册")

    import uuid

    from ..core.security import hash_password
    from ..core.storage import file_transaction, get_paths as _paths

    paths = _paths()
    db = get_index_db()
    uid = uuid.uuid4().hex
    created_at = _now()
    profile = {
        "id": uid,
        "email": email_clean,
        "name": name_clean,
        "auth_role": "user",
        "status": "pending",
        "password_hash": hash_password(password),
        "feishu_user_id": None,
        "team": None,
        "title": None,
        "avatar_url": None,
        "created_at": created_at,
        "last_login_at": None,
        "self_registered": True,
        "registration_submitted_at": created_at,
        "reviewed_by": None,
        "reviewed_at": None,
        "reject_reason": None,
    }
    with file_transaction([paths.user_profile(uid), paths.user_tasks_index(uid)]) as tx:
        tx.makedirs(
            [
                paths.user_dir(uid) / "tasks",
                paths.user_dir(uid) / "notifications",
                paths.user_dir(uid) / "audit",
            ]
        )
        tx.write_json(paths.user_profile(uid), profile)
        tx.write_json(paths.user_tasks_index(uid), [])
        tx.write_json(paths.user_settings(uid), {"theme": "dark"})
    await db.upsert(
        "users_index",
        {
            "id": uid,
            "email": profile["email"],
            "name": profile["name"],
            "auth_role": "user",
            "status": "pending",
            "feishu_user_id": None,
            "last_login_at": None,
            "password_hash": profile["password_hash"],
            "created_at": profile["created_at"],
        },
    )
    return {
        "status": "pending",
        "user": _to_public(profile),
        "message": "账号申请已提交，管理员审批通过后即可登录",
    }


async def password_login(email: str, password: str) -> dict:
    """Password login. super_admin gate per D85.

    super_admin must use Feishu IF feishu is configured AND the user is already bound.
    Bootstrap escape: when FEISHU not configured globally, password login is allowed
    so the platform can be operated without external IdP.
    """
    s = get_settings()
    user = await load_user_by_email(email)
    if not user:
        raise APIError(401, ErrorCode.INVALID_CREDENTIALS, "账号或密码错误")
    # Verify password BEFORE returning status-specific errors so a random
    # attacker can't enumerate pending/rejected accounts.
    if not verify_password(password, user.get("password_hash")):
        raise APIError(401, ErrorCode.INVALID_CREDENTIALS, "账号或密码错误")
    status_now = user.get("status") or "active"
    if status_now == "pending":
        raise APIError(
            403,
            ErrorCode.ACCOUNT_PENDING_APPROVAL,
            "账号正在等待管理员审批，审批通过后方可登录",
        )
    if status_now == "rejected":
        raise APIError(
            403,
            ErrorCode.ACCOUNT_REJECTED,
            "账号申请已被驳回" + (f"：{user.get('reject_reason')}" if user.get("reject_reason") else ""),
        )
    if status_now == "disabled":
        raise APIError(403, ErrorCode.ACCOUNT_DISABLED, "账号已被禁用")
    if user["auth_role"] == "super_admin" and s.feishu_enabled and user.get("feishu_user_id"):
        raise APIError(403, ErrorCode.SUPER_ADMIN_REQUIRES_FEISHU, "super_admin 必须使用飞书登录")
    return await _issue_tokens_and_touch(user)


async def feishu_login(
    feishu_user_id: str,
    email: str | None,
    name: str | None = None,
    avatar_url: str | None = None,
) -> dict:
    """Used by /auth/feishu/oauth/callback after Feishu API verifies the code.

    Behavior:
    - existing user (matched by email or feishu_user_id) → auto-bind on first
      login + issue tokens
    - no existing user:
        toggle `enable_feishu_auto_register`=true (default) → auto-provision
            a new `auth_role=user` account, bind feishu, issue tokens
        toggle false → 403 FEISHU_ACCOUNT_NOT_WHITELISTED
    """
    user = None
    if email:
        user = await load_user_by_email(email)
    if not user:
        # try lookup by feishu_user_id (in case email scope wasn't granted)
        from ..core.storage import get_index_db as _idb

        row = await _idb().fetchone(
            "SELECT id FROM users_index WHERE feishu_user_id = ? LIMIT 1",
            [feishu_user_id],
        )
        if row:
            user = await load_user_by_id(row["id"])

    if not user:
        from . import sysconfig_svc

        if not sysconfig_svc.get_toggles().get("enable_feishu_auto_register", True):
            raise APIError(
                403,
                ErrorCode.FEISHU_ACCOUNT_NOT_WHITELISTED,
                "飞书账号未在白名单内，且自动注册已关闭。请联系管理员开启 enable_feishu_auto_register，或在 /admin/users 手动添加。",
            )
        return await _auto_provision_from_feishu(
            feishu_user_id=feishu_user_id, email=email, name=name, avatar_url=avatar_url
        )

    if user.get("feishu_user_id") and user["feishu_user_id"] != feishu_user_id:
        raise APIError(409, ErrorCode.FEISHU_BINDING_CONFLICT, "飞书账号已绑定至其他用户")
    user["feishu_user_id"] = feishu_user_id
    user["feishu_bound_at"] = _now()
    if name and not user.get("name"):
        user["name"] = name
    if avatar_url and not user.get("avatar_url"):
        user["avatar_url"] = avatar_url
    return await _issue_tokens_and_touch(user)


async def _auto_provision_from_feishu(
    *,
    feishu_user_id: str,
    email: str | None,
    name: str | None,
    avatar_url: str | None,
) -> dict:
    """Create a fresh `auth_role=user` account bound to the Feishu identity."""
    import uuid

    from ..core.security import hash_password
    from ..core.storage import get_index_db, get_paths

    paths = get_paths()
    db = get_index_db()
    uid = uuid.uuid4().hex
    # email is the public username; if scope didn't include it, synthesize a
    # feishu-suffixed handle so the system invariant (unique email) holds.
    fallback_email = email or f"feishu-{feishu_user_id[:12]}@auto.local"
    profile = {
        "id": uid,
        "email": fallback_email,
        "name": name or fallback_email.split("@")[0],
        "auth_role": "user",
        "status": "active",
        "password_hash": hash_password(uuid.uuid4().hex),  # random; cannot password-login
        "feishu_user_id": feishu_user_id,
        "feishu_bound_at": _now(),
        "team": None,
        "title": None,
        "avatar_url": avatar_url,
        "created_at": _now(),
        "last_login_at": None,
        "auto_provisioned": True,
    }
    with file_transaction([paths.user_profile(uid), paths.user_tasks_index(uid)]) as tx:
        tx.makedirs(
            [
                paths.user_dir(uid) / "tasks",
                paths.user_dir(uid) / "notifications",
                paths.user_dir(uid) / "audit",
            ]
        )
        tx.write_json(paths.user_profile(uid), profile)
        tx.write_json(paths.user_tasks_index(uid), [])
        tx.write_json(paths.user_settings(uid), {"theme": "dark"})
    await db.upsert(
        "users_index",
        {
            "id": uid,
            "email": profile["email"],
            "name": profile["name"],
            "auth_role": "user",
            "status": "active",
            "feishu_user_id": feishu_user_id,
            "last_login_at": None,
            "password_hash": profile["password_hash"],
            "created_at": profile["created_at"],
        },
    )
    return await _issue_tokens_and_touch(profile)


async def _issue_tokens_and_touch(user: dict) -> dict:
    s = get_settings()
    user["last_login_at"] = _now()
    paths = get_paths()
    with file_transaction([paths.user_profile(user["id"])]) as tx:
        tx.write_json(paths.user_profile(user["id"]), user)
    db = get_index_db()
    await db.execute(
        "UPDATE users_index SET last_login_at = ?, feishu_user_id = COALESCE(?, feishu_user_id) WHERE id = ?",
        [user["last_login_at"], user.get("feishu_user_id"), user["id"]],
    )
    return {
        "user": _to_public(user),
        "tokens": {
            "access_token": create_access_token(user["id"], user["auth_role"]),
            "refresh_token": create_refresh_token(user["id"]),
            "token_type": "bearer",
            "expires_in": s.ICE_ACCESS_TOKEN_TTL_MIN * 60,
        },
    }


def _to_public(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "auth_role": user.get("auth_role", "user"),
        "avatar_url": user.get("avatar_url"),
        "feishu_bound": bool(user.get("feishu_user_id")),
        "team": user.get("team"),
        "title": user.get("title"),
    }
