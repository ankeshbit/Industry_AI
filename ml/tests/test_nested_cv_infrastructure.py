"""
Unit and Integration Tests for Stage 3 Repeated Nested Cross-Validation Infrastructure

Validates all 12 architectural requirements defined in:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§2.2, §4.1, §4.3, §5.2)
- Root PRD.md v1.2 (§10.1.3–§10.1.5)
"""

import json
from pathlib import Path
import numpy as np
import pytest

from ml.src.data.loader import load_ai4i_dataset
from ml.src.features.schemas import (
    AI4I_SHA256_CHECKSUM,
    PRIMARY_TARGET,
    prepare_features_and_target,
)
from ml.src.data.nested_splitting import (
    generate_repeated_nested_cv_manifest,
    load_nested_cv_splits,
    compute_indices_hash,
    HISTORICAL_TRAIN_INDEX_HASH,
    HISTORICAL_LOCKED_TEST_HASH,
    DEFAULT_NESTED_CV_ARTIFACT_PATH,
    HISTORICAL_SPLIT_ARTIFACT_PATH,
)


@pytest.fixture(scope="module")
def manifest():
    """Load the authoritative serialized Stage 3 nested CV manifest."""
    assert DEFAULT_NESTED_CV_ARTIFACT_PATH.is_file(), (
        f"Artifact missing: {DEFAULT_NESTED_CV_ARTIFACT_PATH}. Run generator first."
    )
    return load_nested_cv_splits(DEFAULT_NESTED_CV_ARTIFACT_PATH, verify_integrity=True)


