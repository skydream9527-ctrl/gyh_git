"""Example + edge-case tests for the WebSocket authentication paths.

These are deterministic example tests (NOT randomized property tests) covering
the auth resolution surface of the chat WebSocket handshake, exercising the
combination of the pure subprotocol parser (`app.core.ws_auth.extract_bearer`)
and the shared auth resolver (`app.core.deps.resolve_user`) exactly as the
WS_Endpoint wires them together.

They use the shared conftest fixtures (`fake_users`, `decode_token_stub`,
`aegis_verify_stub`) which stub JWT decode and Aegis verify via the opaque
encodings ``faketoken:<account_id>`` / ``fakeaegis:<email>`` so the three auth
paths can be driven without real RSA keys or signed JWTs.

The WS_Endpoint translates an auth-resolution ``APIError`` into a WebSocket
close with code 4401 (missing-account / no-credential) — these tests assert the
resolver raises ``APIError`` at the points where the handler would close 4401.

Covered acceptance criteria:
  Positive: 2.1, 2.2, 2.3, 2.7, 4.2, 4.3
  Edge/error: 1.3, 2.6, 2.8, 3.4, 3.5
"""
from __future__ import annotations

import asyncio

import pytest

from app.core import config as cfg
from app.core.deps import resolve_user
from app.core.errors import APIError
from app.core.ws_auth import extract_bearer


# ---------------------------------------------------------------------------
# Helper: drive the resolver exactly as the WS handshake does.
# ws_chat / get_current_user_ws first run extract_bearer over the offered
# Sec-WebSocket-Protocol header + legacy ?token= query param, then resolve_user
# over (X-Proxy-UserDetail, "Bearer <bearer>").
# ---------------------------------------------------------------------------
def _ws_resolve(
    *,
    aegis_header: str | None = None,
    offered_header: str | None = None,
    query_token: str | None = None,
) -> dict:
    chosen_proto, bearer = extract_bearer(offered_header, query_token)
    auth_header = f"Bearer {bearer}" if bearer else None
    return asyncio.run(resolve_user(aegis_header, auth_header))


# ===========================================================================
# Positive auth paths
# ===========================================================================
def test_subprotocol_jwt_authenticates(decode_token_stub):
    """2.1 — a valid access JWT offered via the ``["bearer", token]``
    subprotocol authenticates the connection using the subprotocol token."""
    fake_users = decode_token_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    token = fake_users.bearer_token(acct)

    user = _ws_resolve(offered_header=f"bearer, {token}")

    assert user["id"] == acct["id"]
    assert user["_auth_source"] == "password"


def test_legacy_query_token_authenticates(decode_token_stub):
    """2.2 — when no subprotocol is offered, a valid ``?token=`` query JWT
    authenticates the connection."""
    fake_users = decode_token_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    token = fake_users.bearer_token(acct)

    user = _ws_resolve(offered_header=None, query_token=token)

    assert user["id"] == acct["id"]
    assert user["_auth_source"] == "password"


def test_signed_aegis_header_authenticates(aegis_verify_stub):
    """2.3 — with Aegis enabled and a configured key, a verifying
    ``X-Proxy-UserDetail`` header authenticates via the Aegis payload."""
    fake_users = aegis_verify_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    header = fake_users.aegis_header(acct)

    user = _ws_resolve(aegis_header=header)

    assert user["email"] == acct["email"]
    assert user["_auth_source"] == "aegis"


def test_aegis_disabled_falls_through_to_bearer(decode_token_stub, monkeypatch):
    """2.7 — when Aegis is disabled, an ``X-Proxy-UserDetail`` header is
    ignored and resolution falls through to the bearer token."""
    monkeypatch.setenv("AEGIS_ENABLED", "false")
    cfg.get_settings.cache_clear()

    fake_users = decode_token_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    token = fake_users.bearer_token(acct)

    # Aegis header is present but must be ignored; bearer wins.
    user = _ws_resolve(
        aegis_header=fake_users.aegis_header(acct),
        offered_header=f"bearer, {token}",
    )

    assert user["id"] == acct["id"]
    assert user["_auth_source"] == "password"


def test_aegis_no_public_key_falls_through_to_bearer(decode_token_stub):
    """2.7 — when Aegis is enabled but NO public key is configured (the
    default test settings), the header is ignored and resolution falls through
    to the bearer token rather than hard-failing."""
    # Default settings: AEGIS_ENABLED=True but AEGIS_PUBLIC_KEY unset.
    settings = cfg.get_settings()
    assert settings.AEGIS_ENABLED is True
    assert settings.aegis_public_keys == []

    fake_users = decode_token_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    token = fake_users.bearer_token(acct)

    user = _ws_resolve(
        aegis_header=fake_users.aegis_header(acct),
        query_token=token,
    )

    assert user["id"] == acct["id"]
    assert user["_auth_source"] == "password"


