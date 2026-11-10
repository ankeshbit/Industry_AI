# INDUSTRIA AI — Stage 3 Evaluation Architecture Specification

**Document Status:** FINALIZED — READY FOR STAGE 3 IMPLEMENTATION (Architecture v1.4.2)  
**Authoritative Reference:** Root `PRD.md` v1.2 (§10.1.3–§10.1.5, §11.1, §13.5, §18.3, AC-FP-5, AC-XAI-1, AC-XAI-2)  
**Supporting Analysis:** `docs/STAGE_3_EVALUATION_GAP_ANALYSIS.md`, `docs/ML_EXPERIMENT_LOG.md`  
**Target Milestone:** Stage 3 Modeling, Baseline Re-Evaluation & Candidate Promotion Pipeline  
**Methodological Governance Notice:** This document constitutes an approved, frozen evaluation specification and governance contract. It does not constitute empirical evidence or performance validation, which can only be established after the experimental pipeline executes.

---

## 1. Architectural Overview & Design Objectives

This specification defines the authoritative, implementation-ready machine learning evaluation, calibration, and threshold-optimization architecture for Stage 3 of INDUSTRIA AI. It translates the requirements of PRD v1.2 into an unambiguous, leak-free, reproducible experimental pipeline.

### Core Architectural Invariants:
1. **Strict Data Leakage Prevention:** Every transformation, imputer, scaler, feature-engineering step, calibrator, and decision threshold is fitted strictly on designated training and validation partitions.
2. **Preservation of the Locked Historical Test Partition:** The Stage 2B test partition ($N=2,000$) is preserved as an immutable historical benchmark. It is never used for hyperparameter selection, calibration fitting, or threshold optimization.
3. **Parity Between Baselines and Candidates (§10.1.5):** All candidate models and baseline models evaluate under identical partition indices, identical search budget rules, identical calibration procedures, and identical cost metrics.
4. **Decoupled Objective Optimization:** Model discrimination (PR-AUC), probability calibration (Brier score, ECE), and decision thresholding (operational cost) are treated as distinct, sequentially optimized objectives.

---

## 2. Dataset and Partition Governance

```
========================================================================================
FULL RAW AI4I 2020 DATASET (N = 10,000 observations | 339 Failures, 3.39%)
Verified SHA-256: dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e
========================================================================================
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      ▼                                                             ▼
LOCKED TEST PARTITION (20%)                                DEVELOPMENT PARTITION (80%)
Total: 2,000 rows | Failures: 68 (3.40%)                    Total: 8,000 rows | Failures: 271 (3.3875%)
Index Hash: 8e8fef98bdc3f3d6acd0abe46e342ff4...             Index Hash: 67471419f2a9a808e27a300667946...
ROLE: Historical Benchmark (Exploratory / Non-Independent)  ROLE: Nested Cross-Validation Pool
                                                                    │
                                     ┌──────────────────────────────┴──────────────────────────────┐
                                     ▼                                                             ▼
                          OUTER CV FOLDS (K_outer = 5)                                  INNER CV PARTITIONS
                          Estimates Procedure Generalization                            Model Selection & Threshold Tuning
```

### 2.1 Deterministic Index Persistence
- Split indices are serialized to immutable JSON artifacts with cryptographic SHA-256 validation:
  - `ml/artifacts/split_indices.json`: Stores `train_indices` ($N=8,000$) and `test_indices` ($N=2,000$).
  - `ml/artifacts/nested_cv_indices.json`: Stores the outer and inner fold index assignments across all repetitions.
- Prior to executing any pipeline, the loader asserts:
  $$\text{SHA-256}(\text{raw\_dataset}) == \text{AI4I\_SHA256\_CHECKSUM}$$
  $$\text{SHA-256}(\text{test\_indices}) == \text{LOCKED\_TEST\_HASH}$$
- Both AI4I configurations (Configuration A: `WITH_TYPE` and Configuration B: `NO_TYPE`) read the exact same index file, satisfying PRD §10.1.5 item 1.

### 2.2 Repeated Nested Stratified Cross-Validation Protocol
PRD §10.1.4 explicitly mandates:
> *"Validate and split (stratified, locked test) → repeated stratified CV with a fixed search budget → choose by CV PR-AUC → calibrate (isotonic or Platt) on the validation partition → choose the threshold by a configured cost ratio (placeholder, Appendix E) → evaluate once on the test partition with CIs, curves and SHAP summary → registration gate."*

To satisfy this requirement literally without silent reinterpretation:
- **Repetition Specification:** The primary evaluation architecture executes **$R = 5$ repetitions of a $5 \times 4$ Nested Stratified Cross-Validation**:
  - **Outer Loop ($K_{\text{outer}} = 5$ folds per repetition, total $R \times K_{\text{outer}} = 25$ outer evaluations):**
    - In each repetition $r \in \{0, 1, 2, 3, 4\}$, the 8,000 development rows are partitioned into 5 stratified outer test folds ($N_{\text{outer\_test}} = 1,600$, $\approx 54$ failures) and 5 outer training sets ($N_{\text{outer\_train}} = 6,400$, $\approx 217$ failures).
    - Seed Strategy: Repetition $r$ is initialized with deterministic seed $42 + r \cdot 100$.
    - Within each repetition, the 5 outer test folds are pairwise disjoint and partition the 8,000 rows exactly once.
  - **Inner Loop ($K_{\text{inner}} = 4$):**
    - Executed strictly within the **Sub-Train pool ($70\%$, $N_{\text{sub\_train}} = 4,480$)** of each outer training partition ($N_{\text{outer\_train}} = 6,400$), fully isolating the Calibration ($15\%$) and Threshold ($15\%$) pools from hyperparameter selection.
    - 4 inner stratified folds ($N_{\text{inner\_train}} = 3,360$, $N_{\text{inner\_val}} = 1,120$).
    - Optimizes hyperparameter configurations and preprocessing selection under a pre-declared, fixed search budget using inner validation PR-AUC as the selection criterion.
    - The selected optimal configuration $\theta_k^*$ is refitted once on the complete Sub-Train pool ($N=4,480$) to produce base estimator $M_k$.
- **Statistical Dependence and Reporting Protocol:**
  - **The 25 outer evaluations are NOT independent experiments.** Folds within a repetition share $75\%$ training overlap; folds across repetitions share $\approx 80\%$ training overlap and evaluate overlapping test instances. Treating $R \times K = 25$ as 25 independent samples or using $df = 24$ in naive $t$-tests causes severe Type I error inflation.
  - **Primary Reporting is Descriptive:** The evaluation reports:
    1. Per-fold metrics for each outer evaluation $(r, k)$.
    2. Repetition-level means and spread: $\bar{m}_r = \frac{1}{5} \sum_{k=1}^5 m_{r, k}$ and $s_{\text{rep}} = \text{std}(\bar{m}_r)$.
    3. Overall grand mean across repetitions: $\bar{m} = \frac{1}{R} \sum_{r=1}^R \bar{m}_r$.
    4. Full outer fold observed dispersion range: $[\min m_{r,k}, \max m_{r,k}]$.
    5. Paired model differences $\bar{d} = \bar{m}_A - \bar{m}_B$ with fold difference ranges.
  - **Exploratory Hypothesis Testing:** Any resampled $t$-test (Nadeau & Bengio, 2003; Bouckaert & Frank, 2004) is classified strictly as an **exploratory heuristic indicator**, not inferential proof of statistical superiority. Formal confirmatory claims are never asserted from repeated CV alone; they are strictly restricted to an unseen external dataset.
