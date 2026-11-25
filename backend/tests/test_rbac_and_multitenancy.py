"""
Comprehensive RBAC and Multi-Tenancy Security Test Suite (PRD v1.2 §5.1, §8.1, AC-ORG-2, AC-ORG-4, AC-ORG-5, AC-ORG-8)
Tests authorization, tenant isolation, IDOR defenses, role restrictions, and account lifecycle.
"""

import io
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.models.auth import Organisation, User, Plant
from backend.app.models.machine import Machine
from backend.app.models.dataset import Dataset, DatasetVersion, ColumnMapping, ValidationReport
from backend.app.models.compatibility import CompatibilityCheck, PipelineProfile
from backend.app.models.analysis import AnalysisResult
from backend.app.models.job import Job
from backend.app.services.auth_service import hash_password, create_access_token


SAMPLE_CSV = (
    "UDI,Product ID,Type,Air temperature [K],Process temperature [K],Rotational speed [rpm],Torque [Nm],Tool wear [min],Machine failure\n"
    "1,M14860,M,298.1,308.6,1551,42.8,0,0\n"
    "2,L47181,L,298.2,308.7,1408,46.3,3,0\n"
)

VALID_MAPPINGS = {
    "air_temperature": {"column": "Air temperature [K]", "unit": "K"},
    "process_temperature": {"column": "Process temperature [K]", "unit": "K"},
    "rotational_speed": {"column": "Rotational speed [rpm]", "unit": "rpm"},
    "torque": {"column": "Torque [Nm]", "unit": "Nm"},
    "tool_wear": {"column": "Tool wear [min]", "unit": "min"}
}

# Precompute Argon2 hash once at module level to avoid re-hashing per fixture
PRECOMPUTED_HASH = hash_password("SuperSecretSecurePassword123!")


