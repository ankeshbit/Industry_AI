# Model Card: ai4i_failure_clf_typed

## 1. Model Details
- **Model Name:** `ai4i_failure_clf_typed`
- **Model Version:** `1.0.0-baseline`
- **Experiment ID:** `EXP-004` (Stage 2B Baseline)
- **Pipeline:** `A` (Machine Failure Binary Classification)
- **Configuration:** `WITH_TYPE` (Profile: `ai4i_failure_with_type@1.0.0`)
- **Model Architecture:** XGBoost Classifier (`n_estimators=100, max_depth=5, learning_rate=0.05, scale_pos_weight=28.520295, subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=42`)
- **Preprocessing Pipeline:** `ColumnTransformer(transformers=[('numeric', StandardScaler(), ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']), ('categorical', OneHotEncoder(drop='first', sparse_output=False), ['Type'])])`
- **Training Domain:** `REFERENCE_DATASET` (AI4I 2020 Predictive Maintenance Dataset, synthetic)
- **Training Partition:** 8,000 observations (271 failures, 3.39%), Train index hash: `67471419f2a9a808e27a300667946f2927d7d3b160ea1e4675cabd17cdfc66e8`
- **Historical Test Partition:** 2,000 observations (68 failures, 3.40%), Test index hash: `8e8fef98bdc3f3d6acd0abe46e342ff4fb29d336aaa77143a3e84b2fef10073b`
- **Artifact Path:** `ml/artifacts/models/EXP-004_xgboost_config_a.joblib`
- **Artifact SHA-256:** `a256f0aeaa4729dd009fb3a3d5fbc8448cffa427bd28e69cb615170347141e81`

## 2. Mandatory Evaluation Status Disclosure
> These models represent historical Stage 2B reference experiments. The original test partition was evaluated during baseline model comparison and is not an independent confirmatory evaluation set.

## 3. Input Feature Schema
Requires 5 numeric operating state features plus confirmed categorical variant:
1. `Type` (categorical variant: `L`, `M`, `H` - requires explicit user semantics assertion `W_TYPE_SEMANTICS_ASSERTED`)
2. `Air temperature [K]` (canonical: Kelvin, allowed: K, degC, degF)
3. `Process temperature [K]` (canonical: Kelvin, allowed: K, degC, degF)
4. `Rotational speed [rpm]` (canonical: rpm, allowed: rpm, rad_s, Hz)
5. `Torque [Nm]` (canonical: Nm, allowed: Nm, lbf_ft)
6. `Tool wear [min]` (canonical: min, allowed: min, h)

**Quarantined / Forbidden Features:**
- `machine_failure` (ground truth label)
- Failure modes: `TWF`, `HDF`, `PWF`, `OSF`, `RNF`
- Identifiers: `UDI`, `Product ID`

## 4. Historical Test Partition Evaluation (N=2,000, 68 Failures)
All figures below are forensic empirical values extracted directly from `ml/artifacts/baseline_results.json` and verified against live execution of `ml/artifacts/models/EXP-004_xgboost_config_a.joblib`:

### A. Threshold-Independent Ranking Metrics
- **PR-AUC (Average Precision):** **0.7753**
- **ROC-AUC:** **0.9730**
- **Brier Score (Raw Model Output):** **0.0309** (uncalibrated logistic link probabilities)

### B. Threshold-Dependent Operational Metrics
- **At Standard Decision Threshold ($\tau = 0.50$):**
  - Confusion Matrix: True Negatives = 1,857, False Positives = 75, False Negatives = 10, True Positives = 58
  - Accuracy: 0.9575
  - Precision: 0.4361
  - Recall: 0.8529
  - F1-Score: 0.5771
  - Total Operational Cost ($C_{\text{FN}}=\$10,000, C_{\text{FP}}=\$200$): **$115,000**
- **At Provisional Heuristic Threshold ($\tau = 0.45$):**
  - Confusion Matrix: True Negatives = 1,845, False Positives = 87, False Negatives = 9, True Positives = 59
  - Precision: 0.4041
  - Recall: 0.8676
  - F1-Score: 0.5514
  - Total Operational Cost ($C_{\text{FN}}=\$10,000, C_{\text{FP}}=\$200$): **$107,400**

## 5. Customer-Specific Validation
- **Status:** **None performed**
- **Reliability Tier:** `REFERENCE_ONLY`
- **Notice:** This model has been evaluated solely on the public AI4I 2020 synthetic benchmark. It has **not** been validated on customer industrial equipment.

## 6. Limitations & Methodological Caveats
- **Uncalibrated Baseline:** The model outputs raw XGBoost probabilities (logistic sigmoid link on tree margin sums) without post-hoc calibrators (Platt/isotonic).
- **Single-Split Protocol:** This baseline was trained on a single 80/20 train/test split. Repeated cross-validation (§10.1.4) was not executed in Stage 2B.
- **Rule Recovery vs Generalization:** Because AI4I is synthetic and its data generation equations depend partly on product variant, variant sensitivity reflects benchmark rule recovery, not transferable operational benefit.
- **Semantics Requirement:** Using this model requires the customer to assert that their column represents the AI4I manufacturing quality variant. The system never infers or imputes missing types.
- **Provisional Operational Threshold:** The threshold $\tau = 0.45$ is an empirical heuristic balancing precision and recall on uncalibrated baseline scores. Decision-theoretic cost-optimal thresholding requires genuine probability calibration scheduled for Stage 3.
- **Explainability Disclaimer:** Feature attributions describe model scoring behavior on the underlying tree margin, not physical causality.
