"""
Logistic Regression Baseline (B1) Evaluator Module for INDUSTRIA AI (Stage 3 Phase 2A)

Implements the 6-candidate hyperparameter grid search, inner 4-fold cross-validation,
tie-breaking, and Sub-Train refit adhering strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3)
- Root PRD.md v1.2 (§10.1.3, §10.1.4, §10.1.5)

Specifications:
1. Candidate Grid (6 candidates):
   C in {0.001, 0.01, 0.1, 1.0, 10.0, 100.0}
2. Fixed Hyperparameters:
   penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=1000, random_state=42
3. Preprocessing Isolation:
   StandardScaler on numeric columns (and OneHotEncoder if Configuration A)
   fitted strictly on inner-train folds during selection, and on Sub-Train during refit.
4. Selection Metric:
   Mean canonical PR-AUC across 4 inner folds using sklearn average_precision_score.
5. Deterministic Tie-Breaking:
   Stronger regularization (smaller C value).
"""

from typing import Dict, Any, List, Tuple, Optional, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import average_precision_score

from ml.src.preprocessing.pipeline import build_preprocessor


B1_C_CANDIDATES: List[float] = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]
B1_FIXED_PARAMS: Dict[str, Any] = {
    "penalty": "l2",
    "solver": "lbfgs",
    "class_weight": "balanced",
    "max_iter": 1000,
    "random_state": 42,
}


def build_b1_pipeline(
    c_val: float,
    configuration: str = "A",
) -> Pipeline:
    """
    Constructs an un-fitted scikit-learn Pipeline with preprocessor and LogisticRegression.

    Args:
        c_val: Inverse regularization strength C.
        configuration: 'A' (WITH_TYPE) or 'B' (NO_TYPE).

    Returns:
        Configured Pipeline.
    """
    preprocessor = build_preprocessor(configuration=configuration, scale_numeric=True)
    clf = LogisticRegression(
        C=float(c_val),
        penalty=B1_FIXED_PARAMS["penalty"],
        solver=B1_FIXED_PARAMS["solver"],
        class_weight=B1_FIXED_PARAMS["class_weight"],
        max_iter=B1_FIXED_PARAMS["max_iter"],
        random_state=B1_FIXED_PARAMS["random_state"],
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", clf),
    ])


class LogisticRegressionCandidateEvaluator:
    """
    Manages the 6-candidate grid evaluation across inner 4-fold CV splits on Sub-Train data,
    executes deterministic tie-breaking, and fits the final base estimator M_k.
    """

    def __init__(
        self,
        configuration: str = "A",
        candidates: Optional[List[float]] = None,
    ):
        self.configuration = configuration.upper().strip()
        self.candidates = candidates if candidates is not None else B1_C_CANDIDATES

        self.best_c_: Optional[float] = None
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
    ) -> float:
        """
        Evaluates all 6 candidates across the 4 inner folds using canonical PR-AUC.

        Args:
            X_sub_train: Features DataFrame for the Sub-Train partition (N = 4,480).
            y_sub_train: Binary labels for the Sub-Train partition (N = 4,480).
            inner_folds: List of inner fold split dictionaries from nested_cv_indices.json.
            sub_train_indices_map: Mapping from global dataset index to local Sub-Train index [0..4479].

        Returns:
            The selected best C value.
        """
        assert len(inner_folds) == 4, f"Expected 4 inner folds, got {len(inner_folds)}"

        y_arr = np.asarray(y_sub_train, dtype=int).ravel()
        candidate_results = []

        for c_val in self.candidates:
            fold_scores = []

            for inner_f in inner_folds:
                # Map global inner train / val indices to local Sub-Train positions
                in_train_local = [sub_train_indices_map[idx] for idx in inner_f["inner_train_indices"]]
                in_val_local = [sub_train_indices_map[idx] for idx in inner_f["inner_val_indices"]]

                X_tr = X_sub_train.iloc[in_train_local]
                y_tr = y_arr[in_train_local]
                X_va = X_sub_train.iloc[in_val_local]
                y_va = y_arr[in_val_local]

                pipe = build_b1_pipeline(c_val=c_val, configuration=self.configuration)
                pipe.fit(X_tr, y_tr)

                # Canonical candidate-ranking metric (§3.3): sklearn average_precision_score
                y_prob = pipe.predict_proba(X_va)[:, 1]
                ap = float(average_precision_score(y_va, y_prob))
                fold_scores.append(ap)

            mean_ap = float(np.mean(fold_scores))
            std_ap = float(np.std(fold_scores, ddof=1)) if len(fold_scores) > 1 else 0.0

            candidate_results.append({
                "C": float(c_val),
                "mean_ap": mean_ap,
                "std_ap": std_ap,
                "fold_ap_scores": fold_scores,
            })

        # Selection and Tie-Breaking Rule (§3.3):
        # 1. Maximize mean inner AP
        # 2. Tie-break: smaller C (stronger regularization)
        max_ap = max(res["mean_ap"] for res in candidate_results)
        top_candidates = [
            res for res in candidate_results
            if np.isclose(res["mean_ap"], max_ap, atol=1e-6)
        ]

        # Sort top candidates by C ascending (smaller C = stronger regularization wins tie)
        top_candidates.sort(key=lambda item: item["C"])
        winning_candidate = top_candidates[0]

        self.best_c_ = winning_candidate["C"]
        self.best_inner_ap_ = winning_candidate["mean_ap"]
        self.candidate_scores_ = candidate_results
        self.is_evaluated_ = True
        return self.best_c_

    def refit_on_sub_train(
        self,
        X_sub_train: pd.DataFrame,
        y_sub_train: Union[pd.Series, np.ndarray],
    ) -> Pipeline:
        """
        Refits the selected B1 pipeline on the entire Sub-Train partition (N = 4,480).

        Args:
            X_sub_train: Features DataFrame for the Sub-Train partition.
            y_sub_train: Binary labels for the Sub-Train partition.

        Returns:
            Fitted Pipeline (M_k).
        """
        if not self.is_evaluated_ or self.best_c_ is None:
            raise RuntimeError("Must evaluate inner candidates before refitting on Sub-Train.")

        y_arr = np.asarray(y_sub_train, dtype=int).ravel()
        final_pipe = build_b1_pipeline(c_val=self.best_c_, configuration=self.configuration)
        final_pipe.fit(X_sub_train, y_arr)
        self.fitted_pipeline_ = final_pipe
        return final_pipe