@pytest.fixture(scope="function")
def rbac_setup(db_session):
    """
    Sets up an organisation with one user for each of the four roles:
    ORG_ADMIN, ENGINEER, ANALYST, VIEWER.
    Also provisions a baseline machine and dataset.
    """
    org = Organisation(name="AeroDynamics Corp", slug="aerodynamics-corp", status="ACTIVE")
    db_session.add(org)
    db_session.flush()

    plant = Plant(organisation_id=org.id, code="DEFAULT", name="Main Facility", is_default=True)
    db_session.add(plant)
    db_session.flush()

    roles = ["ORG_ADMIN", "ENGINEER", "ANALYST", "VIEWER"]
    users = {}
    headers = {}

    for r in roles:
        u = User(
            organisation_id=org.id,
            email=f"{r.lower()}@aerodynamics.com",
            full_name=f"{r.replace('_', ' ').title()} User",
            password_hash=PRECOMPUTED_HASH,
            role=r,
            is_active=True,
            token_version=1
        )
        db_session.add(u)
        db_session.flush()
        users[r] = u
        token, _ = create_access_token(u.id, org.id, r, token_version=1)
        headers[r] = {"Authorization": f"Bearer {token}"}

    # Machine created by ORG_ADMIN
    machine = Machine(
        organisation_id=org.id,
        plant_id=plant.id,
        asset_tag="MILL-001",
        name="CNC Milling Machine 01",
        category_code="GENERAL_MACHINE_TOOL"
    )
    db_session.add(machine)
    db_session.flush()

    # Dataset created by ORG_ADMIN
    dataset = Dataset(
        organisation_id=org.id,
        machine_id=machine.id,
        name="Telemetry Baseline 2026",
        dataset_type="TABULAR_OPERATING_STATE",
        provenance="CUSTOMER",
        status="ACTIVE",
        created_by=users["ORG_ADMIN"].id
    )
    db_session.add(dataset)
    db_session.flush()

    # Version
    version = DatasetVersion(
        organisation_id=org.id,
        dataset_id=dataset.id,
        version_no=1,
        file_kind="CSV",
        original_filename="telemetry_baseline.csv",
        storage_key=f"datasets/{dataset.id}/v1.csv",
        size_bytes=len(SAMPLE_CSV.encode()),
        sha256="dummy_sha256_hash",
        row_count=2,
        column_count=9,
        status="PROCESSED"
    )
    db_session.add(version)
    db_session.flush()

    # Mapping
    mapping = ColumnMapping(
        organisation_id=org.id,
        dataset_version_id=version.id,
        profile_id="ai4i_failure_no_type",
        mapping_version=1,
        mappings=VALID_MAPPINGS
    )
    db_session.add(mapping)
    db_session.flush()

    # Report
    report = ValidationReport(
        organisation_id=org.id,
        dataset_version_id=version.id,
        mapping_id=mapping.id,
        quality_score=98.5,
        quality_components={"S_complete": 1.0, "S_valid": 1.0, "S_unique": 1.0, "S_consistent": 1.0, "S_outlier": 0.95},
        checks=[],
        preview=[{"UDI": 1, "Product ID": "M14860"}]
    )
    db_session.add(report)
    db_session.flush()

    # Profile
    profile = db_session.query(PipelineProfile).filter(PipelineProfile.profile_id == "ai4i_failure_no_type").first()

    # Check
    check = CompatibilityCheck(
        organisation_id=org.id,
        dataset_version_id=version.id,
        machine_id=machine.id,
        profile_uuid=profile.id,
        mapping_id=mapping.id,
        status="COMPATIBLE",
        applicability_level="FULLY_APPLICABLE",
        reliability_tier="TIER_1_REFERENCE_COMPLIANT",
        reasons=[],
        inputs_hash="test_inputs_hash_val"
    )
    db_session.add(check)
    db_session.flush()

    # Job
    job = Job(
        organisation_id=org.id,
        job_type="RUN_ANALYSIS",
        status="SUCCEEDED",
        payload={"compatibility_check_id": check.id},
        created_by=users["ORG_ADMIN"].id
    )
    db_session.add(job)
    db_session.flush()

    # Analysis Result
    analysis = AnalysisResult(
        organisation_id=org.id,
        machine_id=machine.id,
        dataset_version_id=version.id,
        job_id=job.id,
        compatibility_check_id=check.id,
        profile_uuid=profile.id,
        pipeline="A",
        configuration="NO_TYPE",
        result_version=1,
        is_latest=True,
        applicability_level="FULLY_APPLICABLE",
        reliability_tier="TIER_1_REFERENCE_COMPLIANT",
        summary={"total_rows": 2, "predicted_failures": 0, "risk_distribution": {"LOW": 2, "MEDIUM": 0, "HIGH": 0}},
        top_rows=[{"row_index": 1, "failure_probability": 0.002, "risk_class": "LOW"}],
        ood_summary={},
        limitations=[]
    )
    db_session.add(analysis)
    db_session.commit()

    return {
        "org": org,
        "plant": plant,
        "users": users,
        "headers": headers,
        "machine": machine,
        "dataset": dataset,
        "version": version,
        "mapping": mapping,
        "check": check,
        "analysis": analysis,
        "job": job
    }


# ============================================================================
# 1. VIEWER RESTRICTIONS (NEGATIVE AUTHORIZATION)
# ============================================================================

