"""Auth service. Source of truth = users/{uid}/profile.json; index in cache."""
from __future__ import annotations

from datetime import datetime, timezone

from ...core.config import get_settings
from ...core.errors import APIError, ErrorCode
from ...core.security import create_access_token, create_refresh_token, new_jti, verify_password
from ...core.storage import file_transaction, get_index_db, get_paths, read_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


import re as _re

# Common-password rejection list. Tiny on purpose — bcrypt + rate-limit
# already raise the cost; this just catches the most embarrassing choices.
# All entries normalized lower-case + alphanumeric-only (digits stripped of
# l33t-speak `@→a / 0→o / 1→i / 3→e / $→s / !→i`) so `Password123!` /
# `P@ssw0rd1!` / `Adm1n@12345` collapse to the same canonical form.
_BANNED_BASES = {
    "password", "passw0rd", "password1", "password123",
    "admin", "admin123", "admin1234", "administrator",
    "qwerty", "qwerty123", "qwertyuiop",
    "12345678", "123456789", "1234567890", "11111111", "00000000",
    "letmein", "welcome", "iloveyou", "abc12345", "testtest",
    "test123", "test1234",
    "iceworkbench", "ice123",
}

# Disposable / throwaway email domains. Reject these at register time so an
# attacker can't spin up a `mailinator.com` mailbox per attempt to walk the
# admin-approval queue. Sourced from the public disposable-email-domain
# lists (mailinator/yopmail/etc.). Keep it short — additions go through
# admin so an over-aggressive list can be tuned in one PR.
_DISPOSABLE_EMAIL_DOMAINS = frozenset({
    "10minutemail.com", "20minutemail.com", "30minutemail.com",
    "tempmail.com", "temp-mail.org", "throwaway.email", "throwawaymail.com",
    "guerrillamail.com", "guerrillamailblock.com", "grr.la", "sharklasers.com",
    "mailinator.com", "mailinator.net", "yopmail.com", "yopmail.net",
    "fakeinbox.com", "dispostable.com", "trashmail.com", "trashmail.de",
    "maildrop.cc", "harakirimail.com", "getnada.com", "nada.email",
    "spambog.com", "spamgourmet.com", "anonbox.net", "mintemail.com",
    "moakt.com", "mvrht.com", "mt2015.com", "spam4.me",
})

# RFC 5322-ish but strict enough to reject obvious junk. Sufficient for a
# pre-registration sniff test; the canonical check is "can we deliver to
# this address" but our flow is admin-approval not email-verification, so
# we lean on shape + blocklist instead.
_EMAIL_REGEX = _re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

# Name allowlist: CJK letters, ASCII letters/digits, space, dot, hyphen,
# underscore, bullet `·`. Catches `<script>` injections and zero-width / RTL
# override sneakery without restricting normal Chinese / English / mixed
# names like `张明远` / `John Doe` / `Wang·Bo` / `mike_admin`.
_NAME_REGEX = _re.compile(r"^[一-龥A-Za-z0-9 .\-_·]+$")


def _validate_xiaomi_email(value: str) -> str:
    """Validate the Xiaomi-office email used for Feishu sharing.

    Returns the cleaned (lowercased + stripped) value. Raises APIError on bad
    format. We accept any @xiaomi.com address — internal tooling uses several
    sub-domains (e.g. xiaomi.com / mi.com / 米家 alias), but for now restrict
    to the canonical xiaomi.com so feishu perm add lands on the right account.
    """
    cleaned = (value or "").strip().lower()
    if not cleaned:
        return ""
    if not _EMAIL_REGEX.match(cleaned):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "小米办公邮箱格式不正确")
    domain = cleaned.rsplit("@", 1)[-1]
    if domain not in ("xiaomi.com", "mi.com"):
        raise APIError(
            400,
            ErrorCode.VALIDATION_ERROR,
            "小米办公邮箱必须是 @xiaomi.com 或 @mi.com 域名",
        )
    return cleaned


def _validate_email_format(email: str) -> None:
    if not _EMAIL_REGEX.match(email):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "邮箱格式不正确")
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in _DISPOSABLE_EMAIL_DOMAINS:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "不允许使用临时 / 一次性邮箱注册")


def _validate_name_format(name: str) -> None:
    if not _NAME_REGEX.match(name):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "姓名包含非法字符")
    # Reject control / zero-width / direction-override codepoints. The
    # allowlist regex above already rejects ASCII control chars but not
    # all of unicode's invisible bag (U+200B BOM, U+202E RTL override, etc).
    for ch in name:
        cp = ord(ch)
        if cp < 0x20 or cp == 0x7F:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "姓名包含控制字符")
        if 0x200B <= cp <= 0x200F or 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "姓名包含不可见 / 方向控制字符")

