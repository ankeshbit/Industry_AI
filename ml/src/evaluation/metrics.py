"""
Model Evaluation and Business Metrics Module
Computes precision, recall, PR-AUC (Average Precision), ROC-AUC, confusion matrices,
and asymmetric operational cost penalties using illustrative PRD assumptions.
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)
import matplotlib.pyplot as plt
import seaborn as sns


# Asymmetric Operational Maintenance Cost Constants (Illustrative Baseline Assumptions from PRD Section 5.3)
DEFAULT_COST_FN: float = 10000.0  # Unpredicted breakdown: emergency downtime, lost throughput, ruined workpiece
DEFAULT_COST_FP: float = 200.0    # False alarm: 30-minute technician visual inspection & vibration probe


def compute_evaluation_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    cost_fn: float = DEFAULT_COST_FN,
    cost_fp: float = DEFAULT_COST_FP,
) -> Dict[str, Any]:
    """
    Computes a full suite of predictive maintenance evaluation metrics.

    Args:
        y_true: True binary target array.
        y_pred: Predicted binary labels.
        y_prob: Optional predicted failure probabilities.
        cost_fn: Cost penalty per False Negative (unpredicted catastrophic failure).
        cost_fp: Cost penalty per False Positive (unnecessary preventive inspection).

    Returns:
        Dictionary containing all metrics, confusion counts, and operational costs.
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Classification Metrics
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Threshold-independent curves
    roc_auc = None
    pr_auc = None
    if y_prob is not None:
        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except ValueError:
            roc_auc = 0.5
        try:
            pr_auc = float(average_precision_score(y_true, y_prob))
        except ValueError:
            pr_auc = float(np.mean(y_true))

    # Asymmetric Financial Cost Penalty
    operational_cost = float((fn * cost_fn) + (fp * cost_fp))

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "cost_fn_unit": cost_fn,
        "cost_fp_unit": cost_fp,
        "total_operational_cost": round(operational_cost, 2),
    }


def plot_confusion_matrices_grid(
    results: Dict[str, Dict[str, Any]],
    title_suffix: str = "",
    save_path: Optional[str] = None
) -> None:
    """Plots a multi-panel grid of confusion matrices for a set of models."""
    n_models = len(results)
    fig, axes = plt.subplots(1, n_models, figsize=(4.5 * n_models, 4))
    if n_models == 1:
        axes = [axes]

    for ax, (model_name, res) in zip(axes, results.items()):
        cm = np.array([
            [res["true_negatives"], res["false_positives"]],
            [res["false_negatives"], res["true_positives"]]
        ])
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            ax=ax,
            xticklabels=["Pred Normal", "Pred Fail"],
            yticklabels=["Act Normal", "Act Fail"]
        )
        cost_str = f"${res['total_operational_cost']:,.0f}"
        ax.set_title(
            f"{model_name}\nRecall: {res['recall']:.2f} | Cost: {cost_str}",
            fontweight="bold",
            fontsize=10
        )

    plt.suptitle(f"Confusion Matrices & Operational Costs {title_suffix}", fontsize=13, fontweight="bold", y=1.03)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close()


# ==============================================================================
# Stage 3 Multi-Tiered Evaluation Metrics Suite (PRD §10.1.4, §10.1.5, Architecture v1.4.2 §7.1)
# ==============================================================================

