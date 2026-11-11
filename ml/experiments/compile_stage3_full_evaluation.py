"""
Stage 3 Comprehensive Model Evaluation, Comparison, and Selection Compiler

Compiles results from all completed evaluation reports:
- Stage 3 Phase 2A (B0 Prevalence, B1 Logistic Regression)
- Stage 3 Phase 2B.1 (M1 Random Forest)
- Stage 3 Phase 2C (M2 XGBoost)
Across both Configuration A (WITH_TYPE) and Configuration B (NO_TYPE).

Evaluates PRD v1.2 §10.1.5 Promotion Criteria:
- Candidate model must demonstrate simultaneous improvement on BOTH PR-AUC (Average Precision)
  and Brier Score over the baseline.
- Selection must NOT be based solely on ROC-AUC.
- Formal descriptive comparison without naive independent-sample statistical tests.

Produces:
ml/artifacts/stage3_full_evaluation_report.json
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np


ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
BASELINE_REPORT_PATH = ARTIFACTS_DIR / "stage3_phase2a_baseline_report.json"
RF_REPORT_PATH = ARTIFACTS_DIR / "stage3_phase2b1_random_forest_report.json"
XGB_REPORT_PATH = ARTIFACTS_DIR / "stage3_phase2c_xgboost_report.json"
FULL_REPORT_PATH = ARTIFACTS_DIR / "stage3_full_evaluation_report.json"


def load_report(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_hyperparameter_frequencies(fold_evaluations: List[Dict[str, Any]]) -> Dict[str, int]:
    freq: Dict[str, int] = {}
    for fold in fold_evaluations:
        params = fold.get("winning_hyperparameters", {})
        # Format a clean string key
        key_parts = []
        for k in sorted(params.keys()):
            val = params[k]
            key_parts.append(f"{k}={val}")
        param_str = ", ".join(key_parts) if key_parts else "default"
        freq[param_str] = freq.get(param_str, 0) + 1
    return freq


def extract_model_summary(exp_data: Dict[str, Any]) -> Dict[str, Any]:
    folds = exp_data.get("fold_evaluations", [])
    n_evals = len(folds)

    # Metric collections
    ap_vals = [f["outer_test_metrics"]["ranking_metrics"]["average_precision"] for f in folds]
    roc_vals = [f["outer_test_metrics"]["ranking_metrics"]["roc_auc"] for f in folds]
    bs_vals = [f["outer_test_metrics"]["calibration_metrics"]["brier_score"] for f in folds]
    bss_vals = [f["outer_test_metrics"]["calibration_metrics"]["brier_skill_score"] for f in folds]
    ece_vals = [f["outer_test_metrics"]["calibration_metrics"]["expected_calibration_error"] for f in folds]
    cost_vals = [f["outer_test_metrics"]["operational_metrics"]["total_operational_cost"] for f in folds]
    tau_vals = [f["threshold_optimization"]["optimal_threshold"] for f in folds]

    tp_vals = [f["outer_test_metrics"]["classification_metrics"]["true_positives"] for f in folds]
    fp_vals = [f["outer_test_metrics"]["classification_metrics"]["false_positives"] for f in folds]
    fn_vals = [f["outer_test_metrics"]["classification_metrics"]["false_negatives"] for f in folds]
    tn_vals = [f["outer_test_metrics"]["classification_metrics"]["true_negatives"] for f in folds]
    prec_vals = [f["outer_test_metrics"]["classification_metrics"]["precision"] for f in folds]
    rec_vals = [f["outer_test_metrics"]["classification_metrics"]["recall"] for f in folds]
    f1_vals = [f["outer_test_metrics"]["classification_metrics"]["f1_score"] for f in folds]

    w_vals = [f["calibration_diagnostics"].get("w", 1.0) for f in folds]
    c_vals = [f["calibration_diagnostics"].get("c", 0.0) for f in folds]

    return {
        "model_family": exp_data.get("model_family"),
        "configuration": exp_data.get("configuration"),
        "total_outer_evaluations": n_evals,
        "ranking_metrics": {
            "average_precision": {
                "mean": round(float(np.mean(ap_vals)), 5),
                "std": round(float(np.std(ap_vals, ddof=1)), 5) if n_evals > 1 else 0.0,
                "min": round(float(np.min(ap_vals)), 5),
                "max": round(float(np.max(ap_vals)), 5),
            },
            "roc_auc": {
                "mean": round(float(np.mean(roc_vals)), 5),
                "std": round(float(np.std(roc_vals, ddof=1)), 5) if n_evals > 1 else 0.0,
                "min": round(float(np.min(roc_vals)), 5),
                "max": round(float(np.max(roc_vals)), 5),
            },
        },
        "calibration_metrics": {
            "brier_score": {
                "mean": round(float(np.mean(bs_vals)), 6),
                "std": round(float(np.std(bs_vals, ddof=1)), 6) if n_evals > 1 else 0.0,
                "min": round(float(np.min(bs_vals)), 6),
                "max": round(float(np.max(bs_vals)), 6),
            },
            "brier_skill_score": {
                "mean": round(float(np.mean(bss_vals)), 5),
                "std": round(float(np.std(bss_vals, ddof=1)), 5) if n_evals > 1 else 0.0,
                "min": round(float(np.min(bss_vals)), 5),
                "max": round(float(np.max(bss_vals)), 5),
            },
            "expected_calibration_error": {
                "mean": round(float(np.mean(ece_vals)), 5),
                "std": round(float(np.std(ece_vals, ddof=1)), 5) if n_evals > 1 else 0.0,
            },
            "calibration_parameters": {
                "w_slope_mean": round(float(np.mean(w_vals)), 4),
                "w_slope_std": round(float(np.std(w_vals, ddof=1)), 4) if n_evals > 1 else 0.0,
                "c_intercept_mean": round(float(np.mean(c_vals)), 4),
                "c_intercept_std": round(float(np.std(c_vals, ddof=1)), 4) if n_evals > 1 else 0.0,
            },
        },
        "operational_metrics": {
            "operational_cost": {
                "mean": round(float(np.mean(cost_vals)), 2),
                "std": round(float(np.std(cost_vals, ddof=1)), 2) if n_evals > 1 else 0.0,
                "min": round(float(np.min(cost_vals)), 2),
                "max": round(float(np.max(cost_vals)), 2),
            },
            "threshold_distribution": {
                "mean": round(float(np.mean(tau_vals)), 4),
                "std": round(float(np.std(tau_vals, ddof=1)), 4) if n_evals > 1 else 0.0,
                "min": round(float(np.min(tau_vals)), 4),
                "max": round(float(np.max(tau_vals)), 4),
            },
        },
        "classification_metrics": {
            "precision": {
                "mean": round(float(np.mean(prec_vals)), 4),
                "std": round(float(np.std(prec_vals, ddof=1)), 4) if n_evals > 1 else 0.0,
            },
            "recall": {
                "mean": round(float(np.mean(rec_vals)), 4),
                "std": round(float(np.std(rec_vals, ddof=1)), 4) if n_evals > 1 else 0.0,
            },
            "f1_score": {
                "mean": round(float(np.mean(f1_vals)), 4),
                "std": round(float(np.std(f1_vals, ddof=1)), 4) if n_evals > 1 else 0.0,
            },
            "confusion_matrix_means_per_fold": {
                "true_positives": round(float(np.mean(tp_vals)), 1),
                "false_positives": round(float(np.mean(fp_vals)), 1),
                "false_negatives": round(float(np.mean(fn_vals)), 1),
                "true_negatives": round(float(np.mean(tn_vals)), 1),
            },
            "confusion_matrix_totals_across_folds": {
                "true_positives": int(np.sum(tp_vals)),
                "false_positives": int(np.sum(fp_vals)),
                "false_negatives": int(np.sum(fn_vals)),
                "true_negatives": int(np.sum(tn_vals)),
            },
        },
        "hyperparameter_frequencies": extract_hyperparameter_frequencies(folds),
    }


def compile_full_evaluation_report() -> Dict[str, Any]:
    baseline_rep = load_report(BASELINE_REPORT_PATH)
    rf_rep = load_report(RF_REPORT_PATH)
    xgb_rep = load_report(XGB_REPORT_PATH)

    if not baseline_rep:
        raise FileNotFoundError(f"Baseline report not found at {BASELINE_REPORT_PATH}")
    if not rf_rep:
        raise FileNotFoundError(f"Random Forest report not found at {RF_REPORT_PATH}")
    if not xgb_rep:
        raise FileNotFoundError(f"XGBoost report not found at {XGB_REPORT_PATH}")

    all_experiments = {}
    all_experiments.update(baseline_rep.get("experiments", {}))
    all_experiments.update(rf_rep.get("experiments", {}))
    all_experiments.update(xgb_rep.get("experiments", {}))

    model_summaries = {}
    for exp_label, exp_data in all_experiments.items():
        model_summaries[exp_label] = extract_model_summary(exp_data)

    # Comparative Analysis and Promotion Evaluation (PRD §10.1.5)
    comparative_results = {}
    for cfg in ["A", "B"]:
        cfg_name = "WITH_TYPE" if cfg == "A" else "NO_TYPE"
        b0_key = f"B0_Prevalence_Config_{cfg}_{cfg_name}"
        b1_key = f"B1_LogisticRegression_Config_{cfg}_{cfg_name}"
        m1_key = f"M1_RandomForest_Config_{cfg}_{cfg_name}"
        m2_key = f"M2_XGBoost_Config_{cfg}_{cfg_name}"

        b0_sum = model_summaries[b0_key]
        b1_sum = model_summaries[b1_key]
        m1_sum = model_summaries[m1_key]
        m2_sum = model_summaries[m2_key]

        b1_ap = b1_sum["ranking_metrics"]["average_precision"]["mean"]
        b1_brier = b1_sum["calibration_metrics"]["brier_score"]["mean"]

        candidates = [("M1", m1_key, m1_sum), ("M2", m2_key, m2_sum)]
        promotion_decisions = []

        for cand_name, cand_key, cand_sum in candidates:
            cand_ap = cand_sum["ranking_metrics"]["average_precision"]["mean"]
            cand_brier = cand_sum["calibration_metrics"]["brier_score"]["mean"]

            ap_delta = cand_ap - b1_ap
            ap_pct = (ap_delta / b1_ap) * 100.0 if b1_ap > 0 else 0.0

            brier_delta = cand_brier - b1_brier  # negative is improvement (lower error)
            brier_pct = (brier_delta / b1_brier) * 100.0 if b1_brier > 0 else 0.0

            # PRD §10.1.5 gate: candidate must improve on BOTH AP (higher) and Brier (lower)
            passes_ap = cand_ap > b1_ap
            passes_brier = cand_brier < b1_brier
            promotable = passes_ap and passes_brier

            promotion_decisions.append({
                "candidate": cand_name,
                "label": cand_key,
                "ap_mean": cand_ap,
                "ap_delta_vs_b1": round(ap_delta, 5),
                "ap_relative_change_pct": round(ap_pct, 2),
                "passes_ap_gate": passes_ap,
                "brier_mean": cand_brier,
                "brier_delta_vs_b1": round(brier_delta, 6),
                "brier_relative_change_pct": round(brier_pct, 2),
                "passes_brier_gate": passes_brier,
                "is_promotable": promotable,
                "mean_operational_cost": cand_sum["operational_metrics"]["operational_cost"]["mean"],
                "mean_roc_auc": cand_sum["ranking_metrics"]["roc_auc"]["mean"],
            })

        # Determine winner: among promotable candidates, maximize Average Precision
        promotable_candidates = [d for d in promotion_decisions if d["is_promotable"]]
        if promotable_candidates:
            # Sort by AP descending
            promotable_candidates.sort(key=lambda x: x["ap_mean"], reverse=True)
            winner = promotable_candidates[0]
            selected_model = winner["candidate"]
            selection_rationale = (
                f"{winner['candidate']} demonstrated superior Average Precision ({winner['ap_mean']:.5f} vs B1 {b1_ap:.5f}, "
                f"+{winner['ap_relative_change_pct']}%) while simultaneously achieving lower Brier Score ({winner['brier_mean']:.6f} vs B1 {b1_brier:.6f}, "
                f"{winner['brier_relative_change_pct']}%), satisfying PRD §10.1.5 simultaneous improvement criteria."
            )
        else:
            # Fallback to B1 if no candidate beats both gates
            selected_model = "B1"
            selection_rationale = "No candidate satisfied PRD §10.1.5 dual improvement criteria over active baseline B1; B1 retained."

        comparative_results[f"Configuration_{cfg}_{cfg_name}"] = {
            "baseline_b1_metrics": {
                "average_precision": b1_ap,
                "brier_score": b1_brier,
                "roc_auc": b1_sum["ranking_metrics"]["roc_auc"]["mean"],
                "operational_cost": b1_sum["operational_metrics"]["operational_cost"]["mean"],
            },
            "candidate_evaluations": promotion_decisions,
            "selected_model": selected_model,
            "selection_rationale": selection_rationale,
        }

    full_report = {
        "metadata": {
            "title": "INDUSTRIA AI — Stage 3 Complete Multi-Model Evaluation and Selection Report",
            "architecture_version": "v1.4.2",
            "prd_version": "v1.2",
            "models_evaluated": ["B0_Prevalence", "B1_LogisticRegression", "M1_RandomForest", "M2_XGBoost"],
            "configurations": ["Configuration A (WITH_TYPE)", "Configuration B (NO_TYPE)"],
            "total_outer_evaluations": sum(s["total_outer_evaluations"] for s in model_summaries.values()),
            "evaluation_protocol": "Repeated 5x5 Nested Stratified Cross-Validation (25 outer folds x 4 models x 2 configs = 200 outer evaluations)",
            "manifest_fingerprint": baseline_rep["metadata"]["manifest_fingerprint"],
            "dataset_checksum": baseline_rep["metadata"]["dataset_checksum"],
        },
        "model_summaries": model_summaries,
        "comparative_analysis": comparative_results,
    }

    with open(FULL_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print(f"Successfully compiled full multi-model evaluation report to: {FULL_REPORT_PATH}")
    return full_report


if __name__ == "__main__":
    compile_full_evaluation_report()