# Map common l33t-speak substitutions to letters so the canonical form
# captures `Password!23` and `P@ssw0rd1!` together. Conservative — only
# the substitutions that genuinely flatten weak choices.
_LEET_MAP = str.maketrans({"@": "a", "0": "o", "1": "i", "3": "e", "$": "s", "!": "i", "5": "s", "7": "t"})


def _canonicalize_password(s: str) -> str:
    return s.lower().translate(_LEET_MAP)


def _has_substring_overlap(haystack: str, needle: str, *, min_len: int = 4) -> bool:
    """True if `needle` (or a window of it) of length >= min_len is contained
    in `haystack`. Used to catch passwords like `john.smith2026!` for user
    `john.smith@example.com`."""
    if not needle or len(needle) < min_len:
        return False
    h = haystack.lower()
    n = needle.lower()
    if len(n) <= min_len:
        return n in h
    for i in range(len(n) - min_len + 1):
        if n[i : i + min_len] in h:
            return True
    return False


def _validate_password_strength(
    password: str | None,
    *,
    email: str | None = None,
    name: str | None = None,
) -> None:
    """Reject weak/short/common passwords + ones derived from user identity.

    Rules:
    1. Length 10..128.
    2. >= 3 of {lower, upper, digit, symbol}.
    3. Canonical form (lower-case + l33t-speak collapsed) not in the banned list.
    4. Does not contain a >=4-char substring of email-local-part or name.
    Rule of thumb consistent with NIST SP 800-63B "memorized secret" guidance
    for a non-MFA system: length + dictionary + similarity, not arbitrary
    rotation or extreme complexity rules.
    """
    if password is None or len(password) < 10:
        raise APIError(400, ErrorCode.WEAK_PASSWORD, "密码至少 10 位")
    if len(password) > 128:
        raise APIError(400, ErrorCode.WEAK_PASSWORD, "密码最长 128 位")

    classes = sum([
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ])
    if classes < 3:
        raise APIError(
            400, ErrorCode.WEAK_PASSWORD,
            "密码需包含大小写字母 / 数字 / 符号中的任意 3 类",
        )

    # Reject runs of identical chars (`aaaa`, `1111`, `!!!!`) and trivial
    # ascending sequences (`1234`, `abcd`). Length-4 threshold keeps `aa`
    # in `Aaa-Bbb-2026` legal but blocks `aaaa-2026`.
    if _re.search(r"(.)\1{3,}", password):
        raise APIError(
            400, ErrorCode.WEAK_PASSWORD,
            "密码不能包含 4 个以上连续重复字符",
        )
    lowered = password.lower()
    for i in range(len(lowered) - 3):
        a, b, c, d = lowered[i], lowered[i + 1], lowered[i + 2], lowered[i + 3]
        if all(ord(x) - ord(y) == -1 for x, y in zip((a, b, c), (b, c, d))):
            raise APIError(
                400, ErrorCode.WEAK_PASSWORD,
                "密码不能包含 4 个以上连续递增字符（如 1234 / abcd）",
            )

    canonical = _canonicalize_password(password)
    # Strip non-alphanumerics from canonical form so `Password!23` (which
    # canonicalizes to `passwordi2e`) collapses against `password123` after
    # filtering — both share `passwordi`. Then check both raw and stripped.
    canonical_alpha = "".join(c for c in canonical if c.isalnum())
    for banned in _BANNED_BASES:
        if banned in canonical_alpha:
            raise APIError(
                400, ErrorCode.WEAK_PASSWORD,
                "密码包含常见弱口令片段，请重新设置",
            )

    # Similarity check: password must not embed parts of the user's identity.
    local_part = (email or "").split("@", 1)[0]
    if _has_substring_overlap(canonical, local_part):
        raise APIError(
            400, ErrorCode.WEAK_PASSWORD,
            "密码不能包含账号片段",
        )
    if name and _has_substring_overlap(canonical, name):
        raise APIError(
            400, ErrorCode.WEAK_PASSWORD,
            "密码不能包含姓名片段",
        )


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
        # If the auth path passed a real @xiaomi.com address, treat that as
        # the office email by default — Aegis / 米盾 already does this. User
        # can override later in AccountModal.
        "xiaomi_email": email_clean if email_clean.endswith("@xiaomi.com") or email_clean.endswith("@mi.com") else None,
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


