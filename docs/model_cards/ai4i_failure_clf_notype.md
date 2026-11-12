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

---

## 7. Stage 3 Production Model (v3.0.0 — M2 XGBoost with Platt Scaling)

### A. Production Artifact Details
- **Registry Name:** `ai4i_failure_clf_notype`
- **Model Version:** `3.0.0` (Promoted to `PRODUCTION` stage)
- **Model Family:** M2 XGBoost 2.1.4
- **Configuration:** `NO_TYPE` (Profile: `ai4i_failure_no_type`)
- **Winning Hyperparameters:** `learning_rate=0.05, max_depth=6, min_child_weight=5, colsample_bytree=0.8, subsample=0.8, n_estimators=100, tree_method="hist", random_state=42`
- **Class Balancing:** `scale_pos_weight = N_neg / N_pos = 28.47` (computed on Sub-Train)
- **Artifact Path:** `ml/artifacts/models/production_m2_config_b.joblib`
- **Artifact SHA-256:** `182f3a58a6ef0f2e35a23401cd7214d2699f7887d289e216258d9ac7cac4a8d5`
- **Training Domain:** `REFERENCE_DATASET` (Synthetic AI4I 2020)
- **Reliability Tier:** `REFERENCE_ONLY`

### B. Nested Cross-Validation Performance (Stage 3 Phase 2C: 5 Reps x 5 Folds = 25 Outer Evaluations)
- **Average Precision (PR-AUC):** **0.69961 ± 0.07189** (Min: 0.57430, Max: 0.80379)
  - *Vs. B1 Logistic Regression baseline (0.43522):* **+60.8% relative improvement** (satisfies PRD §10.1.5 AP promotion gate).
- **ROC-AUC:** **0.97198 ± 0.01067** (Min: 0.94409, Max: 0.98686)
- **Brier Score:** **0.016541 ± 0.001894**
  - *Vs. B1 Logistic Regression baseline (0.024733):* **-33.1% error reduction** (satisfies PRD §10.1.5 Brier promotion gate).
- **Brier Skill Score (BSS):** **0.49469 ± 0.05673**
- **Expected Calibration Error (ECE):** **0.00822 ± 0.00205**
- **Optimal Threshold ($\tau^*$):** Mean = 0.0344, Min = 0.005, Max = 0.125
- **Operational Cost at $\tau^*$ (50:1 cost ratio):** **$74,432.00 ± $25,478.53**

### C. Confirmed Historical Benchmark Test Evaluation (N=2,000, 68 Failures, Hash `8e8fef98...`)
- **Average Precision (PR-AUC):** **0.73822**
- **ROC-AUC:** **0.97159**
- **Brier Score:** **0.014970**
- **Brier Skill Score:** **0.54421**
- **Optimal Decision Threshold:** $\tau^* = \mathbf{0.0100}$ (Bayes theoretical = 0.01961)
- **Operational Decision Metrics at $\tau^* = 0.0100$:**
  - True Positives (TP): 65
  - False Positives (FP): 212
  - False Negatives (FN): 3
  - True Negatives (TN): 1,720
  - **Recall:** **0.9559** (65 of 68 failures successfully detected)
  - **Precision:** **0.2347**
  - **F1-Score:** **0.3768**
  - **Illustrative Operational Cost:** **$72,400.00** ($3 \times \$10,000 + 212 \times \$200$)

### D. Calibration & Explainability Verification
- **Platt Sigmoid Calibrator:** Fitted on disjoint Calibration partition ($N = 1,200$, $N_{\text{cal,pos}} = 41 \ge 25$).
  - Slope ($w$): $0.9701 \pm 0.1084$
  - Intercept ($c$): $-2.1979 \pm 0.2407$
- **TreeSHAP Explainability (AC-XAI-1, AC-XAI-2):**
  - Margin additivity verified: $\max | \sum \phi_j + \phi_0 - f(x) | = 1.19 \times 10^{-6} \le 10^{-5}$ tolerance.
  - Non-Causality Notice: Feature attributions describe model behaviour, not physical causation.
