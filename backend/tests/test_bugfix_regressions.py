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


def test_suggestions_match_sample_file_headers(client, tenant_fixture):
    """Headers from the authoritative sample CSVs (e.g. 'Ambient Temp [C]') got no suggestions at all."""
    csv = (
        "Ambient Temp [C],Process Chamber Temp [C],Spindle RPM,Drive Torque [Nm],Cumulative Tool Wear [min]\n"
        "25.0,35.5,1550,42.5,15\n"
    )
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=csv, name="Sample Headers DS")
    sug = client.get(
        f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_no_type/suggestions", headers=tenant_fixture["headers"]
    ).json()["suggestions"]
    assert sug["air_temperature"] == {"column": "Ambient Temp [C]", "unit": "degC", "suggested": True, "confirmed": False}
    assert sug["process_temperature"]["column"] == "Process Chamber Temp [C]"
    assert sug["rotational_speed"]["column"] == "Spindle RPM"
    assert sug["torque"]["column"] == "Drive Torque [Nm]"
    assert sug["tool_wear"]["column"] == "Cumulative Tool Wear [min]"


def test_product_type_on_no_type_profile_error_code(client, tenant_fixture):
    """PRD §13.4: product_type on any other profile -> E_FEATURE_NOT_IN_PROFILE (was E_FORBIDDEN_FEATURE)."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="PT DS")
    resp = client.put(
        f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_no_type",
        json={"mappings": {"product_type": {"column": "RPM", "asserted_equivalence": True}}},
        headers=tenant_fixture["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "E_FEATURE_NOT_IN_PROFILE"


@needs_models
def test_analysis_result_carries_standing_advisory(client, tenant_fixture):
    """PRD §14.2: the standing advisory must accompany every API result (it was UI-only and abbreviated)."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Advisory DS")
    map_valid_features(client, tenant_fixture, vid)
    _, resp = _run_analysis(client, tenant_fixture, vid)
    res = client.get(f"/api/v1/analyses/{resp.json()['analysis_result_id']}", headers=tenant_fixture["headers"]).json()
    assert "has not been validated on your specific equipment" in res["advisory_notice"]
    assert res["trust"]["compatibility"] in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS")


# ---------------------------------------------------------------------------------------------
# Third audit pass
# ---------------------------------------------------------------------------------------------

def _machine_and_dataset(client, tenant, name):
    m = client.post(
        "/api/v1/machines",
        json={"asset_tag": f"TAG-{name}", "name": name, "category_code": "GENERAL_MACHINE_TOOL"},
        headers=tenant["headers"],
    ).json()
    ds = client.post(f"/api/v1/machines/{m['id']}/datasets", json={"name": name}, headers=tenant["headers"]).json()
    return m["id"], ds["id"]


def _upload(client, tenant, dataset_id, content: bytes, filename: str):
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    return client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant["headers"])


def test_tsv_upload_is_parsed_and_usable_downstream(client, tenant_fixture):
    """TSV uploads were accepted but parsed as a single column (and re-read as CSV downstream)."""
    _, ds_id = _machine_and_dataset(client, tenant_fixture, "TSV")
    resp = _upload(client, tenant_fixture, ds_id, VALID_AI4I_CSV.replace(",", "\t").encode(), "data.tsv")
    assert resp.status_code == 201
    assert resp.json()["column_count"] == 5 and resp.json()["row_count"] == 5
    vid = resp.json()["dataset_version_id"]
    map_valid_features(client, tenant_fixture, vid)
    chk = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"],
    ).json()[0]
    assert chk["compatibility"]["status"] in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS")


def test_utf8_bom_header_is_stripped(client, tenant_fixture):
    """Guard (not a past bug: pandas already tolerates a BOM): Excel BOM files must keep clean header names."""
    _, ds_id = _machine_and_dataset(client, tenant_fixture, "BOM")
    resp = _upload(client, tenant_fixture, ds_id, b"\xef\xbb\xbf" + VALID_AI4I_CSV.encode(), "bom.csv")
    assert resp.status_code == 201
    cols = client.get(
        f"/api/v1/dataset-versions/{resp.json()['dataset_version_id']}", headers=tenant_fixture["headers"]
    ).json()["columns"]
    assert cols[0]["name"] == "Air temp"


def test_non_numeric_mapped_column_is_incompatible_not_500(client, tenant_fixture):
    """Mapping a text column to a numeric feature crashed convert_to_canonical (astype(float)) later on."""
    csv = VALID_AI4I_CSV.replace("42.8", "high").replace("46.3", "low")
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=csv, name="NonNum DS")
    map_valid_features(client, tenant_fixture, vid)
    resp = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"],
    )
    assert resp.status_code == 201
    chk = resp.json()[0]
    assert chk["compatibility"]["status"] == "INCOMPATIBLE"
    assert "E_NON_NUMERIC_COLUMN" in [r["code"] for r in chk["compatibility"]["reasons"]]


def test_required_feature_completeness_gate(client, tenant_fixture):
    """profile.minimums.required_feature_completeness (0.95) was declared but never enforced."""
    csv = (
        "Air temp,Process temp,RPM,Torque,Tool wear\n"
        "298.1,308.6,1551,,0\n298.2,308.7,1408,,3\n298.1,308.5,1498,,5\n"
        "298.2,308.6,1433,39.5,7\n298.2,308.7,1408,40.0,9\n"
    )
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=csv, name="Sparse DS")
    map_valid_features(client, tenant_fixture, vid)
    chk = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"],
    ).json()[0]
    assert chk["compatibility"]["status"] == "INSUFFICIENT_DATA"
    assert "E_INSUFFICIENT_COMPLETENESS" in [r["code"] for r in chk["compatibility"]["reasons"]]


