"""Regression tests for ML tooling bugs (no dataset required)."""

import numpy as np
import pandas as pd

from ml.experiments.run_baseline_experiments import update_experiment_log
from ml.src.data.splitting import generate_stratified_split


def _fake_results():
    metrics = {
        "pr_auc": 0.7, "roc_auc": 0.9, "f1_score": 0.6, "recall": 0.5, "precision": 0.7, "accuracy": 0.97,
        "true_negatives": 90, "false_positives": 2, "false_negatives": 4, "true_positives": 4,
        "total_operational_cost": 40400.0, "execution_time_sec": 0.1,
    }
    return {
        "EXP-001": {
            "experiment_id": "EXP-001", "model_name": "XGBoost", "configuration": "A", "configuration_label": "With Type",
            "features": ["Type"], "hyperparameters": {}, "test_metrics": metrics, "train_metrics": dict(metrics),
            "artifact_path": "ml/artifacts/models/x.joblib", "random_state": 42, "dataset_checksum": "abc",
        }
    }


def test_experiment_log_update_is_idempotent(tmp_path):
    """Every re-run appended a second copy of all experiment sections to ML_EXPERIMENT_LOG.md."""
    log = tmp_path / "log.md"
    log.write_text("# Log\n\nexisting text\n", encoding="utf-8")
    update_experiment_log(_fake_results(), log)
    once = log.read_text(encoding="utf-8")
    update_experiment_log(_fake_results(), log)
    twice = log.read_text(encoding="utf-8")
    assert once == twice
    assert twice.count("### EXP-001") == 1
    assert twice.startswith("# Log\n\nexisting text")
    # counts are derived from the metrics, not hard-coded (was always '2,000 holdout components, 68 failures')
    assert "out of 100 holdout components (8 true failures)" in twice


def test_split_index_hash_is_dtype_independent():
    """tobytes() hashed platform-dependent integer widths (int32 on Windows numpy<2), so hashes differed per OS."""
    df = pd.DataFrame({"y": [0] * 90 + [1] * 10, "x": np.arange(100)})
    _, _, meta = generate_stratified_split(df, "y", test_size=0.2, random_state=1)
    import hashlib
    train_idx, _, _ = generate_stratified_split(df, "y", test_size=0.2, random_state=1)
    expected = hashlib.sha256(np.asarray(train_idx, dtype=np.int64).tobytes()).hexdigest()
    assert meta["train_index_hash"] == expected
