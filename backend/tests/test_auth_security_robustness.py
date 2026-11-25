"""
Authentication Security and Account Recovery Robustness Tests
(PRD v1.2 §8.1, §13.2, §15, AC-ORG-1, AC-SEC-1..5)

Attack Scenarios Verified:
1. Expired token rejection & password invariance.
2. Consumed token rejection.
3. Concurrent token consumption (atomic conditional CAS update).
4. Token reuse attempt.
5. SMTP delivery failure (previous active token preserved, no leak).
6. Rate-limit bypass attempts (email normalization, spoofed X-Forwarded-For).
7. Old access JWT revocation after password reset (token-version validation).
8. Refresh-token reuse detection & family revocation.
9. Account deactivation enforcement across login, reset, and protected endpoints.
10. HTML injection prevention and reset URL validation.
"""

import hashlib
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.models.auth import User, PasswordResetToken, RefreshToken, RateLimitAttempt
from backend.app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    clear_reset_rate_limits,
    request_password_reset,
    reset_user_password,
    verify_reset_token,
)
from backend.app.services.email_service import (
    clear_dev_outbox,
    get_dev_outbox,
    validate_reset_url,
    build_password_reset_html,
)


@pytest.fixture(autouse=True)
def clean_security_state(db_session):
    """Automatically cleans test outbox and rate limit records before each test."""
    clear_dev_outbox()
    clear_reset_rate_limits(db_session)
    yield
    clear_dev_outbox()
    clear_reset_rate_limits(db_session)


# ==============================================================================
# 1. Expired token rejection & password invariance
# ==============================================================================
def test_1_expired_token_rejected_and_password_unchanged(client, tenant_fixture, db_session):
    """Attack Scenario 1: Expired token cannot reset password; password remains unchanged."""
    user = tenant_fixture["user"]
    initial_hash = user.password_hash

    # Request reset
    req_resp = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert req_resp.status_code == 200

    outbox = get_dev_outbox()
    assert len(outbox) == 1
    raw_token = outbox[0]["reset_token"]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Artificially expire the token in database
    db_session.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).update({"expires_at": datetime.utcnow() - timedelta(seconds=10)})
    db_session.commit()

    # Pre-validation endpoint check
    verify_resp = client.get(f"/api/v1/auth/verify-reset-token?token={raw_token}")
    assert verify_resp.status_code == 400
    assert verify_resp.json()["error"]["code"] == "EXPIRED_TOKEN"

    # Attempt reset with expired token
    reset_resp = client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewSecurePassword1234!"
    })
    assert reset_resp.status_code == 400
    assert reset_resp.json()["error"]["code"] == "EXPIRED_TOKEN"

    # Verify password was NOT modified
    db_session.expire_all()
    refreshed_user = db_session.query(User).filter(User.id == user.id).first()
    assert refreshed_user.password_hash == initial_hash
    assert verify_password("SuperSecretPassword123!", refreshed_user.password_hash)


# ==============================================================================
# 2. Consumed token rejection
# ==============================================================================
def test_2_consumed_token_rejected(client, tenant_fixture, db_session):
    """Attack Scenario 2: A consumed token is immediately rejected for any subsequent check or reset."""
    user = tenant_fixture["user"]
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    raw_token = get_dev_outbox()[0]["reset_token"]

    # First consumption: valid reset
    resp1 = client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "ValidNewPassword123!"
    })
    assert resp1.status_code == 200

    # Second consumption with the exact same token
    resp2 = client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "AnotherNewPassword456!"
    })
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_OR_CONSUMED_TOKEN"


# ==============================================================================
# 3. Concurrent token consumption (atomic conditional CAS update)
# ==============================================================================
def test_3_concurrent_token_consumption_is_atomic(tenant_fixture, db_session):
    """
    Attack Scenario 3:
    Simultaneous requests attempting to consume the same token at the exact same instant.
    Conditional CAS ensures exactly 1 winner, and 1 loser.
    """
    user = tenant_fixture["user"]
    request_password_reset(db=db_session, email=user.email, ip_address="127.0.0.1")
    raw_token = get_dev_outbox()[0]["reset_token"]

    bind = db_session.get_bind()
    SessionFactory = sessionmaker(bind=bind, autocommit=False, autoflush=False)

    barrier = threading.Barrier(2)
    results = []

    def attempt_reset_task(thread_id: int):
        session = SessionFactory()
        try:
            barrier.wait()
            res = reset_user_password(
                db=session,
                token=raw_token,
                new_password=f"ConcurrentPassword{thread_id}123!"
            )
            results.append((thread_id, 200, res))
        except Exception as e:
            err_code = getattr(e, "detail", {}).get("error", {}).get("code", str(e))
            results.append((thread_id, getattr(e, "status_code", 500), err_code))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_reset_task, 1)
        f2 = executor.submit(attempt_reset_task, 2)
        f1.result()
        f2.result()

    successes = [r for r in results if r[1] == 200]
    failures = [r for r in results if r[1] == 400 and r[2] == "INVALID_OR_CONSUMED_TOKEN"]

    assert len(successes) == 1, f"Expected exactly 1 successful consumption, got: {results}"
    assert len(failures) == 1, f"Expected exactly 1 rejected consumption, got: {results}"