- **Alternative Fast Benchmark Protocol:**
  - A single $5 \times 4$ nested CV execution ($R=1$, seed 42, exactly 5 outer evaluations) is supported as a fast development benchmark. However, because PRD §10.1.4 specifies repeated CV, single-run execution is formally classified as a **temporary engineering deviation requiring approval** before candidate promotion.

---

## 3. Baseline and Candidate Parity Protocol (§10.1.3 & §10.1.5)

PRD §10.1.5 mandates that candidate models must beat the baseline on PR-AUC and Brier score under an identical experimental protocol.

### 3.1 Model Ladder (§10.1.3 Authoritative Specification)
The evaluation architecture executes the identical nested CV ladder across all algorithms defined in PRD §10.1.3:
1. **B0: Majority-Class / Prevalence Predictor:** Trivial reference floor; predicts constant empirical base rate $\bar{y}_{\text{sub\_train}}$ to demonstrate why classification accuracy is deceptive on imbalanced data.
2. **B1: Logistic Regression:** $L_2$ regularization, class-weighted, standardized numeric features; interpretable linear benchmark.
3. **M1: Random Forest:** Class-weighted, non-linear interaction benchmark.
4. **M2: XGBoost:** `scale_pos_weight` tuned to class imbalance ratio, early stopping on inner validation; primary gradient-boosted benchmark.
5. **Optional Candidates (Stage 3):** LightGBM, CatBoost, or small Multi-Layer Perceptrons (MLP). Promoted only if justified in the model card by non-overlapping confidence intervals.

#### 3.1.1 Resolution of Decision Tree ("B2") Status
- **PRD Specification Authority:** PRD §10.1.3 explicitly defines the model ladder as B0, B1, M1, M2, and Optional. The term "Decision Tree" does not appear in PRD §10.1.3 or anywhere in `PRD.md` v1.2.
- **Historical Benchmark Provenance:** A standalone Decision Tree was trained as an exploratory benchmark (`EXP-002` / `EXP-006`) during historical Stage 2B baseline runs.
- **Formal Exclusion Justification:** Decision Tree is **not a required Stage 3 candidate** and is excluded from the required evaluation ladder with documented justification:
  1. It is omitted from authoritative PRD §10.1.3.
  2. Single unpruned decision trees exhibit high variance and poor rank ordering on rare-event tabular datasets ($3.39\%$ failure rate).
  3. Its modeling intent (capturing non-linear interactions) is strictly superseded by M1 (Random Forest).
  Unless the PRD is formally amended, Decision Tree remains an archived historical Stage 2B reference only.

### 3.2 Parity Rules and Interpretation of "Fixed Search Budget" (§10.1.4 & §10.1.5)
- **Authoritative PRD Specification:**
  - PRD §10.1.4 mandates: *"repeated stratified CV with a fixed search budget → choose by CV PR-AUC"*.
  - PRD §10.1.5 mandates: *"Unfair configuration comparison: Both AI4I configurations use identical splits, folds, search budgets and metrics (§10.1.5)"* and *"2. Same procedure: identical algorithm ladder, search budgets, calibration method, threshold rule and metrics."*
- **Clarification of Budget Interpretation:**
  1. **Cross-Configuration Invariance:** The PRD mandate for identical search budgets strictly requires that Configuration A (`WITH_TYPE`) and Configuration B (`NO_TYPE`) evaluate under the **identical search space, identical candidate count, and identical random seeds per algorithm family** (LR: 6 candidates for both; RF: 24 candidates for both; XGBoost: 20 candidates for both).
  2. **Bounded Search Per Algorithm Family:** Per algorithm family, the search budget is a **predetermined, bounded, finite count of candidate configurations** pre-declared prior to experimental execution, preventing open-ended or adaptive search expansion.
  3. **Non-Uniformity Across Algorithm Families:** Candidate counts differ across algorithm families (LR=6, RF=24, XGB=20) because the dimensionality of their hyperparameter spaces differs fundamentally (1D for Logistic Regression regularization; 3D for Random Forest depth/split/features; 5D for XGBoost). The architecture does **NOT** claim equal computational or candidate budgets across different algorithm families.
- **Identical Partition Assignments:** Candidates and baselines evaluate on the exact same repeated CV fold assignments stored in `nested_cv_indices.json`.
- **Identical Metrics:** Evaluated against identical primary metrics (PR-AUC, Brier score, Brier Skill Score, operational cost).

### 3.3 Pre-Declared Hyperparameter Search Spaces and Search Budgets

> **Governance Notice:** The requirement for a fixed search budget and selection by CV PR-AUC is an authoritative PRD §10.1.4 requirement. The specific hyperparameter candidate grids, distributions, and candidate counts ($6, 24, 20$) defined below are **architectural implementation specifications**, designed to balance parameter coverage against computational feasibility in nested cross-validation.

| Model | Hyperparameters & Candidate Search Grid | Search Strategy | Total Candidates | Fixed Seed | Inner-CV Selection & Tie-Breaking Rules | Early Stopping & Computational Guards |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **B0: Prevalence Predictor** | None (constant predictor $\hat{p} = \bar{y}_{\text{sub\_train}}$) | Deterministic | $1$ | N/A | Trivial reference floor; no hyperparameter tuning. | Analytical base rate computation; zero tuning overhead. |
| **B1: Logistic Regression** | `C`: $\{0.001, 0.01, 0.1, 1.0, 10.0, 100.0\}$ ($6$ values)<br>`penalty`: fixed `l2`<br>`solver`: fixed `lbfgs`<br>`class_weight`: fixed `balanced`<br>`max_iter`: fixed $1,000$ | Deterministic Grid Search | $6$ | 42 | **Selection:** Mean inner PR-AUC across 4 folds.<br>**Tie-Breaker:** Stronger regularization (smaller $C$). | Standardized numeric features via `StandardScaler` inside each inner fold; fast convergence ($6 \times 4 = 24$ fits). |
| **M1: Random Forest** | `n_estimators`: fixed $100$<br>`max_depth`: $\{5, 8, 12, \text{None}\}$ ($4$ values)<br>`min_samples_split`: $\{2, 5, 10\}$ ($3$ values)<br>`max_features`: $\{\text{"sqrt"}, \text{"log2"}\}$ ($2$ values)<br>`class_weight`: fixed `balanced` | Deterministic Grid Search | $24$ | 42 | **Selection:** Mean inner PR-AUC across 4 folds.<br>**Tie-Breaker:** Simpler model (lower `max_depth`, higher `min_samples_split`, then lower `max_features`). | Parallelized execution (`n_jobs=-1`); bounded depth prevents infinite tree expansion ($24 \times 4 = 96$ fits). |
| **M2: XGBoost** | `n_estimators`: fixed upper bound $T_{\text{max}} = 300$<br>`max_depth`: $\{3, 4, 5, 6\}$<br>`learning_rate`: $\{0.01, 0.03, 0.05, 0.1\}$<br>`subsample`: $\{0.7, 0.8, 1.0\}$<br>`colsample_bytree`: $\{0.7, 0.8, 1.0\}$<br>`min_child_weight`: $\{1, 3, 5\}$<br>`scale_pos_weight`: fixed $\frac{N_{\text{neg}}}{N_{\text{pos}}}$ (computed on inner train) | Bounded Random Search (sampled from discrete grid) | $20$ | 42 | **Selection:** Mean inner canonical PR-AUC (`average_precision_score`) across 4 folds.<br>**Tie-Breaker:** Lower `learning_rate`, then lower `max_depth`, then lower `min_child_weight`. | **Early Stopping:** Evaluated on inner validation fold ($20 \times 4 = 80$ fits). Native `aucpr` monitors stopping counter (`early_stopping_rounds=20`, max 300 trees); canonical `average_precision_score` scores validation predictions for candidate ranking. Detailed in §3.3.1. |