async def register(email: str, name: str, password: str, xiaomi_email: str = "") -> dict:
    """Self-service registration — now goes through admin approval.

    Gated by sysconfig toggle `enable_open_register`. Validates input, checks
    email uniqueness, stores a bcrypt-hashed password, and creates the user
    with `status="pending"`. **No tokens are issued** — the user must wait for
    an admin to approve via /admin/users before they can log in.

    Returns the public user summary so the frontend can show "submitted, wait
    for approval" rather than redirecting to dashboard.
    """
    from app.services.admin import sysconfig_svc

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
    # 历史允许 `admin` / `zhangmingyuan` 这种纯用户名作为 "email" 字段（米盾
    # / 飞书都把工号当邮箱前缀）。所以只在带 `@` 时才走严格邮箱校验，否则
    # 走轻量字符校验保住 LDAP-style 用户名的兼容。
    if "@" in email_clean:
        _validate_email_format(email_clean.lower())
    elif any(c.isspace() for c in email_clean):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "账号不能包含空格")
    elif not _re.match(r"^[A-Za-z0-9._\-]+$", email_clean):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "账号包含非法字符")
    _validate_name_format(name_clean)
    _validate_password_strength(password, email=email_clean, name=name_clean)
    xiaomi_email_clean = _validate_xiaomi_email(xiaomi_email)

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

    from ...core.security import hash_password
    from ...core.storage import file_transaction
    from ...core.storage import get_paths as _paths

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
        # 用于 feishu_publish 自动加权限的小米办公邮箱（可选，但缺了就无法
        # 把工具创建的飞书文档分享给本人；建议在注册时就采集）
        "xiaomi_email": xiaomi_email_clean or None,
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


# Per-account lockout knobs. Process-local rate_limit_svc throttles by
# (email, IP) but counters are evicted across worker restarts and don't
# survive an attacker rotating IPs against one user. The on-disk lockout
# below is durable + IP-agnostic — 5 failed attempts in any window lock
# the account for 15 min, and a successful login clears the counter.
_LOGIN_LOCKOUT_THRESHOLD = 5
_LOGIN_LOCKOUT_DURATION_SEC = 15 * 60


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _persist_login_failure(user: dict) -> None:
    """Bump the failure counter; lock the account when the threshold trips.
    Writes through file_transaction so concurrent workers serialize on the
    same per-user lock.
    """
    paths = get_paths()
    with file_transaction([paths.user_profile(user["id"])]) as tx:
        current = tx.read_json(paths.user_profile(user["id"])) or user
        attempts = int(current.get("failed_login_attempts") or 0) + 1
        current["failed_login_attempts"] = attempts
        if attempts >= _LOGIN_LOCKOUT_THRESHOLD:
            current["locked_until"] = _now_epoch() + _LOGIN_LOCKOUT_DURATION_SEC
            current["failed_login_attempts"] = 0  # restart counter post-lock
        tx.write_json(paths.user_profile(user["id"]), current)


def _clear_login_failures(user: dict) -> None:
    if not (user.get("failed_login_attempts") or user.get("locked_until")):
        return  # nothing to clear
    paths = get_paths()
    with file_transaction([paths.user_profile(user["id"])]) as tx:
        current = tx.read_json(paths.user_profile(user["id"])) or user
        current["failed_login_attempts"] = 0
        current["locked_until"] = None
        tx.write_json(paths.user_profile(user["id"]), current)


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
    # Per-account lockout: durable across worker restarts, blind to IP rotation.
    locked_until = user.get("locked_until")
    if isinstance(locked_until, (int, float)) and locked_until > _now_epoch():
        remaining = int(locked_until - _now_epoch())
        raise APIError(
            429, ErrorCode.LOGIN_RATE_LIMITED,
            f"账号因连续登录失败已锁定，请 {remaining // 60 + 1} 分钟后再试",
        )
    # Verify password BEFORE returning status-specific errors so a random
    # attacker can't enumerate pending/rejected accounts.
    if not verify_password(password, user.get("password_hash")):
        _persist_login_failure(user)
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
    _clear_login_failures(user)
    return await _issue_tokens_and_touch(user)


