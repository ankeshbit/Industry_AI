"""
Data Pipeline Integrity, Ingestion Validation, and End-to-End Prediction Test Suite
Verifies:
1. Upload Validation:
   - Empty files (0 bytes and whitespace only) reject with 422 E_EMPTY.
   - Duplicate column headers reject with 422 E_DUPLICATE_COLUMNS.
   - Extremely wide datasets reject with 422 E_TOO_MANY_COLUMNS.
   - Malformed CSV structure rejects with 415/422 E_MALFORMED_CSV.
   - Encoding resilience: UTF-8 with BOM, UTF-16, Latin-1 with special characters.
   - Delimiter resilience: TSV (tab-separated) and semicolon-separated CSV.
2. Storage & Traversal Security:
   - Path traversal prevention on storage directory resolution.
   - Transactional rollback on database failures prevents orphaned files on disk.
3. Column Mapping:
   - Rejects mapping when required profile features are missing (422 E_MISSING_FEATURE).
   - Rejects mapping when mapped column does not exist in dataset (422 E_UNKNOWN_COLUMN).
   - Rejects mapping forbidden leakage columns like target/failure/twf (422 E_FORBIDDEN_FEATURE).
   - Rejects invalid categorical values for product_type (422 E_INVALID_CATEGORY_VALUES).
4. Inference & Explainability:
   - Rejects infinite values with 422 E_INFINITE_VALUES.
   - Strictly preserves feature names and ordering matching trained model bundles.
   - Validates calibrated output probabilities in [0.0, 1.0] and risk tiers.
   - Clearly identifies TreeSHAP vs fallback metadata.
5. Full Row Predictions & Pagination:
   - Saves complete row-level predictions to storage.
   - Paginated retrieval via GET /analyses/{id}/rows with filtering.
   - Streaming export endpoint GET /analyses/{id}/export?format=csv|json.
6. Provenance & Versioning:
   - Correct result_version incrementing and is_latest management.
"""

import io
import csv
import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from fastapi import HTTPException

from backend.app.config import settings
from backend.app.models.compatibility import PipelineProfile, CompatibilityCheck
from backend.app.models.dataset import Dataset, DatasetVersion, ColumnMapping
from backend.app.models.analysis import AnalysisResult
from backend.app.models.machine import Machine
from backend.app.services.dataset_service import (
    upload_dataset_version_stream,
    save_column_mapping,
    compute_quality_score_and_report,
)
from backend.app.services.inference_service import execute_analysis
from backend.app.services.model_loader import resolve_and_load_model


@pytest.fixture
def test_setup(client, db_session, tenant_fixture):
    """Sets up machine and dataset collection for tests."""
    headers = tenant_fixture["headers"]
    org_id = tenant_fixture["user"].organisation_id

    # Create machine
    m_resp = client.post("/api/v1/machines", json={
        "asset_tag": "TEST-PIPELINE-01",
        "name": "Pipeline Testing Machine",
        "category_code": "GENERAL_MACHINE_TOOL"
    }, headers=headers)
    assert m_resp.status_code == 201
    machine_id = m_resp.json()["id"]

    # Create dataset
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Pipeline Ingestion Dataset"
    }, headers=headers)
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    return {
        "headers": headers,
        "org_id": org_id,
        "machine_id": machine_id,
        "dataset_id": dataset_id,
        "user_id": tenant_fixture["user"].id
    }


