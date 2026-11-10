"""
Preprocessing and Feature Transformation Pipeline Module
Builds leakage-free ColumnTransformer pipelines fitted strictly within training data.
"""

from typing import Optional
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

from ml.src.features.schemas import (
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    CONFIG_A_FEATURES,
    CONFIG_B_FEATURES,
)


def build_preprocessor(
    configuration: str = "A",
    scale_numeric: bool = True
) -> ColumnTransformer:
    """
    Constructs an sklearn ColumnTransformer preprocessor for the specified configuration.

    Args:
        configuration: 'A' (With Type) or 'B' (Without Type)
        scale_numeric: Whether to standardize numeric features using StandardScaler.

    Returns:
        Configured ColumnTransformer instance.
    """
    config_upper = configuration.upper().strip()

    transformers = []

    # Numeric pipeline
    if scale_numeric:
        numeric_transformer = StandardScaler()
    else:
        numeric_transformer = "passthrough"

    transformers.append(("numeric", numeric_transformer, NUMERICAL_FEATURES))

    # Categorical pipeline (Only in Configuration A)
    if config_upper in ("A", "WITH_TYPE"):
        categorical_transformer = OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False
        )
        transformers.append(("categorical", categorical_transformer, CATEGORICAL_FEATURES))
    elif config_upper in ("B", "WITHOUT_TYPE"):
        pass
    else:
        raise ValueError(f"Unknown configuration '{configuration}'. Must be 'A' or 'B'.")

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False
    )

    return preprocessor