#### 3.3.1 XGBoost Inner Early Stopping, Metric Consistency, and Final Refit Protocol
To guarantee mathematical consistency, reproducible stopping, and leak-free execution across all 20 XGBoost candidate configurations:

1. **Fixed Maximum Iteration Bound:**
   Every XGBoost candidate operates with an immutable upper bound of $T_{\text{max}} = 300$ boosting trees. No candidate may exceed 300 rounds under any condition.
2. **PR-AUC Metric Distinction and Canonical Candidate Scoring:**
   - *Technical Audit of Pinned XGBoost (v2.1.4):* An empirical audit of `xgboost==2.1.4` confirms that passing a custom callable metric to `XGBClassifier` is technically unreliable for early stopping: `XGBClassifier`'s internal early-stopping handler treats custom callable metrics as loss functions to be minimized, silently inverting early stopping for Average Precision (stopping when AP is at its lowest rather than highest). Furthermore, tuple-based return signatures raise `TypeError: must be real number, not tuple`, and custom callback dictionaries are rejected by scikit-learn wrapper boundaries (`XGBoostError: Unknown metric function`).
   - *Operational Protocol:*
     - **Early-Stopping Proxy:** XGBoost's fast internal C++ implementation of `eval_metric="aucpr"` is retained strictly as an early-stopping heuristic proxy to monitor validation progress within the C++ booster loop and trigger the stopping counter (`early_stopping_rounds = 20`) on the inner validation fold.
     - **Canonical Candidate Ranking:** Once early stopping determines the best iteration, the model generates predicted probabilities on the inner validation fold, and the fold score is computed using **scikit-learn's canonical `average_precision_score(y_val, y_pred_proba)`**.
     - *Distinction Invariant:* The native `aucpr` metric and scikit-learn `average_precision_score` are **not mathematically identical**; they use different interpolation and tie-handling algorithms. The native metric is strictly an internal stopping proxy, while candidate selection across all algorithm families (B0, B1, M1, M2) is governed exclusively by the canonical scikit-learn implementation.
3. **Best-Iteration Indexing Conversion:**
   - In XGBoost, `model.best_iteration` is a **0-based integer index** ($0 \le \text{best\_iteration} \le 299$).
   - The actual number of boosting rounds trained/required to produce that model state is:
     `number_of_boosting_rounds = best_iteration + 1`
     $$\text{number\_of\_boosting\_rounds} = \text{best\_iteration} + 1$$
   - For each inner fold $j \in \{1, 2, 3, 4\}$, the fold-specific boosting-round count is explicitly calculated using this conversion:
     $$T_j^* = \text{best\_iteration}_j + 1 \quad \text{where } 1 \le T_j^* \le 300$$
4. **Hyperparameter Selection and Deterministic Median Rounding Rule:**
   - Candidate performance for configuration $\theta_i$ is evaluated by the mean canonical inner-CV PR-AUC across the four inner folds:
     $$\overline{\text{PR-AUC}}_i = \frac{1}{4} \sum_{j=1}^4 \text{average\_precision\_score}(y_{\text{val}, j}, \, \hat{p}_{i, j})$$
   - The optimal hyperparameter tuple $\theta^*$ is selected by $\arg\max_i \overline{\text{PR-AUC}}_i$, with deterministic tie-breaking (lower `learning_rate`, then lower `max_depth`, then lower `min_child_weight`).
   - For the selected winning configuration $\theta^*$, its four inner fold boosting-round counts are sorted in ascending order:
     $$T_{(1)}^* \le T_{(2)}^* \le T_{(3)}^* \le T_{(4)}^*$$
   - The mathematical median of four values is the average of the two middle values: $\frac{T_{(2)}^* + T_{(3)}^*}{2}$. Because this average yields a half-integer when the sum is odd, the architecture specifies the **deterministic ceiling integer-rounding rule**:
     $$T^* = \left\lceil \frac{T_{(2)}^* + T_{(3)}^*}{2} \right\rceil = \text{floor}\left( \frac{T_{(2)}^* + T_{(3)}^* + 1}{2} \right)$$
   - *Rationale:* The ceiling operation ($\lceil \cdot \rceil$) is a pre-declared deterministic mathematical convention for converting the midpoint of two integer boosting counts into a unique integer when their sum is odd. (It does not imply that increasing boosting rounds increases regularization; additional boosting trees increase model capacity).
   - **Strict Bounding Invariant:**
     $$1 \le T^* \le 300$$
5. **Final Sub-Train Refit:**
   - The final base estimator $M_k$ is trained on the **entire Sub-Train partition ($N = 4,480$)** using configuration $\theta^*$ for **exactly $T^*$ boosting rounds**, with **NO early stopping** (as no validation holdout exists within the Sub-Train pool).
6. **Strict Forward Sealing and Consistency Verification:**
   - All 20 XGBoost candidates use the exact same early-stopping protocol and the exact same maximum limit of 300 boosting rounds.
   - Zero calibration rows ($N=960$), threshold rows ($N=960$), or outer-test rows ($N=1,600$) are ever observed during hyperparameter search or during $T^*$ determination.
   - The resulting fitted estimator $M_k$ is completely frozen and identical across subsequent calibration, threshold optimization, and outer-test evaluation.

- **Configuration Invariance:** The exact same candidate search configurations and selection rules apply to both Configuration A (`WITH_TYPE`) and Configuration B (`NO_TYPE`), satisfying PRD §10.1.5 item 2.
- **Inner Selection Scope:** The inner loop evaluates only the base estimator $M_k$. Post-hoc calibrators ($C_k$) and decision thresholds ($\tau_k^*$) are **never tuned during inner CV**; they are optimized on their dedicated downstream partitions.

