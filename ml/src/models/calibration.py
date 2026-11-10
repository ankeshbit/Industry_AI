"""
Model-Agnostic Probability Calibration Module for INDUSTRIA AI (Stage 3 Phase 2A)

Implements post-hoc probability calibration adhering strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§5.1, §5.2)
- Root PRD.md v1.2 (§10.1.4, AC-FP-5)

Specifications:
1. Model-Agnostic Raw Score Extraction:
   - B0 (Prevalence): Identity mapping (untransformed prevalence probability).
   - B1 (Logistic Regression): Linear logit predictor via decision_function(X).
   - M1 (Random Forest): Clipped log-odds margin z = log((p + eps) / (1 - p + eps)).
   - M2 (XGBoost): Additive tree leaf margin f(x) via output_margin=True.
2. Parametric Platt Sigmoid Calibration:
   p_cal = sigma(w * z + c) = 1 / (1 + exp(-(w * z + c)))
3. Exact Fisher Information / Inverse Hessian Standard Errors:
   SE(w) = sqrt(H^-1[0,0]), SE(c) = sqrt(H^-1[1,1])
4. Strict Governance Guards:
   - Hard positive event gate: N_cal,pos >= 25 (raises InsufficientCalibrationEventsError).
   - Monotonicity invariant: w > 0 (raises CalibrationFailureError).
   - Plausibility boundaries: 0.05 <= w <= 20.0.
   - Instability warning: SE(w)/w > 0.5 or w > 10.0 tags HIGH_CALIBRATION_VARIANCE.
   - Zero silent fallback: Fail-closed architecture on numerical or optimization divergence.
"""

from typing import Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.base import BaseEstimator, ClassifierMixin


class InsufficientCalibrationEventsError(ValueError):
    """Raised when the calibration partition fails the minimum positive failure event gate (N_cal,pos < 25)."""
    pass


class CalibrationFailureError(RuntimeError):
    """Raised when probability calibration fails to converge, produces invalid parameters, or violates w > 0."""
    pass


