"""Property-based test for WebSocket auth-path id equivalence.

Feature: websocket-token-stability, Property 1: Auth path id equivalence

For any account that is resolvable through more than one auth path
(Subprotocol_Auth, Legacy_Query_Auth, Aegis_Auth), the resulting User_Dict
contains the **common core key-set** ``{id, email, name, auth_role, status,
_auth_source, is_admin}`` identical across all paths. Paths MAY add
path-specific profile fields (for example the Aegis path's ``display_name``,
``department_name``, ``avatar_url``, ``mi_id``, ``uid``, ``user``, ``type``), so
this property asserts the core set is a SUBSET of every path's keys rather than
requiring strict full key-set equality. The canonical ``id`` is a non-empty
string drawn from the local users registry that is byte-for-byte identical
across every path for that account.

Resolution model used here:

* Subprotocol_Auth and Legacy_Query_Auth differ only in *transport* — both carry
  the same bearer JWT, which ``ws_auth.extract_bearer`` collapses to a single
  ``Authorization: Bearer <token>`` header before ``resolve_user`` ever runs.
  So both paths are exercised by resolving the SAME bearer through
  ``resolve_user(None, "Bearer <token>")``.
* Aegis_Auth resolves via the ``X-Proxy-UserDetail`` header
  (``resolve_user(<aegis_header>, None)``).

All three are driven through the real ``app.core.deps.resolve_user`` with the
shared conftest stubs (``fake_users``, ``decode_token_stub``,
``aegis_verify_stub``) so no real RSA keys or signed JWTs are needed. The fake
registry maps the opaque encodings ``faketoken:<id>`` / ``fakeaegis:<email>``
back to the same canonical account, so every path must land on the same ``id``.

``resolve_user`` is async; it is driven via ``asyncio.run`` per example, and the
function-scoped-fixture health check is suppressed (mirroring
``test_ws_auth_precedence_pbt.py``).

**Validates: Requirements 3.1, 3.2, 3.3, 4.1**
"""
from __future__ import annotations

import asyncio
import string

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core.deps import resolve_user

# The common core key-set every auth path must produce identically (Req 3.1).
# Paths MAY add path-specific profile fields on top of this set (e.g. Aegis adds
# display_name / department_name / avatar_url / mi_id / uid / user / type), so we
# assert this set is a SUBSET of each path's keys, not full key-set equality.
_CORE_KEYS = {"id", "email", "name", "auth_role", "status", "_auth_source", "is_admin"}

# Local-parts for synthesized emails / ids. The "acct-" prefixes keep generated
# accounts clear of the conftest's default seed (alice@xiaomi.com / user-001)
# and unambiguous even when two examples generate the same local-part.
_locals = st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=16)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(email_local=_locals, id_suffix=_locals)
def test_auth_path_id_equivalence(
    fake_users,
    decode_token_stub,
    aegis_verify_stub,
    email_local,
    id_suffix,
):
    """Feature: websocket-token-stability, Property 1: Auth path id equivalence

    The same underlying account, resolved through Subprotocol_Auth,
    Legacy_Query_Auth, and Aegis_Auth, exposes the common core key-set with
    matching values (excepting ``_auth_source``, which legitimately differs by
    path) and a byte-for-byte identical, non-empty canonical ``id``.

    **Validates: Requirements 3.1, 3.2, 3.3, 4.1**
    """
    # One canonical account in the local registry, reachable by both a bearer
    # token (keyed on id) and an Aegis header (keyed on email).
    email = f"acct-{email_local}@xiaomi.com"
    acct_id = f"acct-{id_suffix}"
    account = fake_users.add(id=acct_id, email=email, name="Account User")

    bearer = fake_users.bearer_token(account)          # faketoken:<id>
    aegis_header = fake_users.aegis_header(account)     # fakeaegis:<email>
    authorization = f"Bearer {bearer}"

    # Subprotocol and Legacy-query both reduce to the same Bearer header, so the
    # same resolve_user(None, authorization) call models both transports.
    subprotocol_user = asyncio.run(resolve_user(None, authorization))
    legacy_query_user = asyncio.run(resolve_user(None, authorization))
    # Aegis resolves via the proxy header.
    aegis_user = asyncio.run(resolve_user(aegis_header, None))

    paths = (subprotocol_user, legacy_query_user, aegis_user)

    # 3.2: canonical id is a non-empty string from the local registry on every path.
    for user in paths:
        assert isinstance(user.get("id"), str)
        assert user["id"] != ""

    # 3.3 / 4.1: the id is byte-for-byte identical across paths for this account.
    assert (
        subprotocol_user["id"]
        == legacy_query_user["id"]
        == aegis_user["id"]
        == acct_id
    )

    # 3.1: the common core key-set is a SUBSET of every path's keys. Paths may
    # add path-specific profile fields (Aegis does) — we do NOT require strict
    # full key-set equality, only that the shared core is present everywhere.
    for user in paths:
        assert _CORE_KEYS.issubset(user.keys())

    # 3.1: the core-key VALUES match across paths — EXCEPT `_auth_source`, which
    # legitimately differs by transport ("password" for the bearer subprotocol/
    # legacy-query paths vs "aegis" for the Aegis header path). So compare the
    # core values on the set MINUS `_auth_source`, and separately assert
    # `_auth_source` is present and non-empty on every path.
    comparable_keys = _CORE_KEYS - {"_auth_source"}
    sub_core = {k: subprotocol_user[k] for k in comparable_keys}
    legacy_core = {k: legacy_query_user[k] for k in comparable_keys}
    aegis_core = {k: aegis_user[k] for k in comparable_keys}
    assert sub_core == legacy_core == aegis_core

    for user in paths:
        assert isinstance(user.get("_auth_source"), str)
        assert user["_auth_source"] != ""
