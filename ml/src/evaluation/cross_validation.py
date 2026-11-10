"""
Nested Cross-Validation and Statistical Hypothesis Testing Module (Stage 3)

Implements:
1. Leak-Free Nested Stratified Cross-Validation (Outer K=5, Inner K=4).
2. Inner-fold threshold optimization with out-of-sample outer fold evaluation.
3. Nadeau & Bengio Corrected Resampled t-Test for dependent CV fold comparison.
4. Exact Binomial McNemar Test for discrete paired predictions.
5. Stratified Bootstrap Confidence Intervals for rare-event metrics.
"""

from typing import Dict, Any, List, Tuple, Callable, Optional
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedKFold
from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

from ml.src.evaluation.threshold import optimize_decision_threshold
from ml.src.evaluation.metrics import DEFAULT_COST_FN, DEFAULT_COST_FP


def run_nested_cross_validation(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    outer_k: int = 5,
    inner_k: int = 4,
    random_state: int = 42,
    cost_fn: float = DEFAULT_COST_FN,
    cost_fp: float = DEFAULT_COST_FP,
) -> Dict[str, Any]:
    """
    Executes a complete 5x4 nested cross-validation protocol:
    - Inner loop optimizes decision threshold tau*_k on inner OOF predictions.
    - Outer loop evaluates the frozen model and frozen tau*_k out-of-sample.

    Args:
        pipeline: Un-fitted Scikit-learn Pipeline.
        X: Features DataFrame.
        y: Target Series.
        outer_k: Number of outer folds (default: 5).
        inner_k: Number of inner folds (default: 4).
        random_state: Deterministic random seed.
        cost_fn: Cost per False Negative.
        cost_fp: Cost per False Positive.

    Returns:
        Comprehensive nested CV evaluation dictionary.
    """
    outer_cv = StratifiedKFold(n_splits=outer_k, shuffle=True, random_state=random_state)
    
    outer_results = []
    pooled_y_true = []
    pooled_outer_probs = []
    pooled_outer_preds = []

    y_arr = y.values.astype(int)

    for outer_fold, (train_idx, val_idx) in enumerate(outer_cv.split(X, y_arr)):
        X_outer_train, y_outer_train = X.iloc[train_idx], y.iloc[train_idx]
        X_outer_val, y_outer_val = X.iloc[val_idx], y.iloc[val_idx]
        y_val_arr = y_outer_val.values.astype(int)

        # -------------------------------------------------------------
        # INNER LOOP: Evaluate inner CV to find optimal tau*_k
        # -------------------------------------------------------------
        inner_cv = StratifiedKFold(n_splits=inner_k, shuffle=True, random_state=random_state + outer_fold)
        inner_oof_probs = np.zeros(len(X_outer_train))
        y_inner_train_arr = y_outer_train.values.astype(int)

        for inner_train_idx, inner_val_idx in inner_cv.split(X_outer_train, y_inner_train_arr):
            X_in_train = X_outer_train.iloc[inner_train_idx]
            y_in_train = y_outer_train.iloc[inner_train_idx]
            X_in_val = X_outer_train.iloc[inner_val_idx]

            fold_pipe = clone(pipeline)
            fold_pipe.fit(X_in_train, y_in_train)
            inner_oof_probs[inner_val_idx] = fold_pipe.predict_proba(X_in_val)[:, 1]

        # Inner Threshold Optimization on Inner OOF probabilities ONLY
        thresh_opt = optimize_decision_threshold(
            y_true=y_inner_train_arr,
            y_prob=inner_oof_probs,
            cost_fn=cost_fn,
            cost_fp=cost_fp,
        )
        tau_k = thresh_opt["optimal_threshold"]

        # -------------------------------------------------------------
        # OUTER EVALUATION: Fit on full D_train,k and predict on D_val,k
        # -------------------------------------------------------------
        final_outer_pipeline = clone(pipeline)
        final_outer_pipeline.fit(X_outer_train, y_outer_train)

        val_probs = final_outer_pipeline.predict_proba(X_outer_val)[:, 1]
        val_preds_optimal = (val_probs >= tau_k).astype(int)
        val_preds_default = (val_probs >= 0.5).astype(int)

        # Metrics at optimal threshold tau_k
        cm_opt = confusion_matrix(y_val_arr, val_preds_optimal, labels=[0, 1])
        tn_opt, fp_opt, fn_opt, tp_opt = cm_opt.ravel()
        cost_opt = float((fn_opt * cost_fn) + (fp_opt * cost_fp))

        # Metrics at default threshold 0.5
        cm_def = confusion_matrix(y_val_arr, val_preds_default, labels=[0, 1])
        tn_def, fp_def, fn_def, tp_def = cm_def.ravel()
        cost_def = float((fn_def * cost_fn) + (fp_def * cost_fp))

        pr_auc = float(average_precision_score(y_val_arr, val_probs))
        roc_auc = float(roc_auc_score(y_val_arr, val_probs))
        rec_opt = float(recall_score(y_val_arr, val_preds_optimal, zero_division=0))
        prec_opt = float(precision_score(y_val_arr, val_preds_optimal, zero_division=0))
        f1_opt = float(f1_score(y_val_arr, val_preds_optimal, zero_division=0))

        fold_record = {
            "outer_fold": outer_fold + 1,
            "pr_auc": round(pr_auc, 4),
            "roc_auc": round(roc_auc, 4),
            "optimal_threshold": tau_k,
            "cost_at_optimal": round(cost_opt, 2),
            "cost_at_default": round(cost_def, 2),
            "fn_at_optimal": int(fn_opt),
            "fp_at_optimal": int(fp_opt),
            "fn_at_default": int(fn_def),
            "fp_at_default": int(fp_def),
            "recall_at_optimal": round(rec_opt, 4),
            "precision_at_optimal": round(prec_opt, 4),
            "f1_at_optimal": round(f1_opt, 4),
        }
        outer_results.append(fold_record)

        pooled_y_true.extend(y_val_arr.tolist())
        pooled_outer_probs.extend(val_probs.tolist())
        pooled_outer_preds.extend(val_preds_optimal.tolist())

    # Aggregate Statistics Across Outer Folds
    df_folds = pd.DataFrame(outer_results)
    mean_pr_auc = float(df_folds["pr_auc"].mean())
    std_pr_auc = float(df_folds["pr_auc"].std())
    mean_roc_auc = float(df_folds["roc_auc"].mean())
    std_roc_auc = float(df_folds["roc_auc"].std())
    mean_cost_opt = float(df_folds["cost_at_optimal"].mean())
    std_cost_opt = float(df_folds["cost_at_optimal"].std())
    mean_cost_def = float(df_folds["cost_at_default"].mean())

    # Pooled Global Metrics
    pooled_y_true_arr = np.array(pooled_y_true)
    pooled_probs_arr = np.array(pooled_outer_probs)
    pooled_preds_arr = np.array(pooled_outer_preds)

    pooled_pr_auc = float(average_precision_score(pooled_y_true_arr, pooled_probs_arr))
    pooled_cm = confusion_matrix(pooled_y_true_arr, pooled_preds_arr, labels=[0, 1])
    p_tn, p_fp, p_fn, p_tp = pooled_cm.ravel()
    pooled_total_cost = float((p_fn * cost_fn) + (p_fp * cost_fp))

    return {
        "n_outer_folds": outer_k,
        "n_inner_folds": inner_k,
        "outer_fold_results": outer_results,
        "summary": {
            "mean_pr_auc": round(mean_pr_auc, 4),
            "std_pr_auc": round(std_pr_auc, 4),
            "mean_roc_auc": round(mean_roc_auc, 4),
            "std_roc_auc": round(std_roc_auc, 4),
            "mean_cost_optimal_tau": round(mean_cost_opt, 2),
            "std_cost_optimal_tau": round(std_cost_opt, 2),
            "mean_cost_default_tau": round(mean_cost_def, 2),
            "pooled_pr_auc": round(pooled_pr_auc, 4),
            "pooled_total_cost": round(pooled_total_cost, 2),
            "pooled_false_negatives": int(p_fn),
            "pooled_false_positives": int(p_fp),
        },
        "pooled_arrays": {
            "y_true": pooled_y_true_arr,
            "y_prob": pooled_probs_arr,
            "y_pred": pooled_preds_arr,
        }
    }