---

## 4. Calibration Architecture and Score-Distribution Mismatch Resolution

### 4.1 Resolution of Calibration and Final-Model Score-Distribution Mismatch
* **The Methodological Problem:**
  In naive cross-validation calibration, base models are trained on inner subsets (e.g. 4,800 rows), and a calibrator is fitted on their out-of-fold predictions. If the final estimator deployed to the outer test set is subsequently refitted on all 6,400 outer training rows, a **score-distribution mismatch** occurs. An estimator fitted on 6,400 rows ($33\%$ more training data, $N_{\text{pos}} = 217$ vs $163$) develops deeper trees, different leaf margins, and narrower confidence bounds. Wrapping this 6,400-row estimator in a calibrator fitted on 4,800-row score outputs distorts probability mapping.
* **Comparative Evaluation of Architectural Alternatives:**
  1. *Alternative 1 (Cross-Fitted Ensemble / Bagged Outer Predictor):*
     Train 4 inner models on 4,800 rows each; calibrate each on its held-out inner fold; deploy the 4-model ensemble average $\hat{P}(x) = \frac{1}{4} \sum_{i=1}^4 C_i(M_i(x))$ to the outer test set.
     - *Limitation:* Produces a composite ensemble rather than the single identifiable baseline model mandated by PRD §10.1.3, and complicates SHAP TreeExplainer under AC-XAI-1.
  2. *Alternative 2 (Dedicated Outer-Train Partitioning / Fixed-Estimator Protocol — SELECTED DESIGN):*
     Within each outer training partition $D_{\text{outer\_train}, k}$ ($N=6,400$), allocate deterministic, disjoint partitions:
     - **Sub-Train Partition ($70\%$, $N=4,480$, $\approx 152$ failures):** Fits the base estimator $M_k$.
     - **Calibration Partition ($15\%$, $N=960$, $\approx 32$ failures):** Evaluated by $M_k$ to extract raw scores and fit the post-hoc calibrator $C_k$.
     - **Threshold-Validation Partition ($15\%$, $N=960$, $\approx 32$ failures):** Evaluated by the calibrated pipeline $C_k(M_k(\cdot))$ to search for the cost-optimal decision threshold $\tau_k^*$.
     - **Outer Test Partition ($N=1,600$, $\approx 54$ failures):** Evaluated strictly out-of-sample using the **exact same fitted pipeline $C_k(M_k(\cdot))$ and frozen threshold $\tau_k^*$**.

### 4.2 Why Alternative 2 Eliminates Score-Distribution and Threshold Leakage
1. **Zero Score-Distribution Mismatch:** The base estimator $M_k$ evaluated during calibration fitting and threshold search is the **exact, identical estimator deployed to the outer test fold**. No refitting on larger data occurs after calibration.
2. **Zero Threshold In-Sample Bias:** The threshold $\tau_k^*$ is optimized on observations ($N=960$) that were **completely unobserved during calibrator fitting**.
3. **Strict Outer Sealing:** Outer test observations ($N=1,600$) are completely untouched until final out-of-sample evaluation.

```
========================================================================================
OUTER TRAINING PARTITION: D_outer_train,k (N = 6,400 | ~217 Failures)
========================================================================================
          │
          ├───────────────────────────────┬───────────────────────────────┐
          ▼                               ▼                               ▼
Sub-Train Split (70%)           Calibration Split (15%)         Threshold Split (15%)
N = 4,480 | ~152 Positives      N = 960 | ~32 Positives         N = 960 | ~32 Positives
          │                               │                               │
          ▼                               ▼                               ▼
Fit Base Estimator M_k          Extract Scores via M_k          Apply C_k(M_k(X))
                                Fit Calibrator C_k              Optimize Threshold tau*_k
                                          │                               │
                                          └───────────────┬───────────────┘
                                                          ▼
                                          FROZEN CALIBRATED PIPELINE
                                          Pipeline_k = C_k(M_k(X)) @ tau*_k
                                                          │
                                                          ▼ [Evaluate Once]
                                          OUTER TEST FOLD: D_outer_test,k
                                          (N = 1,600 | ~54 Failures | Strictly Sealed)
```

### 4.3 Complete Sequential Execution Pipeline and Backward Isolation Verification
To eliminate all potential paths of implicit or explicit data leakage, the evaluation procedure inside each outer fold $k \in \{1, \dots, 5\}$ executes strictly through the following unidirectional 8-step sequence:

1. **Outer Train/Test Separation:**
   The development pool ($N=8,000$) is partitioned into outer training ($N_{\text{outer\_train}} = 6,400$) and outer test ($N_{\text{outer\_test}} = 1,600$) folds. The locked historical test partition ($N=2,000$) remains completely firewalled.
2. **Disjoint 3-Way Split of Outer-Training Data:**
   The outer training partition ($N=6,400$) is divided deterministically into:
   - Sub-Train Partition ($70\%$, $N=4,480$, $\approx 152$ failure events).
   - Calibration Partition ($15\%$, $N=960$, $\approx 32$ failure events).
   - Threshold-Validation Partition ($15\%$, $N=960$, $\approx 32$ failure events).
3. **Four-Fold Inner CV Restricted to Sub-Train:**
   Inner cross-validation executes strictly within the Sub-Train partition ($N=4,480$). Each inner fold allocates $N_{\text{inner\_train}} = 3,360$ and $N_{\text{inner\_val}} = 1,120$. No calibration rows, threshold rows, or outer-test rows are present.
4. **Hyperparameter and Early Stopping Selection:**
   Inner validation canonical PR-AUC (`average_precision_score`) determines the optimal candidate configuration $\theta^*$. For XGBoost, fold-level boosting rounds $T_j^* = \text{best\_iteration}_j + 1$ are computed, and the integer ceiling median across the four inner folds determines the fixed boosting rounds $T^* \in [1, 300]$ (§3.3.1).
5. **Final Base Estimator Refit on Complete Sub-Train Partition:**
   The base estimator $M_k$ is trained on all $4,480$ observations of the complete Sub-Train partition using configuration $\theta^*$ (for exactly $T^*$ boosting rounds for XGBoost) with zero early stopping.
6. **Calibration Fitting on Disjoint Calibration Partition:**
   Base estimator $M_k$ extracts uncalibrated raw scores from the separate Calibration partition ($N=960$). Post-hoc calibrator $C_k$ is fitted ($p = \sigma(w \cdot f(x) + c)$) subject to $N_{\text{cal,pos}} \ge 25$ and $w > 0$. Estimator $M_k$ is completely frozen during this step.
7. **Threshold Selection and Sensitivity Analysis on Disjoint Threshold-Validation Partition:**
   The calibrated pipeline $C_k(M_k(\cdot))$ scores instances on the separate Threshold-Validation partition ($N=960$). Operational threshold $\tau_k^*$ is optimized under the cost ratio with tie-breaking to $\tau_{\text{Bayes}}^*$. Threshold-neighborhood sensitivity analysis (with boundary clipping and deduplication) and cost-ratio sensitivity sweeps are executed exclusively on this partition. Threshold $\tau_k^*$ is frozen permanently.
