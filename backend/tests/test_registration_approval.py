"""Tests for the admin-approval registration flow.

Flow:
1. register() — creates the user with status="pending", does NOT return tokens
2. password_login() — pending user is rejected with ACCOUNT_PENDING_APPROVAL
3. admin_svc.review_registration(approved) — status flips to active
4. password_login() — approved user can now log in
5. review_registration(rejected, reason) — status → rejected, login shows
   ACCOUNT_REJECTED with the reason surfaced
"""
from __future__ import annotations

import pytest

from app.core.errors import APIError
from app.seed.runner import bootstrap
from app.services import admin_svc, auth_svc, sysconfig_svc


async def _prepare():
    """Bootstrap admin + flip open-register toggle on."""
    await bootstrap()
    # bootstrap() creates the toggles file; make sure open register is on.
    sysconfig_svc.update_toggles({"enable_open_register": True})


@pytest.mark.asyncio
async def test_register_creates_pending_user_without_tokens(isolated_data_root):
    await _prepare()
    result = await auth_svc.register("alice@example.com", "Alice", "secret123")
    assert result["status"] == "pending"
    # Backend returns the public user summary but NO tokens.
    assert "tokens" not in result
    assert result["user"]["email"] == "alice@example.com"
    # Profile on disk confirms the status + audit fields.
    profile = await auth_svc.load_user_by_email("alice@example.com")
    assert profile["status"] == "pending"
    assert profile["registration_submitted_at"]
    assert profile["self_registered"] is True
    assert profile["reviewed_by"] is None


@pytest.mark.asyncio
async def test_password_login_blocked_when_pending(isolated_data_root):
    await _prepare()
    await auth_svc.register("bob@example.com", "Bob", "secret123")
    with pytest.raises(APIError) as exc:
        await auth_svc.password_login("bob@example.com", "secret123")
    assert exc.value.error_code == "ACCOUNT_PENDING_APPROVAL"
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_pending_account_wrong_password_still_invalid_credentials(isolated_data_root):
    """Wrong-password must NOT leak pending-account existence to enumeration
    attempts; they should see INVALID_CREDENTIALS just like a non-existent
    account."""
    await _prepare()
    await auth_svc.register("carol@example.com", "Carol", "secret123")
    with pytest.raises(APIError) as exc:
        await auth_svc.password_login("carol@example.com", "wrongwrong")
    assert exc.value.error_code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_admin_approve_unlocks_login(isolated_data_root):
    await _prepare()
    admin = await auth_svc.load_user_by_email("admin")
    await auth_svc.register("dave@example.com", "Dave", "secret123")
    dave = await auth_svc.load_user_by_email("dave@example.com")
    reviewed = await admin_svc.review_registration(
        operator=admin, uid=dave["id"], decision="approved"
    )
    assert reviewed["status"] == "active"
    assert reviewed["reviewed_by"] == admin["id"]
    # Now login works.
    result = await auth_svc.password_login("dave@example.com", "secret123")
    assert result["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_admin_reject_sets_status_and_reason(isolated_data_root):
    await _prepare()
    admin = await auth_svc.load_user_by_email("admin")
    await auth_svc.register("eve@example.com", "Eve", "secret123")
    eve = await auth_svc.load_user_by_email("eve@example.com")
    reviewed = await admin_svc.review_registration(
        operator=admin,
        uid=eve["id"],
        decision="rejected",
        reason="non-business email",
    )
    assert reviewed["status"] == "rejected"
    assert reviewed["reject_reason"] == "non-business email"
    # Login now shows ACCOUNT_REJECTED with the reason.
    with pytest.raises(APIError) as exc:
        await auth_svc.password_login("eve@example.com", "secret123")
    assert exc.value.error_code == "ACCOUNT_REJECTED"
    assert "non-business email" in exc.value.message


@pytest.mark.asyncio
async def test_rejected_account_can_be_re_approved(isolated_data_root):
    """Admin may change their mind — a rejected account can be flipped back
    to active without re-registration."""
    await _prepare()
    admin = await auth_svc.load_user_by_email("admin")
    await auth_svc.register("frank@example.com", "Frank", "secret123")
    frank = await auth_svc.load_user_by_email("frank@example.com")
    await admin_svc.review_registration(operator=admin, uid=frank["id"], decision="rejected")
    reviewed = await admin_svc.review_registration(
        operator=admin, uid=frank["id"], decision="approved"
    )
    assert reviewed["status"] == "active"
    assert reviewed["reject_reason"] is None
    result = await auth_svc.password_login("frank@example.com", "secret123")
    assert result["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_cannot_review_active_account(isolated_data_root):
    """review_registration guards against flipping an already-active account."""
    await _prepare()
    admin = await auth_svc.load_user_by_email("admin")
    with pytest.raises(APIError) as exc:
        await admin_svc.review_registration(
            operator=admin, uid=admin["id"], decision="approved"
        )
    assert exc.value.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_resubmit_same_email_returns_pending_error(isolated_data_root):
    """If a user re-submits while still pending, they see a specific error
    (not the generic EMAIL_ALREADY_EXISTS) so the UI can prompt them to wait."""
    await _prepare()
    await auth_svc.register("grace@example.com", "Grace", "secret123")
    with pytest.raises(APIError) as exc:
        await auth_svc.register("grace@example.com", "Grace", "secret456")
    assert exc.value.error_code == "ACCOUNT_PENDING_APPROVAL"
