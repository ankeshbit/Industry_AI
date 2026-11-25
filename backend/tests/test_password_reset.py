"""
Automated Test Suite for INDUSTRIA AI Forgot Password & Secure Password Reset
Covers:
1. Forgot-password request for registered account.
2. Forgot-password request for unknown account.
3. Generic response consistency (enumeration prevention).
4. Invalid email format rejection (422).
5. Invalid reset token rejection (400).
6. Expired reset token rejection (400).
7. Successful password reset.
8. Reuse of consumed token rejection (400).
9. Password policy enforcement (< 12 characters rejected).
10. Old password rejection after reset.
11. New password authentication success.
12. IP / Email rate limiting (429).
13. Existing login and registration regression verification.
"""

import pytest
import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import status

from backend.app.models.auth import User, PasswordResetToken, RefreshToken
from backend.app.services.email_service import (
    clear_dev_outbox,
    get_dev_outbox,
    get_latest_reset_link_for_email,
)
from backend.app.services.auth_service import (
    clear_reset_rate_limits,
    hash_password,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure outbox and rate limits are clean before and after each test."""
    clear_dev_outbox()
    clear_reset_rate_limits()
    yield
    clear_dev_outbox()
    clear_reset_rate_limits()


def test_01_forgot_password_registered_account(client, tenant_fixture, db_session):
    """1. Forgot-password request for a registered account generates a hashed token and sends email."""
    user = tenant_fixture["user"]
    email = user.email

    response = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert data["status"] == "SENT"
    assert "password reset link has been sent" in data["message"].lower()

    # Verify a token record was created in the database
    token_record = db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
    assert token_record is not None
    assert token_record.is_consumed is False
    assert token_record.expires_at > datetime.utcnow()
    assert len(token_record.token_hash) == 64  # SHA-256 hash length

    # Verify email was captured in dev outbox
    outbox = get_dev_outbox()
    assert len(outbox) == 1
    assert outbox[0]["to_email"] == email
    assert "token=" in outbox[0]["reset_url"] or "reset_token=" in outbox[0]["reset_url"]


def test_02_forgot_password_unknown_account(client, db_session):
    """2. Forgot-password request for an unknown account does not reveal lack of registration."""
    unknown_email = "nonexistent.engineer@nowhere-plant.io"

    response = client.post("/api/v1/auth/forgot-password", json={"email": unknown_email})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "SENT"

    # Verify NO token was created in DB and NO email was sent
    tokens = db_session.query(PasswordResetToken).all()
    assert len(tokens) == 0
    assert len(get_dev_outbox()) == 0


def test_03_generic_response_consistency(client, tenant_fixture):
    """3. Verify generic response message and schema are identical for registered vs unknown emails."""
    registered_email = tenant_fixture["user"].email
    unknown_email = "random-unregistered-account-9876@acme.com"

    res_registered = client.post("/api/v1/auth/forgot-password", json={"email": registered_email})
    res_unknown = client.post("/api/v1/auth/forgot-password", json={"email": unknown_email})

    assert res_registered.status_code == res_unknown.status_code
    assert res_registered.json() == res_unknown.json()
    assert res_registered.json() == {
        "message": "If that email address is registered, a password reset link has been sent.",
        "status": "SENT"
    }


def test_04_invalid_email_format_rejection(client):
    """4. Verify invalid email formats are rejected with 422 Unprocessable Entity."""
    invalid_emails = [
        "not-an-email",
        "missingatsign.com",
        "@nodomain.com",
        "spaces in@address.org",
    ]

    for bad_email in invalid_emails:
        res = client.post("/api/v1/auth/forgot-password", json={"email": bad_email})
        assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_05_invalid_reset_token_rejection(client):
    """5. Verify nonexistent / invalid reset token is rejected on verify and reset."""
    fake_token = "completely_bogus_token_1234567890_abcdef"

    # Verify endpoint
    v_res = client.get(f"/api/v1/auth/verify-reset-token?token={fake_token}")
    assert v_res.status_code == status.HTTP_400_BAD_REQUEST
    assert v_res.json()["error"]["code"] == "INVALID_OR_CONSUMED_TOKEN"

    # Reset endpoint
    r_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": fake_token, "new_password": "NewStrongPassword2026!"}
    )
    assert r_res.status_code == status.HTTP_400_BAD_REQUEST
    assert r_res.json()["error"]["code"] == "INVALID_OR_CONSUMED_TOKEN"


def test_06_expired_reset_token_rejection(client, tenant_fixture, db_session):
    """6. Verify expired reset token is rejected."""
    user = tenant_fixture["user"]
    raw_token = "expired_raw_token_for_testing_1234567"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Create an expired token record (5 minutes ago)
    expired_record = PasswordResetToken(
        organisation_id=user.organisation_id,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() - timedelta(minutes=5),
        is_consumed=False
    )
    db_session.add(expired_record)
    db_session.commit()

    # Pre-validation check
    v_res = client.get(f"/api/v1/auth/verify-reset-token?token={raw_token}")
    assert v_res.status_code == status.HTTP_400_BAD_REQUEST
    assert v_res.json()["error"]["code"] == "EXPIRED_TOKEN"

    # Reset attempt
    r_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "NewStrongPassword2026!"}
    )
    assert r_res.status_code == status.HTTP_400_BAD_REQUEST
    assert r_res.json()["error"]["code"] == "EXPIRED_TOKEN"


def test_07_successful_password_reset(client, tenant_fixture, db_session):
    """7. Verify full successful password reset workflow."""
    user = tenant_fixture["user"]
    email = user.email

    # Request reset
    req_res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert req_res.status_code == status.HTTP_200_OK

    # Extract token from dev outbox link
    reset_link = get_latest_reset_link_for_email(email)
    assert reset_link is not None
    # Token param
    token = reset_link.split("token=")[-1].split("&")[0]

    # Pre-validate token
    val_res = client.get(f"/api/v1/auth/verify-reset-token?token={token}")
    assert val_res.status_code == status.HTTP_200_OK
    assert val_res.json()["valid"] is True

    # Submit new password
    new_password = "BrandNewValidPassword2026!#"
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password}
    )
    assert reset_res.status_code == status.HTTP_200_OK
    assert reset_res.json()["status"] == "SUCCESS"

    # Verify token record is now consumed
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    rec = db_session.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    assert rec.is_consumed is True
    assert rec.consumed_at is not None


def test_08_consumed_token_cannot_be_reused(client, tenant_fixture, db_session):
    """8. Verify consumed token cannot be reused for a second password reset."""
    user = tenant_fixture["user"]
    email = user.email

    # Request and perform reset
    client.post("/api/v1/auth/forgot-password", json={"email": email})
    reset_link = get_latest_reset_link_for_email(email)
    token = reset_link.split("token=")[-1].split("&")[0]

    # First reset succeeds
    res1 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "InitialNewPassword2026!"}
    )
    assert res1.status_code == status.HTTP_200_OK

    # Attempt second reset with same token
    res2 = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "SecondNewPassword2026!"}
    )
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    assert res2.json()["error"]["code"] == "INVALID_OR_CONSUMED_TOKEN"


def test_09_password_policy_enforcement(client, tenant_fixture):
    """9. Verify password policy requires minimum 12 characters."""
    user = tenant_fixture["user"]
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    reset_link = get_latest_reset_link_for_email(user.email)
    token = reset_link.split("token=")[-1].split("&")[0]

    # Less than 12 characters
    res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "short123"}
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_10_and_11_old_password_rejected_and_new_password_authenticates(client, tenant_fixture):
    """10 & 11. Old password is confirmed non-functional; new password authenticates and issues JWT."""
    user = tenant_fixture["user"]
    email = user.email
    old_password = "SuperSecretPassword123!"
    new_password = "CompletelyNewPassword2026!#"

    # Request and perform reset
    client.post("/api/v1/auth/forgot-password", json={"email": email})
    reset_link = get_latest_reset_link_for_email(email)
    token = reset_link.split("token=")[-1].split("&")[0]

    res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password}
    )
    assert res.status_code == status.HTTP_200_OK

    # 10: Old password fails
    old_login = client.post("/api/v1/auth/login", json={"email": email, "password": old_password})
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED

    # 11: New password succeeds
    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == status.HTTP_200_OK
    login_data = new_login.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data

    # Use access token to fetch current user profile
    auth_header = {"Authorization": f"Bearer {login_data['access_token']}"}
    me_res = client.get("/api/v1/auth/users/me", headers=auth_header)
    assert me_res.status_code == status.HTTP_200_OK
    assert me_res.json()["email"] == email


def test_12_rate_limiting_prevents_abuse(client, tenant_fixture):
    """12. Verify IP rate limit stops rapid repeated reset attempts."""
    email = tenant_fixture["user"].email

    # Limit is 5 per 15 minutes per IP
    for i in range(5):
        res = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
            headers={"X-Forwarded-For": "198.51.100.42"}
        )
        assert res.status_code == status.HTTP_200_OK

    # 6th attempt should be rate limited
    blocked_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
        headers={"X-Forwarded-For": "198.51.100.42"}
    )
    assert blocked_res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert blocked_res.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_13_existing_auth_flows_unaffected(client, db_session):
    """13. Verify standard login and registration continue functioning without regression."""
    # Ensure fresh state
    new_email = "new.engineer@acme-industrial.com"
    pwd = "ValidEngineerPassword2026!"

    # Registration
    reg_res = client.post("/api/v1/auth/register", json={
        "organisation_name": "Acme Industrial Plants",
        "email": new_email,
        "full_name": "Sam Engineer",
        "password": pwd
    })
    assert reg_res.status_code == status.HTTP_201_CREATED

    # Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": new_email,
        "password": pwd
    })
    assert login_res.status_code == status.HTTP_200_OK
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Token Refresh
    refresh_res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"]
    })
    assert refresh_res.status_code == status.HTTP_200_OK
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens

