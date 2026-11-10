"""
Data Splitting and Leakage Prevention Module
Implements reproducible stratified train/test partitioning with index serialization.
"""

import json
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.src.features.schemas import AI4I_SHA256_CHECKSUM


def generate_stratified_split(
    df: pd.DataFrame,
    target_col: str,
    test_size: float = 0.20,
    random_state: int = 42,
    save_path: Optional[Path] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Creates a reproducible stratified split on the given target column,
    guaranteeing identical train and test partitions.

    Args:
        df: Input DataFrame.
        target_col: Target column name for stratification.
        test_size: Proportion of dataset allocated to the holdout test set.
        random_state: Deterministic random seed.
        save_path: Optional path to save split index JSON.

    Returns:
        Tuple of (train_indices, test_indices, split_metadata).
    """
    indices = np.arange(len(df))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=test_size,
        stratify=df[target_col],
        random_state=random_state,
        shuffle=True,
    )

    # Calculate deterministic hash of indices
    train_hash = hashlib.sha256(train_idx.tobytes()).hexdigest()
    test_hash = hashlib.sha256(test_idx.tobytes()).hexdigest()

    metadata = {
        "dataset_checksum": AI4I_SHA256_CHECKSUM,
        "total_samples": int(len(df)),
        "train_samples": int(len(train_idx)),
        "test_samples": int(len(test_idx)),
        "test_size": float(test_size),
        "random_state": int(random_state),
        "target_col": str(target_col),
        "train_failure_rate": float(df.iloc[train_idx][target_col].mean()),
        "test_failure_rate": float(df.iloc[test_idx][target_col].mean()),
        "train_index_hash": train_hash,
        "test_index_hash": test_hash,
    }

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": metadata,
            "train_indices": train_idx.tolist(),
            "test_indices": test_idx.tolist(),
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return train_idx, test_idx, metadata

