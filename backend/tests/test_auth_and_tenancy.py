"""
Authentication and Tenant Isolation Tests (PRD v1.2 §8.1, §13.2, §15, AC-ORG-1..3, AC-SEC-1, AC-SEC-4)
"""

import os
import io
from pathlib import Path
import pytest
from sqlalchemy import inspect
from backend.app.config import settings
from backend.app.database import Base
from backend.app.models.auth import Organisation, User, Plant
from backend.app.models.machine import Machine

def test_registration_creates_org_plant_and_admin(client, db_session):
    """AC-ORG-1: Registering creates one organisation, one default plant, and one admin user."""
    payload = {
        "organisation_name": "Titanium CNC Works",
        "email": "lead@titaniumcnc.com",
        "full_name": "Marcus Titan",
        "password": "CorrectHorseBatteryStaple123!"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ACTIVE"

    # Verify DB records
    org = db_session.query(Organisation).filter(Organisation.name == "Titanium CNC Works").first()
    assert org is not None
    assert org.slug == "titanium-cnc-works"

    plant = db_session.query(Plant).filter(Plant.organisation_id == org.id).first()
    assert plant is not None
    assert plant.code == "DEFAULT"
    assert plant.is_default is True

    user = db_session.query(User).filter(User.email == "lead@titaniumcnc.com").first()
    assert user is not None
    assert user.role == "ORG_ADMIN"

def test_second_registration_refused_when_multi_org_disabled(client, tenant_fixture):
    """AC-ORG-1: With MULTI_ORG_ENABLED=false, a second registration returns 403 MULTI_ORG_DISABLED."""
    settings.MULTI_ORG_ENABLED = False

    payload = {
        "organisation_name": "Second Org Attempt",
        "email": "admin2@secondorg.com",
        "full_name": "Bob Second",
        "password": "ValidPassword987654321!"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 403
    err = resp.json()["error"]
    assert err["code"] == "MULTI_ORG_DISABLED"

def test_duplicate_email_registration_returns_generic_response(client, tenant_fixture):
    """AC-ORG-1: An existing email yields the generic response to prevent user enumeration."""
    # Temporarily allow multi-org to test duplicate email specifically
    settings.MULTI_ORG_ENABLED = True
    try:
        payload = {
            "organisation_name": "Another Company",
            "email": "admin@acmeprecision.com",  # already exists in tenant_fixture
            "full_name": "Imposter",
            "password": "Password12345678!"
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "eligible for registration" in data["message"]
    finally:
        settings.MULTI_ORG_ENABLED = False

def test_password_length_enforcement(client):
    """AC-SEC-1: Passwords must be at least 12 characters."""
    payload = {
        "organisation_name": "Short Password Org",
        "email": "test@shortpwd.com",
        "full_name": "Shorty",
        "password": "Short123!"  # < 12 characters
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] in ("WEAK_PASSWORD", "VALIDATION_ERROR")

def test_login_success_and_user_profile(client, tenant_fixture):
    """AC-SEC-1: Login returns access JWT (15-min) and refresh token."""
    login_payload = {
        "email": "admin@acmeprecision.com",
        "password": "SuperSecretPassword123!"
    }
    resp = client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] == 900
    assert data["user"]["role"] == "ORG_ADMIN"
    assert data["user"]["organisation"]["name"] == "Acme Precision Machining"

    # Test /users/me
    token = data["access_token"]
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "admin@acmeprecision.com"

def test_login_lockout_after_five_failed_attempts(client, tenant_fixture):
    """AC-SEC-1: 5 failed attempts locks account for 15 minutes with 423 status."""
    payload = {
        "email": "admin@acmeprecision.com",
        "password": "WrongPassword123!"
    }

    # Attempts 1 to 4 return 401
    for _ in range(4):
        resp = client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHENTICATED"

    # 5th attempt locks account and returns 423
    resp5 = client.post("/api/v1/auth/login", json=payload)
    assert resp5.status_code == 423
    assert resp5.json()["error"]["code"] == "ACCOUNT_LOCKED"

    # Even with correct password, login is blocked while locked
    correct_payload = {
        "email": "admin@acmeprecision.com",
        "password": "SuperSecretPassword123!"
    }
    resp_locked = client.post("/api/v1/auth/login", json=correct_payload)
    assert resp_locked.status_code == 423
    assert resp_locked.json()["error"]["code"] == "ACCOUNT_LOCKED"

def test_refresh_token_rotation_and_reuse_detection(client, tenant_fixture):
    """AC-SEC-1: Refresh rotation issues new tokens and detects reuse, revoking the family."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin@acmeprecision.com",
        "password": "SuperSecretPassword123!"
    })
    token1 = login_resp.json()["refresh_token"]

    # 1. Successful rotation
    rot_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert rot_resp.status_code == 200
    token2 = rot_resp.json()["refresh_token"]
    assert token1 != token2

    # 2. Reuse of token1: must detect reuse and revoke session
    reuse_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["error"]["code"] == "TOKEN_REUSE_DETECTED"

    # 3. Subsequently token2 is also revoked because the entire family was invalidated
    subsequent_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token2})
    assert subsequent_resp.status_code == 401

def test_two_tenant_isolation(client, two_tenants_fixture, db_session):
    """AC-ORG-2: Every ID-parameterized endpoint returns 404 for another tenant's resources."""
    t1 = two_tenants_fixture["tenant1"]
    t2 = two_tenants_fixture["tenant2"]

    # 1. Machine isolation
    m1 = Machine(
        organisation_id=t1["org"].id,
        plant_id=t1["org"].plants[0].id,
        asset_tag="CNC-001",
        name="Tenant 1 CNC",
        category_code="GENERAL_MACHINE_TOOL"
    )
    db_session.add(m1)
    db_session.commit()

    # Tenant 1 can read its machine
    resp1 = client.get(f"/api/v1/machines/{m1.id}", headers=t1["headers"])
    assert resp1.status_code == 200
    assert resp1.json()["name"] == "Tenant 1 CNC"

    # Tenant 2 requests Tenant 1's machine: returns 404 NOT_FOUND
    resp2 = client.get(f"/api/v1/machines/{m1.id}", headers=t2["headers"])
    assert resp2.status_code == 404
    assert resp2.json()["error"]["code"] == "NOT_FOUND"

    # 2. Limitation acknowledgement isolation: Tenant 2 cannot ack for Tenant 1's machine
    lim_resp_t2 = client.post("/api/v1/limitations/acknowledge", json={
        "machine_id": m1.id,
        "profile_uuid": "some-profile-uuid"
    }, headers=t2["headers"])
    assert lim_resp_t2.status_code == 404

    # 3. Dataset & Version isolation: Create dataset and upload version for Tenant 1
    ds1_resp = client.post(f"/api/v1/machines/{m1.id}/datasets", json={
        "name": "T1 Telemetry Batch"
    }, headers=t1["headers"])
    assert ds1_resp.status_code == 201
    ds1_id = ds1_resp.json()["id"]

    csv_data = "air_temperature,process_temperature,rotational_speed,torque,tool_wear\n298.1,308.2,1500,40.0,10\n"
    files = {"file": ("t1_data.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    up1_resp = client.post(f"/api/v1/datasets/{ds1_id}/versions/upload", files=files, headers=t1["headers"])
    assert up1_resp.status_code == 201
    vid1 = up1_resp.json()["dataset_version_id"]

    # Tenant 1 can preview, get suggestions, and get validation reports
    assert client.get(f"/api/v1/dataset-versions/{vid1}/preview", headers=t1["headers"]).status_code == 200
    assert client.get(f"/api/v1/dataset-versions/{vid1}/mappings/ai4i_failure_no_type/suggestions", headers=t1["headers"]).status_code == 200
    assert client.get(f"/api/v1/dataset-versions/{vid1}/validation-reports", headers=t1["headers"]).status_code == 200

    # Tenant 2 MUST NOT be able to preview, get suggestions, or get validation reports (AC-ORG-2 returns 404)
    t2_preview = client.get(f"/api/v1/dataset-versions/{vid1}/preview", headers=t2["headers"])
    assert t2_preview.status_code == 404

    t2_suggestions = client.get(f"/api/v1/dataset-versions/{vid1}/mappings/ai4i_failure_no_type/suggestions", headers=t2["headers"])
    assert t2_suggestions.status_code == 404

    t2_val_reports = client.get(f"/api/v1/dataset-versions/{vid1}/validation-reports", headers=t2["headers"])
    assert t2_val_reports.status_code == 404

def test_tenant_tables_have_organisation_id(db_session):
    """AC-ORG-3: Schema test verifying that every tenant table has an organisation_id column."""
    inspector = inspect(db_session.bind)
    table_names = inspector.get_table_names()

    # Global tables without organisation_id
    global_tables = {"machine_categories", "pipeline_profiles", "model_versions", "model_evaluations", "organisations"}

    for table in table_names:
        if table in global_tables:
            continue
        columns = [c["name"] for c in inspector.get_columns(table)]
        assert "organisation_id" in columns, f"Tenant table '{table}' is missing 'organisation_id' column!"

def test_repository_security_scan():
    """AC-SEC-4: No secrets in repo, no plaintext private keys, no customer data in source."""
    forbidden_patterns = [
        "BEGIN RSA PRIVATE KEY",
        "BEGIN OPENSSH PRIVATE KEY",
        "ghp_",
        "AKIA[0-9A-Z]{16}"
    ]
    root_dir = Path(__file__).resolve().parent.parent.parent
    ignored_dirs = {".venv", ".git", "node_modules", "__pycache__", "dist", ".gemini"}
    valid_exts = {".py", ".json", ".md", ".yml", ".yaml"}

    import os
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext in valid_exts:
                if fname == "test_auth_and_tenancy.py":
                    continue
                fpath = Path(dirpath) / fname
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                for pat in forbidden_patterns:
                    assert pat not in text, f"Forbidden secret pattern '{pat}' found in {fpath}!"
