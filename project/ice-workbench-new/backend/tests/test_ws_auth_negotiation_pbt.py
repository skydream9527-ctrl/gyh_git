"""Property-based tests for the server-side subprotocol negotiation contract.

Feature: websocket-token-stability, Property 4: Subprotocol negotiation contract

Server side: for any non-empty token offered as ``["bearer", token]``,
``app.core.ws_auth.extract_bearer`` returns ``chosen_proto == "bearer"`` and a
bearer equal to the token, never echoing the token as the negotiated proto
value; for an empty offer it returns ``(None, query_token)``.

These tests exercise the pure helper directly (no I/O, no framework) across a
minimum of 100 iterations via the conftest ``ice`` Hypothesis profile
(max_examples=100, default).

Validates: Requirements 1.4, 1.5
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.core.ws_auth import extract_bearer

# A subprotocol token entry: printable, non-space ASCII excluding the comma
# delimiter, so each entry survives `extract_bearer`'s split/strip unchanged.
# "bearer" is excluded because it is the literal negotiation marker, not a token.
_token_chars = st.characters(min_codepoint=33, max_codepoint=126, blacklist_characters=",")
tokens = st.text(alphabet=_token_chars, min_size=1).filter(lambda s: s != "bearer")

# Empty offers: header values that parse to zero offered entries (None, empty,
# whitespace-only, or only commas/whitespace).
empty_headers = st.sampled_from([None, "", "   ", "\t", " , ", ",", ",,", "  ,  ,  "])

# Legacy ?token= query param, including the absent case.
query_tokens = st.one_of(st.none(), tokens)


@given(token=tokens, bearer_first=st.booleans(), query_token=query_tokens)
def test_bearer_offer_negotiates_bearer_never_token(token, bearer_first, query_token):
    """For ["bearer", token] (either ordering) the negotiated proto is exactly
    "bearer" and the bearer equals the offered token — never the token echoed
    as the proto value, and the subprotocol token wins over any ?token=.

    Feature: websocket-token-stability, Property 4: Subprotocol negotiation contract
    Validates: Requirements 1.4, 1.5
    """
    offered = ["bearer", token] if bearer_first else [token, "bearer"]
    header = ", ".join(offered)

    chosen_proto, bearer = extract_bearer(header, query_token)

    # Negotiated subprotocol is the literal "bearer", never the token value.
    assert chosen_proto == "bearer"
    assert chosen_proto != token
    # The bearer source is the offered subprotocol token (preferred over query).
    assert bearer == token


@given(header=empty_headers, query_token=query_tokens)
def test_empty_offer_yields_none_proto_and_query_fallback(header, query_token):
    """For an empty offer, no subprotocol is negotiated and the bearer falls
    back to the legacy ?token= query value.

    Feature: websocket-token-stability, Property 4: Subprotocol negotiation contract
    Validates: Requirements 1.4, 1.5
    """
    chosen_proto, bearer = extract_bearer(header, query_token)

    assert chosen_proto is None
    assert bearer == query_token


@given(
    non_bearer_entries=st.lists(tokens, max_size=4),
    include_bearer=st.booleans(),
    bearer_pos=st.integers(min_value=0, max_value=5),
    query_token=query_tokens,
)
def test_negotiation_contract_for_arbitrary_offer_orderings(
    non_bearer_entries, include_bearer, bearer_pos, query_token
):
    """General contract over arbitrary offered orderings: when the offered list
    contains "bearer", chosen_proto is exactly "bearer" (never a token) and the
    bearer is the first non-"bearer" entry (or the query_token fallback); when
    it does not, chosen_proto is None and bearer is the query_token.

    Feature: websocket-token-stability, Property 4: Subprotocol negotiation contract
    Validates: Requirements 1.4, 1.5
    """
    offered = list(non_bearer_entries)
    if include_bearer:
        offered.insert(min(bearer_pos, len(offered)), "bearer")
    header = ",".join(offered)

    chosen_proto, bearer = extract_bearer(header, query_token)

    if include_bearer:
        # Negotiated value is the literal marker, never a token value.
        assert chosen_proto == "bearer"
        first_non_bearer = non_bearer_entries[0] if non_bearer_entries else None
        expected_bearer = first_non_bearer if first_non_bearer is not None else query_token
        assert bearer == expected_bearer
        # The proto value is never the chosen bearer token.
        if bearer is not None:
            assert chosen_proto != bearer
    else:
        assert chosen_proto is None
        assert bearer == query_token