8. **Single Outer-Test Out-of-Sample Evaluation:**
   The frozen calibrated pipeline $C_k(M_k(\cdot))$ is evaluated **exactly once** on the untouched Outer-Test fold ($N=1,600$) at frozen threshold $\tau_k^*$.

* **Strict Backward-Isolation Assertion:**
  No information, scores, labels, or distribution statistics from later partitions (Calibration, Threshold-Validation, or Outer Test) ever flow backwards into earlier modeling stages (inner CV, hyperparameter selection, boosting-round selection, or base estimator refitting). Every transformation is forward-causal only.

---

## 5. Model-Agnostic Probability Calibration Protocol

To satisfy AC-FP-5 and PRD §10.1.4, raw model outputs must be mapped to empirical posterior probabilities $P(Y=1 \mid x)$. Because algorithm families operate in different output spaces, the calibration architecture defines family-specific score extraction and calibration transformations.

### 5.1 Score Extraction and Calibration by Algorithm Family

| Model Family (PRD §10.1.3) | Raw Score Type | Extraction Method | Domain | Prescribed Calibration Method | Pre-Declared Justification & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **B0: Majority-Class Baseline** | Empirical Training Prevalence | $\hat{p}(x) = \bar{y}_{\text{sub\_train}}$ | $[0, 1]$ | None (Identity mapping) | Trivial prevalence floor; learned calibration is mathematically redundant. |
| **B1: Logistic Regression** | Linear Logit Predictor | `decision_function(X)` | $(-\infty, +\infty)$ | Univariate Platt Scaling: $p = \sigma(w \cdot z + c)$ | Standard logistic regression outputs probabilities, but `class_weight="balanced"` shifts the intercept. Platt scaling on linear logits corrects base-rate calibration while preserving linearity. Requires $w > 0$. |
| **M1: Random Forest** | Bagged Class Frequencies | `predict_proba(X)[:, 1]` | $[0, 1]$ | Platt Scaling on Clipped Log-Odds: $z = \log\frac{p + \epsilon}{1 - p + \epsilon}$ ($\epsilon = 10^{-4}$) | Random Forest probabilities are compressed toward the center due to bagging variance. Platt scaling on log-odds expands compressed tails back to empirical base rates. Requires $w > 0$. |
| **M2: XGBoost / Boosted Trees** | Unconstrained Tree Margins | `booster.predict(..., output_margin=True)` | $(-\infty, +\infty)$ | Margin-Level Platt Scaling: $p = \sigma(w \cdot f(x) + c)$ | Avoids scikit-learn's double-sigmoid distortion on `predict_proba`. Direct scaling of additive tree leaf margins guarantees a smooth, monotonic probability mapping. Requires $w > 0$. |
| **Optional Candidates (LightGBM/CatBoost/MLP)** | Margins or Pre-Softmax Logits | Native margin / logit extraction | $(-\infty, +\infty)$ | Margin-Level Platt Scaling: $p = \sigma(w \cdot f(x) + c)$ | Operates on continuous unbounded logit space. Requires $w > 0$. |

### 5.2 Mathematical Formulation and Calibration Safeguards
For all models calibrated via Platt scaling:
$$p_{\text{cal}}(x) = \sigma(w \cdot f(x) + c) = \frac{1}{1 + \exp\left(-(w \cdot f(x) + c)\right)}$$

* **Single Pre-Declared Sample Size Rule ($N_{\text{cal,pos}} \ge 25$):**
  - **Threshold Justification:** In the $15\%$ calibration partition ($N = 960$) drawn from the development pool ($3.3875\%$ failure prevalence), the expected count of positive failure events is $\approx 32.5$. Under stratified sampling, each outer fold receives $32$ or $33$ positive observations. A minimum threshold of $N_{\text{cal,pos}} \ge 25$ is enforced. This safeguard ensures that unexpected data filtering or missingness does not degrade the sample into extreme small-sample instability. Events Per Variable (EPV $\approx 16$) is treated as a rough heuristic diagnostic rather than a mathematical guarantee of calibration quality.
  - **Failure Handling:** If any outer fold's calibration split yields $N_{\text{cal,pos}} < 25$, the pipeline raises `InsufficientCalibrationEventsError` and **aborts the evaluation of that fold**, recording a `CALIBRATION_GATE_FAILURE`. If any fold within an evaluation run fails this gate, the entire procedure for that candidate algorithm is marked as `INVALID_INSUFFICIENT_CALIBRATION_DATA` and cannot be registered or promoted.
* **Monotonicity and Parameter Boundary Invariants:**
  - Because raw scores $f(x)$ are positively oriented with failure risk ($\frac{\partial f}{\partial \text{risk}} > 0$), the fitted slope coefficient must satisfy:
    $$w > 0$$
  - Plausibility boundaries are asserted: $0.05 \le w \le 20.0$. Slope values outside this range indicate extreme shrinkage or explosive gradients.
* **Failure Handling & Non-Fallback Guarantee:**
  - If the calibration optimizer fails to converge within maximum iterations, or yields $w \le 0$, the pipeline raises `CalibrationFailureError`. **Silent fallback to uncalibrated probabilities is strictly prohibited.**
* **Calibration Instability Reporting:**
  - The evaluation logger must compute and report $(w_k, c_k, \text{SE}(w_k), \text{SE}(c_k))$ for every fold, where standard errors are estimated from the inverse Hessian of the logistic log-likelihood.
  - Any fold exhibiting $\frac{\text{SE}(w_k)}{w_k} > 0.5$ (relative standard error $> 50\%$) or $w_k > 10.0$ is tagged with the audit warning `HIGH_CALIBRATION_VARIANCE`.

### 5.3 Secondary Calibration Sensitivity Analyses
* PRD §10.1.4 permits: *"calibrate (isotonic or Platt) on the validation partition"*.
* **Sample Size Limitations on Non-Parametric Calibration:**
  Isotonic regression fits a non-parametric, piecewise-constant step function via the pool-adjacent violators (PAV) algorithm. With $N_{\text{cal,pos}} \approx 32$ positive failure events in the $N=960$ calibration partition, isotonic regression creates large flat steps (zero-gradient plateaus), severely degrading local rank ordering and probability resolution.
* **Pre-Declared Sensitivity Scope:** Platt scaling is pre-declared as the **primary calibration method** across all parametric and tree models. Isotonic regression and Beta calibration are retained strictly as **pre-declared diagnostic sensitivity checks** (evaluated for exploratory comparison only), not primary candidates. No empirical validity or superiority is claimed prior to experimental execution.

---

## 6. Threshold Selection Architecture

