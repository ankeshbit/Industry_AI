"""
Production Model Loading, Inference, Integrity, and Provenance Test Suite
Validates:
1. Both production model configurations (WITH_TYPE and NO_TYPE) load and execute.
2. Missing artifacts return clear HTTP 503 errors with provisioning instructions.
3. Corrupted artifacts return clear HTTP 500 errors.
4. Schema and bundle structure validation.
5. Consistent 0.0100 decision threshold across database, loaded bundle, API, and inference results.
6. Database model registry consistency with filesystem metadata.
7. End-to-end analysis execution, Platt calibration, TreeSHAP margin additivity, and provenance.
"""

import io
import os
import json
import shutil
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from fastapi import HTTPException

from backend.app.config import settings
from backend.app.models.compatibility import PipelineProfile, CompatibilityCheck
from backend.app.models.dataset import DatasetVersion, ColumnMapping
from backend.app.models.model import ModelVersion
from backend.app.models.machine import Machine
from backend.app.services.model_loader import (
    resolve_and_load_model,
    validate_model_bundle_structure,
    resolve_expected_artifact,
    compute_file_checksum,
    clear_model_cache,
    LoadedModelBundle,
)
from backend.app.services.inference_service import execute_analysis


def test_1_model_registry_consistency(db_session):
    """Verifies production ModelVersion records in DB match the Stage 3 contract."""
    models = db_session.query(ModelVersion).filter(ModelVersion.stage == "PRODUCTION").all()
    assert len(models) == 2, f"Expected 2 production models, found {len(models)}"

    reg_map = {m.configuration: m for m in models}
    assert "WITH_TYPE" in reg_map
    assert "NO_TYPE" in reg_map

    for cfg, m in reg_map.items():
        assert m.thresholds is not None
        assert m.thresholds.get("optimal_tau") == 0.01, f"{cfg} optimal_tau must be 0.0100"
        assert m.thresholds.get("cost_ratio") == 50.0
        assert "Platt" in m.algorithm or "Calibrated" in m.algorithm

        # Verify evaluations
        eval_metrics = {e.metric_name: e.metric_value for e in m.evaluations}
        assert "ROC-AUC" in eval_metrics
        assert "PR-AUC" in eval_metrics
        assert "Precision" in eval_metrics
        assert "Recall" in eval_metrics
        assert eval_metrics["Recall"] >= 0.90, "Model must achieve target high recall at 50:1 cost ratio"


def test_2_production_artifacts_load_and_validate(db_session):
    """Verifies that both WITH_TYPE and NO_TYPE production artifacts load cleanly."""
    clear_model_cache()
    profile_typed = db_session.query(PipelineProfile).filter(PipelineProfile.configuration == "WITH_TYPE").first()
    profile_notype = db_session.query(PipelineProfile).filter(PipelineProfile.configuration == "NO_TYPE").first()

    assert profile_typed is not None
    assert profile_notype is not None

    bundle_a = resolve_and_load_model(db_session, profile_typed)
    assert isinstance(bundle_a, LoadedModelBundle)
    assert bundle_a.configuration == "WITH_TYPE"
    assert bundle_a.optimal_threshold == 0.01
    assert "Type" in bundle_a.feature_names
    assert len(bundle_a.feature_names) == 6
    assert hasattr(bundle_a.calibrator, "predict_proba")

    bundle_b = resolve_and_load_model(db_session, profile_notype)
    assert isinstance(bundle_b, LoadedModelBundle)
    assert bundle_b.configuration == "NO_TYPE"
    assert bundle_b.optimal_threshold == 0.01
    assert "Type" not in bundle_b.feature_names
    assert len(bundle_b.feature_names) == 5
    assert hasattr(bundle_b.calibrator, "predict_proba")


def test_3_missing_artifact_raises_503(db_session, monkeypatch, tmp_path):
    """Verifies that a missing artifact triggers an explicit 503 error."""
    clear_model_cache()
    profile = db_session.query(PipelineProfile).filter(PipelineProfile.configuration == "NO_TYPE").first()

    # Point models_dir to an empty temporary directory
    fake_models_dir = tmp_path / "empty_models"
    fake_models_dir.mkdir()

    def fake_resolve(configuration):
        return "production_m2_config_b.joblib", fake_models_dir / "production_m2_config_b.joblib", fake_models_dir / "production_m2_config_b_metadata.json"

    monkeypatch.setattr("backend.app.services.model_loader.resolve_expected_artifact", fake_resolve)

    with pytest.raises(HTTPException) as exc_info:
        resolve_and_load_model(db_session, profile)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error"]["code"] == "MODEL_ARTIFACT_NOT_FOUND"
    assert "provision_artifacts" in exc_info.value.detail["error"]["message"]


def test_4_corrupted_artifact_raises_500(db_session, monkeypatch, tmp_path):
    """Verifies that a corrupted artifact (checksum mismatch) raises HTTP 500."""
    clear_model_cache()
    profile = db_session.query(PipelineProfile).filter(PipelineProfile.configuration == "NO_TYPE").first()

    corrupt_dir = tmp_path / "corrupt_models"
    corrupt_dir.mkdir()

    fake_joblib = corrupt_dir / "production_m2_config_b.joblib"
    fake_joblib.write_bytes(b"corrupted binary data")

    fake_meta = corrupt_dir / "production_m2_config_b_metadata.json"
    fake_meta.write_text(json.dumps({"artifact_sha256": "expected_valid_sha256_hash_value"}), encoding="utf-8")

    def fake_resolve(configuration):
        return "production_m2_config_b.joblib", fake_joblib, fake_meta

    monkeypatch.setattr("backend.app.services.model_loader.resolve_expected_artifact", fake_resolve)

    with pytest.raises(HTTPException) as exc_info:
        resolve_and_load_model(db_session, profile)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail["error"]["code"] == "MODEL_ARTIFACT_CORRUPTED"


