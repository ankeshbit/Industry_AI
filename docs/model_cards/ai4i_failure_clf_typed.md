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

---

## 7. Stage 3 Production Model (v3.0.0 — M2 XGBoost with Platt Scaling)

### A. Production Artifact Details
- **Registry Name:** `ai4i_failure_clf_typed`
- **Model Version:** `3.0.0` (Promoted to `PRODUCTION` stage)
- **Model Family:** M2 XGBoost 2.1.4
- **Configuration:** `WITH_TYPE` (Profile: `ai4i_failure_with_type`)
- **Winning Hyperparameters:** `learning_rate=0.1, max_depth=4, min_child_weight=1, colsample_bytree=1.0, subsample=0.7, n_estimators=74, tree_method="hist", random_state=42`
- **Class Balancing:** `scale_pos_weight = N_neg / N_pos = 28.47` (computed on Sub-Train)
- **Artifact Path:** `ml/artifacts/models/production_m2_config_a.joblib`
- **Artifact SHA-256:** `caa17fdb6c6871afdd87c5bd05d1ad5bc5a568e2c94877935bd242fbcb16824a`
- **Training Domain:** `REFERENCE_DATASET` (Synthetic AI4I 2020)
- **Reliability Tier:** `REFERENCE_ONLY`

### B. Nested Cross-Validation Performance (Stage 3 Phase 2C: 5 Reps x 5 Folds = 25 Outer Evaluations)
- **Average Precision (PR-AUC):** **0.71723 ± 0.06152** (Min: 0.60361, Max: 0.82641)
  - *Vs. B1 Logistic Regression baseline (0.44038):* **+62.9% relative improvement** (satisfies PRD §10.1.5 AP promotion gate).
- **ROC-AUC:** **0.97147 ± 0.00968** (Min: 0.95385, Max: 0.98663)
- **Brier Score:** **0.016128 ± 0.001671**
  - *Vs. B1 Logistic Regression baseline (0.024738):* **-34.8% error reduction** (satisfies PRD §10.1.5 Brier promotion gate).
- **Brier Skill Score (BSS):** **0.50723 ± 0.05086**
- **Expected Calibration Error (ECE):** **0.00858 ± 0.00259**
- **Optimal Threshold ($\tau^*$):** Mean = 0.0308, Min = 0.005, Max = 0.110
- **Operational Cost at $\tau^*$ (50:1 cost ratio):** **$72,856.00 ± $23,740.93**

### C. Confirmed Historical Benchmark Test Evaluation (N=2,000, 68 Failures, Hash `8e8fef98...`)
- **Average Precision (PR-AUC):** **0.76165**
- **ROC-AUC:** **0.96881**
- **Brier Score:** **0.014822**
- **Brier Skill Score:** **0.54870**
- **Optimal Decision Threshold:** $\tau^* = \mathbf{0.0100}$ (Bayes theoretical = 0.01961)
- **Operational Decision Metrics at $\tau^* = 0.0100$:**
  - True Positives (TP): 65
  - False Positives (FP): 236
  - False Negatives (FN): 3
  - True Negatives (TN): 1,696
  - **Recall:** **0.9559** (65 of 68 failures successfully detected)
  - **Precision:** **0.2159**
  - **F1-Score:** **0.3523**
  - **Illustrative Operational Cost:** **$77,200.00** ($3 \times \$10,000 + 236 \times \$200$)

### D. Calibration & Explainability Verification
- **Platt Sigmoid Calibrator:** Fitted on disjoint Calibration partition ($N = 1,200$, $N_{\text{cal,pos}} = 41 \ge 25$).
  - Slope ($w$): $0.9502 \pm 0.1068$
  - Intercept ($c$): $-2.2492 \pm 0.2384$
- **TreeSHAP Explainability (AC-XAI-1, AC-XAI-2):**
  - Margin additivity verified: $\max | \sum \phi_j + \phi_0 - f(x) | = 2.86 \times 10^{-6} \le 10^{-5}$ tolerance.
  - Non-Causality Notice: Feature attributions describe model behaviour, not physical causation.

