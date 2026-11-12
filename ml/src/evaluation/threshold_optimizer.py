"""
Cost-Sensitive Decision Threshold Optimization Module (Stage 3 Phase 2A)

Implements out-of-sample decision threshold optimization and sensitivity sweeps
strictly adhering to STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§6.1–§6.4).

Specifications:
1. Candidate Threshold Grid (201 points):
   tau in {0.0} U {0.005, 0.010, ..., 0.995} U {1.0}
2. Theoretical Bayes Optimal Threshold:
   tau*_Bayes = C_FP / (C_FN + C_FP) = 200 / 10,200 approx 0.0196078
3. Deterministic Tie-Breaking Rule:
   tau* = argmin_{tau in T_min} |tau - tau*_Bayes|
   Ties in distance break toward the higher threshold (minimizing false alarm fatigue).
4. Threshold-Validation Sensitivity Analysis (Pre-Outer-Test):
   Evaluates delta in {-0.02, -0.01, 0.0, +0.01, +0.02} with boundary clipping to [0, 1]
   and deduplication on the Threshold-Validation partition.
5. Economic Cost Ratio Sweep:
   Evaluates 10:1, 20:1, 50:1, and 100:1 ratios on Threshold-Validation data.
6. Strict Freezing Invariant:
   Threshold tau* is frozen permanently before outer-test evaluation.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score


# Authoritative illustrative cost constants from PRD v1.2 Appendix E
PRD_COST_FN: float = 10000.0  # False negative penalty: undetected catastrophic breakdown
PRD_COST_FP: float = 200.0    # False positive penalty: unnecessary preventive inspection
PRD_COST_RATIO_DISCLAIMER: str = (
    "The 50:1 cost ratio ($10,000 / $200) is an illustrative PRD benchmark (Appendix E) "
    "and does not represent verified customer plant economics."
)

# Standard 201-point candidate grid
STANDARD_THRESHOLD_GRID = np.concatenate(
    ([0.0], np.arange(0.005, 1.0, 0.005), [1.0])
)


def compute_bayes_threshold(cost_fn: float = PRD_COST_FN, cost_fp: float = PRD_COST_FP) -> float:
    """Computes the theoretical Bayes optimal threshold: tau*_Bayes = C_FP / (C_FN + C_FP)."""
    return float(cost_fp / (cost_fn + cost_fp))


def evaluate_threshold_cost(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    cost_fn: float = PRD_COST_FN,
    cost_fp: float = PRD_COST_FP,
) -> Dict[str, Any]:
    """
    Evaluates confusion matrix, classification metrics, and operational cost at a specific threshold.
    """
    y_true_arr = np.asarray(y_true, dtype=int).ravel()
    y_prob_arr = np.asarray(y_prob, dtype=float).ravel()

    # For threshold = 0.0, all samples predict 1
    # For threshold = 1.0, all samples predict 0 unless prob == 1.0
    if threshold == 0.0:
        y_pred = np.ones_like(y_true_arr)
    elif threshold >= 1.0:
        y_pred = (y_prob_arr >= 1.0).astype(int)
    else:
        y_pred = (y_prob_arr >= threshold).astype(int)

    cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    cost = float((fn * cost_fn) + (fp * cost_fp))
    rec = float(recall_score(y_true_arr, y_pred, zero_division=0))
    prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))

    flags = []
    if int(tp + fp) == 0:
        flags.append("UNDEFINED_ZERO_PREDICTIONS")

    return {
        "threshold": round(float(threshold), 5),
        "cost": cost,
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
        "recall": round(rec, 4),
        "precision": round(prec, 4),
        "f1_score": round(f1, 4),
        "flags": flags,
    }


class ThresholdOptimizer:
    """
    Optimizes operational decision threshold on the Threshold-Validation partition
    with exact Bayes tie-breaking and sensitivity sweeps.
    """

    def __init__(
        self,
        cost_fn: float = PRD_COST_FN,
        cost_fp: float = PRD_COST_FP,
        threshold_grid: Optional[np.ndarray] = None,
    ):
        self.cost_fn = cost_fn
        self.cost_fp = cost_fp
        self.threshold_grid = (
            np.asarray(threshold_grid, dtype=float)
            if threshold_grid is not None
            else STANDARD_THRESHOLD_GRID
        )
        self.tau_bayes_ = compute_bayes_threshold(cost_fn, cost_fp)

        # Optimization results
        self.optimal_threshold_: Optional[float] = None
        self.min_cost_: Optional[float] = None
        self.validation_metrics_: Optional[Dict[str, Any]] = None
        self.sensitivity_results_: Optional[List[Dict[str, Any]]] = None
        self.cost_ratio_sweep_: Optional[List[Dict[str, Any]]] = None
        self.full_cost_curve_: Optional[List[Dict[str, Any]]] = None
        self.is_optimized_: bool = False

    def optimize(
        self,
        y_val: np.ndarray,
        y_prob_val: np.ndarray,
    ) -> "ThresholdOptimizer":
        """
        Executes threshold optimization on the Threshold-Validation partition (N = 960).

        Args:
            y_val: Ground truth binary labels for threshold-validation partition.
            y_prob_val: Calibrated probabilities for threshold-validation partition.

        Returns:
            Fitted ThresholdOptimizer instance.
        """
        y_val_arr = np.asarray(y_val, dtype=int).ravel()
        y_prob_arr = np.asarray(y_prob_val, dtype=float).ravel()

        curve = []
        min_cost = float("inf")
        candidate_records = []

        for tau in self.threshold_grid:
            rec = evaluate_threshold_cost(
                y_true=y_val_arr,
                y_prob=y_prob_arr,
                threshold=tau,
                cost_fn=self.cost_fn,
                cost_fp=self.cost_fp,
            )
            curve.append(rec)
            candidate_records.append((tau, rec["cost"], rec))
            if rec["cost"] < min_cost:
                min_cost = rec["cost"]

        self.min_cost_ = min_cost
        self.full_cost_curve_ = curve

        # Collect candidate set achieving exact minimum cost
        min_candidates = [
            (tau, rec) for (tau, c, rec) in candidate_records if np.isclose(c, min_cost, atol=1e-5)
        ]

        if len(min_candidates) == 1:
            best_tau, best_rec = min_candidates[0]
        else:
            # Deterministic Tie-Breaking Rule (§6.2):
            # argmin_{tau in T_min} |tau - tau*_Bayes|, with tie breaking toward higher threshold
            distances = [abs(tau - self.tau_bayes_) for (tau, _) in min_candidates]
            min_dist = min(distances)
            closest_candidates = [
                (tau, rec)
                for (tau, rec), dist in zip(min_candidates, distances)
                if np.isclose(dist, min_dist, atol=1e-8)
            ]
            # Break distance ties toward higher threshold
            closest_candidates.sort(key=lambda item: item[0], reverse=True)
            best_tau, best_rec = closest_candidates[0]

        self.optimal_threshold_ = float(best_tau)
        self.validation_metrics_ = best_rec

        # Execute Neighborhood Sensitivity Sweep (§6.3)
        self.sensitivity_results_ = self._run_neighborhood_sensitivity(
            y_val_arr, y_prob_arr, self.optimal_threshold_
        )

        # Execute Cost Ratio Sweep (§6.4)
        self.cost_ratio_sweep_ = self._run_cost_ratio_sweep(
            y_val_arr, y_prob_arr
        )

        self.is_optimized_ = True
        return self

    def _run_neighborhood_sensitivity(
        self,
        y_val: np.ndarray,
        y_prob: np.ndarray,
        optimal_tau: float,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates local neighborhood around optimal threshold with boundary clipping to [0, 1]
        and deduplication (§6.3).
        """
        offsets = [-0.02, -0.01, 0.0, 0.01, 0.02]
        # Boundary clipping and deduplication
        unique_cands = sorted(list(set(
            round(float(np.clip(optimal_tau + delta, 0.0, 1.0)), 5)
            for delta in offsets
        )))

        base_rec = self.validation_metrics_
        base_fn = base_rec["false_negatives"]
        base_fp = base_rec["false_positives"]
        base_cost = base_rec["cost"]

        results = []
        for tau in unique_cands:
            rec = evaluate_threshold_cost(
                y_val, y_prob, threshold=tau, cost_fn=self.cost_fn, cost_fp=self.cost_fp
            )
            rec["delta_fn"] = int(rec["false_negatives"] - base_fn)
            rec["delta_fp"] = int(rec["false_positives"] - base_fp)
            rec["delta_cost"] = float(rec["cost"] - base_cost)
            rec["is_optimal"] = bool(np.isclose(tau, optimal_tau, atol=1e-5))
            results.append(rec)

        return results

    def _run_cost_ratio_sweep(
        self,
        y_val: np.ndarray,
        y_prob: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates pre-declared economic cost ratio sweeps on Threshold-Validation data (§6.4).
        """
        ratios = [
            {"ratio_name": "10:1", "cost_fn": 2000.0, "cost_fp": 200.0},
            {"ratio_name": "20:1", "cost_fn": 4000.0, "cost_fp": 200.0},
            {"ratio_name": "50:1 (PRD Baseline)", "cost_fn": 10000.0, "cost_fp": 200.0},
            {"ratio_name": "100:1", "cost_fn": 20000.0, "cost_fp": 200.0},
        ]

        sweep_results = []
        for r in ratios:
            c_fn = r["cost_fn"]
            c_fp = r["cost_fp"]
            t_bayes = compute_bayes_threshold(c_fn, c_fp)

            sub_opt = ThresholdOptimizer(
                cost_fn=c_fn,
                cost_fp=c_fp,
                threshold_grid=self.threshold_grid,
            )
            # Evaluate across grid for this cost ratio
            min_c = float("inf")
            cands = []
            for tau in self.threshold_grid:
                rec = evaluate_threshold_cost(y_val, y_prob, tau, cost_fn=c_fn, cost_fp=c_fp)
                if rec["cost"] < min_c:
                    min_c = rec["cost"]
                cands.append((tau, rec["cost"]))

            tied = [tau for (tau, c) in cands if np.isclose(c, min_c, atol=1e-5)]
            if len(tied) == 1:
                opt_t = tied[0]
            else:
                dists = [abs(tau - t_bayes) for tau in tied]
                min_d = min(dists)
                closest = [tau for tau, d in zip(tied, dists) if np.isclose(d, min_d, atol=1e-8)]
                opt_t = max(closest)

            rec_opt = evaluate_threshold_cost(y_val, y_prob, opt_t, cost_fn=c_fn, cost_fp=c_fp)
            sweep_results.append({
                "cost_ratio": r["ratio_name"],
                "cost_fn": c_fn,
                "cost_fp": c_fp,
                "tau_bayes": round(float(t_bayes), 5),
                "optimal_validation_threshold": round(float(opt_t), 5),
                "validation_cost": rec_opt["cost"],
                "validation_recall": rec_opt["recall"],
                "validation_precision": rec_opt["precision"],
            })

        return sweep_results

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured dictionary summarizing threshold optimization results."""
        if not self.is_optimized_:
            raise RuntimeError("ThresholdOptimizer has not been optimized yet.")

        return {
            "optimal_threshold": self.optimal_threshold_,
            "theoretical_bayes_threshold": round(self.tau_bayes_, 5),
            "distance_to_bayes": round(abs(self.optimal_threshold_ - self.tau_bayes_), 5),
            "validation_min_cost": self.min_cost_,
            "cost_constants": {
                "cost_fn": self.cost_fn,
                "cost_fp": self.cost_fp,
                "cost_ratio": f"{int(self.cost_fn / self.cost_fp)}:1",
                "disclaimer": PRD_COST_RATIO_DISCLAIMER,
            },
            "validation_metrics": self.validation_metrics_,
            "neighborhood_sensitivity": self.sensitivity_results_,
            "cost_ratio_sweep": self.cost_ratio_sweep_,
        }

