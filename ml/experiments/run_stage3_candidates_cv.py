"""
Stage 3 Phase 2B.1 Random Forest Candidate Evaluation Runner (Repeated Nested CV)

Executes complete 25-fold repeated nested cross-validation across all 5 repetitions
for M1 (Random Forest) under both Configuration A (WITH_TYPE) and Configuration B (NO_TYPE)
— completing all 50 M1 evaluations.

Adheres strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2 (§3.3, §5.1, §6.1–§6.4, §7.1–§7.2)
- Root PRD.md v1.2 (§10.1.3–§10.1.5, §11.1, §13.5, §18.3)
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

from ml.src.evaluation.engine import Stage3EvaluationEngine
from ml.src.data.nested_splitting import DEFAULT_NESTED_CV_ARTIFACT_PATH


DEFAULT_M1_OUTPUT_REPORT_PATH = (
    Path(__file__).resolve().parent.parent / "artifacts" / "stage3_phase2b1_random_forest_report.json"
)


def run_m1_candidates_evaluations(
    save_path: Path = DEFAULT_M1_OUTPUT_REPORT_PATH,
    repetition_indices: List[int] = list(range(5)),
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Executes all 50 M1 evaluations (25 outer folds x 2 configurations).

    Returns:
        Structured dictionary containing full fold-level, repetition-level,
        and configuration-level results.
    """
    start_time = time.time()
    engine = Stage3EvaluationEngine()

    experiments = [
        {"model_family": "M1", "configuration": "A", "label": "M1_RandomForest_Config_A_WITH_TYPE"},
        {"model_family": "M1", "configuration": "B", "label": "M1_RandomForest_Config_B_NO_TYPE"},
    ]

    all_experiment_results: Dict[str, Any] = {}
    total_evaluations_executed = 0

    if verbose:
        print("=" * 80)
        print("INDUSTRIA AI — Stage 3 Phase 2B.1 Random Forest Evaluation Runner")
        print(f"Coverage: {len(repetition_indices)} Repetitions x 5 Outer Folds x 2 Configurations = {len(repetition_indices)*10} Runs")
        print("=" * 80)

    for exp in experiments:
        family = exp["model_family"]
        config = exp["configuration"]
        label = exp["label"]

        if verbose:
            print(f"\n[Starting Experiment: {label}] (Family: {family}, Config: {config}, Folds: {len(repetition_indices)*5})")
        exp_start = time.time()

        res = engine.evaluate_model_family(
            model_family=family,
            configuration=config,
            repetition_indices=repetition_indices,
        )
        exp_duration = time.time() - exp_start
        res["execution_duration_seconds"] = round(exp_duration, 2)
        all_experiment_results[label] = res

        n_evals = res["total_outer_evaluations"]
        total_evaluations_executed += n_evals

        if verbose:
            mean_ap = res["ranking_metrics"]["average_precision"]["mean"]
            mean_roc = res["ranking_metrics"]["roc_auc"]["mean"]
            mean_bss = res["calibration_metrics"]["brier_skill_score"]["mean"]
            mean_cost = res["operational_metrics"]["operational_cost"]["mean"]
            mean_tau = res["operational_metrics"]["threshold_distribution"]["mean"]
            print(f"  Completed {n_evals} outer folds in {exp_duration:.2f}s")
            print(f"  Mean AP: {mean_ap:.5f} | Mean ROC-AUC: {mean_roc:.5f} | Mean BSS: {mean_bss:.5f}")
            print(f"  Mean Operational Cost: ${mean_cost:,.2f} | Mean Optimal Threshold: {mean_tau:.4f}")

    total_duration = time.time() - start_time

    final_report = {
        "metadata": {
            "evaluation_phase": "Stage 3 Phase 2B.1 (Random Forest M1)",
            "architecture_version": "v1.4.2",
            "prd_version": "v1.2",
            "n_repetitions": len(repetition_indices),
            "outer_k": 5,
            "inner_k": 4,
            "total_evaluations": total_evaluations_executed,
            "total_duration_seconds": round(total_duration, 2),
            "manifest_fingerprint": engine.manifest["metadata"]["manifest_hash"],
            "dataset_checksum": engine.manifest["metadata"]["dataset_checksum"],
        },
        "experiments": all_experiment_results,
    }

    if save_path:
        engine.save_evaluation_report(final_report, save_path)
        if verbose:
            print(f"\nSuccessfully serialized comprehensive Phase 2B.1 M1 report to: {save_path}")

    return final_report


if __name__ == "__main__":
    run_m1_candidates_evaluations()