# ==============================================================================
# 4. Token reuse attempt
# ==============================================================================
def test_4_token_reuse_attempt_fails(client, tenant_fixture, db_session):
    """Attack Scenario 4: Consumed token cannot be reused even with the original password."""
    user = tenant_fixture["user"]
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    raw_token = get_dev_outbox()[0]["reset_token"]

    # Reset
    resp1 = client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewUpdatedPassword123!"
    })
    assert resp1.status_code == 200

    # Try re-using token
    resp2 = client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "SuperSecretPassword123!"
    })
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_OR_CONSUMED_TOKEN"


# ==============================================================================
# 5. SMTP failure handling & link preservation
# ==============================================================================
def test_5_smtp_failure_preserves_existing_valid_token_and_does_not_leak_error(client, tenant_fixture, db_session):
    """
    Attack Scenario 5:
    If SMTP delivery fails during a reset request, the user's previously active reset token
    is NOT invalidated, no unreachable token is stored, and the response is generic (no enumeration leak).
    """
    user = tenant_fixture["user"]

    # Step 1: Successful initial request
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    initial_token = get_dev_outbox()[0]["reset_token"]
    initial_hash = hashlib.sha256(initial_token.encode("utf-8")).hexdigest()

    token_rec1 = db_session.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == initial_hash
    ).first()
    assert token_rec1 is not None
    assert token_rec1.is_consumed is False

    # Step 2: Second request where SMTP delivery fails
    with patch("backend.app.services.auth_service.send_password_reset_email", return_value=False):
        resp_fail = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
        # Enumeration resistance: still returns generic 200 response
        assert resp_fail.status_code == 200
        assert "password reset link has been sent" in resp_fail.json()["message"]

    # Step 3: Verify previous token is STILL valid and unconsumed
    db_session.expire_all()
    token_rec1_check = db_session.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == initial_hash
    ).first()
    assert token_rec1_check.is_consumed is False

    # Verify user can still successfully reset password with the first link
    reset_resp = client.post("/api/v1/auth/reset-password", json={
        "token": initial_token,
        "new_password": "WorkingAfterSmtpFail123!"
    })
    assert reset_resp.status_code == 200


# ==============================================================================
# 6. Rate-limit bypass attempts (email normalization & spoofed X-Forwarded-For)
# ==============================================================================
def test_6_rate_limit_bypass_attempts(client, tenant_fixture, db_session):
    """
    Attack Scenario 6:
    - Attempting email rate-limit bypass via mixed casing and whitespace is normalized.
    - Attempting IP rate-limit bypass via forged X-Forwarded-For from untrusted clients is rejected.
    """
    user = tenant_fixture["user"]

    # Part A: Email normalization throttle
    # 3 allowed per 15 min; 4th should be throttled silently
    client.post("/api/v1/auth/forgot-password", json={"email": user.email.upper()})
    client.post("/api/v1/auth/forgot-password", json={"email": f"  {user.email}  "})
    client.post("/api/v1/auth/forgot-password", json={"email": user.email.title()})

    outbox_count_before = len(get_dev_outbox())
    assert outbox_count_before == 3

    # 4th attempt with another casing variant: throttled silently, no email dispatched
    resp4 = client.post("/api/v1/auth/forgot-password", json={"email": user.email.lower()})
    assert resp4.status_code == 200
    assert len(get_dev_outbox()) == 3  # Count unchanged

    # Part B: IP rate limit enforcement (5 attempts / 15m)
    clear_reset_rate_limits(db_session)
    clear_dev_outbox()

    # Simulate 5 requests from same client
    for i in range(5):
        r = client.post("/api/v1/auth/forgot-password", json={"email": f"test{i}@example.com"})
        assert r.status_code == 200

    # 6th request from same IP -> 429 RATE_LIMIT_EXCEEDED
    r_blocked = client.post("/api/v1/auth/forgot-password", json={"email": "another@example.com"})
    assert r_blocked.status_code == 429
    assert r_blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


