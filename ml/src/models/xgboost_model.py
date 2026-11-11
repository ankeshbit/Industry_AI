"""
XGBoost Candidate Evaluator Module (M2) for INDUSTRIA AI (Stage 3 Phase 2C)

Implements the 20-candidate bounded random search, inner 4-fold cross-validation with native aucpr early stopping,
canonical average_precision_score candidate ranking, deterministic median ceiling round selection,
and full Sub-Train refit adhering strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3, §3.3.1, §5.1, §5.2)
- Root PRD.md v1.2 (§10.1.3, §10.1.4, §10.1.5)

Specifications:
1. Candidate Search Space (20 bounded random candidates from discrete grid):
   - n_estimators = 300 (maximum upper bound)
   - max_depth in {3, 4, 5, 6}
   - learning_rate in {0.01, 0.03, 0.05, 0.1}
   - subsample in {0.7, 0.8, 1.0}
   - colsample_bytree in {0.7, 0.8, 1.0}
   - min_child_weight in {1, 3, 5}
   - scale_pos_weight: N_neg / N_pos computed on inner train fold
   - random_state = 42
   - n_jobs = -1
2. Inner CV Early Stopping and Metric Distinction (§3.3.1):
   - Early stopping counter: early_stopping_rounds = 20 monitored by native eval_metric="aucpr".
   - Candidate ranking: canonical scikit-learn average_precision_score on inner validation predictions.
   - Fold boosting rounds: T_j* = best_iteration + 1 (1 <= T_j* <= 300).
3. Deterministic Median Ceiling Integer Rounding Rule (§3.3.1 item 4):
   - T* = ceil((T_(2)* + T_(3)*) / 2) = floor((T_(2)* + T_(3)* + 1) / 2)
   - Clamped to 1 <= T* <= 300.
4. Deterministic Tie-Breaking:
   - Lower learning_rate, then lower max_depth, then lower min_child_weight.
5. Final Sub-Train Refit (§3.3.1 item 5):
   - Train on entire Sub-Train partition (N = 4,480) with winning params and exactly T* trees with NO early stopping.
"""

import itertools
from typing import Dict, Any, List, Tuple, Optional, Union
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import average_precision_score

from ml.src.preprocessing.pipeline import build_preprocessor


def generate_m2_candidates(seed: int = 42, n_candidates: int = 20) -> List[Dict[str, Any]]:
    """
    Generates exactly 20 bounded random-search candidate configurations deterministically
    sampled from the pre-declared discrete grid (§3.3).
    """
    grid = list(itertools.product(
        [3, 4, 5, 6],                     # max_depth
        [0.01, 0.03, 0.05, 0.1],          # learning_rate
        [0.7, 0.8, 1.0],                  # subsample
        [0.7, 0.8, 1.0],                  # colsample_bytree
        [1, 3, 5],                        # min_child_weight
    ))
    assert len(grid) == 432, f"Expected 432 grid points, got {len(grid)}"

    rng = np.random.RandomState(seed)
    sampled_indices = sorted(rng.choice(len(grid), size=n_candidates, replace=False))

    candidates = []
    for idx in sampled_indices:
        md, lr, ss, cs, mcw = grid[idx]
        candidates.append({
            "max_depth": md,
            "learning_rate": lr,
            "subsample": ss,
            "colsample_bytree": cs,
            "min_child_weight": mcw,
            "n_estimators": 300,
            "random_state": 42,
            "n_jobs": -1,
            "tree_method": "hist",
        })
    assert len(candidates) == n_candidates, f"Expected exactly {n_candidates} candidates, got {len(candidates)}"
    return candidates


M2_CANDIDATES: List[Dict[str, Any]] = generate_m2_candidates(seed=42, n_candidates=20)


def m2_tie_breaker_key(cand_params: Dict[str, Any]) -> Tuple[float, int, int]:
    """
    Computes sort key for deterministic simpler-model tie-breaking (§3.3):
    1. Lower learning_rate
    2. Lower max_depth
    3. Lower min_child_weight
    """
    return (
        float(cand_params["learning_rate"]),
        int(cand_params["max_depth"]),
        int(cand_params["min_child_weight"]),
    )


