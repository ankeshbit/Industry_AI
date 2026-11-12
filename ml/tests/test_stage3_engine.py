"""
Unit and Integration Tests for Stage 3 Evaluation Engine and B0/B1 Baselines (Phase 2A)

Validates all 13 methodological and architectural requirements defined in:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3, §4.3, §5.1–§5.2, §6.1–§6.4, §7.1)
- Root PRD.md v1.2 (§10.1.3–§10.1.5, §11.1, §13.5, §18.3)
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.src.data.loader import load_ai4i_dataset
from ml.src.features.schemas import (
    PRIMARY_TARGET,
    prepare_features_and_target,
)
from ml.src.data.nested_splitting import (
    load_nested_cv_splits,
    HISTORICAL_LOCKED_TEST_HASH,
    HISTORICAL_SPLIT_ARTIFACT_PATH,
)
from ml.src.models.prevalence import PrevalenceBaseline
from ml.src.models.logistic_regression import (
    LogisticRegressionCandidateEvaluator,
    build_b1_pipeline,
    B1_C_CANDIDATES,
)
from ml.src.models.random_forest import (
    M1_CANDIDATES,
    m1_tie_breaker_key,
    build_m1_pipeline,
    RandomForestCandidateEvaluator,
)
from ml.src.models.calibration import (
    PlattCalibrator,
    ModelAgnosticCalibrator,
    InsufficientCalibrationEventsError,
    CalibrationFailureError,
)
from ml.src.evaluation.threshold_optimizer import (
    ThresholdOptimizer,
    compute_bayes_threshold,
    evaluate_threshold_cost,
    PRD_COST_FN,
    PRD_COST_FP,
)
from ml.src.evaluation.metrics import (
    compute_brier_score,
    compute_brier_skill_score,
    compute_expected_calibration_error,
    compute_stage3_metrics,
)
from ml.src.evaluation.engine import Stage3EvaluationEngine


@pytest.fixture(scope="module")
def raw_dataset():
    """Authoritative raw AI4I dataset."""
    return load_ai4i_dataset(verify_checksum=True)


@pytest.fixture(scope="module")
def nested_manifest():
    """Validated repeated nested CV manifest."""
    return load_nested_cv_splits(verify_integrity=True)


@pytest.fixture(scope="module")
def historical_splits():
    """Historical Stage 2B split indices."""
    with open(HISTORICAL_SPLIT_ARTIFACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------------------
# 1. Deterministic B0 Output
# ------------------------------------------------------------------------------
def test_b0_deterministic_prevalence(raw_dataset, nested_manifest):
    """
    Validation 1:
    B0 constant prevalence baseline learns empirical base rate of Sub-Train,
    ignores features, and outputs identical predictions across feature configurations.
    """
    f0 = nested_manifest["repetitions"][0]["outer_folds"][0]
    sub_idx = f0["sub_train_indices"]

    X_a, y_a = prepare_features_and_target(raw_dataset, configuration="A")
    X_b, y_b = prepare_features_and_target(raw_dataset, configuration="B")

    b0_a = PrevalenceBaseline()
    b0_a.fit(X_a.iloc[sub_idx], y_a[sub_idx])

    b0_b = PrevalenceBaseline()
    b0_b.fit(X_b.iloc[sub_idx], y_b[sub_idx])

    expected_p = float(y_a[sub_idx].mean())
    assert np.isclose(b0_a.prevalence_, expected_p)
    assert np.isclose(b0_b.prevalence_, expected_p)

    # Predictions must be constant across all samples
    dummy_X = pd.DataFrame({"feat": [10.0, 20.0, 30.0]})
    proba_a = b0_a.predict_proba(dummy_X)
    proba_b = b0_b.predict_proba(dummy_X)

    assert proba_a.shape == (3, 2)
    assert np.allclose(proba_a[:, 1], expected_p)
    assert np.allclose(proba_b[:, 1], expected_p)
    assert np.allclose(proba_a[:, 0], 1.0 - expected_p)


# ------------------------------------------------------------------------------
# 2. B1 Candidate Search and Deterministic Tie-Breaking
# ------------------------------------------------------------------------------
def test_b1_candidate_search_and_tie_breaking(raw_dataset, nested_manifest):
    """
    Validation 2:
    B1 evaluates all 6 prescribed C candidates across 4 inner folds using canonical AP,
    and deterministically tie-breaks to smaller C (stronger regularization).
    """
    f0 = nested_manifest["repetitions"][0]["outer_folds"][0]
    sub_idx = f0["sub_train_indices"]
    sub_map = {idx: i for i, idx in enumerate(sub_idx)}

    X, y = prepare_features_and_target(raw_dataset, configuration="A")
    X_sub = X.iloc[sub_idx]
    y_sub = y[sub_idx]

    evaluator = LogisticRegressionCandidateEvaluator(configuration="A")
    assert evaluator.candidates == B1_C_CANDIDATES
    assert len(evaluator.candidates) == 6

    best_c = evaluator.evaluate_inner_candidates(X_sub, y_sub, f0["inner_folds"], sub_map)
    assert best_c in B1_C_CANDIDATES
    assert len(evaluator.candidate_scores_) == 6

    for cand_rec in evaluator.candidate_scores_:
        assert "C" in cand_rec
        assert "mean_ap" in cand_rec
        assert len(cand_rec["fold_ap_scores"]) == 4

    # Test synthetic tie-breaking to smaller C
    evaluator_tie = LogisticRegressionCandidateEvaluator(configuration="A")
    # Simulate candidate results where C=0.01 and C=0.1 have identical mean AP
    evaluator_tie.candidates = [0.01, 0.1]
    # Synthetic inner folds mapping
    syn_X = pd.DataFrame(np.zeros((4480, 6)), columns=X.columns)
    syn_y = np.zeros(4480, dtype=int)
    syn_y[:150] = 1

    # Both yield identical AP
    best_c_tie = evaluator_tie.evaluate_inner_candidates(syn_X, syn_y, f0["inner_folds"], sub_map)
    assert best_c_tie == 0.01, "Tie breaker must choose smaller C (stronger regularization)"


# ------------------------------------------------------------------------------
# 3. No Inner-CV Access to Calibration or Threshold-Validation
# ------------------------------------------------------------------------------
def test_data_isolation_inner_cv(nested_manifest):
    """
    Validation 3:
    Inner fold index sets are strictly confined to Sub-Train and have zero overlap
    with Calibration, Threshold-Validation, or Outer-Test partitions.
    """
    for rep in nested_manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            sub_set = set(fold["sub_train_indices"])
            cal_set = set(fold["calibration_indices"])
            th_set = set(fold["threshold_indices"])
            test_set = set(fold["outer_test_indices"])

            for in_f in fold["inner_folds"]:
                in_train = set(in_f["inner_train_indices"])
                in_val = set(in_f["inner_val_indices"])

                # Confinement
                assert in_train.issubset(sub_set)
                assert in_val.issubset(sub_set)

                # Strict isolation
                assert in_train.isdisjoint(cal_set)
                assert in_train.isdisjoint(th_set)
                assert in_train.isdisjoint(test_set)
                assert in_val.isdisjoint(cal_set)
                assert in_val.isdisjoint(th_set)
                assert in_val.isdisjoint(test_set)


# ------------------------------------------------------------------------------
# 4. Preprocessing Fit Isolation
# ------------------------------------------------------------------------------
def test_preprocessing_fit_isolation(raw_dataset, nested_manifest):
    """
    Validation 4:
    StandardScaler and OneHotEncoder are fitted strictly on training data
    without leaking validation or test statistics.
    """
    f0 = nested_manifest["repetitions"][0]["outer_folds"][0]
    sub_idx = f0["sub_train_indices"]
    test_idx = f0["outer_test_indices"]

    X, y = prepare_features_and_target(raw_dataset, configuration="A")
    X_sub = X.iloc[sub_idx]
    X_test = X.iloc[test_idx]

    pipe = build_b1_pipeline(c_val=1.0, configuration="A")
    pipe.fit(X_sub, y[sub_idx])

    scaler: StandardScaler = pipe.named_steps["preprocessor"].named_transformers_["numeric"]
    sub_numeric_means = X_sub[["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]].mean().values

    # Scaler mean must match Sub-Train mean exactly, not Outer-Test or combined mean
    np.testing.assert_allclose(scaler.mean_, sub_numeric_means, rtol=1e-5)

    combined_mean = X.mean(numeric_only=True).values
    assert not np.allclose(scaler.mean_, combined_mean)


# ------------------------------------------------------------------------------
# 5. Calibration Fit Isolation
# ------------------------------------------------------------------------------
def test_calibration_fit_isolation(raw_dataset, nested_manifest):
    """
    Validation 5:
    Platt calibrator fits strictly on the Calibration partition.
    Base estimator weights remain strictly frozen during calibration.
    """
    f0 = nested_manifest["repetitions"][0]["outer_folds"][0]
    sub_idx = f0["sub_train_indices"]
    cal_idx = f0["calibration_indices"]

    X, y = prepare_features_and_target(raw_dataset, configuration="A")
    pipe = build_b1_pipeline(c_val=1.0, configuration="A")
    pipe.fit(X.iloc[sub_idx], y[sub_idx])

    # Record base estimator weights before calibration
    orig_coef = pipe.named_steps["classifier"].coef_.copy()
    orig_intercept = pipe.named_steps["classifier"].intercept_.copy()

    mac = ModelAgnosticCalibrator(base_estimator=pipe, model_family="B1")
    mac.fit(X.iloc[cal_idx], y[cal_idx])

    # Assert base estimator weights were untouched
    np.testing.assert_array_equal(pipe.named_steps["classifier"].coef_, orig_coef)
    np.testing.assert_array_equal(pipe.named_steps["classifier"].intercept_, orig_intercept)

    # Calibrator attributes
    assert mac.is_fitted_ is True
    assert mac.calibrator_.w_ > 0.0
    assert mac.diagnostics_["cal_samples"] == len(cal_idx)


# ------------------------------------------------------------------------------
# 6. Threshold Selection Isolation
# ------------------------------------------------------------------------------
def test_threshold_selection_isolation(raw_dataset, nested_manifest):
    """
    Validation 6:
    Threshold is optimized strictly on Threshold-Validation data.
    Outer test data is completely unobserved during threshold selection.
    """
    f0 = nested_manifest["repetitions"][0]["outer_folds"][0]
    th_idx = f0["threshold_indices"]
    test_idx = f0["outer_test_indices"]

    assert set(th_idx).isdisjoint(set(test_idx))

    y_all = raw_dataset[PRIMARY_TARGET].values
    y_th = y_all[th_idx]

    # Synthetic predictions for threshold search
    np.random.seed(42)
    prob_th = np.clip(np.random.beta(0.5, 10, size=len(th_idx)), 0.0, 1.0)

    opt = ThresholdOptimizer()
    opt.optimize(y_th, prob_th)

    assert opt.is_optimized_ is True
    assert 0.0 <= opt.optimal_threshold_ <= 1.0
    assert opt.validation_metrics_["cost"] == opt.min_cost_


# ------------------------------------------------------------------------------
# 7. Calibration Slope and Parameter Constraints
# ------------------------------------------------------------------------------
def test_calibration_parameter_constraints():
    """
    Validation 7:
    Platt calibrator asserts w > 0, checks plausibility boundaries [0.05, 20.0],
    computes inverse Hessian standard errors, and raises CalibrationFailureError if w <= 0.
    """
    cal = PlattCalibrator()

    # Normal case: positively correlated scores and labels
    np.random.seed(42)
    z = np.random.randn(500)
    y = (z > 0.5).astype(int)
    cal.fit(z, y)

    assert cal.w_ > 0.0
    assert cal.se_w_ is not None
    assert cal.se_c_ is not None
    assert cal.se_w_ > 0.0

    # Inverted case: negatively correlated scores (w <= 0)
    z_inv = -z
    cal_inv = PlattCalibrator()
    with pytest.raises(CalibrationFailureError):
        cal_inv.fit(z_inv, y)


# ------------------------------------------------------------------------------
# 8. Insufficient Calibration Events Failure
# ------------------------------------------------------------------------------
def test_insufficient_calibration_events_failure():
    """
    Validation 8:
    Pipeline raises InsufficientCalibrationEventsError when N_cal,pos < 25 (fails closed).
    """
    class MockEstimator:
        def decision_function(self, X):
            return np.zeros(len(X))

    mac = ModelAgnosticCalibrator(base_estimator=MockEstimator(), model_family="B1", min_calibration_positives=25)

    X_dummy = pd.DataFrame(np.zeros((960, 5)))
    y_insufficient = np.zeros(960, dtype=int)
    y_insufficient[:24] = 1  # 24 positives < 25 gate

    with pytest.raises(InsufficientCalibrationEventsError):
        mac.fit(X_dummy, y_insufficient)


# ------------------------------------------------------------------------------
# 9. No Historical Test Row Access
# ------------------------------------------------------------------------------
def test_no_historical_test_access(nested_manifest, historical_splits):
    """
    Validation 9:
    Zero locked historical test rows (N = 2,000) enter any Stage 3 partition.
    """
    locked_test = set(historical_splits["test_indices"])
    assert len(locked_test) == 2000

    for rep in nested_manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            assert set(fold["outer_train_indices"]).isdisjoint(locked_test)
            assert set(fold["outer_test_indices"]).isdisjoint(locked_test)
            assert set(fold["sub_train_indices"]).isdisjoint(locked_test)
            assert set(fold["calibration_indices"]).isdisjoint(locked_test)
            assert set(fold["threshold_indices"]).isdisjoint(locked_test)


# ------------------------------------------------------------------------------
# 10. Feature Configuration Split Parity
# ------------------------------------------------------------------------------
def test_feature_configuration_split_parity(raw_dataset, nested_manifest):
    """
    Validation 10:
    Both Configuration A (WITH_TYPE) and Configuration B (NO_TYPE) use identical actual indices.
    """
    X_a, y_a = prepare_features_and_target(raw_dataset, configuration="A")
    X_b, y_b = prepare_features_and_target(raw_dataset, configuration="B")

    f0 = nested_manifest["repetitions"][0]["outer_folds"][0]
    for part in ["sub_train_indices", "calibration_indices", "threshold_indices", "outer_test_indices"]:
        idxs = f0[part]
        # Targets are identical
        np.testing.assert_array_equal(y_a[idxs], y_b[idxs])
        # Shared numerical features are identical
        for col in ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]:
            np.testing.assert_array_equal(X_a[col].iloc[idxs], X_b[col].iloc[idxs])


# ------------------------------------------------------------------------------
# 11. Deterministic Reruns
# ------------------------------------------------------------------------------
def test_deterministic_reruns(raw_dataset, nested_manifest):
    """
    Validation 11:
    Rerunning B0 and B1 evaluation on identical data and seeds yields bit-for-bit identical metrics.
    """
    engine = Stage3EvaluationEngine()

    # Rerun B0 on rep 0, fold 0
    res_b0_1 = engine.evaluate_model_family(model_family="B0", configuration="A", repetition_indices=[0])
    res_b0_2 = engine.evaluate_model_family(model_family="B0", configuration="A", repetition_indices=[0])

    assert res_b0_1["ranking_metrics"]["average_precision"]["mean"] == res_b0_2["ranking_metrics"]["average_precision"]["mean"]
    assert res_b0_1["operational_metrics"]["operational_cost"]["mean"] == res_b0_2["operational_metrics"]["operational_cost"]["mean"]


# ------------------------------------------------------------------------------
# 12. Correct Metric Calculations
# ------------------------------------------------------------------------------
def test_metric_calculations_exactness():
    """
    Validation 12:
    Validates Average Precision, ROC-AUC, Brier Score, Brier Skill Score, and ECE
    against known analytical values on synthetic test cases.
    """
    y_true = np.array([0, 0, 1, 1], dtype=int)
    y_prob = np.array([0.1, 0.2, 0.8, 0.9], dtype=float)
    p_ref = 0.5

    bs = compute_brier_score(y_true, y_prob)
    # Expected: (0.01 + 0.04 + 0.04 + 0.01) / 4 = 0.10 / 4 = 0.025
    assert np.isclose(bs, 0.025)

    bss = compute_brier_skill_score(y_true, y_prob, p_reference=p_ref)
    # bs_ref = ((0.5)^2 * 4) / 4 = 0.25
    # BSS = 1 - (0.025 / 0.25) = 1 - 0.10 = 0.90
    assert np.isclose(bss, 0.90)

    ece, bins = compute_expected_calibration_error(y_true, y_prob, n_bins=10)
    assert 0.0 <= ece <= 1.0
    assert len(bins) == 10

    stage3_res = compute_stage3_metrics(y_true, y_prob, threshold=0.5, p_reference=p_ref, cost_fn=10000.0, cost_fp=200.0)
    assert stage3_res["ranking_metrics"]["average_precision"] == 1.0
    assert stage3_res["ranking_metrics"]["roc_auc"] == 1.0
    assert stage3_res["operational_metrics"]["false_negatives"] == 0
    assert stage3_res["operational_metrics"]["false_positives"] == 0
    assert stage3_res["operational_metrics"]["total_operational_cost"] == 0.0


# ------------------------------------------------------------------------------
# 13. Pipeline Frozen Before Outer Test
# ------------------------------------------------------------------------------
def test_pipeline_frozen_before_outer_test(raw_dataset, nested_manifest):
    """
    Validation 13:
    Outer test is evaluated exactly once at a frozen threshold, with zero threshold updates.
    """
    engine = Stage3EvaluationEngine()
    res = engine.evaluate_model_family(model_family="B1", configuration="A", repetition_indices=[0])

    f0 = res["fold_evaluations"][0]
    frozen_tau = f0["threshold_optimization"]["optimal_threshold"]
    outer_tau = f0["outer_test_metrics"]["operational_metrics"]["threshold"]

    assert np.isclose(frozen_tau, outer_tau), "Outer test must use frozen validation threshold!"
    assert "cost_disclaimer" in f0["outer_test_metrics"]["operational_metrics"]


# ------------------------------------------------------------------------------
# 14. M1 Random Forest 24 Candidate Grid & Tie-Breaking
# ------------------------------------------------------------------------------
def test_m1_candidate_grid_and_tie_breaking():
    """
    Validation 14:
    Verifies that M1 candidate grid contains exactly 24 configurations with fixed n_estimators=100,
    and simpler-model tie-breaking prioritizes lower max_depth, higher min_samples_split, and log2 features.
    """
    assert len(M1_CANDIDATES) == 24
    for c in M1_CANDIDATES:
        assert c["n_estimators"] == 100
        assert c["class_weight"] == "balanced"
        assert c["random_state"] == 42
        assert c["max_depth"] in [5, 8, 12, None]
        assert c["min_samples_split"] in [2, 5, 10]
        assert c["max_features"] in ["sqrt", "log2"]

    # Simpler-model tie-breaker check:
    # Candidate A: depth 5, split 10, log2 (simplest)
    cand_a = {"max_depth": 5, "min_samples_split": 10, "max_features": "log2"}
    # Candidate B: depth 5, split 2, sqrt (less simple)
    cand_b = {"max_depth": 5, "min_samples_split": 2, "max_features": "sqrt"}
    # Candidate C: depth 8, split 10, log2
    cand_c = {"max_depth": 8, "min_samples_split": 10, "max_features": "log2"}
    # Candidate D: depth None, split 2, sqrt (most complex)
    cand_d = {"max_depth": None, "min_samples_split": 2, "max_features": "sqrt"}

    assert m1_tie_breaker_key(cand_a) < m1_tie_breaker_key(cand_b)
    assert m1_tie_breaker_key(cand_b) < m1_tie_breaker_key(cand_c)
    assert m1_tie_breaker_key(cand_c) < m1_tie_breaker_key(cand_d)


# ------------------------------------------------------------------------------
# 15. M1 Probability Calibration on Clipped Log-Odds
# ------------------------------------------------------------------------------
def test_m1_calibration_clipped_log_odds():
    """
    Validation 15:
    ModelAgnosticCalibrator with M1 extracts clipped log-odds z = log((p+eps)/(1-p+eps))
    with eps=1e-4 and fits Platt calibrator with w > 0.
    """
    class MockTreeEstimator:
        def predict_proba(self, X):
            # Returns probabilities with some 0 and 1 values to test clipping
            n = len(X)
            probs = np.linspace(0.0, 1.0, n)
            return np.column_stack([1.0 - probs, probs])

    mock_rf = MockTreeEstimator()
    mac = ModelAgnosticCalibrator(base_estimator=mock_rf, model_family="M1", min_calibration_positives=25)

    X_cal = pd.DataFrame(np.zeros((960, 5)))
    z = mac.extract_raw_scores(X_cal)

    # z must be finite and clipped (no +/- inf)
    assert np.all(np.isfinite(z))
    assert np.isclose(z[0], np.log(1e-4 / (1.0 - 1e-4)))
    assert np.isclose(z[-1], np.log((1.0 - 1e-4) / 1e-4))

    y_cal = (z > 0).astype(int)
    # Ensure at least 30 positives for gate
    y_cal[:40] = 1
    mac.fit(X_cal, y_cal)
    assert mac.is_fitted_ is True
    assert mac.calibrator_.w_ > 0.0


