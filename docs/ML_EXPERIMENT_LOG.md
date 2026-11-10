# INDUSTRIA AI — ML Experiment Log

This document tracks all machine learning experimentation, baseline models, hyperparameter searches, feature engineering runs, and evaluation metrics across project stages. Every formal training run must be logged here to ensure transparency, reproducibility, and rigorous model comparison.

---

## Experiment Summary Table

| Exp ID | Date | Author | Model / Algorithm | Feature Set | Primary Metric (PR-AUC) | F1-Score | Recall | Business Cost ($) | Status / Decision |
|---|---|---|---|---|---|---|---|---|---|
| *EXP-000* | *Template* | *Engineer* | *Baseline Logistic Regression* | *Raw Scaled Sensors* | *0.00* | *0.00* | *0.00* | *$0* | *Rejected / Baseline* |

---

## Detailed Experiment Template

Use the template below for each experiment run.

### Experiment ID: `EXP-###`
- **Date**: `YYYY-MM-DD`
- **Author**: `[Engineer Name]`
- **Milestone / Stage**: `[e.g., Stage 3: ML Modeling]`
- **Status**: `[Completed / Promoted / Discarded]`

#### 1. Hypothesis & Objective
- **Hypothesis**: `[What specific hypothesis is being tested? e.g., Adding rolling 6h standard deviation of vibration will improve recall on bearing failures by > 5%]`
- **Primary Metric Targeted**: `[e.g., PR-AUC, Recall at 90% precision, Cost metric]`

#### 2. Data & Feature Configuration
- **Dataset**: `ml/datasets/processed/<dataset_name>.csv`
- **Split Method**: `[e.g., Stratified Temporal Split 70/15/15, Seed: 42]`
- **Preprocessing**: `[e.g., RobustScaler on skewed features, StandardScaling on temperatures]`
- **Features Included**:
  - Raw Sensors: `[list]`
  - Engineered Features: `[e.g., rolling_std_vibration_6h, power_ratio, temp_diff]`
- **Target Variable**: `[e.g., failure_next_24h (binary)]`
- **Class Balance**: `[e.g., Healthy: 98.2%, Failure: 1.8%]`

#### 3. Model Architecture & Hyperparameters
- **Algorithm**: `[e.g., XGBClassifier / RandomForestClassifier / LightGBM]`
- **Hyperparameters**:
  ```json
  {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "scale_pos_weight": 10,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42
  }
  ```

#### 4. Quantitative Results & Evaluation

| Evaluation Split | PR-AUC | ROC-AUC | Precision | Recall | F1-Score | Cost Penalty |
|---|---|---|---|---|---|---|
| **Validation** | `0.000` | `0.000` | `0.000` | `0.000` | `0.000` | `$0` |
| **Test** | `0.000` | `0.000` | `0.000` | `0.000` | `0.000` | `$0` |

- **Confusion Matrix (Test Set)**:
  - True Negatives (TN): `[count]`
  - False Positives (FP): `[count]` (Cost: \$`[FP * C_fp]`)
  - False Negatives (FN): `[count]` (Cost: \$`[FN * C_fn]`)
  - True Positives (TP): `[count]`

#### 5. Explainability & Feature Importance (SHAP)
- **Top 5 Features by Mean |SHAP|**:
  1. `[feature_1]`: `[mean |SHAP| value]`
  2. `[feature_2]`: `[mean |SHAP| value]`
  3. `[feature_3]`: `[mean |SHAP| value]`
  4. `[feature_4]`: `[mean |SHAP| value]`
  5. `[feature_5]`: `[mean |SHAP| value]`
- **Observations on Explanations**: `[e.g., Elevated torque combined with sharp temperature difference correlates with overstrain failure]`

#### 6. Artifacts & Serialization
- Model File: `ml/artifacts/<model_name>_<version>.joblib`
- Pipeline Preprocessor: `ml/artifacts/<preprocessor>_<version>.joblib`
- Plots: `ml/artifacts/plots/exp_###_pr_curve.png`

#### 7. Conclusion & Next Steps
- **Takeaways**: `[Summary of findings]`
- **Decision**: `[Promote to candidate model / Needs further tuning / Discard]`
- **Next Iteration**: `[What to try in next experiment]`



## Baseline Experiments Summary (Stage 2B)

