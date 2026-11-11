"""
Stage 3 Reusable Evaluation Engine Module for INDUSTRIA AI (Phase 2A)

Implements the repeated nested cross-validation orchestration engine adhering strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§2.2, §3.2, §4.1–§4.3, §5.1–§5.2, §6.1–§6.4, §7.1–§7.2)
- Root PRD.md v1.2 (§10.1.3–§10.1.5, §11.1, §13.5, §18.3)

Architectural Invariants Enforced:
1. Complete Partition Isolation:
   - Sub-Train (N = 4,480): Base estimator inner-CV search and refit.
   - Calibration (N = 960): Post-hoc Platt calibrator fitting (N_cal,pos >= 25 gate).
   - Threshold-Validation (N = 960): Cost-sensitive threshold search and sensitivity sweeps.
   - Outer-Test (N = 1,600): Single frozen evaluation out-of-sample.
   - Zero locked test rows (N = 2,000) ever enter Stage 3.
2. Configuration Parity:
   - Identical partition indices apply equally to Configuration A (WITH_TYPE) and B (NO_TYPE).
3. Forward Causal Pipeline:
   - Unidirectional 8-step execution (§4.3) with zero backward leakage.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from ml.src.data.loader import load_ai4i_dataset
from ml.src.features.schemas import (
    AI4I_SHA256_CHECKSUM,
    PRIMARY_TARGET,
    prepare_features_and_target,
)
from ml.src.data.nested_splitting import (
    load_nested_cv_splits,
    compute_indices_hash,
    HISTORICAL_TRAIN_INDEX_HASH,
    HISTORICAL_LOCKED_TEST_HASH,
    DEFAULT_NESTED_CV_ARTIFACT_PATH,
)
from ml.src.models.prevalence import PrevalenceBaseline
from ml.src.models.logistic_regression import LogisticRegressionCandidateEvaluator
from ml.src.models.random_forest import RandomForestCandidateEvaluator
from ml.src.models.xgboost_model import XGBoostCandidateEvaluator
from ml.src.models.calibration import ModelAgnosticCalibrator, InsufficientCalibrationEventsError
from ml.src.evaluation.threshold_optimizer import ThresholdOptimizer, PRD_COST_FN, PRD_COST_FP
from ml.src.evaluation.metrics import compute_stage3_metrics


class Stage3EvaluationEngine:
    """
    Reusable evaluation engine orchestrating repeated nested cross-validation
    for Stage 3 baseline and candidate model families.
    """

    def __init__(
        self,
        dataset_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
        cost_fn: float = PRD_COST_FN,
        cost_fp: float = PRD_COST_FP,
    ):
        self.dataset_path = dataset_path
        self.manifest_path = manifest_path or DEFAULT_NESTED_CV_ARTIFACT_PATH
        self.cost_fn = cost_fn
        self.cost_fp = cost_fp

        # Runtime verified assets
        self.df_raw: Optional[pd.DataFrame] = None
        self.manifest: Optional[Dict[str, Any]] = None
        self._initialize_and_verify_data()

    def _initialize_and_verify_data(self) -> None:
        """Loads and performs defensive runtime verification on data and split manifest."""
        df = load_ai4i_dataset(filepath=self.dataset_path, verify_checksum=True)
        if len(df) != 10000:
            raise ValueError(f"Corrupt dataset: expected 10,000 rows, got {len(df)}")
        self.df_raw = df

        # Load manifest with strict integrity verification
        manifest = load_nested_cv_splits(artifact_path=self.manifest_path, verify_integrity=True)
        meta = manifest["metadata"]

        # Assert index hash continuity with historical Stage 2B
        if meta["dataset_checksum"] != AI4I_SHA256_CHECKSUM:
            raise ValueError("Manifest dataset checksum mismatch!")
        if meta["development_index_hash"] != HISTORICAL_TRAIN_INDEX_HASH:
            raise ValueError("Manifest development index hash mismatch!")
        if meta["locked_test_index_hash"] != HISTORICAL_LOCKED_TEST_HASH:
            raise ValueError("Manifest locked test index hash mismatch!")

        self.manifest = manifest

    def _verify_fold_partitions_runtime(
        self,
        fold_record: Dict[str, Any],
        y_all: np.ndarray,
    ) -> None:
        """
        Defensive runtime assertion verifying fold index bounds, disjointness, completeness,
        and calibration positive gate before executing model training.
        """
        sub_train = fold_record["sub_train_indices"]
        cal = fold_record["calibration_indices"]
        thresh = fold_record["threshold_indices"]
        outer_test = fold_record["outer_test_indices"]
        outer_train = fold_record["outer_train_indices"]

        # 1. Bounds assertions [0, 9999]
        for name, idxs in [
            ("sub_train", sub_train),
            ("calibration", cal),
            ("threshold", thresh),
            ("outer_test", outer_test),
        ]:
            if not all(isinstance(i, int) and 0 <= i < 10000 for i in idxs):
                raise ValueError(f"Out of bounds index detected in {name} partition!")

        # 2. Partition sizes
        if len(sub_train) != 4480:
            raise ValueError(f"Invalid sub_train size: {len(sub_train)}")
        if len(cal) != 960:
            raise ValueError(f"Invalid calibration size: {len(cal)}")
        if len(thresh) != 960:
            raise ValueError(f"Invalid threshold-validation size: {len(thresh)}")
        if len(outer_test) != 1600:
            raise ValueError(f"Invalid outer_test size: {len(outer_test)}")

        # 3. Disjointness
        s_sub = set(sub_train)
        s_cal = set(cal)
        s_th = set(thresh)
        s_ot = set(outer_train)
        s_te = set(outer_test)

        if not s_sub.isdisjoint(s_cal) or not s_sub.isdisjoint(s_th) or not s_cal.isdisjoint(s_th):
            raise ValueError("Sub-Train, Calibration, and Threshold-Validation are not pairwise disjoint!")
        if (s_sub | s_cal | s_th) != s_ot:
            raise ValueError("Sub-Train U Calibration U Threshold does not equal Outer-Train!")
        if not s_ot.isdisjoint(s_te):
            raise ValueError("Outer-Train and Outer-Test partitions overlap!")

        # 4. Calibration positive gate (N_cal,pos >= 25)
        cal_positives = int(np.sum(y_all[cal] == 1))
        if cal_positives < 25:
            raise InsufficientCalibrationEventsError(
                f"Runtime check failed: calibration positive count {cal_positives} < 25."
            )

    def evaluate_model_family(
        self,
        model_family: str = "B1",
        configuration: str = "A",
        repetition_indices: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Executes repeated nested cross-validation for the designated model family and configuration.

        Args:
            model_family: 'B0' (Prevalence Baseline) or 'B1' (Logistic Regression).
            configuration: 'A' (WITH_TYPE) or 'B' (NO_TYPE).
            repetition_indices: Optional subset of repetitions [0..4] (default: all 5).

        Returns:
            Structured dictionary of complete evaluation results.
        """
        family_upper = model_family.upper().strip()
        config_upper = configuration.upper().strip()

        if family_upper not in ("B0", "B1", "M1", "M2"):
            raise ValueError(f"Model family '{model_family}' not supported. Only B0, B1, M1, and M2 permitted.")
        if config_upper not in ("A", "B", "WITH_TYPE", "WITHOUT_TYPE", "NO_TYPE"):
            raise ValueError(f"Unknown configuration '{configuration}'. Must be A or B.")

        # Standardize configuration label
        norm_config = "A" if config_upper in ("A", "WITH_TYPE") else "B"

        # Prepare features and target on the verified raw dataset
        X, y = prepare_features_and_target(self.df_raw, configuration=norm_config)
        y_all = np.asarray(y, dtype=int).ravel()

        repetitions = self.manifest["repetitions"]
        if repetition_indices is not None:
            active_repetitions = [r for r in repetitions if r["repetition_index"] in repetition_indices]
        else:
            active_repetitions = repetitions

        fold_evaluations: List[Dict[str, Any]] = []

        for rep in active_repetitions:
            r_idx = rep["repetition_index"]
            outer_seed = rep["outer_seed"]

            for fold in rep["outer_folds"]:
                k_idx = fold["outer_fold_index"]
                print(f"  [Rep {r_idx}/4 Fold {k_idx}/4] Evaluating {family_upper} Config {norm_config}...", flush=True)

                # 1. Defensive runtime partition assertions
                self._verify_fold_partitions_runtime(fold, y_all)

                sub_train_idx = fold["sub_train_indices"]
                cal_idx = fold["calibration_indices"]
                thresh_idx = fold["threshold_indices"]
                outer_test_idx = fold["outer_test_indices"]

                # Mapping global Sub-Train indices to local 0..4479 array offsets
                sub_train_map = {global_idx: local_idx for local_idx, global_idx in enumerate(sub_train_idx)}

                X_sub = X.iloc[sub_train_idx]
                y_sub = y_all[sub_train_idx]
                X_cal = X.iloc[cal_idx]
                y_cal = y_all[cal_idx]
                X_th = X.iloc[thresh_idx]
                y_th = y_all[thresh_idx]
                X_test = X.iloc[outer_test_idx]
                y_test = y_all[outer_test_idx]

                # Reference prevalence strictly from Sub-Train (§7.1)
                p_reference = float(np.mean(y_sub))

                # 2. Model Selection and Refitting
                if family_upper == "B0":
                    winning_params = {}
                    candidate_scores = []
                    base_estimator = PrevalenceBaseline()
                    base_estimator.fit(X_sub, y_sub)

                elif family_upper == "B1":
                    evaluator = LogisticRegressionCandidateEvaluator(configuration=norm_config)
                    best_c = evaluator.evaluate_inner_candidates(
                        X_sub_train=X_sub,
                        y_sub_train=y_sub,
                        inner_folds=fold["inner_folds"],
                        sub_train_indices_map=sub_train_map,
                    )
                    base_estimator = evaluator.refit_on_sub_train(X_sub, y_sub)
                    winning_params = {"C": best_c}
                    candidate_scores = evaluator.candidate_scores_

                elif family_upper == "M1":
                    evaluator = RandomForestCandidateEvaluator(configuration=norm_config)
                    best_params = evaluator.evaluate_inner_candidates(
                        X_sub_train=X_sub,
                        y_sub_train=y_sub,
                        inner_folds=fold["inner_folds"],
                        sub_train_indices_map=sub_train_map,
                    )
                    base_estimator = evaluator.refit_on_sub_train(X_sub, y_sub)
                    winning_params = best_params
                    candidate_scores = evaluator.candidate_scores_

                elif family_upper == "M2":
                    evaluator = XGBoostCandidateEvaluator(configuration=norm_config)
                    best_params, best_rounds = evaluator.evaluate_inner_candidates(
                        X_sub_train=X_sub,
                        y_sub_train=y_sub,
                        inner_folds=fold["inner_folds"],
                        sub_train_indices_map=sub_train_map,
                    )
                    base_estimator = evaluator.refit_on_sub_train(X_sub, y_sub)
                    winning_params = dict(best_params)
                    winning_params["n_estimators_fitted"] = best_rounds
                    candidate_scores = evaluator.candidate_scores_

                # 3. Post-Hoc Probability Calibration on Disjoint Calibration Partition (§5.1, §5.2)
                calibrator = ModelAgnosticCalibrator(
                    base_estimator=base_estimator,
                    model_family=family_upper,
                    min_calibration_positives=25,
                )
                calibrator.fit(X_cal, y_cal)
                cal_diagnostics = calibrator.diagnostics_

                # 4. Operational Threshold Optimization on Disjoint Threshold-Validation Partition (§6.2, §6.3)
                prob_th = calibrator.predict_proba(X_th)[:, 1]
                threshold_opt = ThresholdOptimizer(
                    cost_fn=self.cost_fn,
                    cost_fp=self.cost_fp,
                )
                threshold_opt.optimize(y_val=y_th, y_prob_val=prob_th)
                optimal_tau = threshold_opt.optimal_threshold_
                threshold_summary = threshold_opt.get_summary()

                # 5. Single Out-of-Sample Outer-Test Evaluation at Frozen Threshold (§4.3, §7.1)
                prob_test = calibrator.predict_proba(X_test)[:, 1]
                outer_metrics = compute_stage3_metrics(
                    y_true=y_test,
                    y_prob=prob_test,
                    threshold=optimal_tau,
                    p_reference=p_reference,
                    cost_fn=self.cost_fn,
                    cost_fp=self.cost_fp,
                )

                fold_record = {
                    "repetition_index": r_idx,
                    "outer_fold_index": k_idx,
                    "outer_seed": outer_seed,
                    "model_family": family_upper,
                    "configuration": norm_config,
                    "p_reference_sub_train": round(p_reference, 6),
                    "winning_hyperparameters": winning_params,
                    "inner_candidate_results": candidate_scores,
                    "calibration_diagnostics": cal_diagnostics,
                    "threshold_optimization": threshold_summary,
                    "outer_test_metrics": outer_metrics,
                }
                fold_evaluations.append(fold_record)

        # 6. Structured Aggregation Across Outer Evaluations (§7.1, §7.2)
        summary = self._aggregate_evaluation_results(fold_evaluations, family_upper, norm_config)
        return summary

    def _aggregate_evaluation_results(
        self,
        fold_evaluations: List[Dict[str, Any]],
        model_family: str,
        configuration: str,
    ) -> Dict[str, Any]:
        """Aggregates per-fold results into repetition and procedure-level statistics."""
        n_evals = len(fold_evaluations)
        if n_evals == 0:
            return {"total_evaluations": 0, "evaluations": []}

        # Extract metric arrays
        ap_list = [f["outer_test_metrics"]["ranking_metrics"]["average_precision"] for f in fold_evaluations]
        roc_list = [f["outer_test_metrics"]["ranking_metrics"]["roc_auc"] for f in fold_evaluations]
        bs_list = [f["outer_test_metrics"]["calibration_metrics"]["brier_score"] for f in fold_evaluations]
        bss_list = [f["outer_test_metrics"]["calibration_metrics"]["brier_skill_score"] for f in fold_evaluations]
        ece_list = [f["outer_test_metrics"]["calibration_metrics"]["expected_calibration_error"] for f in fold_evaluations]
        cost_list = [f["outer_test_metrics"]["operational_metrics"]["total_operational_cost"] for f in fold_evaluations]
        tau_list = [f["threshold_optimization"]["optimal_threshold"] for f in fold_evaluations]

        # Group by repetition for multi-level reporting
        reps_map: Dict[int, List[Dict[str, Any]]] = {}
        for f in fold_evaluations:
            r = f["repetition_index"]
            reps_map.setdefault(r, []).append(f)

        repetition_stats = []
        for r_idx, r_folds in sorted(reps_map.items()):
            r_ap = [f["outer_test_metrics"]["ranking_metrics"]["average_precision"] for f in r_folds]
            r_roc = [f["outer_test_metrics"]["ranking_metrics"]["roc_auc"] for f in r_folds]
            r_cost = [f["outer_test_metrics"]["operational_metrics"]["total_operational_cost"] for f in r_folds]
            repetition_stats.append({
                "repetition_index": r_idx,
                "n_folds": len(r_folds),
                "mean_average_precision": round(float(np.mean(r_ap)), 5),
                "std_average_precision": round(float(np.std(r_ap, ddof=1)), 5) if len(r_ap) > 1 else 0.0,
                "mean_roc_auc": round(float(np.mean(r_roc)), 5),
                "mean_operational_cost": round(float(np.mean(r_cost)), 2),
            })

        procedure_summary = {
            "model_family": model_family,
            "configuration": configuration,
            "total_outer_evaluations": n_evals,
            "n_repetitions": len(reps_map),
            "ranking_metrics": {
                "average_precision": {
                    "mean": round(float(np.mean(ap_list)), 5),
                    "std": round(float(np.std(ap_list, ddof=1)), 5) if n_evals > 1 else 0.0,
                    "min": round(float(np.min(ap_list)), 5),
                    "max": round(float(np.max(ap_list)), 5),
                },
                "roc_auc": {
                    "mean": round(float(np.mean(roc_list)), 5),
                    "std": round(float(np.std(roc_list, ddof=1)), 5) if n_evals > 1 else 0.0,
                    "min": round(float(np.min(roc_list)), 5),
                    "max": round(float(np.max(roc_list)), 5),
                },
            },
            "calibration_metrics": {
                "brier_score": {
                    "mean": round(float(np.mean(bs_list)), 6),
                    "std": round(float(np.std(bs_list, ddof=1)), 6) if n_evals > 1 else 0.0,
                },
                "brier_skill_score": {
                    "mean": round(float(np.mean(bss_list)), 5),
                    "std": round(float(np.std(bss_list, ddof=1)), 5) if n_evals > 1 else 0.0,
                },
                "expected_calibration_error": {
                    "mean": round(float(np.mean(ece_list)), 5),
                    "std": round(float(np.std(ece_list, ddof=1)), 5) if n_evals > 1 else 0.0,
                },
            },
            "operational_metrics": {
                "threshold_distribution": {
                    "mean": round(float(np.mean(tau_list)), 5),
                    "std": round(float(np.std(tau_list, ddof=1)), 5) if n_evals > 1 else 0.0,
                    "min": round(float(np.min(tau_list)), 5),
                    "max": round(float(np.max(tau_list)), 5),
                },
                "operational_cost": {
                    "mean": round(float(np.mean(cost_list)), 2),
                    "std": round(float(np.std(cost_list, ddof=1)), 2) if n_evals > 1 else 0.0,
                    "min": round(float(np.min(cost_list)), 2),
                    "max": round(float(np.max(cost_list)), 2),
                },
                "cost_disclaimer": (
                    "The 50:1 cost ratio ($10,000 / $200) is an illustrative PRD benchmark (Appendix E) "
                    "and does not represent verified customer plant economics."
                ),
            },
            "repetition_breakdown": repetition_stats,
            "governance_notices": [
                "Cross-validation metrics evaluate the model-building procedure, NOT a single deployable artifact.",
                "The 25 repeated outer evaluations share training data and are NOT statistically independent observations.",
                "average_precision is computed using scikit-learn average_precision_score (canonical PR-AUC).",
            ],
            "fold_evaluations": fold_evaluations,
        }

        return procedure_summary

    def save_evaluation_report(
        self,
        report_data: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Serializes structured evaluation report to JSON with UTF-8 encoding."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

