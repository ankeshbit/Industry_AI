"""
Cost-Sensitive Decision Threshold Optimization Module for INDUSTRIA AI (Stage 3)

Implements out-of-fold threshold calibration to minimize asymmetric industrial operational losses:
Cost(tau) = FN(tau) * C_FN + FP(tau) * C_FP
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

from ml.src.evaluation.metrics import DEFAULT_COST_FN, DEFAULT_COST_FP


def optimize_decision_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    cost_fn: float = DEFAULT_COST_FN,
    cost_fp: float = DEFAULT_COST_FP,
    threshold_grid: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Finds the optimal binary classification threshold tau* that minimizes
    the asymmetric operational cost function on out-of-fold probability estimates.

    Args:
        y_true: Ground truth binary target labels (0 or 1).
        y_prob: Predicted positive class probabilities in [0, 1].
        cost_fn: Financial penalty for an undetected catastrophic failure (False Negative).
        cost_fp: Financial penalty for an unnecessary technician dispatch (False Positive).
        threshold_grid: Optional array of candidate thresholds in (0, 1). Default: 0.01 to 0.99.

    Returns:
        Dictionary containing optimal threshold tau*, metrics at tau*, comparison vs default tau=0.5,
        and the full cost curve.
    """
    if threshold_grid is None:
        threshold_grid = np.linspace(0.01, 0.99, 99)

    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    results_table = []
    min_cost = float("inf")
    best_tau = 0.5
    best_metrics = None

    for tau in threshold_grid:
        y_pred = (y_prob_arr >= tau).astype(int)
        cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        cost = float((fn * cost_fn) + (fp * cost_fp))
        rec = float(recall_score(y_true_arr, y_pred, zero_division=0))
        prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
        f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))

        record = {
            "threshold": round(float(tau), 4),
            "cost": cost,
            "false_negatives": int(fn),
            "false_positives": int(fp),
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "recall": round(rec, 4),
            "precision": round(prec, 4),
            "f1_score": round(f1, 4),
        }
        results_table.append(record)

        # Optimization: minimize cost, tie-break on higher recall (safety first in industrial plants)
        if cost < min_cost or (cost == min_cost and rec > (best_metrics["recall"] if best_metrics else 0)):
            min_cost = cost
            best_tau = float(tau)
            best_metrics = record

    # Evaluate default threshold tau = 0.5 for baseline comparison
    y_pred_default = (y_prob_arr >= 0.5).astype(int)
    cm_default = confusion_matrix(y_true_arr, y_pred_default, labels=[0, 1])
    tn_def, fp_def, fn_def, tp_def = cm_default.ravel()
    cost_default = float((fn_def * cost_fn) + (fp_def * cost_fp))
    default_metrics = {
        "threshold": 0.5,
        "cost": cost_default,
        "false_negatives": int(fn_def),
        "false_positives": int(fp_def),
        "true_positives": int(tp_def),
        "true_negatives": int(tn_def),
        "recall": round(float(recall_score(y_true_arr, y_pred_default, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true_arr, y_pred_default, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true_arr, y_pred_default, zero_division=0)), 4),
    }

    savings = round(cost_default - min_cost, 2)

    return {
        "optimal_threshold": round(best_tau, 4),
        "optimal_cost": round(min_cost, 2),
        "optimal_metrics": best_metrics,
        "default_threshold": 0.5,
        "default_cost": round(cost_default, 2),
        "default_metrics": default_metrics,
        "cost_reduction_amount": savings,
        "cost_reduction_percent": round((savings / cost_default) * 100.0, 2) if cost_default > 0 else 0.0,
        "cost_curve": results_table,
    }


def apply_decision_threshold(y_prob: np.ndarray, threshold: float) -> np.ndarray:
    """Applies a calibrated decision threshold to predicted probabilities."""
    return (np.asarray(y_prob) >= threshold).astype(int)