| Exp ID | Date | Author | Model & Setup | Features | PR-AUC | F1-Score | Recall | FN Count | Operational Cost ($) | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| **EXP-001** | 2026-11-10 | ML Engineer | Logistic Regression (Config A) | With Type | 0.3818 | 0.2419 | 0.8235 | 12 | $187,800 | Completed |
| **EXP-002** | 2026-11-10 | ML Engineer | Decision Tree (Config A) | With Type | 0.6479 | 0.4603 | 0.8529 | 10 | $125,200 | Completed |
| **EXP-003** | 2026-11-10 | ML Engineer | Random Forest (Config A) | With Type | 0.6596 | 0.6584 | 0.7794 | 15 | $158,000 | Completed |
| **EXP-004** | 2026-11-10 | ML Engineer | XGBoost (Config A) | With Type | 0.7753 | 0.5771 | 0.8529 | 10 | $115,000 | Completed |
| **EXP-005** | 2026-11-10 | ML Engineer | Logistic Regression (Config B) | Without Type | 0.4034 | 0.2415 | 0.8382 | 11 | $179,400 | Completed |
| **EXP-006** | 2026-11-10 | ML Engineer | Decision Tree (Config B) | Without Type | 0.6008 | 0.4706 | 0.8824 | 8 | $105,400 | Completed |
| **EXP-007** | 2026-11-10 | ML Engineer | Random Forest (Config B) | Without Type | 0.7483 | 0.6474 | 0.8235 | 12 | $129,800 | Completed |
| **EXP-008** | 2026-11-10 | ML Engineer | XGBoost (Config B) | Without Type | 0.7734 | 0.5871 | 0.8676 | 9 | $104,800 | Completed |

---

## Detailed Experiment Records (Stage 2B)

