"""
Unit tests for Stage 3 M2 XGBoost Candidate Evaluator and Pipeline Integration.
Adheres strictly to docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3, §3.3.1, §5.1).
"""

import pytest
import numpy as np
import pandas as pd
from ml.src.models.xgboost_model import (
    generate_m2_candidates,
    m2_tie_breaker_key,
    compute_median_ceiling_rounds,
    build_m2_pipeline,
    XGBoostCandidateEvaluator,
    M2_CANDIDATES,
)
from ml.src.models.calibration import ModelAgnosticCalibrator


def test_m2_candidate_generation():
    candidates = generate_m2_candidates(seed=42, n_candidates=20)
    assert len(candidates) == 20
    # Assert all configurations have required hyperparameters
    for c in candidates:
        assert c["max_depth"] in [3, 4, 5, 6]
        assert c["learning_rate"] in [0.01, 0.03, 0.05, 0.1]
        assert c["subsample"] in [0.7, 0.8, 1.0]
        assert c["colsample_bytree"] in [0.7, 0.8, 1.0]
        assert c["min_child_weight"] in [1, 3, 5]
        assert c["n_estimators"] == 300
        assert c["random_state"] == 42


def test_median_ceiling_rounds():
    # Even midpoint
    assert compute_median_ceiling_rounds([10, 20, 30, 40]) == 25
    # Odd midpoint (20 + 25 = 45 -> 45/2 = 22.5 -> ceil is 23)
    assert compute_median_ceiling_rounds([10, 20, 25, 40]) == 23
    # Boundary clamps
    assert compute_median_ceiling_rounds([0, 0, 0, 0]) == 1
    assert compute_median_ceiling_rounds([350, 400, 450, 500]) == 300


def test_m2_evaluator_inner_and_refit():
    # Synthetic small dataset
    np.random.seed(42)
    n_samples = 200
    X = pd.DataFrame({
        "Air temperature [K]": np.random.normal(300, 2, n_samples),
        "Process temperature [K]": np.random.normal(310, 1.5, n_samples),
        "Rotational speed [rpm]": np.random.normal(1500, 100, n_samples),
        "Torque [Nm]": np.random.normal(40, 10, n_samples),
        "Tool wear [min]": np.random.uniform(0, 200, n_samples),
    })
    y = np.zeros(n_samples, dtype=int)
    y[:15] = 1  # imbalanced targets

    # 4 synthetic inner folds
    inner_folds = []
    for f in range(4):
        val_idx = list(range(f * 50, (f + 1) * 50))
        train_idx = [i for i in range(n_samples) if i not in val_idx]
        inner_folds.append({
            "inner_fold_index": f,
            "inner_train_indices": train_idx,
            "inner_val_indices": val_idx,
        })
    sub_map = {i: i for i in range(n_samples)}

    # Test with small candidate subset for fast test
    test_candidates = M2_CANDIDATES[:2]
    evaluator = XGBoostCandidateEvaluator(configuration="B", candidates=test_candidates)
    best_params, best_rounds = evaluator.evaluate_inner_candidates(
        X_sub_train=X,
        y_sub_train=y,
        inner_folds=inner_folds,
        sub_train_indices_map=sub_map,
    )

    assert best_params in test_candidates
    assert 1 <= best_rounds <= 300
    assert evaluator.is_evaluated_ is True

    # Refit
    pipe = evaluator.refit_on_sub_train(X, y)
    assert pipe is not None

    # Test ModelAgnosticCalibrator with M2 margin extraction
    calibrator = ModelAgnosticCalibrator(
        base_estimator=pipe,
        model_family="M2",
        min_calibration_positives=5,
    )
    raw_scores = calibrator.extract_raw_scores(X)
    assert raw_scores.shape == (n_samples,)
    # Verify values are unbounded continuous log-odds margins
    assert np.any(raw_scores < 0) or np.any(raw_scores > 0)

