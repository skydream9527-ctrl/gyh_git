"""Throwaway smoke test for task 1.1 scaffolding — deleted after verification."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.mark.asyncio
async def test_bearer_stub_resolves(decode_token_stub):
    from app.core.deps import resolve_user

    acct = decode_token_stub.by_id("user-001")
    token = decode_token_stub.bearer_token(acct)
    user = await resolve_user(None, f"Bearer {token}")
    assert user["id"] == "user-001"
    assert user["_auth_source"] == "password"


@pytest.mark.asyncio
async def test_aegis_and_bearer_same_id(isolated_data_root, decode_token_stub, aegis_verify_stub):
    from app.core.deps import resolve_user

    reg = decode_token_stub  # same registry instance as aegis_verify_stub
    acct = reg.add(id="user-777", email="bob@xiaomi.com", name="Bob")
    via_bearer = await resolve_user(None, f"Bearer {reg.bearer_token(acct)}")
    via_aegis = await resolve_user(reg.aegis_header(acct), None)
    assert via_bearer["id"] == via_aegis["id"] == "user-777"


@settings(max_examples=5)
@given(st.integers())
def test_hypothesis_profile_loaded(n):
    # Profile registration smoke: just confirms hypothesis runs under the suite.
    assert isinstance(n, int)
