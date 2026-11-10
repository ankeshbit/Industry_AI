# Model Card: ai4i_failure_clf_notype

## 1. Model Details
- **Model Name:** `ai4i_failure_clf_notype`
- **Model Version:** `1.0.0-baseline`
- **Experiment ID:** `EXP-008` (Stage 2B Baseline)
- **Pipeline:** `A` (Machine Failure Binary Classification)
- **Configuration:** `NO_TYPE` (Profile: `ai4i_failure_no_type@1.0.0`)
- **Model Architecture:** XGBoost Classifier (`n_estimators=100, max_depth=5, learning_rate=0.05, scale_pos_weight=28.520295, subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=42`)
- **Preprocessing Pipeline:** `ColumnTransformer(transformers=[('numeric', StandardScaler(), ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]'])])`
- **Training Domain:** `REFERENCE_DATASET` (AI4I 2020 Predictive Maintenance Dataset, synthetic)
- **Training Partition:** 8,000 observations (271 failures, 3.39%), Train index hash: `67471419f2a9a808e27a300667946f2927d7d3b160ea1e4675cabd17cdfc66e8`
- **Historical Test Partition:** 2,000 observations (68 failures, 3.40%), Test index hash: `8e8fef98bdc3f3d6acd0abe46e342ff4fb29d336aaa77143a3e84b2fef10073b`
- **Artifact Path:** `ml/artifacts/models/EXP-008_xgboost_config_b.joblib`
- **Artifact SHA-256:** `4431f0c417aa54d5789b064c98ec3c6a861b534f7687ba23c005802338f2b7bd`

## 2. Mandatory Evaluation Status Disclosure
> These models represent historical Stage 2B reference experiments. The original test partition was evaluated during baseline model comparison and is not an independent confirmatory evaluation set.

## 3. Input Feature Schema
Strictly requires 5 numeric operating state features. No product type or variant feature is used or required.
1. `Air temperature [K]` (canonical: Kelvin, allowed: K, degC, degF)
2. `Process temperature [K]` (canonical: Kelvin, allowed: K, degC, degF)
3. `Rotational speed [rpm]` (canonical: rpm, allowed: rpm, rad_s, Hz)
4. `Torque [Nm]` (canonical: Nm, allowed: Nm, lbf_ft)
5. `Tool wear [min]` (canonical: min, allowed: min, h)

**Quarantined / Forbidden Features:**
- `machine_failure` (ground truth label)
- Failure modes: `TWF`, `HDF`, `PWF`, `OSF`, `RNF`
- Identifiers: `UDI`, `Product ID`
- `Type` / `Product type`

## 4. Historical Test Partition Evaluation (N=2,000, 68 Failures)
All figures below are forensic empirical values extracted directly from `ml/artifacts/baseline_results.json` and verified against live execution of `ml/artifacts/models/EXP-008_xgboost_config_b.joblib`:

### A. Threshold-Independent Ranking Metrics
- **PR-AUC (Average Precision):** **0.7734**
- **ROC-AUC:** **0.9763**
- **Brier Score (Raw Model Output):** **0.0317** (uncalibrated logistic link probabilities)

### B. Threshold-Dependent Operational Metrics
- **At Standard Decision Threshold ($\tau = 0.50$):**
  - Confusion Matrix: True Negatives = 1,858, False Positives = 74, False Negatives = 9, True Positives = 59
  - Accuracy: 0.9585
  - Precision: 0.4436
  - Recall: 0.8676
  - F1-Score: 0.5871
  - Total Operational Cost ($C_{\text{FN}}=\$10,000, C_{\text{FP}}=\$200$): **$104,800**
- **At Provisional Heuristic Threshold ($\tau = 0.45$):**
  - Confusion Matrix: True Negatives = 1,845, False Positives = 87, False Negatives = 8, True Positives = 60
  - Precision: 0.4082
  - Recall: 0.8824
  - F1-Score: 0.5581
  - Total Operational Cost ($C_{\text{FN}}=\$10,000, C_{\text{FP}}=\$200$): **$97,400**

## 5. Customer-Specific Validation
- **Status:** **None performed**
- **Reliability Tier:** `REFERENCE_ONLY`
- **Notice:** This model has been evaluated solely on the public AI4I 2020 synthetic benchmark. It has **not** been validated on customer industrial equipment.

## 6. Limitations & Methodological Caveats
- **Uncalibrated Baseline:** The model outputs raw XGBoost probabilities (logistic sigmoid link on tree margin sums) without post-hoc calibrators (Platt/isotonic).
- **Single-Split Protocol:** This baseline was trained on a single 80/20 train/test split. Repeated cross-validation (§10.1.4) was not executed in Stage 2B.
- **Provisional Operational Threshold:** The threshold $\tau = 0.45$ is an empirical heuristic balancing precision and recall on uncalibrated baseline scores. Decision-theoretic cost-optimal thresholding requires genuine probability calibration scheduled for Stage 3.
- **Point-in-Time Assessment:** Predictions apply strictly to snapshot operating states; no remaining useful life (RUL) or time-to-failure horizon is implied.
- **Operating Envelopes:** Inputs outside the reference domain ($[\min - 0.10 \cdot \text{range}, \max + 0.10 \cdot \text{range}]$) represent extrapolation and trigger out-of-distribution (OOD) warnings or run refusal.
- **Explainability Disclaimer:** SHAP drivers and feature attributions describe algorithmic score dependencies on the underlying tree margin, not physical causation.