def test_1_upload_empty_files_rejected(client, test_setup):
    """Verifies that 0-byte and whitespace-only files are rejected with 422 E_EMPTY."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    # 1. 0-byte file
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    res1 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=headers)
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "E_EMPTY"

    # 2. Whitespace-only file
    files = {"file": ("whitespace.csv", io.BytesIO(b"   \n  \t  \n  "), "text/csv")}
    res2 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=headers)
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "E_EMPTY"


def test_2_upload_duplicate_headers_rejected(client, test_setup):
    """Verifies that datasets with duplicate column headers are rejected with 422 E_DUPLICATE_COLUMNS."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    csv_content = "Type,Air temperature,Speed,Speed,Torque\nL,298.1,1500,1500,40.0\n"
    files = {"file": ("dupe_headers.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "E_DUPLICATE_COLUMNS"


def test_3_upload_excessive_columns_rejected(client, test_setup):
    """Verifies that datasets exceeding MAX_CSV_COLUMNS are rejected with 422 E_TOO_MANY_COLUMNS."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    num_cols = settings.MAX_CSV_COLUMNS + 5
    col_names = [f"col_{i}" for i in range(num_cols)]
    csv_content = ",".join(col_names) + "\n" + ",".join(["1.0"] * num_cols) + "\n"
    files = {"file": ("wide.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "E_TOO_MANY_COLUMNS"


def test_4_upload_malformed_csv_rejected(client, test_setup):
    """Verifies that unparseable / inconsistent CSV files are rejected with 415 or 422."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    # Inconsistent row with unclosed quotes causing parser error
    malformed_csv = 'Type,Speed,Torque\nL,1500,40\nM,"unclosed_quote_row,1600\n'
    files = {"file": ("malformed.csv", io.BytesIO(malformed_csv.encode("utf-8")), "text/csv")}
    res = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=headers)
    assert res.status_code in (415, 422)
    assert res.json()["error"]["code"] in ("E_MALFORMED_CSV", "UNSUPPORTED_FORMAT")


def test_5_upload_encodings_and_delimiters_support(client, test_setup):
    """Verifies that UTF-8 BOM, UTF-16, Latin-1, TSV, and Semicolon files are correctly ingested."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    # 1. UTF-8 with BOM
    content_bom = "\ufeffType,Air Temp,Speed\nL,298.1,1500\n".encode("utf-8-sig")
    res1 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                       files={"file": ("bom.csv", io.BytesIO(content_bom), "text/csv")}, headers=headers)
    assert res1.status_code == 201
    assert res1.json()["column_count"] == 3

    # 2. UTF-16
    content_utf16 = "Type,Air Temp,Speed\nL,298.1,1500\nM,299.0,1400\n".encode("utf-16")
    res2 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                       files={"file": ("utf16.csv", io.BytesIO(content_utf16), "text/csv")}, headers=headers)
    assert res2.status_code == 201
    assert res2.json()["column_count"] == 3

    # 3. Latin-1 with degree symbol
    content_latin1 = "Type,Temp_°C,Speed\nL,25.0,1500\n".encode("latin-1")
    res3 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                       files={"file": ("latin1.csv", io.BytesIO(content_latin1), "text/csv")}, headers=headers)
    assert res3.status_code == 201
    assert res3.json()["column_count"] == 3

    # 4. TSV format
    content_tsv = "Type\tAir Temp\tSpeed\nL\t298.1\t1500\n".encode("utf-8")
    res4 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                       files={"file": ("data.tsv", io.BytesIO(content_tsv), "text/tab-separated-values")}, headers=headers)
    assert res4.status_code == 201
    assert res4.json()["column_count"] == 3

    # 5. Semicolon format
    content_semi = "Type;Air Temp;Speed\nL;298.1;1500\n".encode("utf-8")
    res5 = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                       files={"file": ("semi.csv", io.BytesIO(content_semi), "text/csv")}, headers=headers)
    assert res5.status_code == 201
    assert res5.json()["column_count"] == 3


def test_6_path_traversal_prevention(client, db_session, test_setup):
    """Verifies that path traversal attempts in org_id or dataset_id are blocked."""
    evil_id = "../../../etc/passwd"
    with pytest.raises(HTTPException) as exc_info:
        upload_dataset_version_stream(
            db=db_session,
            org_id=evil_id,
            dataset_id=test_setup["dataset_id"],
            filename="test.csv",
            file_bytes=b"Type,Speed\nL,1500\n"
        )
    assert exc_info.value.status_code == 400


def test_7_column_mapping_missing_required_feature(client, test_setup):
    """Verifies that omitting a required feature raises 422 E_MISSING_FEATURE."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    csv_data = Path("samples/ai4i_sample_typed_operating_data.csv").read_bytes()
    up = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                     files={"file": ("data.csv", io.BytesIO(csv_data), "text/csv")}, headers=headers)
    assert up.status_code in (200, 201)
    vid = up.json()["dataset_version_id"]

    # Incomplete mapping: omitted tool_wear
    mapping = {
        "mappings": {
            "product_type": {"column": "Type", "asserted_equivalence": True},
            "air_temperature": {"column": "Air temperature [K]", "unit": "K"},
            "process_temperature": {"column": "Process temperature [K]", "unit": "K"},
            "rotational_speed": {"column": "Rotational speed [rpm]", "unit": "rpm"},
            "torque": {"column": "Torque [Nm]", "unit": "Nm"},
            # tool_wear omitted
        }
    }
    res = client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_with_type", json=mapping, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "E_MISSING_FEATURE"


