from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest
from hypothesis import settings as hypothesis_settings

# ---------------------------------------------------------------------------
# Hypothesis profile (websocket-token-stability, task 1.1)
# ---------------------------------------------------------------------------
# The property tests for this feature run a minimum of 100 iterations each
# (see design.md "Testing Strategy"). Register an "ice" profile pinning
# max_examples=100 as the project default and load it for the whole suite.
# An env override (HYPOTHESIS_PROFILE) lets a developer dial iterations up or
# down locally without editing this file.
hypothesis_settings.register_profile("ice", max_examples=100)
hypothesis_settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ice"))


@pytest.fixture(autouse=True)
def isolated_data_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="ice-test-"))
    for sub in ("agents", "skills", "files", "users", "tasks", "teams", ".cache"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATA_ROOT", str(tmp))
    monkeypatch.setenv("ICE_SECRET_KEY", "test-secret-key-with-enough-length-32b")
    # Tests pin a known strong admin password. Without this the seed runner
    # generates a random one on every test run and the login fixtures can't
    # log in. Strong enough to satisfy the security validator (>=12 chars,
    # not in the documented-default list).
    monkeypatch.setenv("ICE_BOOTSTRAP_ADMIN_PASSWORD", "Test-Admin-Pw-2026!")

    # purge cached settings/paths
    from app.core import config as cfg
    from app.core.storage import index_db, paths as p

    cfg.get_settings.cache_clear()
    p.get_paths.cache_clear()
    index_db.get_index_db.cache_clear()

    # Apply IndexDB schema so services that hit the cache (e.g. conversation_svc
    # → user._name_map → users_index) don't trip on a missing table. In prod
    # this is done via `await db.init()` from app/seed/runner.py; here we run
    # the same SCHEMA via stdlib sqlite3 so the fixture stays sync.
    db_path = cfg.get_settings().cache_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(index_db.SCHEMA)
        conn.commit()

    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Reusable auth fixtures (websocket-token-stability, task 1.1)
# ---------------------------------------------------------------------------
# These let the auth-path property/example tests (Properties 1, 2, 4, 9, 11)
# exercise `resolve_user` and the three auth paths (Subprotocol/Legacy bearer
# and Aegis header) WITHOUT real RSA keys or real signed JWTs. They patch the
# names as bound inside `app.core.deps` (deps does `from .security import
# decode_token` / `from .aegis import verify`, so the live references live in
# the deps module namespace).
#
# Opaque credential encoding used by the stubs:
#   bearer token  -> "faketoken:<account_id>"
#   aegis header  -> "fakeaegis:<email>"
# The stubs parse these back to a registry lookup; anything else is rejected
# exactly like the real path (raising APIError / AegisVerifyError).


class FakeUsersRegistry:
    """In-memory stand-in for the local users registry.

    Holds the canonical account records that every auth path must resolve to
    the same `id` for (Requirement 3.1-3.3). Add accounts with `add(...)` and
    mint path-specific credentials with `bearer_token(...)` / `aegis_header(...)`.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, dict] = {}
        self._by_email: dict[str, dict] = {}

    def add(
        self,
        *,
        id: str | None = None,
        email: str,
        name: str | None = None,
        auth_role: str = "user",
        status: str = "active",
    ) -> dict:
        import uuid

        email = email.lower()
        acct = {
            "id": id or uuid.uuid4().hex,
            "email": email,
            "name": name or email.split("@")[0],
            "auth_role": auth_role,
            "status": status,
        }
        self._by_id[acct["id"]] = acct
        self._by_email[email] = acct
        return acct

    def by_id(self, uid: str) -> dict | None:
        acct = self._by_id.get(uid)
        return dict(acct) if acct else None

    def by_email(self, email: str) -> dict | None:
        acct = self._by_email.get((email or "").lower())
        return dict(acct) if acct else None

    def ensure_email(self, email: str, *, name: str | None = None, auth_role: str = "user") -> dict:
        existing = self.by_email(email)
        if existing:
            return existing
        return self.add(email=email, name=name, auth_role=auth_role)

    @staticmethod
    def bearer_token(account: dict) -> str:
        """Opaque token the decode_token stub maps back to this account."""
        return f"faketoken:{account['id']}"

    @staticmethod
    def aegis_header(account: dict) -> str:
        """Opaque X-Proxy-UserDetail value the verify stub maps back to this email."""
        return f"fakeaegis:{account['email']}"


@pytest.fixture
def fake_users() -> FakeUsersRegistry:
    """A fresh fake local users registry, seeded with one default account."""
    reg = FakeUsersRegistry()
    reg.add(id="user-001", email="alice@xiaomi.com", name="Alice", auth_role="user")
    return reg


@pytest.fixture
def decode_token_stub(monkeypatch, fake_users):
    """Patch the bearer path so `faketoken:<id>` resolves via `fake_users`.

    Patches `deps.decode_token` (JWT decode) and `deps.load_user_by_id` so
    `_try_bearer` works against the fake registry instead of real JWTs/index.
    Returns the registry for convenience.
    """
    from app.core import deps
    from app.core.errors import APIError, ErrorCode

    def fake_decode(token: str, expect: str = "access") -> dict:
        if not isinstance(token, str) or not token.startswith("faketoken:"):
            raise APIError(401, ErrorCode.TOKEN_INVALID, "invalid token")
        uid = token.split(":", 1)[1]
        acct = fake_users.by_id(uid)
        role = acct["auth_role"] if acct else "user"
        return {"sub": uid, "type": expect, "role": role}

    async def fake_load_user_by_id(uid: str):
        return fake_users.by_id(uid)

    monkeypatch.setattr(deps, "decode_token", fake_decode)
    monkeypatch.setattr(deps, "load_user_by_id", fake_load_user_by_id)
    return fake_users


@pytest.fixture
def aegis_verify_stub(monkeypatch, fake_users):
    """Patch the Aegis path so `fakeaegis:<email>` resolves without real keys.

    Enables Aegis (with a dummy key so `_try_aegis` doesn't short-circuit) and
    patches `deps.verify` + `deps.ensure_user_for_email` to consult the fake
    registry. Returns the registry for convenience.
    """
    from app.core import config as cfg
    from app.core import deps
    from app.core.aegis import AegisUser, AegisVerifyError

    monkeypatch.setenv("AEGIS_ENABLED", "true")
    monkeypatch.setenv("AEGIS_PUBLIC_KEY", "dummy-key-unused-by-stub")
    cfg.get_settings.cache_clear()

    def fake_verify(header_value: str, public_keys) -> AegisUser:
        if not isinstance(header_value, str) or not header_value.startswith("fakeaegis:"):
            raise AegisVerifyError("stub: unrecognized aegis header")
        email = header_value.split(":", 1)[1]
        return AegisUser(
            uid=None,
            user=email.split("@")[0],
            name=None,
            type="employee",
            display_name=None,
            department_name=None,
            email=email,
            mi_id=None,
            avatar=None,
        )

    async def fake_ensure_user_for_email(email: str, *, name: str | None = None, auth_role: str = "user"):
        return fake_users.ensure_email(email, name=name, auth_role=auth_role)

    monkeypatch.setattr(deps, "verify", fake_verify)
    monkeypatch.setattr(deps, "ensure_user_for_email", fake_ensure_user_for_email)
    return fake_users