async def feishu_login(
    feishu_user_id: str,
    email: str | None,
    name: str | None = None,
    avatar_url: str | None = None,
    feishu_access_token: str | None = None,
    feishu_refresh_token: str | None = None,
    feishu_token_expires_at: float | None = None,
    feishu_refresh_expires_at: float | None = None,
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
        from ...core.storage import get_index_db as _idb

        row = await _idb().fetchone(
            "SELECT id FROM users_index WHERE feishu_user_id = ? LIMIT 1",
            [feishu_user_id],
        )
        if row:
            user = await load_user_by_id(row["id"])

    if not user:
        from app.services.admin import sysconfig_svc

        if not sysconfig_svc.get_toggles().get("enable_feishu_auto_register", True):
            raise APIError(
                403,
                ErrorCode.FEISHU_ACCOUNT_NOT_WHITELISTED,
                "飞书账号未在白名单内，且自动注册已关闭。请联系管理员开启 enable_feishu_auto_register，或在 /admin/users 手动添加。",
            )
        return await _auto_provision_from_feishu(
            feishu_user_id=feishu_user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            feishu_access_token=feishu_access_token,
            feishu_refresh_token=feishu_refresh_token,
            feishu_token_expires_at=feishu_token_expires_at,
            feishu_refresh_expires_at=feishu_refresh_expires_at,
        )

    if user.get("feishu_user_id") and user["feishu_user_id"] != feishu_user_id:
        raise APIError(409, ErrorCode.FEISHU_BINDING_CONFLICT, "飞书账号已绑定至其他用户")
    user["feishu_user_id"] = feishu_user_id
    user["feishu_bound_at"] = _now()
    if name and not user.get("name"):
        user["name"] = name
    if avatar_url and not user.get("avatar_url"):
        user["avatar_url"] = avatar_url
    if feishu_access_token:
        user["feishu_access_token"] = feishu_access_token
    if feishu_refresh_token:
        user["feishu_refresh_token"] = feishu_refresh_token
    if feishu_token_expires_at:
        user["feishu_token_expires_at"] = feishu_token_expires_at
    if feishu_refresh_expires_at:
        user["feishu_refresh_expires_at"] = feishu_refresh_expires_at
    return await _issue_tokens_and_touch(user)


async def _auto_provision_from_feishu(
    *,
    feishu_user_id: str,
    email: str | None,
    name: str | None,
    avatar_url: str | None,
    feishu_access_token: str | None = None,
    feishu_refresh_token: str | None = None,
    feishu_token_expires_at: float | None = None,
    feishu_refresh_expires_at: float | None = None,
) -> dict:
    """Create a fresh `auth_role=user` account bound to the Feishu identity."""
    import uuid

    from ...core.security import hash_password
    from ...core.storage import get_index_db, get_paths

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
    if feishu_access_token:
        profile["feishu_access_token"] = feishu_access_token
    if feishu_refresh_token:
        profile["feishu_refresh_token"] = feishu_refresh_token
    if feishu_token_expires_at:
        profile["feishu_token_expires_at"] = feishu_token_expires_at
    if feishu_refresh_expires_at:
        profile["feishu_refresh_expires_at"] = feishu_refresh_expires_at
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


async def update_self(*, user_id: str, patch: dict) -> dict:
    """普通用户自助修改账户信息。
    允许字段：name / team / title / xiaomi_email / new_password（修改密码时必须同时提供 current_password）。
    禁止字段：email / auth_role / status / feishu_user_id —— 由管理员渠道维护。
    返回：更新后的 _to_public 视图。
    """
    paths = get_paths()
    profile = read_json(paths.user_profile(user_id))
    if not profile:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "用户不存在")

    new_name = patch.get("name")
    if new_name is not None:
        new_name = str(new_name).strip()
        if not new_name:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "姓名不能为空")
        if len(new_name) > 60:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "姓名最长 60 字")

    new_password = patch.get("new_password")
    if new_password:
        # 必须先验证旧密码；飞书-only 用户没有可登录密码（password_hash 为随机值），
        # 仍要求其先设置；这里直接拒绝，让管理员或飞书绑定流程处理。
        if not profile.get("password_hash"):
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "当前账号未设置密码，无法修改")
        current = patch.get("current_password") or ""
        if not verify_password(current, profile["password_hash"]):
            raise APIError(400, ErrorCode.INVALID_CREDENTIALS, "当前密码不正确")
        _validate_password_strength(new_password)

    new_xiaomi_email = patch.get("xiaomi_email")
    if new_xiaomi_email is not None:
        # Empty string = clear the field; non-empty must validate.
        new_xiaomi_email = _validate_xiaomi_email(str(new_xiaomi_email))

    # 应用修改
    if new_name is not None:
        profile["name"] = new_name
    for k in ("team", "title"):
        if k in patch:
            v = patch[k]
            profile[k] = (str(v).strip() or None) if v is not None else None
    if "xiaomi_email" in patch:
        profile["xiaomi_email"] = new_xiaomi_email or None
    if new_password:
        from ...core.security import hash_password
        profile["password_hash"] = hash_password(new_password)

    with file_transaction([paths.user_profile(user_id)]) as tx:
        tx.write_json(paths.user_profile(user_id), profile)
    db = get_index_db()
    await db.execute(
        "UPDATE users_index SET name = ?, password_hash = ? WHERE id = ?",
        [profile["name"], profile.get("password_hash"), user_id],
    )
    return _to_public(profile)


