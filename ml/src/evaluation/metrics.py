"""
Model Evaluation and Business Metrics Module
Computes precision, recall, PR-AUC (Average Precision), ROC-AUC, confusion matrices,
and asymmetric operational cost penalties using illustrative PRD assumptions.
"""

from typing import Dict, Any, Optional
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
            f"{model_name}\\nRecall: {res['recall']:.2f} | Cost: {cost_str}",
            fontweight="bold",
            fontsize=10
        )

    plt.suptitle(f"Confusion Matrices & Operational Costs {title_suffix}", fontsize=13, fontweight="bold", y=1.03)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches="tight", dpi=150)
    plt.close()