def test_viewer_denied_all_write_operations(client: TestClient, rbac_setup):
    """
    PRD v1.2 §5.1: VIEWER role is strictly read-only.
    Must receive HTTP 403 FORBIDDEN on every mutation endpoint.
    """
    v_hdr = rbac_setup["headers"]["VIEWER"]
    m_id = rbac_setup["machine"].id
    d_id = rbac_setup["dataset"].id
    v_id = rbac_setup["version"].id
    c_id = rbac_setup["check"].id

    # 1. Machine creation
    res = client.post("/api/v1/machines", json={"asset_tag": "V-001", "name": "V Machine", "category_code": "GENERAL_MACHINE_TOOL"}, headers=v_hdr)
    assert res.status_code == 403, f"Expected 403 for viewer creating machine, got {res.status_code}"
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 2. Machine update
    res = client.patch(f"/api/v1/machines/{m_id}", json={"name": "Tampered Name"}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 3. Machine archive
    res = client.post(f"/api/v1/machines/{m_id}/archive", headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 4. Dataset creation
    res = client.post(f"/api/v1/machines/{m_id}/datasets", json={"name": "Viewer DS"}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 5. Dataset version upload
    res = client.post(
        f"/api/v1/datasets/{d_id}/versions/upload",
        files={"file": ("test.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")},
        headers=v_hdr
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 6. Column mapping update
    res = client.put(
        f"/api/v1/dataset-versions/{v_id}/mappings/ai4i_failure_no_type",
        json={"mappings": VALID_MAPPINGS},
        headers=v_hdr
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 7. Compatibility check execution
    res = client.post(f"/api/v1/dataset-versions/{v_id}/compatibility-checks", json={}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 8. Warning acknowledgement
    res = client.post(f"/api/v1/compatibility-checks/{c_id}/acknowledge-warnings", json={"reason_codes": []}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 9. Limitation acknowledgement
    res = client.post(
        "/api/v1/limitations/acknowledge",
        json={"machine_id": m_id, "profile_uuid": rbac_setup["check"].profile_uuid},
        headers=v_hdr
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 10. Analysis execution
    res = client.post("/api/v1/analyses", json={"compatibility_check_id": c_id}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 11. Dataset deletion
    res = client.delete(f"/api/v1/datasets/{d_id}", headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 12. Organisation update
    res = client.patch("/api/v1/organisation", json={"name": "Viewer Hacked Org"}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 13. User management
    res = client.get("/api/v1/users", headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    res = client.post("/api/v1/users", json={"email": "new@viewer.com", "full_name": "New", "role": "VIEWER"}, headers=v_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_viewer_allowed_read_only_access(client: TestClient, rbac_setup):
    """
    PRD v1.2 §5.1: VIEWER can read dashboards, machines, datasets, results, and reports.
    """
    v_hdr = rbac_setup["headers"]["VIEWER"]
    m_id = rbac_setup["machine"].id
    d_id = rbac_setup["dataset"].id
    v_id = rbac_setup["version"].id
    c_id = rbac_setup["check"].id
    a_id = rbac_setup["analysis"].id
    j_id = rbac_setup["job"].id

    assert client.get("/api/v1/machines", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/machines/{m_id}", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/machines/{m_id}/datasets", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/datasets/{d_id}", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/dataset-versions/{v_id}", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/dataset-versions/{v_id}/preview", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/dataset-versions/{v_id}/validation-reports", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/dataset-versions/{v_id}/compatibility-checks", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/compatibility-checks/{c_id}", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/analyses/{a_id}", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/analyses/{a_id}/rows", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/machines/{m_id}/analyses", headers=v_hdr).status_code == 200
    assert client.get(f"/api/v1/jobs/{j_id}", headers=v_hdr).status_code == 200
    assert client.get("/api/v1/jobs", headers=v_hdr).status_code == 200
    assert client.get("/api/v1/models").status_code == 200


# ============================================================================
# 2. ANALYST PERMISSIONS & RESTRICTIONS
# ============================================================================

def test_analyst_denied_machine_and_admin_mutations(client: TestClient, rbac_setup):
    """
    PRD v1.2 §5.1: ANALYST cannot create/edit/archive machines, manage org settings, or manage users.
    ANALYST cannot delete datasets created by others.
    """
    a_hdr = rbac_setup["headers"]["ANALYST"]
    m_id = rbac_setup["machine"].id
    d_id = rbac_setup["dataset"].id

    # Denied machine mutation
    res = client.post("/api/v1/machines", json={"asset_tag": "A-001", "name": "A Machine", "category_code": "GENERAL_MACHINE_TOOL"}, headers=a_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    res = client.patch(f"/api/v1/machines/{m_id}", json={"name": "Analyst Rename"}, headers=a_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    res = client.post(f"/api/v1/machines/{m_id}/archive", headers=a_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # Denied org and user administration
    assert client.patch("/api/v1/organisation", json={"name": "Analyst Org"}, headers=a_hdr).status_code == 403
    assert client.get("/api/v1/users", headers=a_hdr).status_code == 403
    assert client.post("/api/v1/users", json={"email": "test@test.com", "full_name": "Test"}, headers=a_hdr).status_code == 403

    # Denied deleting a dataset created by ORG_ADMIN (AC-ORG-8: own datasets only)
    res = client.delete(f"/api/v1/datasets/{d_id}", headers=a_hdr)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_analyst_permitted_dataset_and_analysis_workflows(client: TestClient, rbac_setup):
    """
    PRD v1.2 §5.1: ANALYST can create datasets, upload files, map columns, run checks, and run analyses.
    ANALYST can delete datasets they created.
    """
    a_hdr = rbac_setup["headers"]["ANALYST"]
    m_id = rbac_setup["machine"].id

    # 1. Create dataset
    res = client.post(
        f"/api/v1/machines/{m_id}/datasets",
        json={"name": "Analyst Exploration Data", "dataset_type": "TABULAR_OPERATING_STATE"},
        headers=a_hdr
    )
    assert res.status_code == 201
    analyst_ds_id = res.json()["id"]

    # 2. Upload dataset version
    res = client.post(
        f"/api/v1/datasets/{analyst_ds_id}/versions/upload",
        files={"file": ("analyst_data.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")},
        headers=a_hdr
    )
    assert res.status_code == 201
    vid = res.json()["dataset_version_id"]

    # 3. Save column mapping
    res = client.put(
        f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_no_type",
        json={"mappings": VALID_MAPPINGS},
        headers=a_hdr
    )
    assert res.status_code == 200

    # 4. Run compatibility checks
    res = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=a_hdr
    )
    assert res.status_code == 201
    check_id = res.json()[0]["id"]

    # 5. Acknowledge limitations
    res = client.post(
        "/api/v1/limitations/acknowledge",
        json={"machine_id": m_id, "profile_uuid": rbac_setup["check"].profile_uuid},
        headers=a_hdr
    )
    assert res.status_code == 200

    # 6. Run analysis
    res = client.post(
        "/api/v1/analyses",
        json={"compatibility_check_id": check_id, "limitation_acknowledged": True},
        headers=a_hdr
    )
    assert res.status_code == 202

    # 7. Delete OWN dataset (AC-ORG-8)
    res = client.delete(f"/api/v1/datasets/{analyst_ds_id}", headers=a_hdr)
    assert res.status_code == 200
    assert res.json()["message"] == "Dataset deleted successfully."


# ============================================================================
# 3. ENGINEER PERMISSIONS & RESTRICTIONS
# ============================================================================

def test_engineer_permissions_and_restrictions(client: TestClient, rbac_setup):
    """
    PRD v1.2 §5.1: ENGINEER can create/edit/archive machines, create datasets, run analyses.
    ENGINEER cannot manage org settings, users, or delete datasets created by others.
    """
    e_hdr = rbac_setup["headers"]["ENGINEER"]
    m_id = rbac_setup["machine"].id
    d_id = rbac_setup["dataset"].id

    # Denied org and user administration
    assert client.patch("/api/v1/organisation", json={"name": "Engineer Org"}, headers=e_hdr).status_code == 403
    assert client.get("/api/v1/users", headers=e_hdr).status_code == 403
    assert client.post("/api/v1/users", json={"email": "eng@test.com", "full_name": "Eng"}, headers=e_hdr).status_code == 403

    # Denied deleting a dataset created by ORG_ADMIN
    assert client.delete(f"/api/v1/datasets/{d_id}", headers=e_hdr).status_code == 403

    # Permitted machine operations
    res = client.post(
        "/api/v1/machines",
        json={"asset_tag": "ENG-PUMP-01", "name": "Hydraulic Pump", "category_code": "GENERAL_MACHINE_TOOL"},
        headers=e_hdr
    )
    assert res.status_code == 201
    eng_machine_id = res.json()["id"]

    res = client.patch(f"/api/v1/machines/{eng_machine_id}", json={"name": "Hydraulic Pump Updated"}, headers=e_hdr)
    assert res.status_code == 200

    res = client.post(f"/api/v1/machines/{eng_machine_id}/archive", headers=e_hdr)
    assert res.status_code == 200

    # Permitted creating own dataset and deleting it
    res = client.post(
        f"/api/v1/machines/{m_id}/datasets",
        json={"name": "Engineer Vibration Logs"},
        headers=e_hdr
    )
    assert res.status_code == 201
    eng_ds_id = res.json()["id"]

    res = client.delete(f"/api/v1/datasets/{eng_ds_id}", headers=e_hdr)
    assert res.status_code == 200


# ============================================================================
# 4. ORG ADMIN CAPABILITIES & LAST ADMIN PROTECTION
# ============================================================================

def test_org_admin_full_management_and_last_admin_protection(client: TestClient, rbac_setup):
    """
    PRD v1.2 §5.1, AC-ORG-5:
    - ORG_ADMIN can update organisation settings, view users, create users, update user roles.
    - Last active ORG_ADMIN cannot be deactivated or demoted (HTTP 409 CONFLICT).
    """
    admin_hdr = rbac_setup["headers"]["ORG_ADMIN"]
    admin_user = rbac_setup["users"]["ORG_ADMIN"]

    # 1. Update organisation settings
    res = client.patch(
        "/api/v1/organisation",
        json={"name": "AeroDynamics Global Inc.", "timezone": "America/Chicago"},
        headers=admin_hdr
    )
    assert res.status_code == 200
    assert res.json()["organisation"]["name"] == "AeroDynamics Global Inc."

    # 2. View organisation settings
    res = client.get("/api/v1/organisation", headers=admin_hdr)
    assert res.status_code == 200
    assert res.json()["name"] == "AeroDynamics Global Inc."

    # 3. List organisation users
    res = client.get("/api/v1/users", headers=admin_hdr)
    assert res.status_code == 200
    users_list = res.json()
    assert len(users_list) == 4

    # 4. Create new user
    res = client.post(
        "/api/v1/users",
        json={"email": "contractor@aerodynamics.com", "full_name": "Contractor Bob", "role": "ANALYST"},
        headers=admin_hdr
    )
    assert res.status_code == 201
    new_user_id = res.json()["id"]

    # 5. Deactivate newly created user
    res = client.patch(f"/api/v1/users/{new_user_id}", json={"is_active": False}, headers=admin_hdr)
    assert res.status_code == 200
    assert res.json()["user"]["is_active"] is False

    # 6. AC-ORG-5: Attempt to deactivate the only active ORG_ADMIN -> must fail with 409
    res = client.patch(f"/api/v1/users/{admin_user.id}", json={"is_active": False}, headers=admin_hdr)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "LAST_ORG_ADMIN"

    # 7. AC-ORG-5: Attempt to demote the only active ORG_ADMIN -> must fail with 409
    res = client.patch(f"/api/v1/users/{admin_user.id}", json={"role": "VIEWER"}, headers=admin_hdr)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "LAST_ORG_ADMIN"

    # 8. Delete any dataset in organisation (even created by someone else)
    res = client.delete(f"/api/v1/datasets/{rbac_setup['dataset'].id}", headers=admin_hdr)
    assert res.status_code == 200


# ============================================================================
# 5. MULTI-TENANT ISOLATION & IDOR PREVENTION
# ============================================================================

@pytest.fixture(scope="function")
def two_tenants_with_resources(db_session):
    """Provisions two independent tenants with complete machine and dataset trees."""
    tenants = {}
    for code, name in [("T1", "Alpha Aerospace"), ("T2", "Beta Manufacturing")]:
        org = Organisation(name=name, slug=f"slug-{code.lower()}", status="ACTIVE")
        db_session.add(org)
        db_session.flush()

        plant = Plant(organisation_id=org.id, code="DEFAULT", name=f"{code} Plant", is_default=True)
        db_session.add(plant)
        db_session.flush()

        user = User(
            organisation_id=org.id,
            email=f"admin@{code.lower()}.com",
            full_name=f"{code} Admin",
            password_hash=PRECOMPUTED_HASH,
            role="ORG_ADMIN",
            is_active=True,
            token_version=1
        )
        db_session.add(user)
        db_session.flush()

        machine = Machine(
            organisation_id=org.id,
            plant_id=plant.id,
            asset_tag=f"{code}-M1",
            name=f"{code} Machine",
            category_code="GENERAL_MACHINE_TOOL"
        )
        db_session.add(machine)
        db_session.flush()

        dataset = Dataset(
            organisation_id=org.id,
            machine_id=machine.id,
            name=f"{code} Dataset",
            dataset_type="TABULAR_OPERATING_STATE",
            provenance="CUSTOMER",
            status="ACTIVE",
            created_by=user.id
        )
        db_session.add(dataset)
        db_session.flush()

        version = DatasetVersion(
            organisation_id=org.id,
            dataset_id=dataset.id,
            version_no=1,
            file_kind="CSV",
            original_filename=f"{code.lower()}_telemetry.csv",
            storage_key=f"datasets/{dataset.id}/v1.csv",
            size_bytes=100,
            sha256=f"sha_{code}",
            row_count=2,
            column_count=9,
            status="PROCESSED"
        )
        db_session.add(version)
        db_session.flush()

        report = ValidationReport(
            organisation_id=org.id,
            dataset_version_id=version.id,
            quality_score=95.0,
            quality_components={"S_complete": 1.0, "S_valid": 1.0, "S_unique": 1.0, "S_consistent": 1.0, "S_outlier": 0.9},
            checks=[],
            preview=[{"UDI": 1}]
        )
        db_session.add(report)
        db_session.flush()

        profile = db_session.query(PipelineProfile).filter(PipelineProfile.profile_id == "ai4i_failure_no_type").first()

        check = CompatibilityCheck(
            organisation_id=org.id,
            dataset_version_id=version.id,
            machine_id=machine.id,
            profile_uuid=profile.id,
            status="COMPATIBLE",
            applicability_level="FULLY_APPLICABLE",
            reliability_tier="TIER_1_REFERENCE_COMPLIANT",
            reasons=[],
            inputs_hash=f"hash_{code}"
        )
        db_session.add(check)
        db_session.flush()

        job = Job(
            organisation_id=org.id,
            job_type="RUN_ANALYSIS",
            status="SUCCEEDED",
            payload={"check_id": check.id},
            created_by=user.id
        )
        db_session.add(job)
        db_session.flush()

        analysis = AnalysisResult(
            organisation_id=org.id,
            machine_id=machine.id,
            dataset_version_id=version.id,
            job_id=job.id,
            compatibility_check_id=check.id,
            profile_uuid=profile.id,
            pipeline="A",
            configuration="NO_TYPE",
            result_version=1,
            is_latest=True,
            applicability_level="FULLY_APPLICABLE",
            reliability_tier="TIER_1_REFERENCE_COMPLIANT",
            summary={"total_rows": 2},
            top_rows=[],
            ood_summary={},
            limitations=[]
        )
        db_session.add(analysis)
        db_session.flush()

        token, _ = create_access_token(user.id, org.id, user.role, token_version=1)
        tenants[code] = {
            "org": org,
            "user": user,
            "headers": {"Authorization": f"Bearer {token}"},
            "machine": machine,
            "dataset": dataset,
            "version": version,
            "check": check,
            "analysis": analysis,
            "job": job
        }

    db_session.commit()
    return tenants


def test_cross_tenant_idor_returns_404_on_all_endpoints(client: TestClient, two_tenants_with_resources):
    """
    AC-ORG-2, PRD v1.2 §8.1:
    Every ID-parameterized endpoint must return HTTP 404 NOT_FOUND when accessed
    by a user from a different tenant organisation.
    """
    t1 = two_tenants_with_resources["T1"]
    t2 = two_tenants_with_resources["T2"]

    t1_headers = t1["headers"]
    t2_m_id = t2["machine"].id
    t2_d_id = t2["dataset"].id
    t2_v_id = t2["version"].id
    t2_c_id = t2["check"].id
    t2_a_id = t2["analysis"].id
    t2_j_id = t2["job"].id
    t2_u_id = t2["user"].id

    # Machine endpoints cross-tenant
    assert client.get(f"/api/v1/machines/{t2_m_id}", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/machines/{t2_m_id}/datasets", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/machines/{t2_m_id}/analyses", headers=t1_headers).status_code == 404
    assert client.patch(f"/api/v1/machines/{t2_m_id}", json={"name": "Hacked"}, headers=t1_headers).status_code == 404
    assert client.post(f"/api/v1/machines/{t2_m_id}/archive", headers=t1_headers).status_code == 404
    assert client.post(f"/api/v1/machines/{t2_m_id}/datasets", json={"name": "Injected DS"}, headers=t1_headers).status_code == 404

    # Dataset endpoints cross-tenant
    assert client.get(f"/api/v1/datasets/{t2_d_id}", headers=t1_headers).status_code == 404
    assert client.post(
        f"/api/v1/datasets/{t2_d_id}/versions/upload",
        files={"file": ("hack.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")},
        headers=t1_headers
    ).status_code == 404
    assert client.delete(f"/api/v1/datasets/{t2_d_id}", headers=t1_headers).status_code == 404

    # Dataset Version endpoints cross-tenant
    assert client.get(f"/api/v1/dataset-versions/{t2_v_id}", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/dataset-versions/{t2_v_id}/preview", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/dataset-versions/{t2_v_id}/validation-reports", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/dataset-versions/{t2_v_id}/mappings/ai4i_failure_no_type/suggestions", headers=t1_headers).status_code == 404
    assert client.put(
        f"/api/v1/dataset-versions/{t2_v_id}/mappings/ai4i_failure_no_type",
        json={"mappings": VALID_MAPPINGS},
        headers=t1_headers
    ).status_code == 404
    assert client.post(
        f"/api/v1/dataset-versions/{t2_v_id}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=t1_headers
    ).status_code == 404
    assert client.get(f"/api/v1/dataset-versions/{t2_v_id}/compatibility-checks", headers=t1_headers).status_code == 404

    # Compatibility Check endpoints cross-tenant
    assert client.get(f"/api/v1/compatibility-checks/{t2_c_id}", headers=t1_headers).status_code == 404
    assert client.post(f"/api/v1/compatibility-checks/{t2_c_id}/acknowledge-warnings", json={"reason_codes": []}, headers=t1_headers).status_code == 404
    assert client.post(
        "/api/v1/limitations/acknowledge",
        json={"machine_id": t2_m_id, "profile_uuid": t2["check"].profile_uuid},
        headers=t1_headers
    ).status_code == 404

    # Analysis Result & Job cross-tenant
    assert client.post("/api/v1/analyses", json={"compatibility_check_id": t2_c_id}, headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/analyses/{t2_a_id}", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/analyses/{t2_a_id}/rows", headers=t1_headers).status_code == 404
    assert client.get(f"/api/v1/jobs/{t2_j_id}", headers=t1_headers).status_code == 404

    # User management cross-tenant
    assert client.patch(f"/api/v1/users/{t2_u_id}", json={"is_active": False}, headers=t1_headers).status_code == 404


# ============================================================================
# 6. ACCOUNT DEACTIVATION & SESSION INVALIDATION
# ============================================================================

def test_deactivated_user_immediate_lockout(client: TestClient, rbac_setup, db_session):
    """
    Deactivated users must be immediately rejected from authentication and existing access tokens.
    """
    engineer = rbac_setup["users"]["ENGINEER"]
    e_hdr = rbac_setup["headers"]["ENGINEER"]

    # Valid request before deactivation
    res = client.get("/api/v1/machines", headers=e_hdr)
    assert res.status_code == 200

    # Deactivate the engineer
    engineer.is_active = False
    db_session.commit()

    # Attempt request with old JWT -> 401 ACCOUNT_DEACTIVATED
    res = client.get("/api/v1/machines", headers=e_hdr)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"

    # Attempt login -> 401 ACCOUNT_DEACTIVATED
    res = client.post("/api/v1/auth/login", json={"email": engineer.email, "password": "SuperSecretSecurePassword123!"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "ACCOUNT_DEACTIVATED"


def test_session_invalidation_via_token_version(client: TestClient, rbac_setup, db_session):
    """
    When token_version increments (e.g. after password reset or role modification),
    previously issued tokens are immediately rejected with TOKEN_REVOKED.
    """
    analyst = rbac_setup["users"]["ANALYST"]
    a_hdr = rbac_setup["headers"]["ANALYST"]

    # Valid before version increment
    assert client.get("/api/v1/machines", headers=a_hdr).status_code == 200

    # Bump token_version
    analyst.token_version = (analyst.token_version or 1) + 1
    db_session.commit()

    # Old token rejected
    res = client.get("/api/v1/machines", headers=a_hdr)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_REVOKED"


# ============================================================================
# 7. SUPABASE AUTO-PROVISIONING SECURITY CHECKS
# ============================================================================

def test_supabase_provisioning_blocks_unverified_account_takeover(client: TestClient, rbac_setup, monkeypatch):
    """
    If a local user exists with password auth, an unverified Supabase account
    with the same email must be rejected with 403 UNVERIFIED_EMAIL.
    """
    settings.SUPABASE_URL = "https://mock.supabase.co"
    settings.SUPABASE_ANON_KEY = "mock-key"

    fake_sb_user = {
        "id": "sb-attacker-uuid",
        "email": rbac_setup["users"]["ENGINEER"].email,
        "email_confirmed_at": None,
        "confirmed_at": None,
        "user_metadata": {"email_verified": False}
    }

    monkeypatch.setattr("backend.app.api.deps._verify_supabase_token", lambda token: fake_sb_user)

    res = client.get("/api/v1/machines", headers={"Authorization": "Bearer spoofed-supabase-token"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "UNVERIFIED_EMAIL"


def test_supabase_provisioning_blocks_second_org_when_multi_org_disabled(client: TestClient, rbac_setup, monkeypatch):
    """
    When MULTI_ORG_ENABLED=False, an unprovisioned user cannot auto-create a second organisation.
    Must return 403 MULTI_ORG_DISABLED.
    """
    settings.SUPABASE_URL = "https://mock.supabase.co"
    settings.SUPABASE_ANON_KEY = "mock-key"
    settings.MULTI_ORG_ENABLED = False

    fake_sb_user = {
        "id": "sb-new-user-uuid",
        "email": "stranger@external.com",
        "email_confirmed_at": "2026-11-25T12:00:00Z",
        "user_metadata": {"full_name": "Stranger User", "organisation_name": "Second Corp"}
    }

    monkeypatch.setattr("backend.app.api.deps._verify_supabase_token", lambda token: fake_sb_user)

    res = client.get("/api/v1/machines", headers={"Authorization": "Bearer external-supabase-token"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "MULTI_ORG_DISABLED"