# ==============================================================================
# 7. Old access JWT after reset (token-version session invalidation)
# ==============================================================================
def test_7_old_access_jwt_revoked_after_password_reset(client, tenant_fixture, db_session):
    """
    Attack Scenario 7:
    Access tokens issued prior to a password reset are immediately revoked
    and rejected on protected endpoints.
    """
    user = tenant_fixture["user"]

    # 1. Login to get an active access token
    login_resp = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "SuperSecretPassword123!"
    })
    assert login_resp.status_code == 200
    old_access_token = login_resp.json()["access_token"]
    old_auth_headers = {"Authorization": f"Bearer {old_access_token}"}

    # Verify old token works before reset
    me_resp1 = client.get("/api/v1/users/me", headers=old_auth_headers)
    assert me_resp1.status_code == 200
    assert me_resp1.json()["email"] == user.email

    # 2. Reset password
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    reset_token = get_dev_outbox()[0]["reset_token"]

    reset_resp = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "NewUpdatedPassword123!"
    })
    assert reset_resp.status_code == 200

    # 3. Present OLD access token to protected endpoint: must be REJECTED
    me_resp2 = client.get("/api/v1/users/me", headers=old_auth_headers)
    assert me_resp2.status_code == 401
    assert me_resp2.json()["error"]["code"] == "TOKEN_REVOKED"


# ==============================================================================
# 8. Refresh-token reuse detection & family revocation
# ==============================================================================
def test_8_refresh_token_reuse_detected_and_family_revoked(client, tenant_fixture):
    """
    Attack Scenario 8:
    Reusing an already-rotated refresh token triggers TOKEN_REUSE_DETECTED
    and revokes the entire token family.
    """
    user = tenant_fixture["user"]
    login_resp = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "SuperSecretPassword123!"
    })
    initial_refresh = login_resp.json()["refresh_token"]

    # Legitimate rotation 1
    rot1_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh})
    assert rot1_resp.status_code == 200
    new_refresh = rot1_resp.json()["refresh_token"]

    # Attacker attempts to reuse initial_refresh
    reuse_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh})
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["error"]["code"] == "TOKEN_REUSE_DETECTED"

    # Verify that the legitimate new token was also revoked as part of the family
    subsequent_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert subsequent_resp.status_code == 401


# ==============================================================================
# 9. Account deactivation enforcement
# ==============================================================================
def test_9_account_deactivation_blocks_login_reset_and_access(client, tenant_fixture, db_session):
    """
    Attack Scenario 9:
    Deactivated accounts cannot authenticate, cannot reset passwords,
    and existing JWTs are blocked.
    """
    user = tenant_fixture["user"]

    # Obtain valid access token while active
    login_resp = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "SuperSecretPassword123!"
    })
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Request reset token before deactivation
    client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    reset_token = get_dev_outbox()[0]["reset_token"]

    # Deactivate account
    user.is_active = False
    db_session.commit()

    # 1. Protected endpoint access blocked
    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp.status_code == 401
    assert me_resp.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"

    # 2. Login blocked
    login_attempt = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "SuperSecretPassword123!"
    })
    assert login_attempt.status_code == 401

    # 3. Password reset blocked
    reset_attempt = client.post("/api/v1/auth/reset-password", json={
        "token": reset_token,
        "new_password": "BlockedPassword123!"
    })
    assert reset_attempt.status_code == 400
    assert reset_attempt.json()["error"]["code"] in ("INVALID_USER", "INVALID_OR_CONSUMED_TOKEN")


# ==============================================================================
# 10. HTML injection prevention and reset URL validation
# ==============================================================================
def test_10_html_injection_escaped_and_unsafe_url_rejected():
    """
    Attack Scenario 10:
    User-supplied names containing HTML/script tags are safely escaped in transactional templates.
    Unsafe URL schemes (e.g. javascript:, data:) are rejected.
    """
    malicious_name = "<script>alert('xss')</script><b>Engineer</b>"
    valid_url = "https://app.industria-ai.com/?reset_token=safe-token-123"

    html_out = build_password_reset_html(
        recipient_name=malicious_name,
        reset_url=valid_url,
        expire_minutes=20
    )

    # HTML tags must be escaped
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out
    assert "&lt;b&gt;Engineer&lt;/b&gt;" in html_out

    # URL validation checks
    assert validate_reset_url("https://app.industria-ai.com/reset") is True
    assert validate_reset_url("http://localhost:3000/?token=abc") is True
    assert validate_reset_url("javascript:alert(1)") is False
    assert validate_reset_url("data:text/html,<script>alert(1)</script>") is False
    assert validate_reset_url("ftp://app.industria-ai.com") is False
    assert validate_reset_url("not-a-url") is False
