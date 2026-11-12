"""
Unit and Integration Tests for Supabase Authentication (Hybrid Mode)
Verifies:
1. /api/v1/auth/config endpoint
2. Supabase JWT token verification with local secret
3. Supabase user auto-provisioning and organisation creation
4. Protected endpoint access with Supabase bearer token
5. Rejection of forged / invalid Supabase tokens
"""

import time
import uuid
from datetime import datetime, timedelta
import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import get_db, SessionLocal
from backend.app.models.auth import User, Organisation

client = TestClient(app)

@pytest.fixture
def mock_supabase_env(monkeypatch):
    test_secret = "test-supabase-jwt-secret-xyz-1234567890"
    test_url = "https://example-project.supabase.co"
    test_anon = "test-anon-key-abc"
    monkeypatch.setattr(settings, "SUPABASE_URL", test_url)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", test_secret)
    monkeypatch.setattr(settings, "SUPABASE_ANON_KEY", test_anon)
    return {
        "url": test_url,
        "jwt_secret": test_secret,
        "anon_key": test_anon
    }

def test_auth_config_endpoint(mock_supabase_env):
    """Verifies that /auth/config reports the active provider and Supabase settings."""
    res = client.get("/api/v1/auth/config")
    assert res.status_code == 200
    data = res.json()
    assert data["auth_provider"] == "supabase"
    assert data["supabase_url"] == mock_supabase_env["url"]
    assert data["supabase_anon_key"] == mock_supabase_env["anon_key"]

def test_supabase_token_auto_provisioning_and_auth(mock_supabase_env):
    """Verifies that a valid Supabase JWT authenticates and provisions user in DB."""
    unique_id = uuid.uuid4().hex[:8]
    sb_uid = str(uuid.uuid4())
    sb_email = f"engineer-{unique_id}@supabase-test.com"
    sb_org_name = f"Supabase Robotics {unique_id}"

    # Construct a Supabase Auth JWT
    now_ts = int(time.time())
    payload = {
        "sub": sb_uid,
        "email": sb_email,
        "role": "authenticated",
        "aud": "authenticated",
        "iss": f"{mock_supabase_env['url']}/auth/v1",
        "iat": now_ts,
        "exp": now_ts + 3600,
        "user_metadata": {
            "full_name": "Test Supabase Engineer",
            "organisation_name": sb_org_name
        }
    }

    token = jwt.encode(payload, mock_supabase_env["jwt_secret"], algorithm="HS256")

    # Call protected /users/me
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/users/me", headers=headers)
    assert res.status_code == 200, res.text
    user_data = res.json()
    assert user_data["email"] == sb_email
    assert user_data["full_name"] == "Test Supabase Engineer"
    assert "organisation" in user_data
    if settings.MULTI_ORG_ENABLED:
        assert user_data["organisation"]["name"] == sb_org_name
    else:
        assert user_data["organisation"]["name"] is not None
        assert user_data["organisation"]["id"] is not None

    # Verify user exists in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == sb_email).first()
        assert user is not None
        assert user.email == sb_email
        assert user.password_hash == "SUPABASE_MANAGED_AUTH"
        assert user.organisation is not None
    finally:
        db.close()

def test_invalid_supabase_token_rejected(mock_supabase_env):
    """Verifies that a token signed with an invalid secret is rejected."""
    wrong_secret = "completely-wrong-secret-signature"
    now_ts = int(time.time())
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "hacker@evil.com",
        "aud": "authenticated",
        "exp": now_ts + 3600
    }
    forged_token = jwt.encode(payload, wrong_secret, algorithm="HS256")
    res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"