def compute_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Computes mean squared error of probability predictions: BS = (1/N) * sum((p_i - y_i)^2)."""
    y_true_arr = np.asarray(y_true, dtype=float).ravel()
    y_prob_arr = np.asarray(y_prob, dtype=float).ravel()
    return float(np.mean((y_prob_arr - y_true_arr) ** 2))


def compute_brier_skill_score(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    p_reference: float,
) -> float:
    """
    Computes Brier Skill Score (BSS) relative to the empirical training prevalence baseline:
        BSS = 1 - (BS_candidate / BS_reference)
    where BS_reference = (1/N) * sum((p_reference - y_i)^2).

    Governance Invariant (§7.1): p_reference MUST be derived from Sub-Train (y_bar_sub_train),
    never from outer-test labels.
    """
    bs_cand = compute_brier_score(y_true, y_prob)
    y_true_arr = np.asarray(y_true, dtype=float).ravel()
    ref_probs = np.full_like(y_true_arr, fill_value=float(p_reference))
    bs_ref = float(np.mean((ref_probs - y_true_arr) ** 2))

    if bs_ref <= 0.0:
        return 0.0
    return float(1.0 - (bs_cand / bs_ref))


def compute_expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Computes Expected Calibration Error (ECE) and reliability diagram data using uniform binning over [0, 1].

    Returns:
        Tuple of (ece, reliability_diagram_bins).
    """
    y_true_arr = np.asarray(y_true, dtype=int).ravel()
    y_prob_arr = np.asarray(y_prob, dtype=float).ravel()
    n_samples = len(y_true_arr)

    if n_samples == 0:
        return 0.0, []

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins_data = []
    weighted_abs_err_sum = 0.0

    for m in range(n_bins):
        low = bin_edges[m]
        high = bin_edges[m + 1]

        if m == n_bins - 1:
            in_bin = (y_prob_arr >= low) & (y_prob_arr <= high)
        else:
            in_bin = (y_prob_arr >= low) & (y_prob_arr < high)

        bin_count = int(np.sum(in_bin))
        if bin_count > 0:
            bin_conf = float(np.mean(y_prob_arr[in_bin]))
            bin_acc = float(np.mean(y_true_arr[in_bin]))
            abs_err = abs(bin_acc - bin_conf)
            weighted_abs_err_sum += (bin_count / n_samples) * abs_err
        else:
            bin_conf = float((low + high) / 2.0)
            bin_acc = 0.0
            abs_err = 0.0

        bins_data.append({
            "bin_index": m,
            "bin_lower": round(float(low), 4),
            "bin_upper": round(float(high), 4),
            "sample_count": bin_count,
            "mean_confidence": round(bin_conf, 4),
            "empirical_accuracy": round(bin_acc, 4),
            "calibration_gap": round(abs_err, 4),
        })

    ece = float(weighted_abs_err_sum)
    return ece, bins_data


def compute_stage3_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    p_reference: float,
    cost_fn: float = DEFAULT_COST_FN,
    cost_fp: float = DEFAULT_COST_FP,
) -> Dict[str, Any]:
    """
    Computes complete 4-tier Stage 3 evaluation metrics suite (§7.1):
    1. Ranking: Canonical Average Precision (sklearn) & ROC-AUC.
    2. Calibration: Brier score, Brier Skill Score, ECE, reliability diagram.
    3. Operational decision metrics at frozen threshold tau*.
    4. Operational illustrative costs with mandatory PRD disclaimer.
    """
    y_true_arr = np.asarray(y_true, dtype=int).ravel()
    y_prob_arr = np.asarray(y_prob, dtype=float).ravel()

    # 1. Ranking Metrics
    try:
        ap = float(average_precision_score(y_true_arr, y_prob_arr))
    except ValueError:
        ap = float(np.mean(y_true_arr))

    try:
        roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
    except ValueError:
        roc_auc = 0.5

    # 2. Probability Calibration Metrics
    bs = compute_brier_score(y_true_arr, y_prob_arr)
    ref_probs = np.full_like(y_true_arr, fill_value=float(p_reference), dtype=float)
    bs_ref = compute_brier_score(y_true_arr, ref_probs)
    bss = compute_brier_skill_score(y_true_arr, y_prob_arr, p_reference=p_reference)
    ece, rel_bins = compute_expected_calibration_error(y_true_arr, y_prob_arr, n_bins=10)

    # 3. Operational Decision Metrics at frozen threshold
    if threshold == 0.0:
        y_pred = np.ones_like(y_true_arr)
    elif threshold >= 1.0:
        y_pred = (y_prob_arr >= 1.0).astype(int)
    else:
        y_pred = (y_prob_arr >= threshold).astype(int)

    cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))
    total_cost = float((fn * cost_fn) + (fp * cost_fp))

    return {
        "ranking_metrics": {
            "average_precision": round(ap, 5),
            "roc_auc": round(roc_auc, 5),
            "metric_note": (
                "average_precision uses scikit-learn average_precision_score (canonical PR-AUC), "
                "not trapezoidal approximation."
            ),
        },
        "calibration_metrics": {
            "brier_score": round(bs, 6),
            "reference_brier_score": round(bs_ref, 6),
            "brier_skill_score": round(bss, 5),
            "expected_calibration_error": round(ece, 5),
            "p_reference": round(float(p_reference), 6),
            "reliability_diagram": rel_bins,
        },
        "operational_metrics": {
            "threshold": round(float(threshold), 5),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_negatives": int(tn),
            "recall": round(rec, 4),
            "precision": round(prec, 4),
            "f1_score": round(f1, 4),
            "cost_fn_unit": cost_fn,
            "cost_fp_unit": cost_fp,
            "total_operational_cost": round(total_cost, 2),
            "cost_disclaimer": (
                "The 50:1 cost ratio ($10,000 / $200) is an illustrative PRD benchmark (Appendix E) "
                "and does not represent verified customer plant economics."
            ),
        },
    }