### 6.1 Derivation of the Theoretical Bayes Threshold
Under PRD §10.1.4 and Appendix E:
- $C_{\text{FN}} = \$10,000$ (financial loss of an undetected catastrophic failure).
- $C_{\text{FP}} = \$200$ (cost of an unnecessary technician dispatch).
- Let $p = P(Y=1 \mid x)$ be the true calibrated posterior failure probability.
- Expected cost of predicting negative ($\hat{Y}=0$): $\mathbb{E}[C \mid \hat{Y}=0] = p \cdot C_{\text{FN}}$.
- Expected cost of predicting positive ($\hat{Y}=1$): $\mathbb{E}[C \mid \hat{Y}=1] = (1 - p) \cdot C_{\text{FP}}$.
- The Bayes optimal decision boundary occurs where expected costs are equal:
  $$p^* \cdot C_{\text{FN}} = (1 - p^*) \cdot C_{\text{FP}} \implies p^* (C_{\text{FN}} + C_{\text{FP}}) = C_{\text{FP}}$$
  $$\tau_{\text{Bayes}}^* = \frac{C_{\text{FP}}}{C_{\text{FN}} + C_{\text{FP}}} = \frac{200}{10,000 + 200} = \frac{200}{10,200} = \frac{1}{51} \approx 0.0196078 \quad (\sim 1.96\%)$$

> **Governance Notice:** The $\$10,000$ and $\$200$ costs are **illustrative benchmark assumptions** defined in PRD Appendix E. They do not represent customer-validated plant economics.

### 6.2 Empirical Threshold Selection Protocol
1. **Disjoint Validation Optimization:** Inside each outer fold $k$, threshold search evaluates the cost function strictly on the threshold-validation partition ($N=960$):
   $$\tau_k^* = \arg\min_{\tau \in \mathcal{T}} \left[ C_{\text{FN}} \cdot \text{FN}_{\text{thresh}}(\tau) + C_{\text{FP}} \cdot \text{FP}_{\text{thresh}}(\tau) \right]$$
2. **Candidate Threshold Grid:**
   $$\mathcal{T} = \{0.0\} \cup \{0.005, 0.010, \dots, 0.995\} \cup \{1.0\} \quad (201 \text{ candidate points})$$
   Explicitly includes boundary endpoints:
   - $\tau = 0.0$: All predicted positive ($FN = 0$, $FP = N_{\text{neg}}$, $\text{Cost} = C_{\text{FP}} \cdot N_{\text{neg}}$).
   - $\tau = 1.0$: All predicted negative ($FP = 0$, $FN = N_{\text{pos}}$, $\text{Cost} = C_{\text{FN}} \cdot N_{\text{pos}}$, $\text{Precision} \equiv 0.0$ with flag `UNDEFINED_ZERO_PREDICTIONS`).
   - *Statistical Resolution Notice:* With $N_{\text{val,pos}} \approx 32$ positive failure events, adjacent grid points frequently yield identical confusion matrices. The deterministic tie-breaking rule below resolves these flat plateaus without manual intervention.
3. **Deterministic Tie-Breaking Rule:**
   If multiple candidate thresholds achieve the identical minimum operational cost, the tie is broken deterministically toward the theoretical Bayes threshold:
   $$\tau_k^* = \arg\min_{\tau \in \mathcal{T}_{\text{min}}} \left| \tau - \tau_{\text{Bayes}}^* \right|$$
   Ties in distance break toward the higher threshold to minimize operator false-alarm fatigue.
4. **Fold-Specific Reporting:**
   Because each outer fold optimizes its own threshold, the architecture reports the distribution across the outer folds:
   $$\bar{\tau}^* \pm s_{\tau} \quad [\min \tau_k^*, \max \tau_k^*]$$
   along with fold-level confusion matrices $(TP_k, FP_k, FN_k, TN_k)$ and fold costs.
5. **Decoupling of Threshold Concepts:**
   Reports and API responses strictly separate:
   - Theoretical Bayes threshold ($\tau_{\text{Bayes}}^* \approx 0.0196$).
   - Empirical validation-optimal threshold distribution ($\bar{\tau}^*$).
   - Historical provisional threshold ($\tau_{\text{prov}} = 0.45$).
   The provisional threshold $\tau = 0.45$ is never retained merely because it was historical.

### 6.3 Threshold-Validation Sensitivity Analysis (Strictly Pre-Outer-Test)
To evaluate the stability of the empirical cost minimum without data leakage:
- **Exclusively on Threshold Validation ($N=960$):** Sensitivity analysis is performed **strictly within the threshold-validation partition prior to touching outer-test data**.
- **Neighborhood Evaluation and Boundary Handling:**
  - For each fold, candidate perturbation offsets $\delta \in \{-0.02, -0.01, 0.0, +0.01, +0.02\}$ are evaluated.
  - **Boundary Clipping:** Every candidate threshold is strictly clipped to the valid probability interval $[0.0, 1.0]$:
    $$\tau_{\text{clip}}(\delta) = \min(1.0, \, \max(0.0, \, \tau_k^* + \delta))$$
  - **Deduplication:** Duplicate threshold values produced by clipping at boundary conditions (e.g., when $\tau_k^* < 0.02$ causes both $\tau_k^* - 0.02$ and $\tau_k^* - 0.01$ to clip to $0.0$) are removed:
    $$\mathcal{T}_{\text{sens}} = \text{unique}\left( \left\{ \min(1.0, \, \max(0.0, \, \tau_k^* + \delta)) : \delta \in \{-0.02, -0.01, 0.0, +0.01, +0.02\} \right\} \right)$$
  - For each unique candidate $\tau \in \mathcal{T}_{\text{sens}}$, compute the threshold-validation cost $C_{\text{val}}(\tau)$, validation false negative count shifts $\Delta \text{FN}_{\text{val}}$, and validation false positive count shifts $\Delta \text{FP}_{\text{val}}$.
- **Strict Freezing Before Outer Test:** The selected threshold $\tau_k^*$ is **frozen permanently** prior to outer-test evaluation.
- **Zero Outer-Test Leakage Invariant:**
  - Outer-test results must **NEVER** be used to select, tune, adjust, or compare alternative operational thresholds.
  - The outer test fold is evaluated **exactly once** using the frozen pipeline $C_k(M_k(\cdot))$ and frozen threshold $\tau_k^*$, satisfying PRD §10.1.4.
  - Outer-test confusion matrices and cost figures are reported purely as **out-of-sample evaluation metrics**, not as evidence for threshold selection.

