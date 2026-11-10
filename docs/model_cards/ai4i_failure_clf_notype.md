# Model Card: ai4i_failure_clf_notype

## 1. Model Details
- **Model Name:** `ai4i_failure_clf_notype`
- **Model Version:** `1.0.0`
- **Pipeline:** `A` (Machine Failure Binary Classification)
- **Configuration:** `NO_TYPE` (Profile: `ai4i_failure_no_type@1.0.0`)
- **Model Architecture:** XGBoost Classifier (`n_estimators=100, max_depth=3, learning_rate=0.05, scale_pos_weight=28.49`)
- **Preprocessing Pipeline:** Robust physics feature engineering (`IndustrialFeatureEngineer`) + Standard scaling (`ColumnTransformer`)
- **Training Domain:** `REFERENCE_DATASET` (AI4I 2020 Predictive Maintenance Dataset, synthetic)
- **Artifact Path:** `ml/artifacts/models/EXP-008_xgboost_config_b.joblib`

## 2. Input Feature Schema
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

## 3. Reference Dataset Evaluation (Test Set, N=2,000)
Evaluation conducted strictly under the pre-registered stratified evaluation protocol (seed=42):

| Metric | Reference Value | 95% Bootstrap CI | Notes |
| :--- | :--- | :--- | :--- |
| **PR-AUC (Average Precision)** | **0.760** | [0.690, 0.820] | Primary imbalanced ranking metric |
| **ROC-AUC** | **0.945** | [0.915, 0.970] | Discrimination ability |
| **Recall (at $\tau=0.45$)** | **0.735** | [0.630, 0.835] | Positive failure detection rate |
| **Precision (at $\tau=0.45$)** | **0.720** | [0.615, 0.820] | Operational precision |
| **Brier Score** | **0.021** | [0.015, 0.028] | Probability calibration error |

## 4. Customer-Specific Validation
- **Status:** **None performed**
- **Reliability Tier:** `REFERENCE_ONLY`
- **Notice:** This model has been evaluated solely on the public AI4I 2020 synthetic benchmark. It has **not** been validated on customer industrial equipment.

## 5. Limitations & Intended Use
- **Advisory Only:** The output probability represents a synthetic reference model score, not the physical failure frequency of real-world machines.
- **Calibration Scope:** The model outputs raw XGBoost probabilities (logistic sigmoid link on tree margin sums) without post-hoc calibrators (Platt/isotonic).
- **Provisional Operational Threshold:** The threshold $\tau = 0.45$ is a provisional baseline setting reflecting an asymmetric operational cost penalty ratio ($C_{\text{FN}}/C_{\text{FP}} = 50$). Empirical threshold optimization is scheduled for the Stage 3 nested evaluation protocol.
- **Independent Rows:** Predictions apply strictly to snapshot operating states; no remaining useful life (RUL) or time-to-failure horizon is implied.
- **Operating Envelopes:** Inputs outside the reference domain ($[min - 0.10 \cdot range, max + 0.10 \cdot range]$) represent extrapolation and will trigger out-of-distribution (OOD) warnings or run refusal.
- **Explainability Disclaimer:** SHAP drivers and feature attributions describe algorithmic score dependencies, not physical causation.

