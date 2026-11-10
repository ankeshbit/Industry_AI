"""
Feature and Target Schema Definitions for INDUSTRIA AI

Explicitly defines the feature schemas for Configuration A and Configuration B,
along with identifier exclusions and target leakage quarantine protocols.
"""

from typing import List, Tuple
import pandas as pd

# Expected SHA-256 for the authoritative AI4I 2020 dataset
AI4I_SHA256_CHECKSUM: str = "dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e"

# Identifiers - MUST NEVER be used as model features
IDENTIFIER_COLUMNS: List[str] = ["UDI", "Product ID"]

# Primary Target (Binary Machine Failure)
PRIMARY_TARGET: str = "Machine failure"

# Specific Failure Mechanisms - MUST BE QUARANTINED (Target Leakage for Machine failure)
FAILURE_MODE_TARGETS: List[str] = ["TWF", "HDF", "PWF", "OSF", "RNF"]

# Core Continuous Sensor Telemetry Features
NUMERICAL_FEATURES: List[str] = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]

# Categorical Metadata
CATEGORICAL_FEATURES: List[str] = ["Type"]

# Configuration A (With Type)
CONFIG_A_FEATURES: List[str] = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]

# Configuration B (Without Type)
CONFIG_B_FEATURES: List[str] = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]


def get_feature_schema(configuration: str) -> List[str]:
    """
    Retrieve feature list for specified configuration.

    Args:
        configuration: 'A' (With Type) or 'B' (Without Type)

    Returns:
        List of feature column names.
    """
    config_upper = configuration.upper().strip()
    if config_upper in ("A", "WITH_TYPE"):
        return list(CONFIG_A_FEATURES)
    elif config_upper in ("B", "WITHOUT_TYPE"):
        return list(CONFIG_B_FEATURES)
    else:
        raise ValueError(f"Unknown configuration '{configuration}'. Must be 'A' or 'B'.")


def prepare_features_and_target(
    df: pd.DataFrame, 
    configuration: str = "A"
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Extracts features (X) and target (y) for a given configuration,
    strictly validating against identifier and target leakage.

    Args:
        df: Input raw DataFrame.
        configuration: 'A' or 'B'.

    Returns:
        Tuple of (X, y).
    """
    feature_cols = get_feature_schema(configuration)
    
    # Audit for target leakage
    for forbidden in IDENTIFIER_COLUMNS + FAILURE_MODE_TARGETS:
        if forbidden in feature_cols:
            raise ValueError(f"CRITICAL LEAKAGE: Forbidden column '{forbidden}' found in feature schema!")

    if PRIMARY_TARGET not in df.columns:
        raise KeyError(f"Target column '{PRIMARY_TARGET}' not present in DataFrame.")

    X = df[feature_cols].copy()
    y = df[PRIMARY_TARGET].copy().astype(int)

    return X, y