def test_quality_score_flags_physically_invalid_values(client, tenant_fixture):
    """S_valid only flagged values < -100, so a negative rotational speed passed as 'valid'."""
    csv = VALID_AI4I_CSV.replace("1551", "-5")
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=csv, name="Invalid DS")
    map_valid_features(client, tenant_fixture, vid)
    rep = client.get(f"/api/v1/dataset-versions/{vid}/validation-reports", headers=tenant_fixture["headers"]).json()
    assert rep["quality_components"]["S_valid"] < 1.0
    assert "W_INVALID_VALUES" in [c["code"] for c in rep["checks"]]


def test_models_endpoint_matches_model_cards(client):
    """Seeded evaluation metrics were unsourced numbers (PR-AUC 0.760 etc.) that contradicted the model cards."""
    models = {m["registry_name"]: m for m in client.get("/api/v1/models").json()}
    def metric(name, metric_name):
        return next(e for e in models[name]["reference_evaluations"] if e["metric_name"] == metric_name)
    assert metric("ai4i_failure_clf_notype", "PR-AUC")["metric_value"] == 0.7734
    assert metric("ai4i_failure_clf_notype", "ROC-AUC")["metric_value"] == 0.9763
    assert metric("ai4i_failure_clf_typed", "PR-AUC")["metric_value"] == 0.7753
    # the cards publish no confidence intervals; none may be invented
    assert all(e["ci_low"] is None for m in models.values() for e in m["reference_evaluations"])


def test_acknowledge_warnings_rejects_unknown_codes(client, tenant_fixture):
    """Any arbitrary string was accepted (and duplicated on repeat calls) as a 'warning acknowledgement'."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Ack DS")
    map_valid_features(client, tenant_fixture, vid)
    chk = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"],
    ).json()[0]
    resp = client.post(
        f"/api/v1/compatibility-checks/{chk['id']}/acknowledge-warnings",
        json={"reason_codes": ["NOT_A_REAL_WARNING"]},
        headers=tenant_fixture["headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNKNOWN_WARNING_CODE"


@needs_models
def test_run_persists_acknowledgements(client, tenant_fixture, db_session):
    """The UI acknowledges inline on the run request, so the audit tables stayed empty."""
    from backend.app.models.compatibility import LimitationAcknowledgement, WarningAcknowledgement

    partly_ood = VALID_AI4I_CSV.replace("42.8", "195.0")
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=partly_ood, name="Audit DS")
    map_valid_features(client, tenant_fixture, vid)
    chk = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"],
    ).json()[0]
    resp = client.post(
        "/api/v1/analyses",
        json={
            "compatibility_check_id": chk["id"],
            "acknowledged_reason_codes": chk["requires_acknowledgement"],
            "limitation_acknowledged": True,
        },
        headers=tenant_fixture["headers"],
    )
    assert resp.status_code == 202
    acked = {a.reason_code for a in db_session.query(WarningAcknowledgement).filter_by(compatibility_check_id=chk["id"])}
    assert acked == set(chk["requires_acknowledgement"])
    assert db_session.query(LimitationAcknowledgement).count() == 1


def test_production_refuses_default_secret_key():
    """The publicly known default SECRET_KEY allowed forged JWTs if production forgot to set one."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    env = {**os.environ, "APP_ENV": "production"}
    env.pop("SECRET_KEY", None)
    bad = subprocess.run([sys.executable, "-c", "import backend.app.config"], cwd=repo, env=env, capture_output=True)
    assert bad.returncode != 0 and b"SECRET_KEY" in bad.stderr
    ok = subprocess.run([sys.executable, "-c", "import backend.app.config"], cwd=repo, env={**env, "SECRET_KEY": "x" * 40}, capture_output=True)
    assert ok.returncode == 0, ok.stderr


def test_claim_is_compare_and_set(client, tenant_fixture, db_session):
    """A job that another worker already moved to RUNNING between SELECT and UPDATE must not be claimed again."""
    from backend.app.models.job import Job
    from backend.app.services import queue_service

    job, _ = queue_service.enqueue_job(
        db=db_session, org_id=tenant_fixture["org"].id, job_type="RUN_ANALYSIS", payload={"x": 1}
    )
    real_query = db_session.query
    state = {"raced": False}

    def racing_query(*args, **kwargs):
        q = real_query(*args, **kwargs)
        if args and args[0] is Job and not state["raced"]:
            orig_first = q.first
            def first():
                row = orig_first()
                if row is not None and row.status == "QUEUED" and not state["raced"]:
                    # another worker wins the race right after our SELECT
                    state["raced"] = True
                    real_query(Job).filter(Job.id == row.id).update(
                        {"status": "RUNNING", "claimed_by": "other-worker", "attempt": 1}, synchronize_session=False
                    )
                    db_session.commit()
                return row
            q.first = first
        return q

    db_session.query = racing_query
    try:
        assert queue_service.claim_next_job(db_session, worker_id="me") is None
    finally:
        db_session.query = real_query
    db_session.refresh(job)
    assert job.claimed_by == "other-worker" and job.attempt == 1
