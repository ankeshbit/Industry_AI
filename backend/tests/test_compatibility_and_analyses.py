"""
Compatibility, Applicability, Reliability, and Analysis Execution Tests
(PRD v1.2 §8.4, §8.6, §13.5, AC-CE-1..7, AC-AP-1..5, AC-FP-1..8)
"""

import io
import pytest
from pathlib import Path
from backend.app.config import settings

VALID_AI4I_CSV = (
    "Air temp,Process temp,RPM,Torque,Tool wear\n"
    "298.1,308.6,1551,42.8,0\n"
    "298.2,308.7,1408,46.3,3\n"
    "298.1,308.5,1498,49.4,5\n"
    "298.2,308.6,1433,39.5,7\n"
    "298.2,308.7,1408,40.0,9\n"
)

OUT_OF_RANGE_CSV = (
    "Air temp,Process temp,RPM,Torque,Tool wear\n"
    "298.1,308.6,1551,195.0,0\n"   # Extreme torque (195 Nm >> 83.88 Nm reference range)
    "298.2,308.7,1408,210.0,3\n"   # Extreme torque
    "298.1,308.5,1498,220.0,5\n"   # Extreme torque
    "298.2,308.6,1433,40.0,7\n"
    "298.2,308.7,1408,40.0,9\n"
)

def create_machine_and_dataset(client, tenant_fixture, csv_content=VALID_AI4I_CSV, name="Test DS"):
    m_resp = client.post("/api/v1/machines", json={
        "asset_tag": f"COMPAT-MACH-{name[:5]}",
        "name": "Machine For Compatibility",
        "category_code": "GENERAL_MACHINE_TOOL"
    }, headers=tenant_fixture["headers"])
    machine_id = m_resp.json()["id"]

    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": name
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    files = {"file": ("data.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    up_resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    vid = up_resp.json()["dataset_version_id"]
    return machine_id, dataset_id, vid

def map_valid_features(client, tenant_fixture, vid, profile_id="ai4i_failure_no_type"):
    mapping = {
        "mappings": {
            "air_temperature": {"column": "Air temp", "unit": "K"},
            "process_temperature": {"column": "Process temp", "unit": "K"},
            "rotational_speed": {"column": "RPM", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Tool wear", "unit": "min"}
        }
    }
    client.put(f"/api/v1/dataset-versions/{vid}/mappings/{profile_id}", json=mapping, headers=tenant_fixture["headers"])

def test_compatibility_statuses_and_precedence(client, tenant_fixture):
    """AC-CE-1, AC-CE-2: Checks reach COMPATIBLE and INCOMPATIBLE statuses with strict precedence."""
    # 1. Unmapped dataset -> INCOMPATIBLE
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Unmapped DS")
    resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=tenant_fixture["headers"])
    assert resp.status_code == 201
    check = resp.json()[0]
    assert check["compatibility"]["status"] == "INCOMPATIBLE"
    assert check["applicability"]["level"] == "NOT_ASSESSED"

    # 2. Mapped dataset -> COMPATIBLE
    map_valid_features(client, tenant_fixture, vid)
    resp2 = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=tenant_fixture["headers"])
    assert resp2.status_code == 201
    check2 = resp2.json()[0]
    assert check2["compatibility"]["status"] == "COMPATIBLE"
    assert check2["applicability"]["level"] == "IN_REFERENCE_RANGE"
    assert check2["reliability"]["tier"] == "REFERENCE_ONLY"

def test_applicability_blocking_when_mostly_ood(client, tenant_fixture):
    """AC-AP-2, AC-CE-3: Mostly OOD dataset (>30% rows) triggers MOSTLY_OUTSIDE_REFERENCE_RANGE and APPLICABILITY_BLOCKED."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=OUT_OF_RANGE_CSV, name="OOD DS")
    map_valid_features(client, tenant_fixture, vid)

    # 3 of 5 rows (60% > 30%) have extreme torque
    resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=tenant_fixture["headers"])
    assert resp.status_code == 201
    check = resp.json()[0]
    assert check["applicability"]["level"] == "MOSTLY_OUTSIDE_REFERENCE_RANGE"
    assert check["applicability"]["flagged_row_fraction"] == 0.60

    # Attempt to run analysis: rejected with 422 APPLICABILITY_BLOCKED
    run_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": check["id"],
        "limitation_acknowledged": True
    }, headers=tenant_fixture["headers"])
    assert run_resp.status_code == 422
    assert run_resp.json()["error"]["code"] == "APPLICABILITY_BLOCKED"

def test_limitation_acknowledgement_gate(client, tenant_fixture):
    """AC-AP-5: Run without explicit limitation acknowledgement returns 422 LIMITATIONS_NOT_ACKNOWLEDGED."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Limit Gate DS")
    map_valid_features(client, tenant_fixture, vid)

    chk_resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=tenant_fixture["headers"])
    check_id = chk_resp.json()[0]["id"]

    # Post analysis with limitation_acknowledged = False
    run_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": check_id,
        "limitation_acknowledged": False
    }, headers=tenant_fixture["headers"])
    assert run_resp.status_code == 422
    assert run_resp.json()["error"]["code"] == "LIMITATIONS_NOT_ACKNOWLEDGED"

