"""Pure WebSocket subprotocol-bearer auth helpers.

This module holds framework-free, I/O-free string logic for negotiating the
WebSocket bearer subprotocol. It is shared by `api/v1/ws.py` (`ws_chat`) and
`core/deps.py` (`get_current_user_ws`) so the handshake parsing lives in one
unit-/property-testable place.

Negotiation contract (see design.md "ws.py handshake auth negotiation"):
- The client offers `Sec-WebSocket-Protocol: bearer, <jwt>`.
- The negotiated subprotocol value is **exactly** `"bearer"` whenever the
  offered list contains the literal `"bearer"` — never the token value.
- The token is the first offered entry that is not the literal `"bearer"`.
- The subprotocol token takes precedence over the legacy `?token=` query param.
"""

from __future__ import annotations


def extract_bearer(
    offered_header: str | None,
    query_token: str | None,
) -> tuple[str | None, str | None]:
    """Resolve the negotiated subprotocol and the bearer token from a handshake.

    Args:
        offered_header: The raw `Sec-WebSocket-Protocol` request header value
            (a comma-separated list), or ``None`` when the header is absent.
        query_token: The legacy `?token=` query-param value, or ``None``.

    Returns:
        A ``(chosen_proto, bearer)`` tuple where:
        - ``chosen_proto`` is ``"bearer"`` iff the offered list contains the
          literal ``"bearer"``, otherwise ``None``. This is the exact value the
          server must echo to ``websocket.accept(subprotocol=...)`` — never the
          token value (Req 1.4, 1.5).
        - ``bearer`` is the first offered entry that is not ``"bearer"`` when a
          subprotocol token is present, otherwise it falls back to
          ``query_token``. The subprotocol token therefore takes precedence over
          the legacy query param (Req 2.5).

    Edge cases:
        - ``None`` / empty / whitespace-only header → no offered entries, so
          ``chosen_proto`` is ``None`` and ``bearer`` is ``query_token``.
        - Header containing only ``"bearer"`` with no token → ``chosen_proto``
          is ``"bearer"`` and ``bearer`` falls back to ``query_token``.
        - Multiple non-``"bearer"`` entries → the first one is taken.
    """
    offered = (offered_header or "").split(",")
    offered = [p.strip() for p in offered if p.strip()]

    chosen_proto: str | None = None
    sub_token: str | None = None
    if "bearer" in offered:
        chosen_proto = "bearer"
        for p in offered:
            if p != "bearer":
                sub_token = p
                break

    bearer = sub_token or query_token
    return chosen_proto, bearer
