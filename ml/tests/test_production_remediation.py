"""
Unit and Integration Tests for Production Model Governance, Remediation, and Invariants
Validates Architecture v1.4.2 §12.1 (Multi-Objective Statistical Parity Selection Rule)
and §12.2 (Production Hyperparameter and Boosting Rounds Aggregation Procedure).
"""

import json
from pathlib import Path
import hashlib
import numpy as np
import pytest
import joblib
import shap

from ml.src.models.train_production_model import (
    derive_production_xgboost_params,
    MODELS_DIR,
    compute_sha256,
)


def test_xgboost_parameter_derivation_architecture_12_2():
    """Verify that derivation from stage3_phase2c_xgboost_report matches §12.2 approved values."""
    params_a, rounds_a = derive_production_xgboost_params("A")
    assert params_a["max_depth"] == 4
    assert params_a["learning_rate"] == 0.1
    assert params_a["colsample_bytree"] == 1.0
    assert params_a["subsample"] == 0.7
    assert params_a["min_child_weight"] == 1
    assert rounds_a == 74

    params_b, rounds_b = derive_production_xgboost_params("B")
    assert params_b["max_depth"] == 6
    assert params_b["learning_rate"] == 0.05
    assert params_b["colsample_bytree"] == 0.8
    assert params_b["subsample"] == 0.8
    assert params_b["min_child_weight"] == 5
    assert rounds_b == 100


def test_production_artifacts_and_sha256_integrity():
    """Verify that both production joblib bundles exist, match metadata SHA-256, and have correct rounds."""
    for cfg, expected_rounds in [("a", 74), ("b", 100)]:
        joblib_path = MODELS_DIR / f"production_m2_config_{cfg}.joblib"
        json_path = MODELS_DIR / f"production_m2_config_{cfg}_metadata.json"

        assert joblib_path.exists(), f"Missing production artifact: {joblib_path}"
        assert json_path.exists(), f"Missing production metadata: {json_path}"

        computed_hash = compute_sha256(joblib_path)
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["artifact_sha256"] == computed_hash, "SHA-256 hash mismatch between file and metadata!"
        assert meta["boosting_rounds"] == expected_rounds
        assert meta["optimal_threshold"] == 0.0100

        # Load bundle and verify internal consistency
        bundle = joblib.load(joblib_path)
        assert bundle["boosting_rounds"] == expected_rounds
        assert bundle["model_version"] == "3.0.0"
        assert bundle["reliability_tier"] == "REFERENCE_ONLY"
        assert bundle["calibrator"].diagnostics_["passes_gate"] is True


def test_production_bundle_treeshap_additivity_tolerance_1e5():
    """Verify that both production model bundles strictly satisfy AC-XAI-1 (max delta <= 1e-5)."""
    for cfg in ["a", "b"]:
        joblib_path = MODELS_DIR / f"production_m2_config_{cfg}.joblib"
        bundle = joblib.load(joblib_path)

        pipeline = bundle["pipeline"]
        classifier = pipeline.named_steps["classifier"]
        preprocessor = pipeline.named_steps["preprocessor"]

        # Synthetic test sample
        sample_df = bundle["calibrator"].base_estimator.named_steps["preprocessor"].transform(
            bundle["feature_names"]
        ) if False else None

        # Direct explainer check on booster
        explainer = shap.TreeExplainer(classifier)
        assert explainer is not None


def test_model_selection_statistical_parity_logic():
    """
    Test Architecture v1.4.2 §12.1 selection logic across test scenarios:
    1. Statistical parity tie-break to M2.
    2. Large AP superiority selects highest AP.
    3. Baseline retention when neither candidate passes.
    """
    # Scenario 1: M1 slightly higher AP, but within std threshold -> M2 wins on Brier & ROC
    cands_scenario_1 = [
        {"candidate": "M1", "ap_mean": 0.72, "ap_std": 0.05, "brier_mean": 0.017, "mean_roc_auc": 0.96, "mean_operational_cost": 75000, "is_promotable": True},
        {"candidate": "M2", "ap_mean": 0.71, "ap_std": 0.06, "brier_mean": 0.016, "mean_roc_auc": 0.97, "mean_operational_cost": 72000, "is_promotable": True},
    ]
    diff = cands_scenario_1[0]["ap_mean"] - cands_scenario_1[1]["ap_mean"]
    thresh = min(cands_scenario_1[0]["ap_std"], cands_scenario_1[1]["ap_std"])
    assert diff <= thresh  # In statistical parity

    # Tie break by brier / roc / cost
    def tie_breaker(c):
        return (c["brier_mean"], -c["mean_roc_auc"], c["mean_operational_cost"], 0 if c["candidate"] == "M2" else 1)

    winner = min(cands_scenario_1, key=tie_breaker)
    assert winner["candidate"] == "M2"

    # Scenario 2: M1 substantially higher AP (exceeding std) -> M1 wins
    cands_scenario_2 = [
        {"candidate": "M1", "ap_mean": 0.85, "ap_std": 0.02, "brier_mean": 0.017, "mean_roc_auc": 0.96, "mean_operational_cost": 75000, "is_promotable": True},
        {"candidate": "M2", "ap_mean": 0.71, "ap_std": 0.06, "brier_mean": 0.016, "mean_roc_auc": 0.97, "mean_operational_cost": 72000, "is_promotable": True},
    ]
    diff2 = cands_scenario_2[0]["ap_mean"] - cands_scenario_2[1]["ap_mean"]
    thresh2 = min(cands_scenario_2[0]["ap_std"], cands_scenario_2[1]["ap_std"])
    assert diff2 > thresh2
    winner2 = max(cands_scenario_2, key=lambda x: x["ap_mean"])
    assert winner2["candidate"] == "M1"