### EXP-001: Logistic Regression (Configuration A)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration A (With Type)
- **Features (6):** `Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"class_weight": "balanced", "solver": "lbfgs"}`
- **Artifact:** [`ml\artifacts\models\EXP-001_logistic_regression_config_a.joblib`](file:///ml/artifacts/models/EXP-001_logistic_regression_config_a.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.3818** | 0.4380 |
| **ROC-AUC** | **0.9070** | 0.9012 |
| **F1-Score** | **0.2419** | 0.2358 |
| **Recall (Sensitivity)** | **0.8235** | 0.8118 |
| **Precision** | **0.1418** | 0.1379 |
| **Accuracy** | 0.8245 | 0.8217 |
| **False Negatives (FN)** | **12** | 51 |
| **False Positives (FP)** | 339 | 1375 |
| **Operational Cost** | **$187,800** | $785,000 |
| **Fit Duration** | 0.323s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1593, FP=339, FN=12, TP=56 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 56 out of 68 failures (82.3%), leaving 12 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $187,800 ($10k per FN + $200 per FP).
### EXP-002: Decision Tree (Configuration A)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration A (With Type)
- **Features (6):** `Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"class_weight": "balanced", "max_depth": "6", "min_samples_leaf": "10", "min_samples_split": "20"}`
- **Artifact:** [`ml\artifacts\models\EXP-002_decision_tree_config_a.joblib`](file:///ml/artifacts/models/EXP-002_decision_tree_config_a.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.6479** | 0.7605 |
| **ROC-AUC** | **0.8789** | 0.9848 |
| **F1-Score** | **0.4603** | 0.5166 |
| **Recall (Sensitivity)** | **0.8529** | 0.9779 |
| **Precision** | **0.3152** | 0.3510 |
| **Accuracy** | 0.9320 | 0.9380 |
| **False Negatives (FN)** | **10** | 6 |
| **False Positives (FP)** | 126 | 490 |
| **Operational Cost** | **$125,200** | $158,000 |
| **Fit Duration** | 0.225s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1806, FP=126, FN=10, TP=58 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 58 out of 68 failures (85.3%), leaving 10 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $125,200 ($10k per FN + $200 per FP).
### EXP-003: Random Forest (Configuration A)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration A (With Type)
- **Features (6):** `Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"class_weight": "balanced", "max_depth": "10", "min_samples_leaf": "5", "min_samples_split": "10", "n_estimators": "100"}`
- **Artifact:** [`ml\artifacts\models\EXP-003_random_forest_config_a.joblib`](file:///ml/artifacts/models/EXP-003_random_forest_config_a.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.6596** | 0.9299 |
| **ROC-AUC** | **0.9654** | 0.9973 |
| **F1-Score** | **0.6584** | 0.7793 |
| **Recall (Sensitivity)** | **0.7794** | 0.9705 |
| **Precision** | **0.5699** | 0.6510 |
| **Accuracy** | 0.9725 | 0.9814 |
| **False Negatives (FN)** | **15** | 8 |
| **False Positives (FP)** | 40 | 141 |
| **Operational Cost** | **$158,000** | $108,200 |
| **Fit Duration** | 2.252s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1892, FP=40, FN=15, TP=53 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 53 out of 68 failures (77.9%), leaving 15 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $158,000 ($10k per FN + $200 per FP).
### EXP-004: XGBoost (Configuration A)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration A (With Type)
- **Features (6):** `Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"learning_rate": "0.05", "max_depth": "5", "n_estimators": "100", "scale_pos_weight": "28.52029520295203"}`
- **Artifact:** [`ml\artifacts\models\EXP-004_xgboost_config_a.joblib`](file:///ml/artifacts/models/EXP-004_xgboost_config_a.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.7753** | 0.9401 |
| **ROC-AUC** | **0.9730** | 0.9977 |
| **F1-Score** | **0.5771** | 0.6642 |
| **Recall (Sensitivity)** | **0.8529** | 0.9926 |
| **Precision** | **0.4361** | 0.4991 |
| **Accuracy** | 0.9575 | 0.9660 |
| **False Negatives (FN)** | **10** | 2 |
| **False Positives (FP)** | 75 | 270 |
| **Operational Cost** | **$115,000** | $74,000 |
| **Fit Duration** | 8.180s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1857, FP=75, FN=10, TP=58 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 58 out of 68 failures (85.3%), leaving 10 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $115,000 ($10k per FN + $200 per FP).
### EXP-005: Logistic Regression (Configuration B)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration B (Without Type)
- **Features (5):** `Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"class_weight": "balanced", "solver": "lbfgs"}`
- **Artifact:** [`ml\artifacts\models\EXP-005_logistic_regression_config_b.joblib`](file:///ml/artifacts/models/EXP-005_logistic_regression_config_b.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.4034** | 0.4326 |
| **ROC-AUC** | **0.9080** | 0.8994 |
| **F1-Score** | **0.2415** | 0.2370 |
| **Recall (Sensitivity)** | **0.8382** | 0.8266 |
| **Precision** | **0.1411** | 0.1384 |
| **Accuracy** | 0.8210 | 0.8197 |
| **False Negatives (FN)** | **11** | 47 |
| **False Positives (FP)** | 347 | 1395 |
| **Operational Cost** | **$179,400** | $749,000 |
| **Fit Duration** | 0.049s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1585, FP=347, FN=11, TP=57 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 57 out of 68 failures (83.8%), leaving 11 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $179,400 ($10k per FN + $200 per FP).
### EXP-006: Decision Tree (Configuration B)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration B (Without Type)
- **Features (5):** `Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"class_weight": "balanced", "max_depth": "6", "min_samples_leaf": "10", "min_samples_split": "20"}`
- **Artifact:** [`ml\artifacts\models\EXP-006_decision_tree_config_b.joblib`](file:///ml/artifacts/models/EXP-006_decision_tree_config_b.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.6008** | 0.7548 |
| **ROC-AUC** | **0.9009** | 0.9845 |
| **F1-Score** | **0.4706** | 0.5141 |
| **Recall (Sensitivity)** | **0.8824** | 0.9779 |
| **Precision** | **0.3209** | 0.3487 |
| **Accuracy** | 0.9325 | 0.9374 |
| **False Negatives (FN)** | **8** | 6 |
| **False Positives (FP)** | 127 | 495 |
| **Operational Cost** | **$105,400** | $159,000 |
| **Fit Duration** | 0.055s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1805, FP=127, FN=8, TP=60 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 60 out of 68 failures (88.2%), leaving 8 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $105,400 ($10k per FN + $200 per FP).
### EXP-007: Random Forest (Configuration B)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration B (Without Type)
- **Features (5):** `Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"class_weight": "balanced", "max_depth": "10", "min_samples_leaf": "5", "min_samples_split": "10", "n_estimators": "100"}`
- **Artifact:** [`ml\artifacts\models\EXP-007_random_forest_config_b.joblib`](file:///ml/artifacts/models/EXP-007_random_forest_config_b.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.7483** | 0.9527 |
| **ROC-AUC** | **0.9765** | 0.9982 |
| **F1-Score** | **0.6474** | 0.7845 |
| **Recall (Sensitivity)** | **0.8235** | 0.9742 |
| **Precision** | **0.5333** | 0.6567 |
| **Accuracy** | 0.9695 | 0.9819 |
| **False Negatives (FN)** | **12** | 7 |
| **False Positives (FP)** | 49 | 138 |
| **Operational Cost** | **$129,800** | $97,600 |
| **Fit Duration** | 0.606s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1883, FP=49, FN=12, TP=56 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 56 out of 68 failures (82.3%), leaving 12 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $129,800 ($10k per FN + $200 per FP).
### EXP-008: XGBoost (Configuration B)
- **Date:** 2026-11-10
- **Author:** Senior ML Engineer
- **Milestone:** Stage 2B Baseline Benchmarking
- **Status:** Completed (Baseline Reference)
- **Dataset Configuration:** Configuration B (Without Type)
- **Features (5):** `Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min]`
- **Dataset Checksum:** `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- **Random Seed:** 42
- **Hyperparameters:** `{"learning_rate": "0.05", "max_depth": "5", "n_estimators": "100", "scale_pos_weight": "28.52029520295203"}`
- **Artifact:** [`ml\artifacts\models\EXP-008_xgboost_config_b.joblib`](file:///ml/artifacts/models/EXP-008_xgboost_config_b.joblib)

#### Quantitative Evaluation:
| Metric | Test Set (Holdout) | Train Set |
|---|---|---|
| **PR-AUC** | **0.7734** | 0.9285 |
| **ROC-AUC** | **0.9763** | 0.9975 |
| **F1-Score** | **0.5871** | 0.6708 |
| **Recall (Sensitivity)** | **0.8676** | 0.9926 |
| **Precision** | **0.4436** | 0.5066 |
| **Accuracy** | 0.9585 | 0.9670 |
| **False Negatives (FN)** | **9** | 2 |
| **False Positives (FP)** | 74 | 262 |
| **Operational Cost** | **$104,800** | $72,400 |
| **Fit Duration** | 0.324s | — |

#### Analytical Observations:
- **Confusion Matrix (Test):** TN=1858, FP=74, FN=9, TP=59 out of 2,000 holdout components (68 true failures).
- **Failure Recall:** Caught 59 out of 68 failures (86.8%), leaving 9 unpredicted catastrophic breakdowns.
- **Cost Analysis:** Total cost penalty = $104,800 ($10k per FN + $200 per FP).


---

## Stage 2B Audit Reconciliation & Methodological Governance

**Date:** 2026-11-10  
**Status:** Reconciled Post-Technical Audit  
**Scope:** Stage 2B Baseline Experiments (EXP-001 through EXP-008)  

### 1. Split-Index Cryptographic Hash Reconciliation
- **Train Partition (8,000 samples) SHA-256:** `67471419f2a9a808e27a300667946f2927d7d3b160ea1e4675cabd17cdfc66e8`
- **Test Partition (2,000 samples) SHA-256:** `8e8fef98bdc3f3d6acd0abe46e342ff4fb29d336aaa77143a3e84b2fef10073b`
- *Note:* The authoritative hashes stored in [`ml/artifacts/split_indices.json`](file:///ml/artifacts/split_indices.json) are the 64-character SHA-256 values recorded above. All earlier references to 32-character MD5 hashes in prose are superseded.

### 2. Metric Definition & Algorithmic Implementation
- **PR-AUC Formulation:** The metric reported as PR-AUC is computed via Scikit-learn's `average_precision_score`, which calculates **Average Precision (AP)**:
  $$\text{AP} = \sum_{n} (R_n - R_{n-1}) P_n$$
  This represents the weighted mean of precisions achieved at each recall threshold (avoiding optimistic trapezoidal interpolation artifacts).
- **Comparative Performance Notation:** The performance delta between XGBoost (EXP-004, PR-AUC = 0.7753) and competing baselines is formally stated as:
  - Over Random Forest (EXP-003, PR-AUC = 0.6596): **+11.57 percentage points (pp)**, corresponding to a **+17.54% relative improvement**.
  - Over Decision Tree (EXP-002, PR-AUC = 0.6479): **+12.74 percentage points (pp)**, corresponding to a **+19.66% relative improvement**.

### 3. Operational Cost Matrix Qualification
- **Penalty Constants:** The cost parameters $C_{\text{FN}} = \$10,000$ (catastrophic unpredicted failure) and $C_{\text{FP}} = \$200$ (preventative inspection alarm) originate from PRD Section 5.3 as **illustrative baseline assumptions** (`e.g.`), designed to model order-of-magnitude industrial asymmetry. They are not audited plant accounting constants.

### 4. Decision Threshold Qualification
- All Stage 2B experiments were evaluated at the arbitrary default decision threshold $\tau = 0.5$.
- Reporting EXP-008 ($104,800) as the "lowest cost" reflects its performance at the default threshold; it does **not** represent a globally cost-optimal operating threshold. Threshold calibration ($\tau^*$) across $[0.01, 0.99]$ will be performed out-of-fold during subsequent development.

### 5. Model-Selection Bias & Holdout Contamination Disclosure
- **Crucial Methodological Caveat:** All eight baseline models were evaluated and compared using the identical 2,000-sample test partition (`test_idx`). Selecting candidate architectures based on this test set introduces **model-selection bias (data snooping)**.
- **Status of Stage 2B Metrics:** All test metrics reported for EXP-001 through EXP-008 are designated strictly as **Preliminary Baseline Benchmarks**. They do **not** represent unbiased estimates of final production generalization error.
- **Model Designation:** All AI4I models remain strictly labeled **REFERENCE_ONLY**.
