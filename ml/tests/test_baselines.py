"""
Unit and Integration Tests for Baseline Machine Learning Pipelines
Validates loading, schema isolation, preprocessing, reproducibility, training, and cost evaluation.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml.src.data.loader import load_ai4i_dataset
from ml.src.features.schemas import (
    get_feature_schema,
    prepare_features_and_target,
    CONFIG_A_FEATURES,
    CONFIG_B_FEATURES,
    IDENTIFIER_COLUMNS,
    FAILURE_MODE_TARGETS,
    PRIMARY_TARGET,
)
from ml.src.preprocessing.pipeline import build_preprocessor
from ml.src.data.splitting import generate_stratified_split
from ml.src.models.train import get_baseline_models, build_pipeline_for_model, train_and_evaluate_model
from ml.src.evaluation.metrics import compute_evaluation_metrics, DEFAULT_COST_FN, DEFAULT_COST_FP


def test_dataset_loading_and_checksum():
    """Verify loading of authoritative AI4I dataset and checksum enforcement."""
    df = load_ai4i_dataset(verify_checksum=True)
    assert df is not None
    assert df.shape == (10000, 14)
    assert PRIMARY_TARGET in df.columns

    # Test error handling on bad checksum
    with pytest.raises(FileNotFoundError):
        load_ai4i_dataset(filepath=Path("non_existent_file.csv"))


def test_feature_selection_and_leakage_prevention():
    """Verify feature schema integrity for Configuration A and B without leakage."""
    schema_a = get_feature_schema("A")
    schema_b = get_feature_schema("B")

    assert schema_a == CONFIG_A_FEATURES
    assert schema_b == CONFIG_B_FEATURES
    assert "Type" in schema_a
    assert "Type" not in schema_b

    # Verify no identifiers or failure modes are in schemas
    for forbidden in IDENTIFIER_COLUMNS + FAILURE_MODE_TARGETS:
        assert forbidden not in schema_a
        assert forbidden not in schema_b

    df = load_ai4i_dataset(verify_checksum=False)
    X_a, y_a = prepare_features_and_target(df, configuration="A")
    X_b, y_b = prepare_features_and_target(df, configuration="B")

    assert X_a.shape == (10000, 6)
    assert X_b.shape == (10000, 5)
    assert len(y_a) == 10000
    assert len(y_b) == 10000
    assert (y_a == y_b).all()


def test_preprocessing_pipeline_transformations():
    """Verify ColumnTransformer behaves correctly for both configurations."""
    df = load_ai4i_dataset(verify_checksum=False)
    X_a, _ = prepare_features_and_target(df, configuration="A")
    X_b, _ = prepare_features_and_target(df, configuration="B")

    preprocessor_a = build_preprocessor("A", scale_numeric=True)
    preprocessor_b = build_preprocessor("B", scale_numeric=True)

    X_a_trans = preprocessor_a.fit_transform(X_a)
    X_b_trans = preprocessor_b.fit_transform(X_b)

    # Config A: 5 numeric features + 3 one-hot columns (Type_H, Type_L, Type_M) = 8
    assert X_a_trans.shape == (10000, 8)
    # Config B: 5 numeric features = 5
    assert X_b_trans.shape == (10000, 5)

    # Ensure mean of scaled numeric features is approximately 0
    assert np.allclose(X_b_trans.mean(axis=0), 0, atol=1e-5)


def test_split_reproducibility_and_stratification():
    """Verify that split generation produces strictly identical indices across runs."""
    df = load_ai4i_dataset(verify_checksum=False)
    
    train_idx1, test_idx1, meta1 = generate_stratified_split(
        df=df, target_col=PRIMARY_TARGET, test_size=0.20, random_state=42
    )
    train_idx2, test_idx2, meta2 = generate_stratified_split(
        df=df, target_col=PRIMARY_TARGET, test_size=0.20, random_state=42
    )

    assert np.array_equal(train_idx1, train_idx2)
    assert np.array_equal(test_idx1, test_idx2)
    assert meta1["train_index_hash"] == meta2["train_index_hash"]
    assert meta1["test_index_hash"] == meta2["test_index_hash"]

    # Verify stratified balance in both folds
    overall_rate = df[PRIMARY_TARGET].mean()
    assert abs(meta1["train_failure_rate"] - overall_rate) < 0.005
    assert abs(meta1["test_failure_rate"] - overall_rate) < 0.005


def test_baseline_models_pipeline_training():
    """Verify that models train and predict through end-to-end pipelines without error."""
    df = load_ai4i_dataset(verify_checksum=False).head(500)
    X, y = prepare_features_and_target(df, configuration="A")
    train_idx, test_idx, _ = generate_stratified_split(df, PRIMARY_TARGET, test_size=0.2, random_state=42)

    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

    models = get_baseline_models(scale_pos_weight=20.0, random_state=42)
    for model_name, model in models.items():
        pipeline = build_pipeline_for_model(model_name, model, configuration="A")
        test_metrics, train_metrics, duration = train_and_evaluate_model(
            pipeline, X_train, y_train, X_test, y_test
        )
        assert "recall" in test_metrics
        assert "precision" in test_metrics
        assert "f1_score" in test_metrics
        assert "pr_auc" in test_metrics
        assert "total_operational_cost" in test_metrics
        assert duration >= 0.0


def test_asymmetric_cost_and_evaluation_metrics():
    """Verify evaluation metric calculations and asymmetric cost logic."""
    y_true = np.array([0, 0, 0, 0, 1, 1])
    y_pred = np.array([0, 0, 0, 1, 0, 1])  # TN=3, FP=1, FN=1, TP=1

    res = compute_evaluation_metrics(y_true, y_pred, y_prob=np.array([0.1, 0.2, 0.3, 0.8, 0.4, 0.9]))

    assert res["true_negatives"] == 3
    assert res["false_positives"] == 1
    assert res["false_negatives"] == 1
    assert res["true_positives"] == 1

    # Cost = 1 * 10,000 + 1 * 200 = 10,200
    expected_cost = 1 * DEFAULT_COST_FN + 1 * DEFAULT_COST_FP
    assert res["total_operational_cost"] == expected_cost
    assert res["recall"] == 0.5
    assert res["precision"] == 0.5

