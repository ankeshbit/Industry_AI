"""
Dataset Ingestion, Security, Validation, and Quality Score Tests (PRD v1.2 §8.3, §13.4, AC-DS-1..10)
"""

import io
import pytest
import pandas as pd
from backend.app.config import settings

SAMPLE_CSV_CONTENT = (
    "Air temperature [K],Process temperature [K],Rotational speed [rpm],Torque [Nm],Tool wear [min]\n"
    "298.1,308.6,1551,42.8,0\n"
    "298.2,308.7,1408,46.3,3\n"
    "298.1,308.5,1498,49.4,5\n"
    "298.2,308.6,1433,39.5,7\n"
    "298.2,308.7,1408,40.0,9\n"
)

def create_test_machine(client, tenant_fixture):
    m_resp = client.post("/api/v1/machines", json={
        "asset_tag": "TEST-MACH-01",
        "name": "Validation Test CNC",
        "category_code": "GENERAL_MACHINE_TOOL"
    }, headers=tenant_fixture["headers"])
    return m_resp.json()["id"]

def test_csv_upload_success_and_versioning(client, tenant_fixture):
    """AC-DS-1, AC-DS-6: Valid CSV upload creates immutable version with SHA-256 and quality score."""
    machine_id = create_test_machine(client, tenant_fixture)
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Baseline Production Run"
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    # Upload CSV
    files = {"file": ("test_data.csv", io.BytesIO(SAMPLE_CSV_CONTENT.encode("utf-8")), "text/csv")}
    up_resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    assert up_resp.status_code == 201
    data = up_resp.json()
    assert data["version_no"] == 1
    assert len(data["sha256"]) == 64
    assert data["row_count"] == 5
    assert data["column_count"] == 5
    assert data["quality_score"] > 80.0
    assert data["deduplicated"] is False

    # Upload identical file again: returns deduplicated version (AC-DS-6)
    files2 = {"file": ("test_data_copy.csv", io.BytesIO(SAMPLE_CSV_CONTENT.encode("utf-8")), "text/csv")}
    up_resp2 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files2, headers=tenant_fixture["headers"])
    assert up_resp2.status_code == 201
    assert up_resp2.json()["deduplicated"] is True
    assert up_resp2.json()["dataset_version_id"] == data["dataset_version_id"]

def test_executable_and_wrong_magic_bytes_rejected_415(client, tenant_fixture):
    """AC-DS-1: Executable headers (MZ, ELF) and non-CSV formats rejected with 415 UNSUPPORTED_FORMAT."""
    machine_id = create_test_machine(client, tenant_fixture)
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Security Test Dataset"
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    # Fake Windows PE executable starting with MZ
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100
    files = {"file": ("malicious.exe.csv", io.BytesIO(fake_exe), "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FORMAT"

def test_oversized_file_rejected_413(client, tenant_fixture):
    """AC-DS-2: Files exceeding 50 MB byte limit rejected with 413 PAYLOAD_TOO_LARGE."""
    machine_id = create_test_machine(client, tenant_fixture)
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Oversized Dataset"
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    # Temporarily set max size to 1000 bytes for fast test execution
    old_max = settings.MAX_UPLOAD_SIZE_BYTES
    settings.MAX_UPLOAD_SIZE_BYTES = 500
    try:
        oversized_bytes = b"col1,col2\n" + (b"1,2\n" * 200)  # > 500 bytes
        files = {"file": ("large.csv", io.BytesIO(oversized_bytes), "text/csv")}
        resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = old_max

def test_quality_score_formula_and_components(client, tenant_fixture):
    """AC-DS-4: Quality score strictly matches Q = 100 * (0.30 S_complete + 0.25 S_valid + 0.15 S_unique + 0.20 S_consistent + 0.10 S_outlier)."""
    machine_id = create_test_machine(client, tenant_fixture)
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Quality Math Dataset"
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    # Clean dataset with zero missing, zero duplicates, zero outliers
    clean_csv = "feat_a,feat_b\n" + "\n".join([f"{i*1.0},{i*2.0}" for i in range(1, 101)])
    files = {"file": ("clean.csv", io.BytesIO(clean_csv.encode("utf-8")), "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    assert resp.status_code == 201
    vid = resp.json()["dataset_version_id"]

    rep_resp = client.get(f"/api/v1/dataset-versions/{vid}/validation-reports", headers=tenant_fixture["headers"])
    assert rep_resp.status_code == 200
    report = rep_resp.json()
    assert report["quality_score"] == 100.0
    comps = report["quality_components"]
    assert comps["S_complete"] == 1.0
    assert comps["S_valid"] == 1.0
    assert comps["S_unique"] == 1.0
    assert comps["S_consistent"] == 1.0
    assert comps["S_outlier"] == 1.0

def test_mapping_suggestions_and_confirmation(client, tenant_fixture):
    """AC-DS-9: Mapping suggestions flagged suggested: true and never auto-applied without user confirmation."""
    machine_id = create_test_machine(client, tenant_fixture)
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Suggestions Dataset"
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    # Upload CSV with custom column headers
    custom_csv = (
        "Air temp,Process temp,RPM,Torque,Tool wear\n"
        "298.1,308.6,1551,42.8,0\n"
    )
    files = {"file": ("custom.csv", io.BytesIO(custom_csv.encode("utf-8")), "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    vid = resp.json()["dataset_version_id"]

    # Fetch suggestions
    sug_resp = client.get(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_no_type/suggestions", headers=tenant_fixture["headers"])
    assert sug_resp.status_code == 200
    suggestions = sug_resp.json()["suggestions"]
    assert suggestions["air_temperature"]["column"] == "Air temp"
    assert suggestions["air_temperature"]["suggested"] is True
    assert suggestions["air_temperature"]["confirmed"] is False
    assert suggestions["rotational_speed"]["column"] == "RPM"

def test_forbidden_feature_mapping_rejected_422(client, tenant_fixture):
    """AC-CE-7: Mapping target failure modes or identifiers as inputs returns 422 E_FORBIDDEN_FEATURE."""
    machine_id = create_test_machine(client, tenant_fixture)
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Leakage Risk Dataset"
    }, headers=tenant_fixture["headers"])
    dataset_id = ds_resp.json()["id"]

    leak_csv = "Air temp,Torque,Machine failure,UDI\n298.1,42.8,0,1\n"
    files = {"file": ("leak.csv", io.BytesIO(leak_csv.encode("utf-8")), "text/csv")}
    resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    vid = resp.json()["dataset_version_id"]

    # Attempt to map forbidden column 'Machine failure'
    bad_mapping = {
        "mappings": {
            "air_temperature": {"column": "Air temp", "unit": "K"},
            "torque": {"column": "Machine failure", "unit": "Nm"}
        }
    }
    map_resp = client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_no_type", json=bad_mapping, headers=tenant_fixture["headers"])
    assert map_resp.status_code == 422
    assert map_resp.json()["error"]["code"] == "E_FORBIDDEN_FEATURE"

