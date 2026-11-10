"""
Unit Tests for Stage 3 Physics-Based Feature Engineering

Validates mathematical correctness, stability, absence of NaNs/Infs,
and Scikit-learn Pipeline compatibility for IndustrialFeatureEngineer.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.src.features.engineering import IndustrialFeatureEngineer, ENGINEERED_FEATURE_NAMES
from ml.src.data.loader import load_ai4i_dataset
from ml.src.features.schemas import prepare_features_and_target


def test_feature_engineer_shapes_and_column_names():
    """Verify that all 5 engineered features are correctly appended to DataFrames."""
    df = load_ai4i_dataset(verify_checksum=False)
    X_raw, _ = prepare_features_and_target(df, configuration="B")

    engineer = IndustrialFeatureEngineer(include_raw_features=True)
    X_transformed = engineer.fit_transform(X_raw)

    assert isinstance(X_transformed, pd.DataFrame)
    assert X_transformed.shape[0] == 10000
    assert X_transformed.shape[1] == 5 + len(ENGINEERED_FEATURE_NAMES)

    for col in ENGINEERED_FEATURE_NAMES:
        assert col in X_transformed.columns


def test_feature_engineer_mathematical_precision():
    """Verify exact mathematical formulas against hand-calculated physical ground truth."""
    test_df = pd.DataFrame({
        "Air temperature [K]": [300.0],
        "Process temperature [K]": [310.0],
        "Rotational speed [rpm]": [1500.0],
        "Torque [Nm]": [40.0],
        "Tool wear [min]": [100.0],
    })

    engineer = IndustrialFeatureEngineer(include_raw_features=True)
    res = engineer.fit_transform(test_df)

    # 1. Delta T = 310 - 300 = 10.0 K
    assert pytest.approx(res["Temp_Dissipation_Delta_K"].iloc[0], rel=1e-5) == 10.0

    # 2. Mechanical Power = 40.0 * (1500 * 2 * pi / 60) = 40.0 * 50 * pi = 6283.1853 W
    expected_power = 40.0 * (1500.0 * 2.0 * np.pi / 60.0)
    assert pytest.approx(res["Mechanical_Power_W"].iloc[0], rel=1e-5) == expected_power

    # 3. Overstrain = 100.0 * 40.0 = 4000.0 min*Nm
    assert pytest.approx(res["Overstrain_Min_Nm"].iloc[0], rel=1e-5) == 4000.0

    # 4. Speed / (Torque + 1.0) = 1500.0 / 41.0 = 36.585365
    assert pytest.approx(res["Speed_Torque_Ratio"].iloc[0], rel=1e-5) == (1500.0 / 41.0)

    # 5. Thermal Strain = 10.0 * 100.0 = 1000.0
    assert pytest.approx(res["Thermal_Strain_Interaction"].iloc[0], rel=1e-5) == 1000.0


def test_feature_engineer_numerical_stability_edge_cases():
    """Verify that zero torque or zero rotational speed does not produce NaNs or Infs."""
    edge_df = pd.DataFrame({
        "Air temperature [K]": [300.0, 305.0],
        "Process temperature [K]": [300.0, 305.0],  # delta T = 0
        "Rotational speed [rpm]": [0.0, 2000.0],    # zero rpm
        "Torque [Nm]": [0.0, 0.0],                  # zero torque
        "Tool wear [min]": [0.0, 0.0],              # zero wear
    })

    engineer = IndustrialFeatureEngineer(include_raw_features=True)
    res = engineer.fit_transform(edge_df)

    assert not res.isna().any().any(), "Engineered features produced unexpected NaN"
    assert not np.isinf(res.values).any(), "Engineered features produced unexpected Inf"


def test_feature_engineer_pipeline_integration():
    """Verify that IndustrialFeatureEngineer operates seamlessly inside a Scikit-learn Pipeline."""
    df = load_ai4i_dataset(verify_checksum=False)
    X, y = prepare_features_and_target(df, configuration="B")

    pipe = Pipeline([
        ("feature_engineer", IndustrialFeatureEngineer(include_raw_features=True)),
        ("scaler", StandardScaler()),
    ])

    X_scaled = pipe.fit_transform(X, y)
    assert X_scaled.shape == (10000, 10)
    assert np.allclose(X_scaled.mean(axis=0), 0.0, atol=1e-7)