# Cap concurrent device sessions per account. A list of refresh-token jtis
# stored in the user profile tracks each independent login. New logins beyond
# this cap evict the oldest jti — equivalent to forced sign-out on the oldest
# device. 10 is generous (laptop + phone + a couple of stale tabs) without
# letting an attacker park unlimited tokens after a brief window of access.
_MAX_REFRESH_JTIS_PER_USER = 10


def _add_refresh_jti(user: dict, jti: str) -> None:
    jtis: list[str] = list(user.get("refresh_jtis") or [])
    jtis.append(jti)
    if len(jtis) > _MAX_REFRESH_JTIS_PER_USER:
        jtis = jtis[-_MAX_REFRESH_JTIS_PER_USER:]
    user["refresh_jtis"] = jtis


def _consume_refresh_jti(user: dict, jti: str) -> bool:
    """Single-use: remove jti from the user's valid set.

    Returns True if the jti was present (refresh proceeds) and False if it
    was already consumed / never issued. A False return is suspicious — a
    stolen-and-replayed refresh token is the canonical case — so the caller
    should treat it as a compromise signal and revoke ALL the user's
    refresh tokens. (See the OAuth refresh-token-rotation pattern.)
    """
    jtis: list[str] = list(user.get("refresh_jtis") or [])
    if jti not in jtis:
        return False
    user["refresh_jtis"] = [j for j in jtis if j != jti]
    return True


def _revoke_all_refresh(user: dict) -> None:
    user["refresh_jtis"] = []


async def rotate_refresh_token(refresh_token: str) -> dict:
    """Single-use refresh-token rotation. Returns a fresh access+refresh pair
    or raises if the presented token's jti is already consumed (replay).

    Implementation note: `file_transaction` rolls back on raise, so the
    "revoke-all on replay" path uses a separate transaction that commits
    the revoke before raising. Otherwise the revoke would be silently
    discarded and the attacker could keep rotating other tokens.
    """
    from ...core.security import decode_token

    payload = decode_token(refresh_token, expect="refresh")
    user_id = payload["sub"]
    jti = payload.get("jti")
    if not jti:
        # Pre-rotation tokens (no jti). Reject and require a fresh login —
        # otherwise rotation can be silently bypassed by replaying any
        # legacy token. One-time annoyance per user during the rollout.
        raise APIError(
            401, ErrorCode.TOKEN_REFRESH_FAILED,
            "refresh_token 已失效，请重新登录",
        )
    user = await load_user_by_id(user_id)
    if not user:
        raise APIError(401, ErrorCode.TOKEN_REFRESH_FAILED, "user not found")

    paths = get_paths()
    # Phase 1: try to consume jti and issue new one. Replay → fall to phase 2.
    replay_detected = False
    new_token: str | None = None
    new_role = user.get("auth_role", "user")
    with file_transaction([paths.user_profile(user["id"])]) as tx:
        current = tx.read_json(paths.user_profile(user["id"])) or user
        if not _consume_refresh_jti(current, jti):
            replay_detected = True
        else:
            new_token, new_jti_val = create_refresh_token(current["id"])
            _add_refresh_jti(current, new_jti_val)
            new_role = current.get("auth_role", "user")
            tx.write_json(paths.user_profile(user["id"]), current)

    if replay_detected:
        # Phase 2 (separate tx so the write actually commits): revoke ALL
        # the user's refresh jtis. Then raise.
        with file_transaction([paths.user_profile(user["id"])]) as tx:
            current = tx.read_json(paths.user_profile(user["id"])) or user
            _revoke_all_refresh(current)
            tx.write_json(paths.user_profile(user["id"]), current)
        raise APIError(
            401, ErrorCode.TOKEN_REFRESH_FAILED,
            "refresh_token 已被使用过，所有会话已注销，请重新登录",
        )

    return {
        "access_token": create_access_token(user["id"], new_role),
        "refresh_token": new_token,
        "token_type": "bearer",
    }


async def _issue_tokens_and_touch(user: dict) -> dict:
    s = get_settings()
    user["last_login_at"] = _now()
    refresh, jti = create_refresh_token(user["id"])
    _add_refresh_jti(user, jti)
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
            "refresh_token": refresh,
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
        "xiaomi_email": user.get("xiaomi_email"),
    }