def test_legacy_only_upgrade(decode_token_stub):
    """4.2 — a pre-feature client offering NO bearer subprotocol but a valid
    ``?token=`` completes the upgrade without requiring Subprotocol_Auth."""
    fake_users = decode_token_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    token = fake_users.bearer_token(acct)

    # No subprotocol offered → extract_bearer negotiates no proto.
    chosen_proto, bearer = extract_bearer(None, token)
    assert chosen_proto is None
    assert bearer == token

    user = _ws_resolve(offered_header=None, query_token=token)
    assert user["id"] == acct["id"]
    assert user["_auth_source"] == "password"


def test_new_client_subprotocol_upgrade_negotiates_bearer(decode_token_stub):
    """4.3 — a new client offering ``["bearer", token]`` and no ``?token=``
    completes the upgrade with the negotiated subprotocol exactly ``"bearer"``
    (never the token value)."""
    fake_users = decode_token_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    token = fake_users.bearer_token(acct)

    chosen_proto, bearer = extract_bearer(f"bearer, {token}", None)
    # Negotiated value is the literal "bearer", never the token.
    assert chosen_proto == "bearer"
    assert chosen_proto != token
    assert bearer == token

    user = _ws_resolve(offered_header=f"bearer, {token}")
    assert user["id"] == acct["id"]
    assert user["_auth_source"] == "password"


# ===========================================================================
# Edge / error cases — the resolver raises APIError where the WS_Endpoint
# would close the handshake with code 4401.
# ===========================================================================
@pytest.mark.parametrize(
    "offered_header, query_token",
    [
        ("bearer", None),           # subprotocol "bearer" offered with no token
        ("bearer", ""),             # empty query fallback
        (None, ""),                 # empty query token, no subprotocol
        (None, "   "),              # whitespace-only query token
        ("bearer, ", None),         # trailing empty subprotocol entry
    ],
)
def test_empty_or_whitespace_token_rejected(decode_token_stub, offered_header, query_token):
    """1.3 — an empty / whitespace-only bearer token yields no usable
    credential and the handshake is rejected (4401)."""
    with pytest.raises(APIError) as exc:
        _ws_resolve(offered_header=offered_header, query_token=query_token)
    assert exc.value.status_code == 401


def test_tampered_aegis_header_rejects_without_bearer_fallthrough(aegis_verify_stub):
    """2.6 — an ``X-Proxy-UserDetail`` header whose signature fails to verify
    rejects the handshake and MUST NOT fall through to bearer authentication,
    even when a valid bearer token is also present."""
    fake_users = aegis_verify_stub
    acct = fake_users.by_email("alice@xiaomi.com")
    valid_token = fake_users.bearer_token(acct)

    # "tampered:..." is not a recognized fakeaegis header → verify stub raises
    # AegisVerifyError → _try_aegis raises APIError. The presence of a valid
    # bearer must NOT rescue the handshake.
    with pytest.raises(APIError) as exc:
        _ws_resolve(
            aegis_header="tampered:alice@xiaomi.com",
            offered_header=f"bearer, {valid_token}",
        )
    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "not-a-valid-jwt",          # malformed: not decodable
        "expired.jwt.payload",      # stand-in for a malformed/expired token
        "bearer-but-garbage",       # decode stub rejects anything not faketoken:*
    ],
)
def test_malformed_or_expired_jwt_rejected(decode_token_stub, token):
    """2.8 — a bearer token that does not decode as a valid, unexpired access
    JWT is rejected. The decode stub raises ``APIError`` for any token that is
    not a well-formed ``faketoken:<id>``, mirroring the real ``decode_token``
    which raises on malformed and expired JWTs alike."""
    with pytest.raises(APIError) as exc:
        _ws_resolve(offered_header=f"bearer, {token}")
    assert exc.value.status_code == 401


def test_unknown_user_jwt_rejected(decode_token_stub):
    """2.8 / 3.4 — a well-formed, decodable bearer token whose subject does NOT
    resolve to a local account is rejected (4401). The credential is 'accepted'
    by decode but no matching local account exists."""
    # faketoken:<id> decodes fine, but no account with this id was registered.
    bogus = "faketoken:no-such-account"
    with pytest.raises(APIError) as exc:
        _ws_resolve(offered_header=f"bearer, {bogus}")
    assert exc.value.status_code == 401


def test_no_credential_rejected(decode_token_stub):
    """3.5 — a handshake presenting no Aegis header, no subprotocol token, and
    no ``?token=`` query param presents no valid credential through any path
    and is rejected (4401)."""
    chosen_proto, bearer = extract_bearer(None, None)
    assert chosen_proto is None
    assert bearer is None

    with pytest.raises(APIError) as exc:
        _ws_resolve()
    assert exc.value.status_code == 401
