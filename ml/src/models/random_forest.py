"""
Random Forest Candidate Evaluator Module (M1) for INDUSTRIA AI (Stage 3 Phase 2B.1)

Implements the 24-candidate hyperparameter grid search, inner 4-fold cross-validation,
deterministic simpler-model tie-breaking, and Sub-Train refit adhering strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3)
- Root PRD.md v1.2 (§10.1.3, §10.1.4, §10.1.5)

Specifications:
1. Candidate Grid (24 candidates):
   - n_estimators = 100
   - max_depth in {5, 8, 12, None}
   - min_samples_split in {2, 5, 10}
   - max_features in {"sqrt", "log2"}
   - class_weight = "balanced"
   - random_state = 42
2. Preprocessing Isolation:
   StandardScaler on numeric columns (and OneHotEncoder if Configuration A)
   fitted strictly on inner-train folds during selection, and on Sub-Train during refit.
3. Selection Metric:
   Mean canonical PR-AUC across 4 inner folds using sklearn average_precision_score.
4. Deterministic Simpler-Model Tie-Breaking:
   1. Lower max_depth (with None treated as infinite depth: 5 < 8 < 12 < None).
   2. Higher min_samples_split (more regularized: 10 > 5 > 2).
   3. Lower max_features ("log2" before "sqrt").
"""

from typing import Dict, Any, List, Tuple, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import average_precision_score

from ml.src.preprocessing.pipeline import build_preprocessor


def generate_m1_candidates() -> List[Dict[str, Any]]:
    """Generates the 24 pre-declared Random Forest candidate configurations in fixed deterministic order."""
    candidates = []
    for max_depth in [5, 8, 12, None]:
        for min_samples_split in [2, 5, 10]:
            for max_features in ["sqrt", "log2"]:
                candidates.append({
                    "n_estimators": 100,
                    "max_depth": max_depth,
                    "min_samples_split": min_samples_split,
                    "max_features": max_features,
                    "class_weight": "balanced",
                    "random_state": 42,
                    "n_jobs": -1,
                })
    assert len(candidates) == 24, f"Expected exactly 24 candidates, got {len(candidates)}"
    return candidates


M1_CANDIDATES: List[Dict[str, Any]] = generate_m1_candidates()


def m1_tie_breaker_key(cand_params: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    Computes sort key for deterministic simpler-model tie-breaking (§3.3):
    1. Lower max_depth (None treated as highest depth)
    2. Higher min_samples_split (higher split is more regularized)
    3. Lower max_features ("log2" before "sqrt")
    """
    d = cand_params["max_depth"] if cand_params["max_depth"] is not None else 999999
    s = -cand_params["min_samples_split"]
    f = 0 if cand_params["max_features"] == "log2" else 1
    return (d, s, f)


def build_m1_pipeline(
    params: Dict[str, Any],
    configuration: str = "A",
) -> Pipeline:
    """
    Constructs an un-fitted scikit-learn Pipeline with preprocessor and RandomForestClassifier.

    Args:
        params: Hyperparameter dictionary for RandomForestClassifier.
        configuration: 'A' (WITH_TYPE) or 'B' (NO_TYPE).

    Returns:
        Configured Pipeline.
    """
    preprocessor = build_preprocessor(configuration=configuration, scale_numeric=True)
    clf = RandomForestClassifier(**params)
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", clf),
    ])


class RandomForestCandidateEvaluator:
    """
    Manages the 24-candidate grid evaluation across inner 4-fold CV splits on Sub-Train data,
    executes deterministic simpler-model tie-breaking, and fits the final base estimator M_k.
    """

    def __init__(
        self,
        configuration: str = "A",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ):
        self.configuration = configuration.upper().strip()
        self.candidates = candidates if candidates is not None else M1_CANDIDATES

        self.best_params_: Optional[Dict[str, Any]] = None
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
    ) -> Dict[str, Any]:
        """
        Evaluates all 24 candidates across the 4 inner folds using canonical PR-AUC.

        Args:
            X_sub_train: Features DataFrame for the Sub-Train partition (N = 4,480).
            y_sub_train: Binary labels for the Sub-Train partition (N = 4,480).
            inner_folds: List of inner fold split dictionaries from nested_cv_indices.json.
            sub_train_indices_map: Mapping from global dataset index to local Sub-Train index [0..4479].

        Returns:
            The selected winning hyperparameter dictionary.
        """
        assert len(inner_folds) == 4, f"Expected 4 inner folds, got {len(inner_folds)}"

        y_arr = np.asarray(y_sub_train, dtype=int).ravel()
        candidate_results = []

        for cand_params in self.candidates:
            fold_scores = []

            for inner_f in inner_folds:
                in_train_local = [sub_train_indices_map[idx] for idx in inner_f["inner_train_indices"]]
                in_val_local = [sub_train_indices_map[idx] for idx in inner_f["inner_val_indices"]]

                X_tr = X_sub_train.iloc[in_train_local]
                y_tr = y_arr[in_train_local]
                X_va = X_sub_train.iloc[in_val_local]
                y_va = y_arr[in_val_local]

                pipe = build_m1_pipeline(params=cand_params, configuration=self.configuration)
                pipe.fit(X_tr, y_tr)

                # Canonical candidate-ranking metric (§3.3): sklearn average_precision_score
                y_prob = pipe.predict_proba(X_va)[:, 1]
                ap = float(average_precision_score(y_va, y_prob))
                fold_scores.append(ap)

            mean_ap = float(np.mean(fold_scores))
            std_ap = float(np.std(fold_scores, ddof=1)) if len(fold_scores) > 1 else 0.0

            candidate_results.append({
                "params": cand_params,
                "mean_ap": mean_ap,
                "std_ap": std_ap,
                "fold_ap_scores": fold_scores,
            })

        # Selection and Simpler-Model Tie-Breaking Rule (§3.3):
        # 1. Maximize mean inner AP
        # 2. Tie-break: simpler model via m1_tie_breaker_key
        max_ap = max(res["mean_ap"] for res in candidate_results)
        top_candidates = [
            res for res in candidate_results
            if np.isclose(res["mean_ap"], max_ap, atol=1e-6)
        ]

        # Sort top candidates by simpler-model key ascending
        top_candidates.sort(key=lambda item: m1_tie_breaker_key(item["params"]))
        winning_candidate = top_candidates[0]

        self.best_params_ = winning_candidate["params"]
        self.best_inner_ap_ = winning_candidate["mean_ap"]
        self.candidate_scores_ = candidate_results
        self.is_evaluated_ = True
        return self.best_params_

    def refit_on_sub_train(
        self,
        X_sub_train: pd.DataFrame,
        y_sub_train: Union[pd.Series, np.ndarray],
    ) -> Pipeline:
        """
        Refits the selected M1 pipeline on the entire Sub-Train partition (N = 4,480).

        Args:
            X_sub_train: Features DataFrame for the Sub-Train partition.
            y_sub_train: Binary labels for the Sub-Train partition.

        Returns:
            Fitted Pipeline (M_k).
        """
        if not self.is_evaluated_ or self.best_params_ is None:
            raise RuntimeError("Must evaluate inner candidates before refitting on Sub-Train.")

        y_arr = np.asarray(y_sub_train, dtype=int).ravel()
        final_pipe = build_m1_pipeline(params=self.best_params_, configuration=self.configuration)
        final_pipe.fit(X_sub_train, y_arr)
        self.fitted_pipeline_ = final_pipe
        return final_pipe
