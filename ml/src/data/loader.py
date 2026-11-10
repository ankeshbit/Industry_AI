"""
Dataset Ingestion and Cryptographic Verification Module
Loads raw AI4I 2020 telemetry data and validates data integrity.
"""

import hashlib
from pathlib import Path
from typing import Optional
import pandas as pd

from ml.src.features.schemas import (
    AI4I_SHA256_CHECKSUM,
    PRIMARY_TARGET,
    FAILURE_MODE_TARGETS,
    NUMERICAL_FEATURES,
    IDENTIFIER_COLUMNS,
    CATEGORICAL_FEATURES,
)


def compute_file_checksum(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def load_ai4i_dataset(
    filepath: Optional[Path] = None,
    verify_checksum: bool = True
) -> pd.DataFrame:
    """
    Loads and validates the authoritative AI4I 2020 Predictive Maintenance Dataset.

    Args:
        filepath: Optional path to the CSV. If None, uses default raw location.
        verify_checksum: Whether to verify the SHA-256 hash against the authoritative hash.

    Returns:
        pd.DataFrame containing the raw 10,000 observations.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If checksum verification fails or schema is malformed.
    """
    if filepath is None:
        filepath = Path(__file__).resolve().parent.parent.parent / "datasets" / "raw" / "ai4i2020.csv"
    else:
        filepath = Path(filepath)

    if not filepath.is_file():
        raise FileNotFoundError(
            f"AI4I dataset not found at '{filepath}'. "
            "Please ensure raw dataset is placed in 'ml/datasets/raw/ai4i2020.csv'."
        )

    if verify_checksum:
        actual_hash = compute_file_checksum(filepath)
        if actual_hash != AI4I_SHA256_CHECKSUM:
            raise ValueError(
                f"Checksum mismatch for '{filepath}'.\\n"
                f"Expected: {AI4I_SHA256_CHECKSUM}\\n"
                f"Got:      {actual_hash}\\n"
                "The dataset may be corrupt or altered."
            )

    df = pd.read_csv(filepath)

    # Validate essential columns
    required_cols = (
        IDENTIFIER_COLUMNS
        + CATEGORICAL_FEATURES
        + NUMERICAL_FEATURES
        + [PRIMARY_TARGET]
        + FAILURE_MODE_TARGETS
    )
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    return df

