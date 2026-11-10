"""
Domain Feature Engineering Module for INDUSTRIA AI (Stage 3)

Implements physics-based domain transformations derived from industrial equipment
dynamics and predictive maintenance failure modes (PWF, HDF, OSF, TWF).
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from sklearn.base import BaseEstimator, TransformerMixin

from ml.src.features.schemas import NUMERICAL_FEATURES


# List of newly generated domain features
ENGINEERED_FEATURE_NAMES: List[str] = [
    "Mechanical_Power_W",
    "Temp_Dissipation_Delta_K",
    "Overstrain_Min_Nm",
    "Speed_Torque_Ratio",
    "Thermal_Strain_Interaction",
]


class IndustrialFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer that computes physics-derived industrial features:
    1. Mechanical Power (W): Torque [Nm] * Rotational Speed [rad/s]
       Directly targets Power Failure (PWF, active outside 3500W-9000W envelope).
    2. Temperature Dissipation Delta (K): Process Temp - Air Temp
       Directly targets Heat Dissipation Failure (HDF, active when delta < 8.6K and speed < 1380 rpm).
    3. Overstrain Metric (min*Nm): Tool wear [min] * Torque [Nm]
       Directly targets Overstrain Failure (OSF, active when product exceeds 11,000-13,000 min*Nm).
    4. Speed-to-Torque Ratio: Rotational speed [rpm] / (Torque [Nm] + 1.0)
       Captures abnormal operating regimes (high-slip or stall-like conditions).
    5. Thermal-Strain Interaction: Temp Delta * Tool wear
       Models compounded wear under adverse thermal conditions.
    """

    def __init__(self, include_raw_features: bool = True):
        self.include_raw_features = include_raw_features
        self.feature_names_out_: Optional[List[str]] = None

    def fit(self, X, y=None):
        """Stateless fit - establishes output feature schema."""
        if isinstance(X, pd.DataFrame):
            base_cols = list(X.columns)
        else:
            base_cols = [f"feat_{i}" for i in range(X.shape[1])]

        if self.include_raw_features:
            self.feature_names_out_ = base_cols + list(ENGINEERED_FEATURE_NAMES)
        else:
            self.feature_names_out_ = list(ENGINEERED_FEATURE_NAMES)

        return self

    def transform(self, X):
        """
        Computes domain features. Accepts either pandas DataFrame or 2D numpy array.
        """
        is_df = isinstance(X, pd.DataFrame)
        if not is_df:
            # Map columns by expected positional schema
            if X.shape[1] == 5:
                df = pd.DataFrame(X, columns=NUMERICAL_FEATURES)
            elif X.shape[1] == 6:
                df = pd.DataFrame(X, columns=["Type"] + NUMERICAL_FEATURES)
            else:
                raise ValueError(f"Unexpected number of features for transformation: {X.shape[1]}")
        else:
            df = X.copy()

        air_temp = df["Air temperature [K]"].values.astype(float)
        proc_temp = df["Process temperature [K]"].values.astype(float)
        speed = df["Rotational speed [rpm]"].values.astype(float)
        torque = df["Torque [Nm]"].values.astype(float)
        wear = df["Tool wear [min]"].values.astype(float)

        # 1. Mechanical Power: P = Torque * omega (omega = rpm * 2 * pi / 60)
        omega = speed * (2.0 * np.pi / 60.0)
        mech_power = torque * omega

        # 2. Temperature Dissipation Delta: Process Temp - Air Temp
        temp_delta = proc_temp - air_temp

        # 3. Overstrain: Tool wear * Torque
        overstrain = wear * torque

        # 4. Speed-to-Torque Ratio (epsilon = 1.0 to prevent division by zero)
        speed_torque_ratio = speed / (torque + 1.0)

        # 5. Thermal-Strain Interaction: Temp Delta * Tool wear
        thermal_strain = temp_delta * wear

        engineered_dict = {
            "Mechanical_Power_W": mech_power,
            "Temp_Dissipation_Delta_K": temp_delta,
            "Overstrain_Min_Nm": overstrain,
            "Speed_Torque_Ratio": speed_torque_ratio,
            "Thermal_Strain_Interaction": thermal_strain,
        }

        if is_df:
            res_df = df.copy() if self.include_raw_features else pd.DataFrame(index=df.index)
            for col_name, col_vals in engineered_dict.items():
                res_df[col_name] = col_vals
            return res_df
        else:
            eng_matrix = np.column_stack(list(engineered_dict.values()))
            if self.include_raw_features:
                return np.hstack([X, eng_matrix])
            else:
                return eng_matrix

    def get_feature_names_out(self, input_features=None) -> List[str]:
        if self.feature_names_out_ is None:
            return list(ENGINEERED_FEATURE_NAMES)
        return self.feature_names_out_
