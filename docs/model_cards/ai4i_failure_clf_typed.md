# Model Card: ai4i_failure_clf_typed

## 1. Model Details
- **Model Name:** `ai4i_failure_clf_typed`
- **Model Version:** `1.0.0`
- **Pipeline:** `A` (Machine Failure Binary Classification)
- **Configuration:** `WITH_TYPE` (Profile: `ai4i_failure_with_type@1.0.0`)
- **Model Architecture:** XGBoost Classifier (`n_estimators=100, max_depth=3, learning_rate=0.05, scale_pos_weight=28.49`)
- **Preprocessing Pipeline:** One-hot encoding for `Type` + Physics feature engineering (`IndustrialFeatureEngineer`) + Standard scaling
- **Training Domain:** `REFERENCE_DATASET` (AI4I 2020 Predictive Maintenance Dataset, synthetic)
- **Artifact Path:** `ml/artifacts/models/EXP-004_xgboost_config_a.joblib`

## 2. Input Feature Schema
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

## 3. Reference Dataset Evaluation (Test Set, N=2,000)
Evaluation conducted strictly under the pre-registered stratified evaluation protocol (seed=42):

| Metric | Reference Value | 95% Bootstrap CI | Notes |
| :--- | :--- | :--- | :--- |
| **PR-AUC (Average Precision)** | **0.772** | [0.705, 0.835] | Imbalanced ranking metric |
| **ROC-AUC** | **0.948** | [0.920, 0.972] | Discrimination ability |
| **Recall (at $\tau=0.45$)** | **0.750** | [0.645, 0.850] | Positive failure detection rate |
| **Precision (at $\tau=0.45$)** | **0.730** | [0.625, 0.830] | Operational precision |
| **Brier Score** | **0.020** | [0.014, 0.027] | Probability calibration error |

## 4. Customer-Specific Validation
- **Status:** **None performed**
- **Reliability Tier:** `REFERENCE_ONLY`
- **Notice:** This model has been evaluated solely on the public AI4I 2020 synthetic benchmark. It has **not** been validated on customer industrial equipment.

## 5. Limitations & Intended Use
- **Advisory Only:** Outputs represent synthetic benchmark scores, not real machine failure probabilities.
- **Calibration Scope:** The model outputs raw XGBoost probabilities without post-hoc calibrators (Platt/isotonic).
- **Provisional Operational Threshold:** The threshold $\tau = 0.45$ is a provisional baseline setting reflecting an asymmetric operational cost penalty ratio ($C_{\text{FN}}/C_{\text{FP}} = 50$). Empirical threshold optimization is scheduled for the Stage 3 nested evaluation protocol.
- **Rule Recovery vs Generalization:** Because AI4I is synthetic and its data generation equations depend partly on product variant, variant sensitivity reflects benchmark rule recovery, not transferable operational benefit.
- **Semantics Requirement:** Using this model requires the customer to assert that their column represents the AI4I manufacturing quality variant. The system never infers or imputes missing types.
- **Explainability Disclaimer:** Feature attributions describe model scoring behavior, not physical causality.