def compute_median_ceiling_rounds(fold_rounds: List[int]) -> int:
    """
    Computes the deterministic ceiling median integer rounding rule across 4 inner folds (§3.3.1 item 4):
    T* = ceil((T_(2)* + T_(3)*) / 2) = floor((T_(2)* + T_(3)* + 1) / 2)
    Subject to: 1 <= T* <= 300.
    """
    assert len(fold_rounds) == 4, f"Expected 4 inner fold round counts, got {len(fold_rounds)}"
    sorted_rounds = sorted(fold_rounds)
    t2 = sorted_rounds[1]
    t3 = sorted_rounds[2]
    # Integer arithmetic for ceiling of midpoint: (t2 + t3 + 1) // 2
    t_star = (t2 + t3 + 1) // 2
    return int(np.clip(t_star, 1, 300))


def build_m2_pipeline(
    params: Dict[str, Any],
    scale_pos_weight: float,
    n_estimators: int,
    configuration: str = "A",
) -> Pipeline:
    """
    Constructs an un-fitted scikit-learn Pipeline with preprocessor and XGBClassifier for refit.

    Args:
        params: Winning hyperparameter dictionary.
        scale_pos_weight: Class weight ratio N_neg / N_pos for Sub-Train.
        n_estimators: Exactly T* boosting rounds.
        configuration: 'A' (WITH_TYPE) or 'B' (NO_TYPE).

    Returns:
        Configured Pipeline.
    """
    preprocessor = build_preprocessor(configuration=configuration, scale_numeric=True)
    clf_params = {k: v for k, v in params.items() if k not in ("n_estimators", "early_stopping_rounds", "eval_metric")}
    clf = XGBClassifier(
        **clf_params,
        n_estimators=n_estimators,
        scale_pos_weight=scale_pos_weight,
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", clf),
    ])