def test_5_structural_validation_catches_invalid_bundles():
    """Verifies validate_model_bundle_structure rejects malformed bundles."""
    with pytest.raises(HTTPException) as exc1:
        validate_model_bundle_structure("not_a_dict", "WITH_TYPE")
    assert exc1.value.detail["error"]["code"] == "INVALID_MODEL_BUNDLE"

    # Missing keys
    with pytest.raises(HTTPException) as exc2:
        validate_model_bundle_structure({"pipeline": None}, "WITH_TYPE")
    assert exc2.value.detail["error"]["code"] == "MALFORMED_MODEL_BUNDLE"

    # Invalid threshold
    invalid_tau_bundle = {
        "pipeline": type("MockPipe", (), {"named_steps": {"preprocessor": 1, "classifier": 2}})(),
        "calibrator": type("MockCal", (), {"predict_proba": lambda x: x})(),
        "optimal_threshold": 1.5,  # > 1.0 invalid
        "feature_names": ["a"],
        "configuration": "WITH_TYPE"
    }
    with pytest.raises(HTTPException) as exc3:
        validate_model_bundle_structure(invalid_tau_bundle, "WITH_TYPE")
    assert exc3.value.detail["error"]["code"] == "INVALID_THRESHOLD"


def test_6_threshold_consistency_across_surfaces(client, db_session):
    """Verifies that decision threshold is 0.0100 consistently across all surfaces."""
    # 1. API endpoint /api/v1/models
    res = client.get("/api/v1/models")
    assert res.status_code == 200
    models_api = res.json()
    assert len(models_api) == 2
    for m in models_api:
        assert m["optimal_threshold"] == 0.01
        assert m["cost_ratio"] == 50.0
        assert m["thresholds"]["optimal_tau"] == 0.01

    # 2. ModelVersion DB records
    for m in db_session.query(ModelVersion).filter(ModelVersion.stage == "PRODUCTION").all():
        assert m.thresholds["optimal_tau"] == 0.01

    # 3. Model bundles on disk
    clear_model_cache()
    for cfg in ["WITH_TYPE", "NO_TYPE"]:
        profile = db_session.query(PipelineProfile).filter(PipelineProfile.configuration == cfg).first()
        bundle = resolve_and_load_model(db_session, profile)
        assert bundle.optimal_threshold == 0.01


def test_7_end_to_end_analysis_execution_and_shap(client, db_session, tenant_fixture):
    """Executes a full end-to-end analysis on sample data and validates all requirements."""
    # 1. Create machine and dataset via API
    m_resp = client.post("/api/v1/machines", json={
        "asset_tag": "CNC-01",
        "name": "CNC Milling Station 01",
        "category_code": "GENERAL_MACHINE_TOOL"
    }, headers=tenant_fixture["headers"])
    assert m_resp.status_code == 201
    machine_id = m_resp.json()["id"]

    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Production Operating Telemetry"
    }, headers=tenant_fixture["headers"])
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    csv_data = Path("samples/ai4i_sample_typed_operating_data.csv").read_bytes()
    files = {"file": ("data.csv", io.BytesIO(csv_data), "text/csv")}
    up_resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=tenant_fixture["headers"])
    assert up_resp.status_code in (200, 201)
    vid = up_resp.json()["dataset_version_id"]

    # 2. Map features
    profile_id = "ai4i_failure_with_type"
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
    map_resp = client.put(f"/api/v1/dataset-versions/{vid}/mappings/{profile_id}", json=mapping, headers=tenant_fixture["headers"])
    assert map_resp.status_code == 200

    # 3. Check compatibility
    compat_resp = client.post(f"/api/v1/dataset-versions/{vid}/compatibility-checks", json={
        "profile_id": profile_id
    }, headers=tenant_fixture["headers"])
    assert compat_resp.status_code == 201
    checks = compat_resp.json()
    assert len(checks) > 0
    check_id = checks[0]["id"]
    assert checks[0]["compatibility"]["status"] in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS")

    # 4. Execute Analysis
    org_id = tenant_fixture["user"].organisation_id
    result = execute_analysis(db_session, org_id, check_id)
    assert result is not None
    assert result.result_version == 1
    assert result.is_latest is True

    # Validate Summary
    assert result.summary["threshold_used"] == 0.01
    assert "provenance" in result.summary

    provenance = result.summary["provenance"]
    assert provenance["decision_threshold"] == 0.01
    assert provenance["cost_ratio"] == 50.0
    assert provenance["calibration_method"] == "Platt Scaling (Logistic Sigmoid)"
    assert len(provenance["artifact_sha256"]) == 64

    # Validate TreeSHAP attributions
    assert result.explanation_meta is not None
    assert result.explanation_meta["method"] == "FactorAttribution"
    assert result.explanation_meta["additivity_verified"] is True
    assert result.explanation_meta["max_reconstruction_delta"] <= 1e-5

    # Validate Top Rows
    assert len(result.top_rows) > 0
    for row in result.top_rows:
        assert 0.0 <= row["failure_probability"] <= 1.0
        assert row["risk_class"] in ("LOW", "MEDIUM", "HIGH")
        assert "feature_attributions" in row
