# INDUSTRIA AI — Dataset Notes: AI4I 2020 Predictive Maintenance Dataset

| Field | Detail |
|---|---|
| **Dataset Identifier** | `ai4i2020-predictive-maintenance` |
| **Author / Citation** | Stephan Matzka, "Explainable Artificial Intelligence for Predictive Maintenance Applications", Third International Conference on Machine Learning and Applications (ICMLA), 2020, pp. 203-209. DOI: [10.1109/ICMLA51294.2020.00116](https://doi.org/10.1109/ICMLA51294.2020.00116) |
| **Authoritative Source** | UCI Machine Learning Repository (Dataset ID: 601, [URL](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset)) |
| **Direct Archive URL** | `https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip` |
| **License** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **Local Raw Path** | `ml/datasets/raw/ai4i2020.csv` |
| **File Format** | Comma-Separated Values (CSV), UTF-8 |
| **File Size** | 522,048 bytes (509.81 KB) |
| **SHA-256 Checksum** | `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e` |
| **Dimensions** | 10,000 rows $\times$ 14 columns |
| **Ingestion Date** | 2026-11-10 |

---

## 1. Dataset Overview & Operational Context

The **AI4I 2020 Predictive Maintenance Dataset** reflects real-world industrial milling machine operations, generated via a physical simulation model developed by Stephan Matzka. The dataset mirrors realistic telemetry recorded from milling operations where components are subjected to rotational velocities, mechanical loads, thermal variations, and cumulative tool wear.

Each observation represents a discrete component manufacturing cycle on an automated industrial milling machine. The machine processes three product quality variants (`L`, `M`, `H`), adding 2, 3, or 5 minutes of tool wear per cycle respectively.

---

## 2. Sensor Feature Dictionary & Column Audit

| Column Name | Raw Type | Category | Physical Unit | Range / Values | Detailed Description | Training Status & Leakage Assessment |
|---|---|---|---|---|---|---|
| `UDI` | `int64` | Identifier | Integer | `[1, 10000]` | Unique Document/row Identifier ranging sequentially from 1 to 10000. | **EXCLUDE**. Identifier only; risks index memorization. |
| `Product ID` | `object` | Identifier | String | 10,000 unique strings | Consists of quality variant letter (`L`, `M`, `H`) followed by a sequential variant counter (e.g. `M14860`, `L47181`). | **EXCLUDE**. Identifier. In Config B, its first letter leaks `Type`. In Config A, `Type` is already captured directly. |
| `Type` | `object` | Categorical Feature | String | `{'L': 6000, 'M': 2997, 'H': 1003}` | Product quality variant: Low (60%), Medium (30%), High (10%). Reflects variant durability and wear rate. | **CONFIG A ONLY**. Included in Config A (encoded); excluded in Config B. |
| `Air temperature [K]` | `float64` | Continuous Sensor | Kelvin (K) | `[295.3, 304.5]` (Mean: 300.0 K) | Ambient room temperature measured near equipment air intake, generated via random walk normalized to standard deviation around 300 K. | **INCLUDE** in both Config A and Config B. Valid predictive sensor. |
| `Process temperature [K]` | `float64` | Continuous Sensor | Kelvin (K) | `[305.7, 313.8]` (Mean: 310.0 K) | Active manufacturing process temperature, modeled as air temperature + 10 K plus operational thermal fluctuations. | **INCLUDE** in both Config A and Config B. Valid predictive sensor. |
| `Rotational speed [rpm]` | `int64` | Continuous Sensor | RPM | `[1168, 2886]` (Mean: 1538.8 RPM) | Spindle angular velocity calculated from a base 2860 W motor power with overlaid normal distribution. | **INCLUDE** in both Config A and Config B. Valid predictive sensor. |
| `Torque [Nm]` | `float64` | Continuous Sensor | Newton-meters (Nm) | `[3.8, 76.6]` (Mean: 40.0 Nm) | Mechanical torque delivered to the cutting spindle, normally distributed around 40 Nm with strictly non-negative values. | **INCLUDE** in both Config A and Config B. Valid predictive sensor. |
| `Tool wear [min]` | `float64` | Continuous Sensor | Minutes | `[0, 253]` (Mean: 108.0 min) | Cumulative cutting tool operational run time. Variants H/M/L add 5/3/2 minutes of tool wear to tool during each operation. | **INCLUDE** in both Config A and Config B. Valid predictive sensor. |
| `Machine failure` | `int64` | Primary Target | Binary flag | `{0: 9661, 1: 339}` | Primary target indicating whether the machine experienced an operational breakdown during this cycle ($1$) or maintained healthy operation ($0$). | **PRIMARY TARGET**. Supervised learning label for binary classification. |
| `TWF` | `int64` | Target / Mode | Binary flag | `{0: 9954, 1: 46}` | **Tool Wear Failure**: The tool is replaced or fails when cumulative tool wear reaches a failure window between 200 and 240 minutes. | **TARGET ONLY**. Catastrophic target leakage if used as a feature for `Machine failure`. |
| `HDF` | `int64` | Target / Mode | Binary flag | `{0: 9885, 1: 115}` | **Heat Dissipation Failure**: Failure caused by insufficient heat dissipation when $\Delta T < 8.6\text{ K}$ and rotational speed $< 1380\text{ rpm}$. | **TARGET ONLY**. Catastrophic target leakage if used as a feature for `Machine failure`. |
| `PWF` | `int64` | Target / Mode | Binary flag | `{0: 9905, 1: 95}` | **Power Failure**: Failure caused when mechanical power $P = \tau \cdot \omega \cdot \frac{2\pi}{60}$ drops below $3500\text{ W}$ or exceeds $9000\text{ W}$. | **TARGET ONLY**. Catastrophic target leakage if used as a feature for `Machine failure`. |
| `OSF` | `int64` | Target / Mode | Binary flag | `{0: 9902, 1: 98}` | **Overstrain Failure**: Failure caused when $\text{Tool wear} \times \text{Torque}$ exceeds variant threshold ($11,000$ for L, $12,000$ for M, $13,000$ for H). | **TARGET ONLY**. Catastrophic target leakage if used as a feature for `Machine failure`. |
| `RNF` | `int64` | Target / Mode | Binary flag | `{0: 9981, 1: 19}` | **Random Failure**: Each process has a 0.1% independent chance of experiencing a random breakdown regardless of operational parameters. | **TARGET ONLY**. Catastrophic target leakage if used as a feature for `Machine failure`. |

---

## 3. Target Formulations & Crucial Discrepancies

### 3.1 Binary Target (`Machine failure`)
- Total Normal Operations (`0`): **9,661 (96.61%)**
- Total Machine Failures (`1`): **339 (3.39%)**
- Class Imbalance Ratio: **28.5 : 1**

### 3.2 Failure Mode Targets
- `TWF`: 46 occurrences (0.46%)
- `HDF`: 115 occurrences (1.15%)
- `PWF`: 95 occurrences (0.95%)
- `OSF`: 98 occurrences (0.98%)
- `RNF`: 19 occurrences (0.19%)

### 3.3 Target Mismatch & Logical Relationship
In the dataset:
$$\text{Machine failure} \neq \text{TWF} \lor \text{HDF} \lor \text{PWF} \lor \text{OSF} \lor \text{RNF}$$

Cross-tabulation reveals two crucial structural discrepancies:
1. **The 18 RNF Mismatches (`Machine failure = 0`, `Any Mode = 1`)**:
   - In 18 out of the 19 `RNF` occurrences, `Machine failure` is recorded as `0`.
   - **Reason**: As specified in Matzka (2020), random failure events represent minor anomalous process disruptions with a 0.1% random occurrence probability; only 1 event resulted in total machine shutdown.
2. **The 9 Unflagged Failure Cases (`Machine failure = 1`, `All Modes = 0`)**:
   - Exactly 9 records have `Machine failure = 1` despite all 5 specific failure flags being `0`.
   - **Reason**: Multi-factor combined operational stress causing machine shutdown without crossing any single isolated failure threshold.
3. **Multi-Label Co-Occurrences**:
   - 24 machines suffer multiple simultaneous failure mechanisms (23 machines with 2 modes, 1 machine with 3 modes: UDI 5910 with TWF + PWF + OSF).
   - Therefore, multi-class failure categorization must be treated as a **multi-label** problem rather than mutually exclusive single-class labels.

---

## 4. PRD Feature Configurations

To support the requirements in the INDUSTRIA AI PRD, two standardized dataset configurations are established:

### Configuration A (With Type)
- **Feature Set**: `['Type', 'Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']`
- **Total Features**: 6 (1 categorical, 5 continuous numeric)
- **Use Case**: Operational scenarios where the enterprise MES/ERP provides the workpiece variant. The model can utilize variant durability priors (`Type L` failure rate = 3.92%, `Type M` = 2.77%, `Type H` = 2.09%).
- **Encoding Requirement**: Ordinal encoding (`L: 0, M: 1, H: 2`) or One-Hot Encoding (`Type_L`, `Type_M`, `Type_H`).

### Configuration B (Without Type)
- **Feature Set**: `['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']`
- **Total Features**: 5 (all continuous numeric)
- **Use Case**: Pure sensor-driven anomaly detection where machine controllers operate autonomously without workpiece metadata.
- **Leakage Prevention**: `Product ID` must be strictly dropped because its first character (`L47181` $\to$ `L`) leaks the product variant.

---

## 5. Physical Governing Equations & Domain Features

Verification demonstrates that three failure modes in AI4I follow exact mathematical equations:

1. **Heat Dissipation**:
   $$\Delta T = \text{Process temperature [K]} - \text{Air temperature [K]}$$
   Condition: $\Delta T < 8.6\text{ K}$ and $\text{Rotational speed} < 1380\text{ rpm}$ matches `HDF == 1` with **100.0% precision**.
2. **Mechanical Power**:
   $$P = \text{Torque [Nm]} \times \text{Rotational speed [rpm]} \times \frac{2\pi}{60}$$
   Condition: $P < 3500\text{ W}$ or $P > 9000\text{ W}$ matches `PWF == 1` with **100.0% precision**.
3. **Overstrain Interaction**:
   $$\text{Overstrain} = \text{Tool wear [min]} \times \text{Torque [Nm]}$$
   Condition: $\text{Overstrain} > \text{Threshold}(\text{Type})$ ($11,000$ for L, $12,000$ for M, $13,000$ for H) matches `OSF == 1` with **100.0% precision**.

These three derived features ($\Delta T$, Power, Tool wear $\times$ Torque) should be added to the Stage 2B feature engineering pipeline.

---

## 6. Data Quality Findings & Outlier Analysis

1. **Completeness**: 0 missing values across all 10,000 rows. No imputation needed.
2. **Uniqueness**: 0 duplicate rows; 10,000 distinct `UDI` values; 10,000 distinct `Product ID` values.
3. **Outlier Reality**:
   - `Rotational speed [rpm]`: 418 upper outliers ($> 1895.5\text{ rpm}$, failure rate = 8.37%).
   - `Torque [Nm]`: 40 upper outliers ($> 67.2\text{ Nm}$, failure rate = **90.0%**), 24 lower outliers ($< 12.8\text{ Nm}$, failure rate = **91.7%**).
   - **Industrial Significance**: Sensor outliers in rotational speed and torque are directly caused by motor stalling or excessive mechanical load. **Outliers must NOT be removed or winsorized**, as doing so would discard active failure precursors.

---

## 7. Known Limitations & Methodological Constraints

1. **Tabular Snapshots vs. Continuous Degradation**:
   - AI4I 2020 consists of independent component manufacturing snapshots.
   - It does **not** provide continuous time-series degradation trajectories from a single machine over months until failure.
   - Consequently, AI4I legitimately supports **Binary Failure Classification** and **Failure Mode Classification**, but **does not support Remaining Useful Life (RUL) regression**. Claims of continuous RUL estimation on AI4I are methodologically unsound.
2. **Extreme Class Imbalance (3.39%)**:
   - Dummy classifiers predicting all zeros achieve 96.61% accuracy.
   - Classification models must be evaluated using PR-AUC, F1-score, Recall, and the asymmetric business cost function defined in the PRD ($C_{\text{FN}} \gg C_{\text{FP}}$).
3. **Quarantine of Target Columns**:
   - `TWF`, `HDF`, `PWF`, `OSF`, `RNF` are alternative targets and must be strictly quarantined from feature matrices when predicting `Machine failure`.