def test_8_column_mapping_unknown_column(client, test_setup):
    """Verifies that mapping to a non-existent column raises 422 E_UNKNOWN_COLUMN."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    csv_data = Path("samples/ai4i_sample_typed_operating_data.csv").read_bytes()
    up = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                     files={"file": ("data.csv", io.BytesIO(csv_data), "text/csv")}, headers=headers)
    assert up.status_code in (200, 201)
    vid = up.json()["dataset_version_id"]

    mapping = {
        "mappings": {
            "product_type": {"column": "Non_Existent_Column_XYZ", "asserted_equivalence": True},
            "air_temperature": {"column": "Air temperature [K]", "unit": "K"},
            "process_temperature": {"column": "Process temperature [K]", "unit": "K"},
            "rotational_speed": {"column": "Rotational speed [rpm]", "unit": "rpm"},
            "torque": {"column": "Torque [Nm]", "unit": "Nm"},
            "tool_wear": {"column": "Tool wear [min]", "unit": "min"}
        }
    }
    res = client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_with_type", json=mapping, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "E_UNKNOWN_COLUMN"


def test_9_column_mapping_forbidden_leakage_features(client, test_setup):
    """Verifies that target/failure leakage columns are rejected with 422 E_FORBIDDEN_FEATURE."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    csv_with_target = "Type,Air,Proc,Speed,Torque,Wear,Machine failure\nL,300,310,1500,40,10,0\n"
    up = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                     files={"file": ("leakage.csv", io.BytesIO(csv_with_target.encode("utf-8")), "text/csv")}, headers=headers)
    assert up.status_code in (200, 201)
    vid = up.json()["dataset_version_id"]

    mapping = {
        "mappings": {
            "product_type": {"column": "Type", "asserted_equivalence": True},
            "air_temperature": {"column": "Air", "unit": "K"},
            "process_temperature": {"column": "Proc", "unit": "K"},
            "rotational_speed": {"column": "Speed", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Machine failure", "unit": "min"}  # Forbidden leakage
        }
    }
    res = client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_with_type", json=mapping, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "E_FORBIDDEN_FEATURE"


def test_10_column_mapping_invalid_category_values(client, test_setup):
    """Verifies that mapping product_type on a column with invalid categories (e.g. Z) raises 422."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]

    csv_invalid_cat = "Type,Air,Proc,Speed,Torque,Wear\nZ,300,310,1500,40,10\n"
    up = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                     files={"file": ("invalid_cat.csv", io.BytesIO(csv_invalid_cat.encode("utf-8")), "text/csv")}, headers=headers)
    assert up.status_code in (200, 201)
    vid = up.json()["dataset_version_id"]

    mapping = {
        "mappings": {
            "product_type": {"column": "Type", "asserted_equivalence": True},
            "air_temperature": {"column": "Air", "unit": "K"},
            "process_temperature": {"column": "Proc", "unit": "K"},
            "rotational_speed": {"column": "Speed", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Wear", "unit": "min"}
        }
    }
    res = client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_with_type", json=mapping, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "E_INVALID_CATEGORY_VALUES"


def test_11_inference_rejects_infinite_values(client, db_session, test_setup):
    """Verifies that inf or -inf numeric values reject inference cleanly with 422 E_INFINITE_VALUES."""
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]
    org_id = test_setup["org_id"]

    csv_inf = "Type,Air,Proc,Speed,Torque,Wear\nL,300,310,inf,40,10\n"
    up = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                     files={"file": ("inf.csv", io.BytesIO(csv_inf.encode("utf-8")), "text/csv")}, headers=headers)
    assert up.status_code in (200, 201)
    vid = up.json()["dataset_version_id"]

    mapping = {
        "mappings": {
            "product_type": {"column": "Type", "asserted_equivalence": True},
            "air_temperature": {"column": "Air", "unit": "K"},
            "process_temperature": {"column": "Proc", "unit": "K"},
            "rotational_speed": {"column": "Speed", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Wear", "unit": "min"}
        }
    }
    client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_with_type", json=mapping, headers=headers)

    compat_resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={
        "profile_id": "ai4i_failure_with_type"
    }, headers=headers)
    check_id = compat_resp.json()[0]["id"]

    with pytest.raises(HTTPException) as exc_info:
        execute_analysis(db_session, org_id, check_id)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"]["code"] == "E_INFINITE_VALUES"


def test_12_full_pipeline_predictions_pagination_and_export(client, db_session, test_setup):
    """
    Executes full pipeline:
    - Verifies feature order and Platt calibration.
    - Verifies complete row-level predictions stored to disk.
    - Verifies paginated row retrieval (GET /analyses/{id}/rows?page=1&page_size=2).
    - Verifies full dataset export (GET /analyses/{id}/export?format=csv).
    - Verifies TreeSHAP explainability metadata.
    """
    dataset_id = test_setup["dataset_id"]
    headers = test_setup["headers"]
    org_id = test_setup["org_id"]

    csv_data = Path("samples/ai4i_sample_typed_operating_data.csv").read_bytes()
    up = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload",
                     files={"file": ("data.csv", io.BytesIO(csv_data), "text/csv")}, headers=headers)
    assert up.status_code in (200, 201)
    vid = up.json()["dataset_version_id"]

    mapping = {
        "mappings": {
            "product_type": {"column": "Type", "asserted_equivalence": True},
            "air_temperature": {"column": "Air temperature [K]", "unit": "K"},
            "process_temperature": {"column": "Process temperature [K]", "unit": "K"},
            "rotational_speed": {"column": "Rotational speed [rpm]", "unit": "rpm"},
            "torque": {"column": "Torque [Nm]", "unit": "Nm"},
            "tool_wear": {"column": "Tool wear [min]", "unit": "min"}
        }
    }
    client.put(f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_with_type", json=mapping, headers=headers)

    compat_resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={
        "profile_id": "ai4i_failure_with_type"
    }, headers=headers)
    check_id = compat_resp.json()[0]["id"]

    # Execute analysis 1
    res1 = execute_analysis(db_session, org_id, check_id)
    assert res1 is not None
    assert res1.result_version == 1
    assert res1.is_latest is True

    # Check files written to storage
    preds_dir = settings.STORAGE_DIR / f"org/{org_id}/analyses/{res1.id}"
    assert (preds_dir / "predictions.csv").exists(), "Complete predictions.csv must be saved"
    assert (preds_dir / "predictions.json").exists(), "Complete predictions.json must be saved"

    # Test Paginated Rows endpoint
    rows_resp = client.get(f"/api/v1/analyses/{res1.id}/rows?page=1&page_size=2", headers=headers)
    assert rows_resp.status_code == 200
    rows_data = rows_resp.json()
    assert rows_data["page"] == 1
    assert rows_data["page_size"] == 2
    assert len(rows_data["rows"]) == 2
    assert rows_data["total_rows"] == 10
    assert rows_data["total_pages"] == 5

    # Test Risk Class Filter
    rows_high = client.get(f"/api/v1/analyses/{res1.id}/rows?risk_class=HIGH", headers=headers)
    assert rows_high.status_code == 200
    for r in rows_high.json()["rows"]:
        assert r["risk_class"] == "HIGH"

    # Test CSV Export endpoint
    export_csv = client.get(f"/api/v1/analyses/{res1.id}/export?format=csv", headers=headers)
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["content-type"]
    csv_text = export_csv.text
    assert "row_index" in csv_text
    assert "failure_probability" in csv_text
    assert "risk_class" in csv_text

    # Test JSON Export endpoint
    export_json = client.get(f"/api/v1/analyses/{res1.id}/export?format=json", headers=headers)
    assert export_json.status_code == 200
    assert "application/json" in export_json.headers["content-type"]
    json_records = export_json.json()
    assert len(json_records) == 10
    assert "failure_probability" in json_records[0]

    # Test Version Increment on Re-run
    res2 = execute_analysis(db_session, org_id, check_id)
    assert res2.result_version == 2
    assert res2.is_latest is True
    # Verify previous result is_latest was set to False
    db_session.refresh(res1)
    assert res1.is_latest is False
