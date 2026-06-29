"""Property-based tests for WebSocket credential precedence.

Feature: websocket-token-stability, Property 2: Credential precedence

Property 2 has two halves, both exercised here:

1. Subprotocol-over-query precedence (pure string logic): for any handshake
   offering BOTH a subprotocol bearer token and a legacy ``?token=`` query
   token, ``app.core.ws_auth.extract_bearer`` selects the subprotocol token as
   the bearer source and ignores the query token.

2. Aegis-over-bearer precedence (auth resolution): for any handshake presenting
   BOTH a valid Aegis ``X-Proxy-UserDetail`` header and a valid bearer token,
   ``app.core.deps.resolve_user`` authenticates via the Aegis payload even
   though a usable bearer is present.

The auth-resolution half uses the shared conftest fixtures (`fake_users`,
`decode_token_stub`, `aegis_verify_stub`) which stub JWT decode and Aegis verify
with the opaque encodings ``faketoken:<id>`` / ``fakeaegis:<email>``.

**Validates: Requirements 2.4, 2.5**
"""
from __future__ import annotations

import asyncio
import string

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core.deps import resolve_user
from app.core.ws_auth import extract_bearer

# Token-ish strings safe to place in a comma-separated Sec-WebSocket-Protocol
# header: no commas, no surrounding whitespace, and never the literal "bearer".
_TOKEN_ALPHABET = string.ascii_letters + string.digits + "._-"
_sub_tokens = st.text(alphabet=_TOKEN_ALPHABET, min_size=1, max_size=40).filter(
    lambda s: s != "bearer"
)
# Query token may be present (non-empty) here so the precedence choice is
# observable, or empty/None to cover the fallback edge.
_query_tokens = st.one_of(
    st.none(),
    st.text(alphabet=_TOKEN_ALPHABET, min_size=0, max_size=40),
)

# Local-parts for synthesized emails / ids. Prefixes guarantee the Aegis and
# bearer accounts stay distinct so the selected account is unambiguous.
_locals = st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=12)


@given(sub_token=_sub_tokens, query_token=_query_tokens)
def test_extract_bearer_prefers_subprotocol_over_query(sub_token, query_token):
    """Feature: websocket-token-stability, Property 2: Credential precedence

    When both a subprotocol bearer token and a ``?token=`` query token are
    offered, ``extract_bearer`` negotiates exactly ``"bearer"`` and uses the
    subprotocol token as the bearer source, ignoring the query token.

    **Validates: Requirements 2.5**
    """
    offered_header = f"bearer, {sub_token}"
    chosen_proto, bearer = extract_bearer(offered_header, query_token)

    # Negotiated subprotocol is the literal "bearer", never the token value.
    assert chosen_proto == "bearer"
    # Subprotocol token wins over the legacy query token.
    assert bearer == sub_token
    # When the two tokens genuinely differ, the query token is observably
    # ignored. (If they coincide, precedence is still satisfied by the line
    # above; there is just nothing distinguishing to assert.)
    if query_token and query_token != sub_token:
        assert bearer != query_token


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(aegis_local=_locals, bearer_local=_locals, bearer_id_suffix=_locals)
def test_resolve_user_prefers_aegis_over_bearer(
    fake_users,
    decode_token_stub,
    aegis_verify_stub,
    aegis_local,
    bearer_local,
    bearer_id_suffix,
):
    """Feature: websocket-token-stability, Property 2: Credential precedence

    When a handshake presents BOTH a valid Aegis header and a valid bearer
    token, ``resolve_user`` selects the Aegis-resolved user. Aegis is evaluated
    first and the bearer path is only consulted if Aegis yields no user.

    **Validates: Requirements 2.4**
    """
    # Distinct accounts per path. Prefixes keep them unambiguous even when the
    # generated local-parts collide.
    aegis_email = f"aegis-{aegis_local}@xiaomi.com"
    bearer_email = f"bearer-{bearer_local}@xiaomi.com"
    bearer_id = f"bearer-{bearer_id_suffix}"

    # The bearer account must exist so the bearer path is genuinely usable —
    # otherwise the test couldn't distinguish "Aegis preferred" from "bearer
    # rejected". (The Aegis account is auto-provisioned by the stub on resolve.)
    bearer_acct = fake_users.add(id=bearer_id, email=bearer_email, name="Bearer User")

    aegis_header = f"fakeaegis:{aegis_email}"
    authorization = f"Bearer {fake_users.bearer_token(bearer_acct)}"

    # Sanity: the bearer credential alone really does resolve the bearer account.
    bearer_only = asyncio.run(resolve_user(None, authorization))
    assert bearer_only["id"] == bearer_id
    assert bearer_only["_auth_source"] == "password"

    # Precedence: with BOTH credentials present, Aegis wins.
    resolved = asyncio.run(resolve_user(aegis_header, authorization))
    assert resolved["_auth_source"] == "aegis"
    assert resolved["email"] == aegis_email.lower()
    # And it is emphatically not the (valid) bearer account.
    assert resolved["id"] != bearer_id
    assert resolved["email"] != bearer_email.lower()