### 6.4 Disclosure of Economic Cost Uncertainty (Cost Ratio Sweep)
- **Economic Disclosure:** Model cards and evaluation artifacts must state: *"The $50:1$ cost ratio ($C_{\text{FN}}=\$10,000, C_{\text{FP}}=\$200$) is an illustrative PRD benchmark (Appendix E) and does not represent verified customer plant economics."*
- **Validation Cost Ratio Sweep:** To document threshold sensitivity to economic assumptions, the pipeline runs a pre-declared sensitivity sweep strictly on the threshold-validation partition across alternative ratios:
  - $10:1$ ($C_{\text{FN}}=\$2,000, C_{\text{FP}}=\$200 \implies \tau_{\text{Bayes}}^* \approx 0.0909$)
  - $20:1$ ($C_{\text{FN}}=\$4,000, C_{\text{FP}}=\$200 \implies \tau_{\text{Bayes}}^* \approx 0.0476$)
  - $50:1$ ($C_{\text{FN}}=\$10,000, C_{\text{FP}}=\$200 \implies \tau_{\text{Bayes}}^* \approx 0.0196$) [PRD Appendix E Baseline]
  - $100:1$ ($C_{\text{FN}}=\$20,000, C_{\text{FP}}=\$200 \implies \tau_{\text{Bayes}}^* \approx 0.0099$)
  Reporting the resulting optimal validation thresholds $\tau_{\text{val}}^*(C_{\text{ratio}})$ illustrates operational trade-offs across customer risk profiles.

---

## 7. Statistical Reporting and Evaluation Governance

### 7.1 Multi-Tiered Metric Suite
Every model evaluated under Stage 3 outputs structured metrics across four tiers:

1. **Ranking Metrics (Threshold-Independent):**
   - **PR-AUC (Average Precision — Canonical Metric):** Primary selection metric for severe class imbalance. Evaluated canonically across all models using scikit-learn's `average_precision_score(y_true, y_score)`:
     $$\text{AP} = \sum_n (R_n - R_{n-1}) P_n$$
     *Metric Consistency Invariant:* XGBoost's native `aucpr` metric is used solely as an internal C++ monitoring heuristic to trigger early stopping. All candidate comparison, inner validation selection, and outer test evaluation use this exact scikit-learn `average_precision_score` implementation.
   - **ROC-AUC:** Diagnostic ranking metric across true positive and false positive rates.
2. **Probability Calibration Metrics:**
   - **Brier Score:** $BS = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$.
   - **Brier Skill Score ($BSS$):** Evaluates percentage calibration improvement over the naive prevalence baseline:
     $$BSS = 1 - \frac{BS_{\text{candidate}}}{BS_{\text{reference}}}$$
     where the reference predictor is the empirical training prevalence of the B0 baseline:
     $$\hat{p}_{\text{ref}} = \bar{y}_{\text{sub\_train}}$$
     This constant probability $\hat{p}_{\text{ref}}$ is applied to every row in the corresponding outer test fold:
     $$BS_{\text{reference}} = \frac{1}{N_{\text{outer\_test}}} \sum_{i \in \text{outer\_test}} (\hat{p}_{\text{ref}} - y_i)^2$$
     *Strict Governance Invariant:* Estimating reference prevalence using outer test labels ($\bar{y}_{\text{outer\_test}}$) is **strictly prohibited**.
   - **Reliability Diagram Data:** 10 quantile (equal-frequency) bins recording mean predicted probability vs. observed empirical failure frequency.
   - **Expected Calibration Error (ECE):** Quantile-binned weighted absolute calibration error.
     - *Methodological Caveat:* Under rare-event prevalence ($3.39\%$), top probability bins have small positive counts, making ECE sensitive to bin boundaries. ECE must always be interpreted alongside the reliability diagram.
3. **Operational Decision Metrics (Evaluated at $\tau_k^*$):**
   - True Positives, False Positives, False Negatives, True Negatives.
   - Recall, Precision, $F_1$-score.
   - Total Operational Cost: $C_{\text{FN}} \cdot \text{FN} + C_{\text{FP}} \cdot \text{FP}$.
4. **Statistical Uncertainty & Comparative Tests:**
   - **Stratified Bootstrap Confidence Intervals (95%):** 1,000 iterations per fold on evaluation partitions. Evaluates sample variance on the designated partition.
     - *Historical Benchmark Governance Notice:* For the locked historical 2,000-sample test partition (hash `8e8fef98...`), bootstrap confidence intervals are **exploratory benchmark metrics only**. Because this partition was previously evaluated during Stage 2B model comparison, bootstrapping does **not** restore statistical independence. The historical test partition must never be described as confirmatory or independent. Formal confirmatory performance claims are strictly reserved for a genuinely unobserved external dataset.
   - **Corrected Resampled t-Tests (Exploratory Heuristic Indicators Only):**
     Evaluates outer fold differences using repeated-resampling corrected variance estimators (Nadeau & Bengio, 2003; Bouckaert & Frank, 2004):
     $$t = \frac{\bar{d}}{\sqrt{\left(\frac{1}{R \cdot K} + \frac{n_{\text{test}}}{n_{\text{train}}}\right) S_{\text{all}}^2}}$$
     - *Methodological Constraints & Non-Inferential Status:* The 25 outer evaluations share $\approx 80\%$ training overlap. Folds are not independent trials. Treating $R \times K = 25$ as $df = 24$ produces severe Type I error inflation. Even setting $df = 4$ lacks proven asymptotic validity for nested CV on imbalanced data. Therefore, resampled $t$-tests are reported strictly as **exploratory diagnostic indicators**, never as inferential proof of superiority.
   - **Exact Binomial McNemar Test:** Strictly restricted to exploratory paired classification comparisons on the **locked historical test partition**. It is mathematically prohibited on pooled CV predictions due to cross-fold dependence.
   - *Exclusion of Wilcoxon Signed-Rank Test:* Mathematically excluded for 5 outer folds because the minimum achievable two-tailed $p$-value for $N=5$ pairs is $2 \cdot (0.5)^5 = 0.0625$, making $\alpha = 0.05$ significance testing impossible.

### 7.2 Fold-Level vs. Pooled Metrics Governance
- **Primary Reporting — Descriptive Statistics Across All 25 Outer Evaluations:**
  To reflect true procedural variance without misleading aggregation, the evaluation report presents:
  1. Complete per-fold outer metrics $(r, k)$ for all 25 runs.
  2. Per-repetition means $\bar{m}_r$ and repetition standard deviation $s_{\text{rep}}$.
  3. Grand procedure mean $\bar{m} = \frac{1}{R} \sum_{r=1}^R \bar{m}_r$.
  4. Full observed outer fold spread $[\min m_{r,k}, \max m_{r,k}]$.
  5. Paired algorithm differences $\bar{d} = \bar{m}_A - \bar{m}_B$ alongside fold-difference ranges.
- **Pooled Out-of-Fold Diagnostics:** Concatenating outer test fold predictions yields global PR-AUC and Brier scores across the 8,000 development observations.
- **Governance Invariant:** Reports must state explicitly that **cross-validation metrics evaluate the model-building procedure, NOT a single deployable model artifact**. Final deployment requires fitting the specified pipeline on the full development pool with inner calibration.

---

## 8. SHAP and Explainability Technical Contract

PRD §8.7 and AC-XAI-1 govern model explainability:
> *"AC-XAI-1 (MS2): SHAP values plus base value reconstruct tree-model output within tolerance on sampled rows."*

