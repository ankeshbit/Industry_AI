"""
Stage 3 Phase 2A Baseline Evaluation Runner (Repeated Nested CV)

Executes complete 25-fold repeated nested cross-validation across all 5 repetitions
for both B0 (Prevalence Baseline) and B1 (Logistic Regression) under both Configuration A (WITH_TYPE)
and Configuration B (NO_TYPE) — completing all 100 evaluations.

Adheres strictly to:
- docs/STAGE_3_EVALUATION_ARCHITECTURE.md v1.4.2
- Root PRD.md v1.2 (§10.1.3–§10.1.5, §11.1, §13.5, §18.3)
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

from ml.src.evaluation.engine import Stage3EvaluationEngine
from ml.src.data.nested_splitting import DEFAULT_NESTED_CV_ARTIFACT_PATH


DEFAULT_OUTPUT_REPORT_PATH = (
    Path(__file__).resolve().parent.parent / "artifacts" / "stage3_phase2a_baseline_report.json"
)


def run_full_phase2a_evaluations(
    save_path: Path = DEFAULT_OUTPUT_REPORT_PATH,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Executes all 100 evaluations (25 outer folds x 2 models x 2 configurations).

    Returns:
        Structured dictionary containing full fold-level, repetition-level,
        and configuration-level results.
    """
    start_time = time.time()
    engine = Stage3EvaluationEngine()

    experiments = [
        {"model_family": "B0", "configuration": "A", "label": "B0_Prevalence_Config_A_WITH_TYPE"},
        {"model_family": "B0", "configuration": "B", "label": "B0_Prevalence_Config_B_NO_TYPE"},
        {"model_family": "B1", "configuration": "A", "label": "B1_LogisticRegression_Config_A_WITH_TYPE"},
        {"model_family": "B1", "configuration": "B", "label": "B1_LogisticRegression_Config_B_NO_TYPE"},
    ]

    all_experiment_results: Dict[str, Any] = {}
    total_evaluations_executed = 0

    if verbose:
        print("=" * 80)
        print("INDUSTRIA AI — Stage 3 Phase 2A Full Evaluation Runner")
        print("Coverage: 5 Repetitions x 5 Outer Folds x 2 Configurations x 2 Models = 100 Runs")
        print("=" * 80)

    for exp in experiments:
        family = exp["model_family"]
        config = exp["configuration"]
        label = exp["label"]

        if verbose:
            print(f"\n[Starting Experiment: {label}] (Family: {family}, Config: {config}, Folds: 25)")
        exp_start = time.time()

        res = engine.evaluate_model_family(
            model_family=family,
            configuration=config,
            repetition_indices=list(range(5)),
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

    # Construct unified multi-model comparison
    final_report = {
        "metadata": {
            "evaluation_phase": "Stage 3 Phase 2A",
            "architecture_version": "v1.4.2",
            "prd_version": "v1.2",
            "n_repetitions": 5,
            "outer_k": 5,
            "inner_k": 4,
            "total_evaluations": total_evaluations_executed,
            "total_duration_seconds": round(total_duration, 2),
            "manifest_fingerprint": engine.manifest["metadata"]["manifest_hash"],
            "dataset_checksum": engine.manifest["metadata"]["dataset_checksum"],
        },
        "experiments": all_experiment_results,
    }

    # Serialize report to disk
    if save_path:
        engine.save_evaluation_report(final_report, save_path)
        if verbose:
            print(f"\nSuccessfully serialized comprehensive Phase 2A report to: {save_path}")

    return final_report


if __name__ == "__main__":
    run_full_phase2a_evaluations()

