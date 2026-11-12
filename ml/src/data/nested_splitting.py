"""
Repeated Nested Cross-Validation Infrastructure Module (Stage 3 Phase 1)

Implements reproducible data-splitting infrastructure strictly adhering to
STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§2.2, §4.1, §4.3, §5.2).

Architecture Specifications:
1. Outer Loop: R=5 repetitions of 5-fold Stratified Cross-Validation (25 outer evaluations).
   - Outer seeds: 42 + r * 100 for r in [0..4] (42, 142, 242, 342, 442).
   - Development partition: N = 8,000 observations (excludes locked historical test partition N = 2,000).
   - Outer train: N = 6,400 | Outer test: N = 1,600 per fold.
2. 3-Way Outer-Training Partitioning:
   - Sub-Train (70%, N = 4,480): Base estimator training pool.
   - Calibration (15%, N = 960): Post-hoc calibration fitting pool.
   - Threshold-Validation (15%, N = 960): Operational threshold optimization pool.
   - All three partitions are strictly pairwise disjoint and sum to 6,400 rows.
   - Calibration positive-count gate: N_cal,pos >= 25 strictly enforced.
3. Inner Loop: 4-fold Stratified Cross-Validation strictly within Sub-Train (N = 4,480).
   - Inner train: N = 3,360 | Inner val: N = 1,120 per inner fold.
   - Zero access to Calibration, Threshold-Validation, or Outer Test partitions.
4. Parity:
   - Identical partition indices apply to both WITH_TYPE and NO_TYPE configurations.
5. Persistence:
   - Complete manifest serialized to ml/artifacts/nested_cv_indices.json with cryptographic SHA-256 verification.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

from ml.src.features.schemas import (
    AI4I_SHA256_CHECKSUM,
    PRIMARY_TARGET,
)
from ml.src.data.loader import load_ai4i_dataset

# Cryptographic hashes of historical Stage 2B partitions
HISTORICAL_TRAIN_INDEX_HASH = "67471419f2a9a808e27a300667946f2927d7d3b160ea1e4675cabd17cdfc66e8"
HISTORICAL_LOCKED_TEST_HASH = "8e8fef98bdc3f3d6acd0abe46e342ff4fb29d336aaa77143a3e84b2fef10073b"

DEFAULT_NESTED_CV_ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "artifacts" / "nested_cv_indices.json"
)
HISTORICAL_SPLIT_ARTIFACT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "artifacts" / "split_indices.json"
)


def compute_indices_hash(indices: List[int]) -> str:
    """Computes deterministic SHA-256 hash of a list of integer indices (using int32 bytes)."""
    arr = np.array(indices, dtype=np.int32)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def compute_manifest_hash(payload_str: str) -> str:
    """Computes SHA-256 hash of the manifest string."""
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


def generate_repeated_nested_cv_manifest(
    dataset_path: Optional[Path] = None,
    historical_split_path: Optional[Path] = None,
    save_path: Optional[Path] = None,
    n_repetitions: int = 5,
    outer_k: int = 5,
    inner_k: int = 4,
    base_seed: int = 42,
    min_calibration_positives: int = 25,
) -> Dict[str, Any]:
    """
    Generates the complete repeated nested cross-validation index manifest for Stage 3.

    Args:
        dataset_path: Optional path to raw AI4I CSV.
        historical_split_path: Optional path to split_indices.json.
        save_path: Destination path for nested_cv_indices.json.
        n_repetitions: Number of outer repetitions (default: 5).
        outer_k: Folds per outer repetition (default: 5).
        inner_k: Folds per inner loop (default: 4).
        base_seed: Base random seed (default: 42).
        min_calibration_positives: Hard gate for calibration positives (default: 25).

    Returns:
        Structured dictionary containing complete repeated nested CV index manifest.
    """
    # 1. Load and verify raw dataset
    df = load_ai4i_dataset(filepath=dataset_path, verify_checksum=True)
    total_samples = len(df)
    assert total_samples == 10000, f"Expected 10,000 raw samples, got {total_samples}"

    y_all = df[PRIMARY_TARGET].values.astype(int)

    # 2. Load historical split indices and verify integrity
    hist_path = historical_split_path or HISTORICAL_SPLIT_ARTIFACT_PATH
    if not hist_path.is_file():
        raise FileNotFoundError(f"Historical split artifact not found at {hist_path}")

    with open(hist_path, "r", encoding="utf-8") as f:
        hist_data = json.load(f)

    dev_indices = np.array(hist_data["train_indices"], dtype=np.int32)
    locked_test_indices = np.array(hist_data["test_indices"], dtype=np.int32)

    # Verify historical hashes and counts
    actual_dev_hash = compute_indices_hash(dev_indices.tolist())
    actual_test_hash = compute_indices_hash(locked_test_indices.tolist())

    if actual_dev_hash != HISTORICAL_TRAIN_INDEX_HASH:
        raise ValueError(f"Development index hash mismatch: expected {HISTORICAL_TRAIN_INDEX_HASH}, got {actual_dev_hash}")
    if actual_test_hash != HISTORICAL_LOCKED_TEST_HASH:
        raise ValueError(f"Locked test index hash mismatch: expected {HISTORICAL_LOCKED_TEST_HASH}, got {actual_test_hash}")

    assert len(dev_indices) == 8000, f"Expected 8,000 dev rows, got {len(dev_indices)}"
    assert len(locked_test_indices) == 2000, f"Expected 2,000 locked test rows, got {len(locked_test_indices)}"

    locked_test_set = set(locked_test_indices.tolist())
    assert set(dev_indices.tolist()).isdisjoint(locked_test_set), "Dev indices overlap with locked test set!"

    y_dev = y_all[dev_indices]
    dev_positives = int(y_dev.sum())
    dev_negatives = int(len(y_dev) - dev_positives)
    dev_failure_rate = float(dev_positives / len(y_dev))

    # 3. Construct repetitions and folds
    repetitions_data: List[Dict[str, Any]] = []
    outer_seeds: List[int] = []

    for r in range(n_repetitions):
        outer_seed = base_seed + r * 100
        outer_seeds.append(outer_seed)

        outer_cv = StratifiedKFold(n_splits=outer_k, shuffle=True, random_state=outer_seed)
        outer_folds_data: List[Dict[str, Any]] = []
        seen_outer_test_indices = set()

        for k, (train_pos, test_pos) in enumerate(outer_cv.split(dev_indices, y_dev)):
            outer_train_idx = dev_indices[train_pos]
            outer_test_idx = dev_indices[test_pos]

            assert len(outer_train_idx) == 6400, f"Expected 6,400 outer train rows, got {len(outer_train_idx)}"
            assert len(outer_test_idx) == 1600, f"Expected 1,600 outer test rows, got {len(outer_test_idx)}"
            assert set(outer_train_idx).isdisjoint(set(outer_test_idx))
            assert set(outer_train_idx).isdisjoint(locked_test_set)
            assert set(outer_test_idx).isdisjoint(locked_test_set)

            # Assert each outer test fold partitions the development pool exactly once per repetition
            assert set(outer_test_idx).isdisjoint(seen_outer_test_indices)
            seen_outer_test_indices.update(outer_test_idx)

            y_outer_train = y_all[outer_train_idx]
            y_outer_test = y_all[outer_test_idx]

            # 3-Way Split of Outer Train: 70% Sub-Train, 15% Calibration, 15% Threshold-Validation
            # Deterministic, unique seeds per repetition and fold
            sub_train_seed = base_seed + r * 100 + k * 10 + 1
            cal_thresh_seed = base_seed + r * 100 + k * 10 + 2

            sub_train_idx, holdout_idx = train_test_split(
                outer_train_idx,
                test_size=0.30,
                stratify=y_outer_train,
                random_state=sub_train_seed,
                shuffle=True,
            )

            y_holdout = y_all[holdout_idx]
            cal_idx, thresh_idx = train_test_split(
                holdout_idx,
                test_size=0.50,
                stratify=y_holdout,
                random_state=cal_thresh_seed,
                shuffle=True,
            )

            assert len(sub_train_idx) == 4480, f"Expected 4,480 sub-train rows, got {len(sub_train_idx)}"
            assert len(cal_idx) == 960, f"Expected 960 calibration rows, got {len(cal_idx)}"
            assert len(thresh_idx) == 960, f"Expected 960 threshold rows, got {len(thresh_idx)}"

            # Disjointness and completeness assertions
            assert set(sub_train_idx).isdisjoint(set(cal_idx))
            assert set(sub_train_idx).isdisjoint(set(thresh_idx))
            assert set(cal_idx).isdisjoint(set(thresh_idx))
            assert set(sub_train_idx) | set(cal_idx) | set(thresh_idx) == set(outer_train_idx)

            y_sub_train = y_all[sub_train_idx]
            y_cal = y_all[cal_idx]
            y_thresh = y_all[thresh_idx]

            cal_positives = int(y_cal.sum())
            cal_passes_gate = bool(cal_positives >= min_calibration_positives)
            if not cal_passes_gate:
                raise ValueError(
                    f"Calibration partition failed minimum positive gate on rep {r}, fold {k}: "
                    f"got {cal_positives} positives, minimum required is {min_calibration_positives}"
                )

            # Inner 4-fold CV strictly within Sub-Train (N = 4,480)
            inner_cv_seed = base_seed + r * 100 + k * 10 + 3
            inner_cv = StratifiedKFold(n_splits=inner_k, shuffle=True, random_state=inner_cv_seed)

            inner_folds_data: List[Dict[str, Any]] = []
            seen_inner_val_indices = set()

            for j, (in_train_pos, in_val_pos) in enumerate(inner_cv.split(sub_train_idx, y_sub_train)):
                in_train_idx = sub_train_idx[in_train_pos]
                in_val_idx = sub_train_idx[in_val_pos]

                assert len(in_train_idx) == 3360, f"Expected 3,360 inner train rows, got {len(in_train_idx)}"
                assert len(in_val_idx) == 1120, f"Expected 1,120 inner val rows, got {len(in_val_idx)}"
                assert set(in_train_idx).isdisjoint(set(in_val_idx))
                assert set(in_train_idx) | set(in_val_idx) == set(sub_train_idx)

                # Inner val partitions Sub-Train exactly once across inner folds
                assert set(in_val_idx).isdisjoint(seen_inner_val_indices)
                seen_inner_val_indices.update(in_val_idx)

                # Strict isolation: inner folds must never see calibration, threshold, or outer test
                assert set(in_train_idx).isdisjoint(set(cal_idx))
                assert set(in_train_idx).isdisjoint(set(thresh_idx))
                assert set(in_train_idx).isdisjoint(set(outer_test_idx))
                assert set(in_val_idx).isdisjoint(set(cal_idx))
                assert set(in_val_idx).isdisjoint(set(thresh_idx))
                assert set(in_val_idx).isdisjoint(set(outer_test_idx))

                y_in_train = y_all[in_train_idx]
                y_in_val = y_all[in_val_idx]

                inner_folds_data.append({
                    "inner_fold_index": int(j),
                    "inner_train_samples": int(len(in_train_idx)),
                    "inner_val_samples": int(len(in_val_idx)),
                    "inner_train_positives": int(y_in_train.sum()),
                    "inner_train_negatives": int(len(in_train_idx) - y_in_train.sum()),
                    "inner_val_positives": int(y_in_val.sum()),
                    "inner_val_negatives": int(len(in_val_idx) - y_in_val.sum()),
                    "inner_train_indices": in_train_idx.tolist(),
                    "inner_val_indices": in_val_idx.tolist(),
                })

            assert seen_inner_val_indices == set(sub_train_idx)

            fold_record = {
                "outer_fold_index": int(k),
                "sub_train_seed": int(sub_train_seed),
                "cal_thresh_seed": int(cal_thresh_seed),
                "inner_cv_seed": int(inner_cv_seed),
                "partition_counts": {
                    "outer_train": {
                        "total": int(len(outer_train_idx)),
                        "positives": int(y_outer_train.sum()),
                        "negatives": int(len(outer_train_idx) - y_outer_train.sum()),
                        "failure_rate": float(y_outer_train.mean()),
                        "index_hash": compute_indices_hash(outer_train_idx.tolist()),
                    },
                    "outer_test": {
                        "total": int(len(outer_test_idx)),
                        "positives": int(y_outer_test.sum()),
                        "negatives": int(len(outer_test_idx) - y_outer_test.sum()),
                        "failure_rate": float(y_outer_test.mean()),
                        "index_hash": compute_indices_hash(outer_test_idx.tolist()),
                    },
                    "sub_train": {
                        "total": int(len(sub_train_idx)),
                        "positives": int(y_sub_train.sum()),
                        "negatives": int(len(sub_train_idx) - y_sub_train.sum()),
                        "failure_rate": float(y_sub_train.mean()),
                        "index_hash": compute_indices_hash(sub_train_idx.tolist()),
                    },
                    "calibration": {
                        "total": int(len(cal_idx)),
                        "positives": int(cal_positives),
                        "negatives": int(len(cal_idx) - cal_positives),
                        "failure_rate": float(y_cal.mean()),
                        "passes_min_positives_gate": cal_passes_gate,
                        "index_hash": compute_indices_hash(cal_idx.tolist()),
                    },
                    "threshold_validation": {
                        "total": int(len(thresh_idx)),
                        "positives": int(y_thresh.sum()),
                        "negatives": int(len(thresh_idx) - y_thresh.sum()),
                        "failure_rate": float(y_thresh.mean()),
                        "index_hash": compute_indices_hash(thresh_idx.tolist()),
                    },
                },
                "outer_train_indices": outer_train_idx.tolist(),
                "outer_test_indices": outer_test_idx.tolist(),
                "sub_train_indices": sub_train_idx.tolist(),
                "calibration_indices": cal_idx.tolist(),
                "threshold_indices": thresh_idx.tolist(),
                "inner_folds": inner_folds_data,
            }
            outer_folds_data.append(fold_record)

        assert seen_outer_test_indices == set(dev_indices.tolist())

        repetitions_data.append({
            "repetition_index": int(r),
            "outer_seed": int(outer_seed),
            "outer_folds": outer_folds_data,
        })

    metadata = {
        "dataset_name": "ai4i2020",
        "dataset_checksum": AI4I_SHA256_CHECKSUM,
        "total_samples": int(total_samples),
        "development_samples": int(len(dev_indices)),
        "locked_test_samples": int(len(locked_test_indices)),
        "development_index_hash": actual_dev_hash,
        "locked_test_index_hash": actual_test_hash,
        "target_col": PRIMARY_TARGET,
        "development_positives": dev_positives,
        "development_negatives": dev_negatives,
        "development_failure_rate": dev_failure_rate,
        "n_repetitions": int(n_repetitions),
        "outer_k": int(outer_k),
        "inner_k": int(inner_k),
        "outer_seeds": outer_seeds,
        "partition_ratios": {
            "sub_train": 0.70,
            "calibration": 0.15,
            "threshold_validation": 0.15,
        },
        "nominal_partition_sizes": {
            "outer_train": 6400,
            "outer_test": 1600,
            "sub_train": 4480,
            "calibration": 960,
            "threshold_validation": 960,
            "inner_train": 3360,
            "inner_val": 1120,
        },
        "min_calibration_positives_gate": int(min_calibration_positives),
        "architecture_version": "v1.4.2",
    }

    manifest = {
        "metadata": metadata,
        "repetitions": repetitions_data,
    }

    # Add cryptographic manifest fingerprint
    manifest_body_str = json.dumps(manifest, sort_keys=True)
    manifest["metadata"]["manifest_hash"] = compute_manifest_hash(manifest_body_str)

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return manifest


def load_nested_cv_splits(
    artifact_path: Optional[Path] = None,
    verify_integrity: bool = True,
) -> Dict[str, Any]:
    """
    Loads and cryptographically validates the Stage 3 repeated nested CV manifest.

    Args:
        artifact_path: Path to nested_cv_indices.json.
        verify_integrity: Whether to verify dataset checksum, historical hashes, and partition rules.

    Returns:
        Validated nested CV manifest dictionary.
    """
    path = artifact_path or DEFAULT_NESTED_CV_ARTIFACT_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"Nested CV manifest not found at {path}. "
            "Please generate it by running generate_repeated_nested_cv_manifest()."
        )

    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if verify_integrity:
        meta = manifest["metadata"]
        assert meta["dataset_checksum"] == AI4I_SHA256_CHECKSUM, "Corrupt dataset checksum in manifest!"
        assert meta["development_index_hash"] == HISTORICAL_TRAIN_INDEX_HASH, "Development hash mismatch!"
        assert meta["locked_test_index_hash"] == HISTORICAL_LOCKED_TEST_HASH, "Locked test hash mismatch!"
        assert meta["n_repetitions"] == 5, "Expected exactly 5 repetitions!"
        assert meta["outer_k"] == 5, "Expected 5 outer folds per repetition!"
        assert meta["inner_k"] == 4, "Expected 4 inner folds per Sub-Train partition!"

        reps = manifest["repetitions"]
        assert len(reps) == 5, f"Expected 5 repetitions, got {len(reps)}"

        for r_idx, rep in enumerate(reps):
            folds = rep["outer_folds"]
            assert len(folds) == 5, f"Expected 5 folds in rep {r_idx}, got {len(folds)}"

            all_rep_test_indices = []
            for fold in folds:
                sub_train = fold["sub_train_indices"]
                cal = fold["calibration_indices"]
                thresh = fold["threshold_indices"]
                outer_test = fold["outer_test_indices"]

                assert len(sub_train) == 4480
                assert len(cal) == 960
                assert len(thresh) == 960
                assert len(outer_test) == 1600

                assert set(sub_train).isdisjoint(set(cal))
                assert set(sub_train).isdisjoint(set(thresh))
                assert set(cal).isdisjoint(set(thresh))
                assert set(sub_train) | set(cal) | set(thresh) == set(fold["outer_train_indices"])
                assert set(fold["outer_train_indices"]).isdisjoint(set(outer_test))

                assert fold["partition_counts"]["calibration"]["passes_min_positives_gate"] is True

                all_rep_test_indices.extend(outer_test)

            assert len(all_rep_test_indices) == 8000
            assert len(set(all_rep_test_indices)) == 8000

    return manifest


if __name__ == "__main__":
    print("Generating authoritative repeated nested CV manifest for Stage 3...")
    manifest = generate_repeated_nested_cv_manifest(
        save_path=DEFAULT_NESTED_CV_ARTIFACT_PATH
    )
    print(f"Successfully generated and serialized nested CV manifest to: {DEFAULT_NESTED_CV_ARTIFACT_PATH}")
    print(f"Total repetitions: {manifest['metadata']['n_repetitions']}")
    print(f"Outer evaluations: {manifest['metadata']['n_repetitions'] * manifest['metadata']['outer_k']}")
    print(f"Manifest SHA-256: {manifest['metadata']['manifest_hash']}")
