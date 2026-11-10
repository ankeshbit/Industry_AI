"""
Automated Baseline Experiment Runner for INDUSTRIA AI (Stage 2B)

Executes 8 rigorous baseline experiments across Configuration A (With Type)
and Configuration B (Without Type) using a strictly held-out stratified test set.
Saves model artifacts, evaluation plots, and metrics, and updates ML_EXPERIMENT_LOG.md.
"""

import json
import time
import sys
from pathlib import Path

# Add project root to sys.path so 'ml.*' modules are importable
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, roc_curve

from ml.src.data.loader import load_ai4i_dataset
from ml.src.data.splitting import generate_stratified_split
from ml.src.features.schemas import (
    prepare_features_and_target,
    AI4I_SHA256_CHECKSUM,
    PRIMARY_TARGET,
    CONFIG_A_FEATURES,
    CONFIG_B_FEATURES,
)
from ml.src.models.train import get_baseline_models, build_pipeline_for_model, train_and_evaluate_model
from ml.src.evaluation.metrics import (
    plot_confusion_matrices_grid,
    DEFAULT_COST_FN,
    DEFAULT_COST_FP,
)


def run_all_baseline_experiments():
    project_root = Path(__file__).resolve().parent.parent.parent
    artifacts_dir = project_root / "ml" / "artifacts"
    models_dir = artifacts_dir / "models"
    plots_dir = artifacts_dir / "plots"
    models_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("INDUSTRIA AI — STAGE 2B: BASELINE EXPERIMENT SUITE")
    print("=" * 70)

    # 1. Load Dataset
    print("\\n[Step 1] Loading and verifying raw AI4I dataset...")
    df = load_ai4i_dataset(verify_checksum=True)
    print(f"Dataset successfully loaded. Shape: {df.shape}")

    # 2. Stratified Split (80% Train, 20% Holdout Test)
    print("\\n[Step 2] Generating reproducible stratified train/test split...")
    split_path = artifacts_dir / "split_indices.json"
    train_idx, test_idx, split_meta = generate_stratified_split(
        df=df,
        target_col=PRIMARY_TARGET,
        test_size=0.20,
        random_state=42,
        save_path=split_path,
    )
    print(f"Train samples: {len(train_idx)} (Failures: {split_meta['train_failure_rate']*100:.2f}%)")
    print(f"Test samples:  {len(test_idx)} (Failures: {split_meta['test_failure_rate']*100:.2f}%)")
    print(f"Split metadata serialized to: {split_path}")

    # Calculate train-set class weighting for XGBoost
    train_df = df.iloc[train_idx]
    n_neg = (train_df[PRIMARY_TARGET] == 0).sum()
    n_pos = (train_df[PRIMARY_TARGET] == 1).sum()
    scale_pos_weight = float(n_neg / n_pos)
    print(f"Dynamic train fold scale_pos_weight for XGBoost: {scale_pos_weight:.2f}")

    # Experiment Definitions
    configs = [
        ("A", "With Type", CONFIG_A_FEATURES, "EXP-001", "EXP-004"),
        ("B", "Without Type", CONFIG_B_FEATURES, "EXP-005", "EXP-008"),
    ]

    all_results = {}
    curve_data = {}

    exp_counter = 1

    for config_key, config_name, feature_list, start_exp, end_exp in configs:
        print(f"\\n{'=' * 70}")
        print(f"RUNNING CONFIGURATION {config_key}: {config_name.upper()}")
        print(f"Features: {feature_list}")
        print("=" * 70)

        # Prepare X, y
        X_full, y_full = prepare_features_and_target(df, configuration=config_key)
        X_train, y_train = X_full.iloc[train_idx], y_full.iloc[train_idx]
        X_test, y_test = X_full.iloc[test_idx], y_full.iloc[test_idx]

        models = get_baseline_models(scale_pos_weight=scale_pos_weight, random_state=42)
        config_results = {}

        for model_name, model_obj in models.items():
            exp_id = f"EXP-{exp_counter:03d}"
            print(f"\\n--- [{exp_id}] {model_name} (Config {config_key}) ---")

            # Build pipeline
            pipeline = build_pipeline_for_model(model_name, model_obj, configuration=config_key)

            # Train and evaluate
            test_metrics, train_metrics, duration = train_and_evaluate_model(
                pipeline=pipeline,
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test,
            )

            print(f"Train F1: {train_metrics['f1_score']:.4f} | Test F1: {test_metrics['f1_score']:.4f}")
            print(f"Test Recall: {test_metrics['recall']:.4f} | Test Precision: {test_metrics['precision']:.4f}")
            print(f"Test PR-AUC: {test_metrics['pr_auc']} | Test ROC-AUC: {test_metrics['roc_auc']}")
            print(f"False Negatives: {test_metrics['false_negatives']} | False Positives: {test_metrics['false_positives']}")
            print(f"Total Operational Cost: ${test_metrics['total_operational_cost']:,.0f}")
            print(f"Execution Time: {duration:.3f}s")

            # Save Model Artifact
            slug = model_name.lower().replace(" ", "_")
            model_path = models_dir / f"{exp_id}_{slug}_config_{config_key.lower()}.joblib"
            joblib.dump(pipeline, model_path)

            # Store Curve Points
            y_test_prob = pipeline.predict_proba(X_test)[:, 1]
            prec_pts, rec_pts, _ = precision_recall_curve(y_test, y_test_prob)
            fpr_pts, tpr_pts, _ = roc_curve(y_test, y_test_prob)

            curve_data[f"{exp_id}_{model_name}_{config_key}"] = {
                "precision": prec_pts.tolist(),
                "recall": rec_pts.tolist(),
                "fpr": fpr_pts.tolist(),
                "tpr": tpr_pts.tolist(),
                "pr_auc": test_metrics["pr_auc"],
                "roc_auc": test_metrics["roc_auc"],
                "model_name": model_name,
                "config": config_key,
            }

            exp_record = {
                "experiment_id": exp_id,
                "model_name": model_name,
                "configuration": config_key,
                "configuration_label": config_name,
                "features": feature_list,
                "hyperparameters": {k: str(v) for k, v in model_obj.get_params().items() if k in ["class_weight", "max_depth", "n_estimators", "learning_rate", "scale_pos_weight", "solver", "min_samples_split", "min_samples_leaf"]},
                "test_metrics": test_metrics,
                "train_metrics": train_metrics,
                "artifact_path": str(model_path.relative_to(project_root)),
                "random_state": 42,
                "dataset_checksum": AI4I_SHA256_CHECKSUM,
            }

            all_results[exp_id] = exp_record
            config_results[model_name] = test_metrics
            exp_counter += 1

        # Plot Confusion Matrices for this configuration
        cm_plot_path = plots_dir / f"confusion_matrices_config_{config_key.lower()}.png"
        plot_confusion_matrices_grid(
            results=config_results,
            title_suffix=f"(Config {config_key}: {config_name})",
            save_path=str(cm_plot_path),
        )
        print(f"Confusion matrix grid saved: {cm_plot_path}")

    # Save Full Baseline Results JSON
    results_json_path = artifacts_dir / "baseline_results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\\nAll experiment metrics serialized to: {results_json_path}")

    # Generate Combined Comparison Plots
    print("\\n[Step 3] Generating multi-model PR & ROC comparison curves...")
    generate_comparison_plots(curve_data, plots_dir)

    # Generate ML_EXPERIMENT_LOG.md markdown update
    print("\\n[Step 4] Generating experiment log markdown...")
    update_experiment_log(all_results, project_root / "docs" / "ML_EXPERIMENT_LOG.md")

    print("\\n" + "=" * 70)
    print("STAGE 2B BASELINE EXPERIMENTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    return all_results


def generate_comparison_plots(curve_data, plots_dir):
    """Generates PR, ROC, and Cost comparison plots."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    colors = {
        "Logistic Regression": "#1f77b4",
        "Decision Tree": "#ff7f0e",
        "Random Forest": "#2ca02c",
        "XGBoost": "#d62728",
    }
    linestyles = {"A": "-", "B": "--"}

    for exp_key, data in curve_data.items():
        m_name = data["model_name"]
        cfg = data["config"]
        label = f"{m_name} (Cfg {cfg}) [PR-AUC={data['pr_auc']:.3f}]"
        axes[0].plot(
            data["recall"],
            data["precision"],
            label=label,
            color=colors.get(m_name, "black"),
            linestyle=linestyles.get(cfg, "-"),
            linewidth=1.8,
        )

        label_roc = f"{m_name} (Cfg {cfg}) [ROC-AUC={data['roc_auc']:.3f}]"
        axes[1].plot(
            data["fpr"],
            data["tpr"],
            label=label_roc,
            color=colors.get(m_name, "black"),
            linestyle=linestyles.get(cfg, "-"),
            linewidth=1.8,
        )

    axes[0].set_title("Precision-Recall Curves (Config A vs B)", fontweight="bold")
    axes[0].set_xlabel("Recall (Sensitivity)")
    axes[0].set_ylabel("Precision")
    axes[0].set_xlim([0.0, 1.05])
    axes[0].set_ylim([0.0, 1.05])
    axes[0].legend(loc="lower left", fontsize=8)
    axes[0].grid(True, linestyle=":", alpha=0.6)

    axes[1].plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Chance")
    axes[1].set_title("ROC Curves (Config A vs B)", fontweight="bold")
    axes[1].set_xlabel("False Positive Rate")
    axes[1].set_ylabel("True Positive Rate (Recall)")
    axes[1].set_xlim([-0.02, 1.02])
    axes[1].set_ylim([0.0, 1.05])
    axes[1].legend(loc="lower right", fontsize=8)
    axes[1].grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    curves_path = plots_dir / "precision_recall_and_roc_comparison.png"
    plt.savefig(curves_path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"Comparison curves saved to: {curves_path}")


def update_experiment_log(all_results, log_path):
    """Updates ML_EXPERIMENT_LOG.md with the 8 baseline experiments."""
    with open(log_path, "r", encoding="utf-8") as f:
        existing_content = f.read()

    # Build the summary table
    table_rows = []
    for exp_id, res in all_results.items():
        m_test = res["test_metrics"]
        cost_str = f"${m_test['total_operational_cost']:,.0f}"
        row = (
            f"| **{exp_id}** | 2026-11-10 | ML Engineer | "
            f"{res['model_name']} (Config {res['configuration']}) | "
            f"{res['configuration_label']} | "
            f"{m_test['pr_auc']:.4f} | "
            f"{m_test['f1_score']:.4f} | "
            f"{m_test['recall']:.4f} | "
            f"{m_test['false_negatives']} | "
            f"{cost_str} | "
            f"Completed |"
        )
        table_rows.append(row)

    table_header = (
        "## Baseline Experiments Summary (Stage 2B)\n\n"
        "| Exp ID | Date | Author | Model & Setup | Features | PR-AUC | F1-Score | Recall | FN Count | Operational Cost ($) | Status |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    summary_section = table_header + "\n".join(table_rows) + "\n\n---\n\n"

    # Build detailed section for each experiment
    detailed_sections = ["## Detailed Experiment Records (Stage 2B)\n\n"]
    for exp_id, res in all_results.items():
        m_test = res["test_metrics"]
        m_train = res["train_metrics"]
        cost_str = f"${m_test['total_operational_cost']:,.0f}"
        art_path = res['artifact_path'].replace('\\', '/')
        sec = f"""### {exp_id}: {res['model_name']} (Configuration {res['configuration']})
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration {res['configuration']} ({res['configuration_label']})
- **Features ({len(res['features'])}):** `{', '.join(res['features'])}`
- **Dataset Checksum:** `{res['dataset_checksum']}`
- **Random Seed:** {res['random_state']}
- **Hyperparameters:** `{json.dumps(res['hyperparameters'])}`
- **Artifact:** [`{res['artifact_path']}`](file:///{art_path})

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **{m_test['pr_auc']:.4f}** | {m_train['pr_auc']:.4f} |
| **ROC-AUC** | **{m_test['roc_auc']:.4f}** | {m_train['roc_auc']:.4f} |
| **F1-Score** | **{m_test['f1_score']:.4f}** | {m_train['f1_score']:.4f} |
| **Recall (Sensitivity)** | **{m_test['recall']:.4f}** | {m_train['recall']:.4f} |
| **Precision** | **{m_test['precision']:.4f}** | {m_train['precision']:.4f} |
| **Accuracy** | {m_test['accuracy']:.4f} | {m_train['accuracy']:.4f} |
| **False Negatives (FN)** | **{m_test['false_negatives']}** | {m_train['false_negatives']} |
| **False Positives (FP)** | {m_test['false_positives']} | {m_train['false_positives']} |
| **Operational Cost** | **{cost_str}** | ${m_train['total_operational_cost']:,.0f} |
| **Fit Duration** | {m_test['execution_time_sec']:.3f}s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN={m_test['true_negatives']}, FP={m_test['false_positives']}, FN={m_test['false_negatives']}, TP={m_test['true_positives']} out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught {m_test['true_positives']} out of 68 failures ({m_test['recall']*100:.1f}%), leaving {m_test['false_negatives']} unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = ${m_test['total_operational_cost']:,.0f} ($10k per FN + $200 per FP).
"""
        detailed_sections.append(sec)

    new_content = existing_content + "\n\n" + summary_section + "".join(detailed_sections)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {log_path} with all 8 experiment records.")


if __name__ == "__main__":
    run_all_baseline_experiments()