### 8.1 Margin-Scale Additive Reconstruction
- **Explainer Target:** For XGBoost and tree models, `shap.TreeExplainer` operates natively on the unconstrained tree margin $f(x) \in (-\infty, +\infty)$:
  $$f(x) = \phi_0 + \sum_{j=1}^M \phi_j(x)$$
  where $\phi_0 = \mathbb{E}[f(x)]$, and $\phi_j(x)$ is the Shapley attribution of feature $j$.
- **Numerical Verification:** The test suite asserts that additive reconstruction holds within numerical tolerance:
  $$\max_{i} \left| f(x_i) - \left( \phi_0 + \sum_{j=1}^M \phi_{j}(x_i) \right) \right| \le 10^{-5}$$

### 8.2 Probability Transformation Non-Additivity Invariant
- Because the Platt calibration mapping $P = \sigma(w \cdot f(x) + c)$ is non-linear:
  - Margin-scale SHAP attributions $\phi_j(x)$ **do not sum to the calibrated failure probability**, nor does $\sigma(\phi_0 + \sum \phi_j)$ equal $\sum \sigma(\phi_j)$.
  - SHAP attributions must **never be represented as percentage contributions to physical failure probability**.
- **Interface Labeling:** Explanation payloads and UI panels must display:
  - `"Contribution to Model Scoring Margin (Log-Odds)"`.
  - Directional consistency notice: Because $w > 0$, any feature with $\phi_j(x) > 0$ increases the log-odds margin, monotonically increasing the calibrated probability $P$.

### 8.3 Mandatory Non-Causality Disclaimer (AC-XAI-2)
Every explanation view, API response, and PDF report must carry the mandatory PRD disclaimer:
> *"Feature attributions describe algorithmic dependencies of the reference model on the logit scale, not physical causation. Correlated operating variables are not independently controllable."*

---

## 9. Historical Test-Set Governance

### 9.1 Preservation vs. Statistical Independence
* **Historical Fact:** The 2,000-sample test partition recorded in `ml/artifacts/split_indices.json` (hash `8e8fef98bdc3f3d6...`) was already accessed and evaluated during Stage 2B across eight baseline models.
* **Governance Invariants:**
  1. **Reproducibility Preservation:** The split indices and hashes are preserved exactly to allow historical replication of Stage 2B benchmarks.
  2. **Exploratory Status:** Preserving the split does **not** restore statistical independence. Any subsequent evaluation on this partition is classified strictly as **exploratory benchmark tracking**. Bootstrap confidence intervals on this partition evaluate sampling variance within the historical sample, but **never constitute confirmatory proof of generalization**.
  3. **Firewall:** The historical test partition must **never be used** for calibration fitting, threshold optimization, or model promotion decisions.
  4. **Confirmatory Generalization Boundary:** Genuine confirmatory evaluation of generalization and calibration error strictly requires an unobserved external industrial dataset.

---

## 10. PRD Compliance Matrix

To avoid conflating architectural intention with empirical verification, compliance is classified across four distinct operational states:
1. `DESIGN SPECIFIED`: The methodology is completely articulated in this architectural specification.
2. `IMPLEMENTATION COMPLETED`: Code has been merged and unit-tested in the repository.
3. `EXPERIMENTALLY VERIFIED`: The numerical pipeline has executed, and empirical metrics have satisfied gates.
4. `DEVIATION / PENDING APPROVAL`: The design deviates from literal PRD wording or awaits formal sign-off.

| PRD Requirement | Governing Clause | Architecture Component | Design Specified | Implementation Completed | Experimentally Verified | Governance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Model Ladder Comparison** | §10.1.3 | Evaluates B0, B1, M1, M2 under parity protocol | **YES** | NO | NO | PENDING IMPLEMENTATION |
| **Repeated Stratified CV** | §10.1.4 | 5 repetitions of $5 \times 4$ Nested CV ($R=5$) | **YES** | NO | NO | PENDING IMPLEMENTATION |
| **Fast Benchmark Single CV** | §10.1.4 | Single $5 \times 4$ Nested CV ($R=1$) | **YES** | NO | NO | **DEVIATION / PENDING APPROVAL** |
| **Validation-Partition Calibration** | §10.1.4 | Dedicated disjoint partition within outer training | **YES** | NO | NO | PENDING IMPLEMENTATION |
| **Cost-Ratio Thresholding** | §10.1.4, App. E | Disjoint validation cost search ($C_{\text{FN}}/C_{\text{FP}}=50$) | **YES** | NO | NO | PENDING IMPLEMENTATION |
| **Configuration Parity** | §10.1.5 | Identical fold indices, seeds, and search budgets | **YES** | NO | NO | PENDING IMPLEMENTATION |
| **Brier Score Promotion Gate** | §10.1.5 | Brier Score and Brier Skill Score promotion gates | **YES** | NO | NO | PENDING IMPLEMENTATION |
| **Calibrated Semantics** | §13.5, AC-FP-5 | API emits calibrated probabilities with exact string | **YES** | Partial (MS1 disclaimer) | NO (Pending calibrated weights) | PENDING STAGE 3 IMPLEMENTATION |
| **SHAP Reconstruction** | AC-XAI-1 | `TreeExplainer` on raw margins ($\text{tol} \le 10^{-5}$) | **YES** | Partial (Booster margins) | Pending Stage 3 run | PENDING STAGE 3 VERIFICATION |
| **Non-Causality Disclaimer** | AC-XAI-2 | Mandatory disclaimer in UI and API payloads | **YES** | **YES** | **YES** | **COMPLIANT** |
| **Milestone 1 Exit Benchmark** | §18.3 | Baseline models trained under §10.1.5 protocol | **YES** | Partial (Stage 2B single split) | NO (Pending repeated CV ladder) | PENDING STAGE 3 EXECUTION |

---

## 11. Summary of Future File Deliverables (Stage 3 Implementation Phase)

```
[Stage 3 Implementation Deliverables]
├── ml/
│   ├── src/
│   │   ├── models/
│   │   │   └── calibration.py          # ModelAgnosticCalibrator & Platt/Isotonic scalers
│   │   ├── evaluation/
│   │   │   ├── nested_cv.py            # Repeated 5x4 nested CV engine (Strategy 2)
│   │   │   ├── statistical_tests.py    # Nadeau-Bengio & exact McNemar test suite
│   │   │   └── threshold_optimizer.py  # Disjoint validation cost search with tie-breaking
│   │   └── features/
│   │       └── engineering.py          # Physics feature engineering transformers
│   ├── experiments/
│   │   ├── run_stage3_baselines_cv.py  # Re-evaluates baselines under repeated CV
│   │   └── run_stage3_candidates_cv.py # Evaluates advanced candidates under parity
│   └── artifacts/
│       ├── nested_cv_indices.json      # Deterministic outer/inner fold indices (R=5)
│       └── stage3_evaluation_report.json # Comprehensive multi-tiered metric report
```

---

**DOCUMENT REVISION COMPLETE. NO CODE MODIFICATIONS, MODEL TRAINING, OR EXPERIMENT EXECUTION PERFORMED.**