class XGBoostCandidateEvaluator:
    """
    Manages the 20-candidate grid evaluation across inner 4-fold CV splits on Sub-Train data
    with native aucpr early stopping, canonical average_precision_score candidate ranking,
    deterministic ceiling median round selection, and fits the final base estimator M_k.
    """

    def __init__(
        self,
        configuration: str = "A",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ):
        self.configuration = configuration.upper().strip()
        self.candidates = candidates if candidates is not None else M2_CANDIDATES

        self.best_params_: Optional[Dict[str, Any]] = None
        self.best_rounds_: Optional[int] = None
        self.best_inner_ap_: Optional[float] = None
        self.candidate_scores_: Optional[List[Dict[str, Any]]] = None
        self.fitted_pipeline_: Optional[Pipeline] = None
        self.is_evaluated_: bool = False

    def evaluate_inner_candidates(
        self,
        X_sub_train: pd.DataFrame,
        y_sub_train: Union[pd.Series, np.ndarray],
        inner_folds: List[Dict[str, Any]],
        sub_train_indices_map: Dict[int, int],
    ) -> Tuple[Dict[str, Any], int]:
        """
        Evaluates all 20 candidates across 4 inner folds using native aucpr early stopping
        and canonical Average Precision ranking.

        Args:
            X_sub_train: Features DataFrame for the Sub-Train partition (N = 4,480).
            y_sub_train: Binary labels for the Sub-Train partition (N = 4,480).
            inner_folds: List of inner fold split dictionaries from nested_cv_indices.json.
            sub_train_indices_map: Mapping from global dataset index to local Sub-Train index [0..4479].

        Returns:
            Tuple of (winning_hyperparameters_dict, T_star_rounds).
        """
        assert len(inner_folds) == 4, f"Expected 4 inner folds, got {len(inner_folds)}"

        y_arr = np.asarray(y_sub_train, dtype=int).ravel()
        n_candidates = len(self.candidates)
        candidate_fold_scores: List[List[float]] = [[] for _ in range(n_candidates)]
        candidate_fold_rounds: List[List[int]] = [[] for _ in range(n_candidates)]

        for inner_f in inner_folds:
            in_train_local = [sub_train_indices_map[idx] for idx in inner_f["inner_train_indices"]]
            in_val_local = [sub_train_indices_map[idx] for idx in inner_f["inner_val_indices"]]

            X_tr = X_sub_train.iloc[in_train_local]
            y_tr = y_arr[in_train_local]
            X_va = X_sub_train.iloc[in_val_local]
            y_va = y_arr[in_val_local]

            # Compute inner train scale_pos_weight
            n_pos = int(np.sum(y_tr == 1))
            n_neg = int(np.sum(y_tr == 0))
            spw = float(n_neg / max(1, n_pos))

            # Fit preprocessor strictly on inner-train fold once
            preprocessor = build_preprocessor(configuration=self.configuration, scale_numeric=True)
            X_tr_trans = preprocessor.fit_transform(X_tr)
            X_va_trans = preprocessor.transform(X_va)

            for cand_idx, cand_params in enumerate(self.candidates):
                clf = XGBClassifier(
                    **cand_params,
                    scale_pos_weight=spw,
                    early_stopping_rounds=20,
                    eval_metric="aucpr",
                )
                clf.fit(
                    X_tr_trans, y_tr,
                    eval_set=[(X_va_trans, y_va)],
                    verbose=False,
                )

                # Best iteration (0-based index) -> boosting rounds (1-based count)
                best_iter = clf.best_iteration
                t_j = best_iter + 1
                assert 1 <= t_j <= 300, f"Boosting rounds out of bounds: {t_j}"
                candidate_fold_rounds[cand_idx].append(t_j)

                # Canonical candidate-ranking metric (§3.3.1): sklearn average_precision_score
                y_prob = clf.predict_proba(X_va_trans)[:, 1]
                ap = float(average_precision_score(y_va, y_prob))
                candidate_fold_scores[cand_idx].append(ap)

        candidate_results = []
        for cand_idx, cand_params in enumerate(self.candidates):
            scores = candidate_fold_scores[cand_idx]
            rounds = candidate_fold_rounds[cand_idx]
            mean_ap = float(np.mean(scores))
            std_ap = float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0
            candidate_results.append({
                "params": cand_params,
                "mean_ap": mean_ap,
                "std_ap": std_ap,
                "fold_ap_scores": scores,
                "fold_rounds": rounds,
                "median_ceiling_rounds": compute_median_ceiling_rounds(rounds),
            })

        # Selection and Simpler-Model Tie-Breaking Rule (§3.3):
        # 1. Maximize mean inner AP
        # 2. Tie-break: simpler model via m2_tie_breaker_key
        max_ap = max(res["mean_ap"] for res in candidate_results)
        top_candidates = [
            res for res in candidate_results
            if np.isclose(res["mean_ap"], max_ap, atol=1e-6)
        ]

        top_candidates.sort(key=lambda item: m2_tie_breaker_key(item["params"]))
        winning_candidate = top_candidates[0]

        self.best_params_ = winning_candidate["params"]
        self.best_rounds_ = winning_candidate["median_ceiling_rounds"]
        self.best_inner_ap_ = winning_candidate["mean_ap"]
        self.candidate_scores_ = candidate_results
        self.is_evaluated_ = True
        return self.best_params_, self.best_rounds_

    def refit_on_sub_train(
        self,
        X_sub_train: pd.DataFrame,
        y_sub_train: Union[pd.Series, np.ndarray],
    ) -> Pipeline:
        """
        Refits the selected M2 pipeline on the entire Sub-Train partition (N = 4,480)
        using winning configuration theta* for exactly T* rounds with NO early stopping (§3.3.1 item 5).

        Args:
            X_sub_train: Features DataFrame for the Sub-Train partition.
            y_sub_train: Binary labels for the Sub-Train partition.

        Returns:
            Fitted Pipeline (M_k).
        """
        if not self.is_evaluated_ or self.best_params_ is None or self.best_rounds_ is None:
            raise RuntimeError("Must evaluate inner candidates before refitting on Sub-Train.")

        y_arr = np.asarray(y_sub_train, dtype=int).ravel()
        n_pos = int(np.sum(y_arr == 1))
        n_neg = int(np.sum(y_arr == 0))
        spw = float(n_neg / max(1, n_pos))

        final_pipe = build_m2_pipeline(
            params=self.best_params_,
            scale_pos_weight=spw,
            n_estimators=self.best_rounds_,
            configuration=self.configuration,
        )
        final_pipe.fit(X_sub_train, y_arr)
        self.fitted_pipeline_ = final_pipe
        return final_pipe