class PlattCalibrator(BaseEstimator, ClassifierMixin):
    """
    Univariate Platt sigmoid calibrator with exact Hessian-derived standard errors.

    Maps uncalibrated 1D decision scores z to posterior probability estimates:
        p(z) = sigma(w * z + c) = 1 / (1 + exp(-(w * z + c)))

    Parameters are optimized by maximizing binary logistic log-likelihood
    (minimizing binary cross-entropy loss).
    """

    def __init__(
        self,
        min_w: float = 0.05,
        max_w: float = 20.0,
        max_iter: int = 500,
        tol: float = 1e-7,
    ):
        self.min_w = min_w
        self.max_w = max_w
        self.max_iter = max_iter
        self.tol = tol

        # Fitted attributes
        self.w_: Optional[float] = None
        self.c_: Optional[float] = None
        self.se_w_: Optional[float] = None
        self.se_c_: Optional[float] = None
        self.covariance_matrix_: Optional[np.ndarray] = None
        self.warnings_: list = []
        self.is_fitted_: bool = False

    def _loss_and_grad(
        self,
        params: np.ndarray,
        z: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[float, np.ndarray]:
        """Computes binary cross-entropy loss and analytical gradient with numerical clipping."""
        w, c = params[0], params[1]
        logits = w * z + c
        p = expit(logits)
        eps = 1e-15
        p_clipped = np.clip(p, eps, 1.0 - eps)

        loss = -float(np.sum(y * np.log(p_clipped) + (1.0 - y) * np.log(1.0 - p_clipped)))
        err = p_clipped - y
        grad_w = float(np.sum(err * z))
        grad_c = float(np.sum(err))
        return loss, np.array([grad_w, grad_c], dtype=np.float64)

    def _compute_hessian(
        self,
        params: np.ndarray,
        z: np.ndarray,
    ) -> np.ndarray:
        """Computes exact 2x2 Fisher information / Hessian matrix at parameters (w, c)."""
        w, c = params[0], params[1]
        logits = w * z + c
        p = expit(logits)
        weights = p * (1.0 - p)

        h_ww = float(np.sum(weights * z * z))
        h_wc = float(np.sum(weights * z))
        h_cc = float(np.sum(weights))
        return np.array([[h_ww, h_wc], [h_wc, h_cc]], dtype=np.float64)

    def fit(self, z: np.ndarray, y: np.ndarray) -> "PlattCalibrator":
        """
        Fits slope w and intercept c on raw scores z and binary labels y.

        Args:
            z: 1D array of continuous decision scores / logits.
            y: 1D array of binary ground truth labels (0 or 1).

        Returns:
            Self instance.
        """
        z_arr = np.asarray(z, dtype=np.float64).ravel()
        y_arr = np.asarray(y, dtype=np.float64).ravel()

        if len(z_arr) != len(y_arr):
            raise ValueError(f"Length mismatch: z has {len(z_arr)} samples, y has {len(y_arr)}")
        if len(np.unique(y_arr)) < 2:
            raise CalibrationFailureError("Calibration target y must contain both classes (0 and 1).")

        pos_count = int(np.sum(y_arr == 1.0))
        neg_count = int(len(y_arr) - pos_count)
        if pos_count == 0 or neg_count == 0:
            raise CalibrationFailureError(f"Degenerate calibration sample: pos={pos_count}, neg={neg_count}")

        # Deterministic initialization based on base rate
        base_rate = float(pos_count / len(y_arr))
        eps = 1e-6
        base_rate_clipped = np.clip(base_rate, eps, 1.0 - eps)
        init_c = float(np.log(base_rate_clipped / (1.0 - base_rate_clipped)))
        init_w = 1.0
        init_params = np.array([init_w, init_c], dtype=np.float64)

        opt_result = minimize(
            fun=self._loss_and_grad,
            x0=init_params,
            args=(z_arr, y_arr),
            method="L-BFGS-B",
            jac=True,
            options={"maxiter": self.max_iter, "ftol": self.tol, "gtol": self.tol},
        )

        if not opt_result.success and "CONVERGENCE" not in opt_result.message.upper():
            raise CalibrationFailureError(f"Platt calibration optimization failed to converge: {opt_result.message}")

        w_opt, c_opt = float(opt_result.x[0]), float(opt_result.x[1])

        # Strict Monotonicity Invariant (§5.2): w > 0
        if w_opt <= 0.0 or np.isnan(w_opt):
            raise CalibrationFailureError(
                f"Fitted Platt calibration slope w={w_opt:.4f} <= 0, violating positive risk monotonicity. "
                "Silent fallback is prohibited."
            )

        self.w_ = w_opt
        self.c_ = c_opt
        self.warnings_ = []

        # Check plausibility boundaries [0.05, 20.0]
        if self.w_ < self.min_w or self.w_ > self.max_w:
            self.warnings_.append(
                f"EXTREME_CALIBRATION_SLOPE: w={self.w_:.4f} outside plausibility interval [{self.min_w}, {self.max_w}]"
            )

        # Compute exact inverse Hessian covariance and standard errors
        hess = self._compute_hessian(opt_result.x, z_arr)
        try:
            cov = np.linalg.inv(hess)
            se_w = float(np.sqrt(np.maximum(0.0, cov[0, 0])))
            se_c = float(np.sqrt(np.maximum(0.0, cov[1, 1])))
            self.covariance_matrix_ = cov
            self.se_w_ = se_w
            self.se_c_ = se_c

            # High calibration variance audit tag (§5.2): SE(w)/w > 0.5 or w > 10.0
            rel_se_w = se_w / self.w_
            if rel_se_w > 0.5 or self.w_ > 10.0:
                self.warnings_.append("HIGH_CALIBRATION_VARIANCE")
        except np.linalg.LinAlgError:
            self.covariance_matrix_ = None
            self.se_w_ = float("nan")
            self.se_c_ = float("nan")
            self.warnings_.append("SINGULAR_CALIBRATION_HESSIAN")

        self.is_fitted_ = True
        return self

    def predict_proba(self, z: np.ndarray) -> np.ndarray:
        """
        Generates calibrated posterior probabilities [P(Y=0|z), P(Y=1|z)].

        Args:
            z: 1D array or 2D array with 1 column of decision scores.

        Returns:
            2D array of shape (N, 2).
        """
        if not self.is_fitted_:
            raise RuntimeError("PlattCalibrator is not fitted yet.")
        z_arr = np.asarray(z, dtype=np.float64).ravel()
        p1 = expit(self.w_ * z_arr + self.c_)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, z: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Generates binary classifications at the given probability threshold."""
        prob = self.predict_proba(z)[:, 1]
        return (prob >= threshold).astype(int)


class ModelAgnosticCalibrator(BaseEstimator, ClassifierMixin):
    """
    Wraps any Stage 3 base estimator (B0, B1, M1, M2) with its algorithm-specific
    raw score extraction and post-hoc probability calibrator.

    Enforces data isolation and the minimum calibration positive event gate (N_cal,pos >= 25).
    """

    def __init__(
        self,
        base_estimator: Any,
        model_family: str = "B1",
        min_calibration_positives: int = 25,
        min_w: float = 0.05,
        max_w: float = 20.0,
    ):
        self.base_estimator = base_estimator
        self.model_family = model_family.upper().strip()
        self.min_calibration_positives = min_calibration_positives
        self.min_w = min_w
        self.max_w = max_w

        self.calibrator_: Optional[PlattCalibrator] = None
        self.is_fitted_: bool = False
        self.diagnostics_: Dict[str, Any] = {}

    def extract_raw_scores(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Extracts raw uncalibrated scores from the base estimator according to algorithm family (§5.1).

        - B0: Returns uncalibrated constant base rate probability.
        - B1: Returns linear logit decision_function(X).
        - M1: Returns clipped log-odds of tree predict_proba.
        - M2: Returns additive tree margin via output_margin=True.
        """
        if self.model_family == "B0":
            # Prevalence baseline: predict_proba already returns empirical base rate
            proba = self.base_estimator.predict_proba(X)
            if proba.ndim == 2:
                return proba[:, 1]
            return proba.ravel()

        elif self.model_family == "B1":
            # Logistic Regression: decision_function gives unbounded linear logit z
            if hasattr(self.base_estimator, "decision_function"):
                return self.base_estimator.decision_function(X).ravel()
            raise AttributeError("Base estimator for B1 does not implement decision_function.")

        elif self.model_family == "M1":
            # Random Forest: bagged probability mapped to log-odds margin z
            proba = self.base_estimator.predict_proba(X)[:, 1]
            eps = 1e-4
            p_clip = np.clip(proba, eps, 1.0 - eps)
            return np.log(p_clip / (1.0 - p_clip))

        elif self.model_family == "M2":
            # XGBoost: unconstrained additive margin
            if hasattr(self.base_estimator, "predict"):
                return self.base_estimator.predict(X, output_margin=True).ravel()
            raise AttributeError("Base estimator for M2 does not support output_margin.")

        else:
            raise ValueError(f"Unsupported model family: '{self.model_family}'. Must be B0, B1, M1, or M2.")

    def fit(
        self,
        X_cal: Union[pd.DataFrame, np.ndarray],
        y_cal: Union[pd.Series, np.ndarray],
    ) -> "ModelAgnosticCalibrator":
        """
        Fits post-hoc calibrator strictly on the separate Calibration partition.
        Base estimator is completely frozen during this step.

        Args:
            X_cal: Features for the calibration partition (N = 960).
            y_cal: Binary failure target for the calibration partition.

        Returns:
            Fitted ModelAgnosticCalibrator.
        """
        y_arr = np.asarray(y_cal, dtype=int).ravel()
        pos_events = int(np.sum(y_arr == 1))

        # Strict Single Pre-Declared Sample Size Rule (§5.2): N_cal,pos >= 25
        if pos_events < self.min_calibration_positives:
            raise InsufficientCalibrationEventsError(
                f"Calibration partition failed minimum positive gate: got {pos_events} failure events, "
                f"minimum required is {self.min_calibration_positives}. Evaluation aborted."
            )

        if self.model_family == "B0":
            # B0: Identity mapping (learned calibration is mathematically redundant, §5.1)
            self.calibrator_ = None
            self.diagnostics_ = {
                "model_family": "B0",
                "calibration_method": "identity",
                "cal_samples": len(y_arr),
                "cal_positives": pos_events,
                "passes_gate": True,
                "w": 1.0,
                "c": 0.0,
                "se_w": 0.0,
                "se_c": 0.0,
                "warnings": [],
            }
            self.is_fitted_ = True
            return self

        # Extract uncalibrated scores from frozen base estimator
        z_cal = self.extract_raw_scores(X_cal)

        # Fit Platt Calibrator
        cal = PlattCalibrator(
            min_w=self.min_w,
            max_w=self.max_w,
        )
        cal.fit(z_cal, y_arr)

        self.calibrator_ = cal
        rel_se_w = cal.se_w_ / cal.w_ if (cal.se_w_ is not None and not np.isnan(cal.se_w_)) else None

        self.diagnostics_ = {
            "model_family": self.model_family,
            "calibration_method": "platt_sigmoid",
            "cal_samples": len(y_arr),
            "cal_positives": pos_events,
            "passes_gate": True,
            "w": cal.w_,
            "c": cal.c_,
            "se_w": cal.se_w_,
            "se_c": cal.se_c_,
            "relative_se_w": rel_se_w,
            "warnings": cal.warnings_,
        }
        self.is_fitted_ = True
        return self

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Generates calibrated posterior probabilities [P(Y=0|X), P(Y=1|X)].

        Args:
            X: Input feature matrix.

        Returns:
            2D numpy array of shape (N, 2).
        """
        if not self.is_fitted_:
            raise RuntimeError("ModelAgnosticCalibrator is not fitted yet.")

        if self.model_family == "B0":
            # Returns prevalence probability directly from base estimator
            return self.base_estimator.predict_proba(X)

        z = self.extract_raw_scores(X)
        return self.calibrator_.predict_proba(z)

    def predict(self, X: Union[pd.DataFrame, np.ndarray], threshold: float = 0.5) -> np.ndarray:
        """Generates binary classifications at specified threshold."""
        prob = self.predict_proba(X)[:, 1]
        return (prob >= threshold).astype(int)