def compute_nadeau_bengio_ttest(
    scores_a: List[float],
    scores_b: List[float],
    n_train: int,
    n_val: int,
) -> Tuple[float, float]:
    """
    Computes the Nadeau & Bengio (2003) corrected resampled t-test for comparing
    two algorithms evaluated across K cross-validation folds.

    Corrects for the variance underestimation caused by training set overlap.

    Returns:
        Tuple of (t_statistic, two_tailed_p_value).
    """
    diffs = np.array(scores_a) - np.array(scores_b)
    k = len(diffs)
    mean_diff = float(np.mean(diffs))
    var_diff = float(np.var(diffs, ddof=1)) if k > 1 else 0.0

    if var_diff == 0.0:
        return 0.0, 1.0

    correction = (1.0 / k) + (float(n_val) / float(n_train))
    denom = np.sqrt(correction * var_diff)

    t_stat = mean_diff / denom
    p_val = float(2.0 * stats.t.sf(np.abs(t_stat), df=k - 1))

    return round(float(t_stat), 4), round(p_val, 4)


def compute_exact_mcnemar_test(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
) -> Tuple[int, int, float]:
    """
    Performs the Exact Binomial McNemar Test on paired discrete classifications
    evaluated on the same test dataset.

    Returns:
        Tuple of (discordant_b, discordant_c, exact_two_sided_p_value).
    """
    y_true_arr = np.asarray(y_true)
    a_correct = (np.asarray(y_pred_a) == y_true_arr)
    b_correct = (np.asarray(y_pred_b) == y_true_arr)

    # b: A wrong, B right
    b = int(np.sum((~a_correct) & b_correct))
    # c: A right, B wrong
    c = int(np.sum(a_correct & (~b_correct)))

    total_discordant = b + c
    if total_discordant == 0:
        return 0, 0, 1.0

    k = min(b, c)
    # Exact two-sided binomial p-value under H0: p = 0.5
    p_value = 2.0 * float(stats.binom.cdf(k, total_discordant, 0.5))
    p_value = min(1.0, p_value)

    return b, c, round(p_value, 4)

