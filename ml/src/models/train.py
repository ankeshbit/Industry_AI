"""
Baseline Model Factory and Training Module
Builds leakage-safe scikit-learn and XGBoost pipelines with class-imbalance compensation.
"""

import time
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from ml.src.preprocessing.pipeline import build_preprocessor
from ml.src.evaluation.metrics import compute_evaluation_metrics


def get_baseline_models(
    scale_pos_weight: float = 28.5,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Instantiates the 4 baseline classifiers with appropriate imbalance handling.

    Args:
        scale_pos_weight: Ratio of negative to positive class for XGBoost.
        random_state: Deterministic random seed.

    Returns:
        Dictionary mapping model names to un-fitted estimator objects.
    """
    models = {
        "Logistic Regression": LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            random_state=random_state
        ),
        "Decision Tree": DecisionTreeClassifier(
            class_weight="balanced",
            max_depth=6,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=random_state
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=random_state,
            n_jobs=-1
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1
        )
    }
    return models


def build_pipeline_for_model(
    model_name: str,
    model: Any,
    configuration: str = "A"
) -> Pipeline:
    """
    Encapsulates a model into an end-to-end sklearn Pipeline with the appropriate preprocessor.

    Args:
        model_name: Model identifier.
        model: Estimator object.
        configuration: 'A' or 'B'.

    Returns:
        Configured Pipeline.
    """
    # Scale numeric features for all models (essential for Logistic Regression, harmless for Trees)
    preprocessor = build_preprocessor(configuration=configuration, scale_numeric=True)

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", model)
    ])
    return pipeline


def train_and_evaluate_model(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
    """
    Fits the end-to-end pipeline strictly on training data and computes test and train metrics.

    Args:
        pipeline: Sklearn Pipeline.
        X_train: Training features DataFrame.
        y_train: Training target Series.
        X_test: Holdout test features DataFrame.
        y_test: Holdout test target Series.

    Returns:
        Tuple of (test_metrics, train_metrics, fit_duration_seconds).
    """
    start_time = time.time()
    pipeline.fit(X_train, y_train)
    fit_duration = time.time() - start_time

    # Evaluate on Test Set
    y_test_pred = pipeline.predict(X_test)
    y_test_prob = None
    if hasattr(pipeline, "predict_proba"):
        y_test_prob = pipeline.predict_proba(X_test)[:, 1]

    test_metrics = compute_evaluation_metrics(
        y_true=y_test.values,
        y_pred=y_test_pred,
        y_prob=y_test_prob
    )
    test_metrics["execution_time_sec"] = round(fit_duration, 4)

    # Evaluate on Train Set (to check overfitting)
    y_train_pred = pipeline.predict(X_train)
    y_train_prob = None
    if hasattr(pipeline, "predict_proba"):
        y_train_prob = pipeline.predict_proba(X_train)[:, 1]

    train_metrics = compute_evaluation_metrics(
        y_true=y_train.values,
        y_pred=y_train_pred,
        y_prob=y_train_prob
    )

    return test_metrics, train_metrics, fit_duration