def test_warning_acknowledgement_gate(client, tenant_fixture):
    """AC-CE-4: Active warnings must be acknowledged; missing returns 422 WARNINGS_NOT_ACKNOWLEDGED."""
    # Create dataset with 1 row outside range (20% -> PARTLY_OUTSIDE_REFERENCE_RANGE)
    partly_ood_csv = (
        "Air temp,Process temp,RPM,Torque,Tool wear\n"
        "298.1,308.6,1551,195.0,0\n"   # 1 extreme row
        "298.2,308.7,1408,46.3,3\n"
        "298.1,308.5,1498,49.4,5\n"
        "298.2,308.6,1433,39.5,7\n"
        "298.2,308.7,1408,40.0,9\n"
    )
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, csv_content=partly_ood_csv, name="Partly OOD DS")
    map_valid_features(client, tenant_fixture, vid)

    chk_resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=tenant_fixture["headers"])
    check = chk_resp.json()[0]
    assert check["applicability"]["level"] == "PARTLY_OUTSIDE_REFERENCE_RANGE"
    assert "W_OOD" in check["requires_acknowledgement"]

    # Attempt run without acknowledging W_OOD
    run_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": check["id"],
        "acknowledged_reason_codes": [],
        "limitation_acknowledged": True
    }, headers=tenant_fixture["headers"])
    assert run_resp.status_code == 422
    assert run_resp.json()["error"]["code"] == "WARNINGS_NOT_ACKNOWLEDGED"

    # Now acknowledge W_OOD: run succeeds!
    run_resp2 = client.post("/api/v1/analyses", json={
        "compatibility_check_id": check["id"],
        "acknowledged_reason_codes": ["W_OOD"],
        "limitation_acknowledged": True
    }, headers=tenant_fixture["headers"])
    assert run_resp2.status_code == 202
    assert run_resp2.json()["status"] == "SUCCEEDED"

def test_full_analysis_execution_and_trust_panel(client, tenant_fixture):
    """AC-FP-5, AC-AP-3, AC-AP-4: Completed analysis result contains full provenance, trust panel, limitations, and OOD flags."""
    _, _, vid = create_machine_and_dataset(client, tenant_fixture, name="Trust DS")
    map_valid_features(client, tenant_fixture, vid)

    chk_resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=tenant_fixture["headers"])
    check_id = chk_resp.json()[0]["id"]

    run_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": check_id,
        "limitation_acknowledged": True
    }, headers=tenant_fixture["headers"])
    assert run_resp.status_code == 202
    result_id = run_resp.json()["analysis_result_id"]

    # Fetch result
    res_resp = client.get(f"/api/v1/analyses/{result_id}", headers=tenant_fixture["headers"])
    assert res_resp.status_code == 200
    res = res_resp.json()

    # Provenance
    assert res["provenance"]["model"]["registry_name"] == "ai4i_failure_clf_notype"
    assert res["provenance"]["model"]["training_domain"] == "REFERENCE_DATASET"

    # Trust Panel (AC-AP-3, AC-AP-4)
    assert res["trust"]["reliability_tier"] == "REFERENCE_ONLY"
    assert "not validated on your equipment" in res["trust"]["label"]
    assert res["semantics"] == "Reference-calibrated failure probability for the supplied operating state; no time horizon is implied."
    assert res["evaluation_sections"]["customer_specific_validation"] is None

    # Summary
    assert res["summary"]["total_rows"] == 5
    assert "predicted_failures" in res["summary"]
    assert "mean_failure_probability" in res["summary"]

    # Fetch rows (AC-FP-8)
    rows_resp = client.get(f"/api/v1/analyses/{result_id}/rows", headers=tenant_fixture["headers"])
    assert rows_resp.status_code == 200
    rows = rows_resp.json()["top_rows"]
    assert len(rows) > 0
    for r in rows:
        assert "failure_probability" in r
        assert r["risk_class"] in ("LOW", "MEDIUM", "HIGH")
        assert "ood_warning" in r

def test_repository_text_scan_no_safety_or_approval_claims():
    """AC-AP-7: Repository text scan finds no wording that calls compatible data approved, validated, or safe."""
    forbidden_terms = [
        "compatible data is validated",
        "compatible data is approved",
        "dataset is approved for production",
        "model is certified safe",
        "guaranteed predictive accuracy"
    ]
    root_dir = Path(__file__).resolve().parent.parent.parent
    for ext in (".py", ".json", ".md"):
        for fpath in root_dir.glob(f"**/*{ext}"):
            if ".venv" in fpath.parts or ".git" in fpath.parts or "node_modules" in fpath.parts:
                continue
            if fpath.name in ("test_compatibility_and_analyses.py", "PRD.md"):
                continue
            text = fpath.read_text(encoding="utf-8", errors="ignore").lower()
            for term in forbidden_terms:
                assert term not in text, f"Forbidden misleading claim '{term}' found in {fpath}!"