@pytest.fixture(scope="module")
def historical_splits():
    """Load the historical Stage 2B split indices for cross-validation checks."""
    assert HISTORICAL_SPLIT_ARTIFACT_PATH.is_file()
    with open(HISTORICAL_SPLIT_ARTIFACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def raw_dataset():
    """Load the authoritative raw AI4I dataset."""
    df = load_ai4i_dataset(verify_checksum=True)
    assert len(df) == 10000
    return df


def test_req1_repetitions_and_outer_fold_counts(manifest):
    """
    Validation Point 1:
    Exactly 5 repetitions, each with 5 outer folds (25 outer evaluations total).
    """
    assert manifest["metadata"]["n_repetitions"] == 5
    assert manifest["metadata"]["outer_k"] == 5
    assert manifest["metadata"]["inner_k"] == 4

    repetitions = manifest["repetitions"]
    assert len(repetitions) == 5

    total_outer_folds = 0
    for r_idx, rep in enumerate(repetitions):
        assert rep["repetition_index"] == r_idx
        folds = rep["outer_folds"]
        assert len(folds) == 5, f"Repetition {r_idx} should have exactly 5 folds, got {len(folds)}"
        total_outer_folds += len(folds)

    assert total_outer_folds == 25


def test_req2_outer_test_partition_coverage(manifest, historical_splits):
    """
    Validation Point 2:
    Every development observation (N = 8,000) is assigned to exactly one
    outer test fold per repetition (exact partition).
    """
    dev_set = set(historical_splits["train_indices"])
    assert len(dev_set) == 8000

    for rep in manifest["repetitions"]:
        rep_test_indices = []
        for fold in rep["outer_folds"]:
            outer_test = fold["outer_test_indices"]
            assert len(outer_test) == 1600
            rep_test_indices.extend(outer_test)

        assert len(rep_test_indices) == 8000
        assert len(set(rep_test_indices)) == 8000
        assert set(rep_test_indices) == dev_set


def test_req3_outer_train_test_disjointness(manifest):
    """
    Validation Point 3:
    Outer train (N = 6,400) and outer test (N = 1,600) are strictly disjoint.
    """
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            outer_train = set(fold["outer_train_indices"])
            outer_test = set(fold["outer_test_indices"])

            assert len(outer_train) == 6400
            assert len(outer_test) == 1600
            assert outer_train.isdisjoint(outer_test)
            assert len(outer_train | outer_test) == 8000


def test_req4_subtrain_cal_thresh_pairwise_disjoint(manifest):
    """
    Validation Point 4:
    Sub-Train (N = 4,480), Calibration (N = 960), and Threshold-Validation (N = 960)
    are pairwise disjoint.
    """
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            sub_train = set(fold["sub_train_indices"])
            cal = set(fold["calibration_indices"])
            thresh = set(fold["threshold_indices"])

            assert len(sub_train) == 4480
            assert len(cal) == 960
            assert len(thresh) == 960

            assert sub_train.isdisjoint(cal), "Sub-train overlaps with Calibration!"
            assert sub_train.isdisjoint(thresh), "Sub-train overlaps with Threshold-Validation!"
            assert cal.isdisjoint(thresh), "Calibration overlaps with Threshold-Validation!"


def test_req5_subtrain_cal_thresh_union_equals_outer_train(manifest):
    """
    Validation Point 5:
    Their union strictly equals outer train (N = 6,400).
    """
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            sub_train = set(fold["sub_train_indices"])
            cal = set(fold["calibration_indices"])
            thresh = set(fold["threshold_indices"])
            outer_train = set(fold["outer_train_indices"])

            assert (sub_train | cal | thresh) == outer_train


def test_req6_inner_train_val_disjointness(manifest):
    """
    Validation Point 6:
    Inner train (N = 3,360) and inner val (N = 1,120) never overlap.
    """
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            inner_folds = fold["inner_folds"]
            assert len(inner_folds) == 4

            for in_f in inner_folds:
                in_train = set(in_f["inner_train_indices"])
                in_val = set(in_f["inner_val_indices"])

                assert len(in_train) == 3360
                assert len(in_val) == 1120
                assert in_train.isdisjoint(in_val)
                assert len(in_train | in_val) == 4480


def test_req7_inner_cv_subtrain_confinement(manifest):
    """
    Validation Point 7:
    Inner CV uses only Sub-Train observations; inner validation partitions
    Sub-Train exactly once across the 4 inner folds.
    """
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            sub_train_set = set(fold["sub_train_indices"])
            cal_set = set(fold["calibration_indices"])
            thresh_set = set(fold["threshold_indices"])
            outer_test_set = set(fold["outer_test_indices"])

            seen_inner_val = set()
            for in_f in fold["inner_folds"]:
                in_train = set(in_f["inner_train_indices"])
                in_val = set(in_f["inner_val_indices"])

                # Strict subset of Sub-Train
                assert in_train.issubset(sub_train_set)
                assert in_val.issubset(sub_train_set)

                # Strict isolation: zero overlap with holdout partitions
                assert in_train.isdisjoint(cal_set)
                assert in_train.isdisjoint(thresh_set)
                assert in_train.isdisjoint(outer_test_set)
                assert in_val.isdisjoint(cal_set)
                assert in_val.isdisjoint(thresh_set)
                assert in_val.isdisjoint(outer_test_set)

                assert in_val.isdisjoint(seen_inner_val)
                seen_inner_val.update(in_val)

            assert seen_inner_val == sub_train_set


def test_req8_locked_test_complete_isolation(manifest, historical_splits):
    """
    Validation Point 8:
    Zero locked historical test observations (N = 2,000) enter Stage 3 partitions.
    """
    locked_test = set(historical_splits["test_indices"])
    assert len(locked_test) == 2000
    assert compute_indices_hash(historical_splits["test_indices"]) == HISTORICAL_LOCKED_TEST_HASH

    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            assert set(fold["outer_train_indices"]).isdisjoint(locked_test)
            assert set(fold["outer_test_indices"]).isdisjoint(locked_test)
            assert set(fold["sub_train_indices"]).isdisjoint(locked_test)
            assert set(fold["calibration_indices"]).isdisjoint(locked_test)
            assert set(fold["threshold_indices"]).isdisjoint(locked_test)

            for in_f in fold["inner_folds"]:
                assert set(in_f["inner_train_indices"]).isdisjoint(locked_test)
                assert set(in_f["inner_val_indices"]).isdisjoint(locked_test)


def test_req9_parity_across_feature_configurations(manifest, raw_dataset):
    """
    Validation Point 9:
    Both WITH_TYPE and NO_TYPE share identical split indices, ensuring fair evaluation.
    """
    X_a, y_a = prepare_features_and_target(raw_dataset, configuration="A")
    X_b, y_b = prepare_features_and_target(raw_dataset, configuration="B")

    assert len(X_a) == len(X_b) == 10000

    # Test sample slice on rep 0, fold 0
    fold0 = manifest["repetitions"][0]["outer_folds"][0]
    sub_train_idx = fold0["sub_train_indices"]
    cal_idx = fold0["calibration_indices"]

    # Verify identical sample indexing across configurations
    y_sub_a = y_a[sub_train_idx]
    y_sub_b = y_b[sub_train_idx]
    np.testing.assert_array_equal(y_sub_a, y_sub_b)

    y_cal_a = y_a[cal_idx]
    y_cal_b = y_b[cal_idx]
    np.testing.assert_array_equal(y_cal_a, y_cal_b)


def test_req10_index_validity_and_bounds(manifest):
    """
    Validation Point 10:
    All indices remain within [0, 9999] bounds and are valid integers.
    """
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            all_fold_indices = (
                fold["sub_train_indices"]
                + fold["calibration_indices"]
                + fold["threshold_indices"]
                + fold["outer_test_indices"]
            )
            for idx in all_fold_indices:
                assert isinstance(idx, int)
                assert 0 <= idx < 10000


def test_req11_split_generation_reproducibility(tmp_path):
    """
    Validation Point 11:
    Split generation is 100% reproducible with identical seeds.
    """
    temp_artifact_1 = tmp_path / "manifest_1.json"
    temp_artifact_2 = tmp_path / "manifest_2.json"

    m1 = generate_repeated_nested_cv_manifest(save_path=temp_artifact_1)
    m2 = generate_repeated_nested_cv_manifest(save_path=temp_artifact_2)

    assert m1["metadata"]["manifest_hash"] == m2["metadata"]["manifest_hash"]

    # Check identical outer and inner fold index hashes
    for r in range(5):
        for k in range(5):
            p1 = m1["repetitions"][r]["outer_folds"][k]["partition_counts"]
            p2 = m2["repetitions"][r]["outer_folds"][k]["partition_counts"]
            assert p1["sub_train"]["index_hash"] == p2["sub_train"]["index_hash"]
            assert p1["calibration"]["index_hash"] == p2["calibration"]["index_hash"]
            assert p1["threshold_validation"]["index_hash"] == p2["threshold_validation"]["index_hash"]
            assert p1["outer_test"]["index_hash"] == p2["outer_test"]["index_hash"]


def test_req12_calibration_positive_events_gate(manifest):
    """
    Validation Point 12:
    Calibration positive events satisfy N_{cal,pos} >= 25 on every fold.
    """
    min_required = manifest["metadata"]["min_calibration_positives_gate"]
    assert min_required == 25

    cal_positives_list = []
    for rep in manifest["repetitions"]:
        for fold in rep["outer_folds"]:
            cal_counts = fold["partition_counts"]["calibration"]
            assert cal_counts["passes_min_positives_gate"] is True
            assert cal_counts["positives"] >= min_required
            cal_positives_list.append(cal_counts["positives"])

    # Verify distribution is tight around nominal expected value (~32.5 positives)
    assert min(cal_positives_list) >= 25
    assert max(cal_positives_list) <= 45
    assert len(cal_positives_list) == 25

