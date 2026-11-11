"""
Regression tests for bugs found during the code audit.
Each test documents the original failure mode in its docstring.
"""

import io

import pytest

from backend.app.services.inference_service import MODEL_PATHS
from backend.app.models.auth import RefreshToken
from backend.app.models.dataset import ColumnMapping
from backend.app.models.usage import UsageEvent
from backend.tests.test_compatibility_and_analyses import (
    VALID_AI4I_CSV,
    create_machine_and_dataset,
    map_valid_features,
)


# Reference model artifacts are gitignored; tests that execute real inference need them.
needs_models = pytest.mark.skipif(
    not all(path.exists() for path in MODEL_PATHS.values()),
    reason="reference model artifacts (ml/artifacts/models/*.joblib) not present",
)


def _run_analysis(client, tenant, vid, **extra):
    chk = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant["headers"],
    ).json()[0]
    body = {"compatibility_check_id": chk["id"], "limitation_acknowledged": True, **extra}
    return chk, client.post("/api/v1/analyses", json=body, headers=tenant["headers"])


@needs_models
def test_usage_event_records_result_id(client, tenant_fixture, db_session):
    """UsageEvent.details.result_id was null because the result had not been flushed yet."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Usage DS")
    map_valid_features(client, tenant_fixture, vid)
    _, resp = _run_analysis(client, tenant_fixture, vid)
    result_id = resp.json()["analysis_result_id"]
    assert result_id

    events = db_session.query(UsageEvent).filter(UsageEvent.event_type == "ANALYSIS_EXECUTION").all()
    assert events and events[-1].details["result_id"] == result_id


@needs_models
def test_force_rerun_creates_new_result(client, tenant_fixture):
    """force_rerun re-executed the same job and violated the unique AnalysisResult.job_id constraint."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Rerun DS")
    map_valid_features(client, tenant_fixture, vid)
    headers = {**tenant_fixture["headers"], "Idempotency-Key": "rerun-key-1"}
    chk = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"],
    ).json()[0]
    body = {"compatibility_check_id": chk["id"], "limitation_acknowledged": True}
    first = client.post("/api/v1/analyses", json=body, headers=headers)
    assert first.json()["status"] == "SUCCEEDED"

    # Same Idempotency-Key + force_rerun used to re-run the old job -> unique job_id violation -> RETRY_WAIT
    second = client.post("/api/v1/analyses", json={**body, "force_rerun": True}, headers=headers)
    assert second.status_code == 202
    assert second.json()["status"] == "SUCCEEDED"
    assert second.json()["analysis_result_id"] != first.json()["analysis_result_id"]
    assert second.json()["job_id"] != first.json()["job_id"]


@needs_models
def test_inline_job_counts_attempt(client, tenant_fixture):
    """Inline (API fast-path) jobs never incremented `attempt`."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Attempt DS")
    map_valid_features(client, tenant_fixture, vid)
    _, resp = _run_analysis(client, tenant_fixture, vid)
    job = client.get(f"/api/v1/jobs/{resp.json()['job_id']}", headers=tenant_fixture["headers"]).json()
    assert job["attempt"] == 1 and job["status"] == "SUCCEEDED"


@needs_models
def test_analysis_provenance_uses_the_right_dataset(client, tenant_fixture):
    """Provenance showed the machine's FIRST dataset and the result_version as the dataset version."""
    machine_id, _, _ = create_machine_and_dataset(client, tenant_fixture, name="First DS")

    ds2 = client.post(
        f"/api/v1/machines/{machine_id}/datasets", json={"name": "Second DS"}, headers=tenant_fixture["headers"]
    ).json()
    files = {"file": ("d2.csv", io.BytesIO(VALID_AI4I_CSV.replace("1551", "1552").encode()), "text/csv")}
    vid2 = client.post(
        f"/api/v1/datasets/{ds2['id']}/versions/upload", files=files, headers=tenant_fixture["headers"]
    ).json()["dataset_version_id"]
    map_valid_features(client, tenant_fixture, vid2)

    _, resp = _run_analysis(client, tenant_fixture, vid2)
    res = client.get(f"/api/v1/analyses/{resp.json()['analysis_result_id']}", headers=tenant_fixture["headers"]).json()
    assert res["provenance"]["dataset"]["name"] == "Second DS"
    assert res["provenance"]["dataset"]["id"] == vid2
    assert res["provenance"]["dataset"]["version"] == 1
    assert res["provenance"]["profile"] == "ai4i_failure_no_type@1.0.0"
    # must not leak the server filesystem path of the model artifact
    assert ".joblib" not in str(res["evaluation_sections"])


def test_compatibility_rejects_foreign_mapping_id(client, two_tenants_fixture, db_session):
    """A mapping_id belonging to another tenant was accepted (tenant isolation hole)."""
    t1, t2 = two_tenants_fixture["tenant1"], two_tenants_fixture["tenant2"]
    _, _, vid1 = create_machine_and_dataset(client, t1, name="T1 DS")
    map_valid_features(client, t1, vid1)
    foreign_mapping_id = db_session.query(ColumnMapping).filter(ColumnMapping.dataset_version_id == vid1).first().id

    _, _, vid2 = create_machine_and_dataset(client, t2, name="T2 DS")
    resp = client.post(
        f"/api/v1/dataset-versions/{vid2}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type", "mapping_id": foreign_mapping_id},
        headers=t2["headers"],
    )
    assert resp.status_code == 404


def test_zip_container_is_rejected(client, tenant_fixture):
    """Only one very specific PK header variant was rejected; any zip/xlsx container should be."""
    machine_id, dataset_id, _ = create_machine_and_dataset(client, tenant_fixture, name="Zip DS")
    files = {"file": ("evil.csv", io.BytesIO(b"PK\x03\x04\x0a\x00\x00\x00rest"), "text/csv")}
    resp = client.post(
        f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"]
    )
    assert resp.status_code == 415


def test_unknown_route_uses_standard_error_envelope(client):
    """Routing 404s bypassed the PRD §13.1 error envelope (handler was bound to the wrong class)."""
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_patch_machine_null_name_is_ignored(client, tenant_fixture):
    """PATCH {"name": null} caused a 500 IntegrityError on a NOT NULL column."""
    m = client.post(
        "/api/v1/machines",
        json={"asset_tag": "PATCH-1", "name": "Keep Me", "category_code": "GENERAL_MACHINE_TOOL"},
        headers=tenant_fixture["headers"],
    ).json()
    resp = client.patch(f"/api/v1/machines/{m['id']}", json={"name": None}, headers=tenant_fixture["headers"])
    assert resp.status_code == 200
    assert client.get(f"/api/v1/machines/{m['id']}", headers=tenant_fixture["headers"]).json()["name"] == "Keep Me"


def test_deactivated_user_cannot_refresh(client, tenant_fixture, db_session):
    """Refresh rotation did not check is_active, so a deactivated user could keep minting tokens."""
    from backend.app.services.auth_service import create_refresh_token

    user = tenant_fixture["user"]
    token = create_refresh_token(db_session, user)
    user.is_active = False
    db_session.commit()

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 401
    # token must not have been rotated/revoked as a side effect
    rf_id = token.split(":", 1)[0]
    assert db_session.query(RefreshToken).filter(RefreshToken.id == rf_id).first().revoked_at is None
