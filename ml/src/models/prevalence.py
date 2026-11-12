"""
Prevalence Baseline Model (B0) Module for INDUSTRIA AI (Stage 3 Phase 2A)

Implements the deterministic empirical prevalence baseline adhering strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3, §5.1, §6.2, §7.1)
- Root PRD.md v1.2 (§10.1.3, §10.1.5)

Specifications:
1. Model Function: Constant probability predictor p_hat(x) = y_bar_sub_train.
2. Zero Hyperparameter Tuning: Deterministic analytical floor; no inner-CV tuning.
3. Feature Invariance: Feature-agnostic; depends purely on Sub-Train target labels.
4. Calibration Treatment: Identity mapping (untransformed prevalence probability;
   learned post-hoc calibration is mathematically redundant).
5. Scikit-learn Compatibility: Implements fit, predict, predict_proba, and decision_function.
"""

from typing import Union, Optional, Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin


class PrevalenceBaseline(BaseEstimator, ClassifierMixin):
    """
    Constant prevalence predictor B0.

    Predicts the empirical base rate of the Sub-Train partition across all instances:
        p_hat(x) = y_bar_sub_train = (1 / N_sub_train) * sum(y_sub_train)
    """

    def __init__(self):
        self.prevalence_: Optional[float] = None
        self.classes_: Optional[np.ndarray] = None
        self.n_samples_fitted_: Optional[int] = None
        self.n_positives_fitted_: Optional[int] = None
        self.is_fitted_: bool = False

    def fit(
        self,
        X: Optional[Union[pd.DataFrame, np.ndarray]] = None,
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> "PrevalenceBaseline":
        """
        Fits baseline strictly on the Sub-Train partition labels.
        Features X are completely ignored.

        Args:
            X: Ignored feature matrix.
            y: Binary target labels (0 or 1).

        Returns:
            Fitted PrevalenceBaseline instance.
        """
        if y is None:
            raise ValueError("Target y must be provided to fit PrevalenceBaseline.")

        y_arr = np.asarray(y, dtype=int).ravel()
        if len(y_arr) == 0:
            raise ValueError("Cannot fit PrevalenceBaseline on empty target array.")

        self.classes_ = np.array([0, 1], dtype=int)
        self.n_samples_fitted_ = len(y_arr)
        self.n_positives_fitted_ = int(np.sum(y_arr == 1))
        self.prevalence_ = float(self.n_positives_fitted_ / self.n_samples_fitted_)
        self.is_fitted_ = True
        return self

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Generates constant predicted probability array [1 - p_hat, p_hat] of shape (N, 2).

        Args:
            X: Input features (used only to determine row count N).

        Returns:
            2D array of shape (N, 2).
        """
        if not self.is_fitted_:
            raise RuntimeError("PrevalenceBaseline is not fitted yet.")

        n_samples = len(X)
        p1 = float(self.prevalence_)
        p0 = 1.0 - p1

        p0_col = np.full((n_samples, 1), fill_value=p0, dtype=np.float64)
        p1_col = np.full((n_samples, 1), fill_value=p1, dtype=np.float64)
        return np.hstack([p0_col, p1_col])

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        threshold: float = 0.5,
    ) -> np.ndarray:
        """
        Generates binary predictions at specified decision threshold.
        """
        prob = self.predict_proba(X)[:, 1]
        return (prob >= threshold).astype(int)

    def decision_function(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Returns log-odds score log(p_hat / (1 - p_hat)).
        """
        if not self.is_fitted_:
            raise RuntimeError("PrevalenceBaseline is not fitted yet.")

        n_samples = len(X)
        eps = 1e-12
        p_clipped = np.clip(self.prevalence_, eps, 1.0 - eps)
        logit = float(np.log(p_clipped / (1.0 - p_clipped)))
        return np.full(n_samples, fill_value=logit, dtype=np.float64)

