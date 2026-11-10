# INDUSTRIA AI — Product Requirements Document (PRD)

| Metadata | Details |
|---|---|
| **Product Name** | INDUSTRIA AI |
| **Document Type** | Master Product Requirements Document |
| **Version** | 1.0.0 |
| **Status** | Approved — Stage 1 Foundation |
| **Category** | Industrial Predictive-Maintenance SaaS Platform |
| **Target Platform** | Web (FastAPI + React) / Modular Monolith |

---

## 1. Executive Summary & Vision

### 1.1 Product Vision
**INDUSTRIA AI** is a production-grade predictive-maintenance SaaS platform engineered for manufacturing plants, industrial facilities, and heavy-asset operators. Modern industrial operations lose billions annually to unplanned equipment downtime and reactive maintenance, while traditional scheduled preventative maintenance routinely overhauls healthy equipment prematurely.

INDUSTRIA AI bridges this gap by continuously evaluating multi-sensor industrial telemetry (temperature, vibration, pressure, rotational speed, torque, electrical current), predicting impending component failures before they manifest, estimating Remaining Useful Life (RUL), and providing maintenance teams with interpretable, explainable root-cause insights.

### 1.2 Core Objectives
- **Zero Unplanned Catastrophic Failures**: Detect equipment degradation patterns 24 to 72 hours prior to physical breakdown.
- **Explainable Anomaly Attribution**: Empower reliability engineers with SHAP (SHapley Additive exPlanations) values to explain *why* an asset was flagged.
- **Cost-Optimized Alerting**: Apply asymmetric cost penalties during model evaluation (where an unpredicted failure costs 10x–50x more than an unnecessary inspection).
- **Lightweight, Modular Architecture**: Deliver a robust modular monolith deployable on standard infrastructure (single-node or Docker Compose) without premature distributed systems complexity.

---

## 2. Target Personas & Primary Use Cases

| Persona | Role | Core Need |
|---|---|---|
| **Reliability Engineer** | Analyzes asset health trends, reviews sensor telemetry, investigates root causes. | Transparent model metrics, feature importance, sensor drift curves, SHAP waterfall charts. |
| **Maintenance Manager** | Schedules crews, orders replacement parts, manages work orders. | High-confidence risk alerts, projected failure timelines, estimated lead time before component failure. |
| **Plant Operations Director** | Monitors plant-wide throughput, uptime KPIs, maintenance ROI. | Plant-wide health overview, downtime reduction metrics, financial impact estimates. |

---

## 3. System Architecture

INDUSTRIA AI follows a strict **modular monolith** architectural pattern. All components share a clear boundary and domain contracts without the operational overhead of microservices.

```
industria-ai/
│
├── frontend/             # Single-Page Dashboard (React + TypeScript + Vite + Tailwind CSS)
├── backend/              # RESTful Core API (FastAPI + SQLAlchemy + Pydantic)
├── ml/                   # ML Training, Feature Engineering, Pipelines & Model Registry
│   ├── datasets/         # Raw and processed industrial telemetry datasets
│   ├── notebooks/        # Prototyping and exploratory data analysis notebooks
│   ├── experiments/      # Experiment configs and run tracking records
│   ├── src/              # Reusable, production-grade ML pipeline source code
│   │   ├── data/         # Ingestion, schema validation, dataset loaders
│   │   ├── preprocessing/# Imputation, scaling, outlier handling, filtering
│   │   ├── features/     # Rolling windows, FFT/frequency analysis, sensor interactions
│   │   ├── models/       # Estimators, XGBoost/tree models, hyperparameter search
│   │   ├── evaluation/   # Classification metrics, cost matrices, SHAP attribution
│   │   └── utils/        # Paths, logging, seed initialization, config parsing
│   ├── artifacts/        # Serialized models, scaler pipelines, evaluation plots
│   ├── tests/            # ML-specific unit and integration tests
│   └── requirements.txt  # ML package dependencies
│
├── docs/                 # Documentation (PRD, Dataset Notes, Experiment Log)
├── infra/                # Infrastructure definitions (Docker, Compose)
├── tests/                # System-level and smoke tests
├── .env.example          # Environment variable template
├── .gitignore            # Git exclusion rules
└── README.md             # Project master overview
```

---

## 4. Technology Decisions & Constraints

### 4.1 Approved Technology Stack

| Layer | Approved Technology | Justification |
|---|---|---|
| **ML & Data Processing** | Python 3.10+, Pandas, NumPy | Standard, high-performance ecosystem for telemetry manipulation. |
| **Machine Learning** | Scikit-learn, XGBoost | Tree-based gradient boosting models excel at tabular sensor data, non-linear degradation curves, and class imbalance. |
| **Model Explainability** | SHAP (Kernel/Tree Explainer) | Industry standard for additive feature attribution and regulatory/operator compliance. |
| **Model Packaging** | Joblib | Efficient serialization of scikit-learn and XGBoost pipelines. |
| **Experiment Tracking** | MLflow *(Stage 4)* | Lightweight, self-hostable experiment logging and model artifact tracking. |
| **Backend API** | FastAPI, Pydantic, SQLAlchemy *(Stage 5)* | High-performance asynchronous REST API with automatic OpenAPI documentation and strict typing. |
| **Database** | PostgreSQL *(Stage 5)* | ACID-compliant relational storage for asset metadata, user auth, maintenance logs, and cached telemetry. |
| **Frontend Dashboard** | React 18+, TypeScript, Vite, Tailwind CSS *(Stage 6)* | Type-safe, reactive component interface with rapid rendering of telemetry time series. |
| **Containerization** | Docker Compose *(Stage 7)* | Deterministic local and on-premise deployment with zero vendor lock-in. |

### 4.2 Strict Architectural Constraints (Non-Goals)
To prevent bloat and maintain stability on a developer workstation (e.g. 16 GB RAM Windows laptop):
- **NO Microservices**: The system is and remains a modular monolith.
- **NO Kubernetes**: Unnecessary orchestration overhead for current scale.
- **NO Redis / Celery in early stages**: Synchronous or lightweight background threads suffice until asynchronous task queues are strictly justified.
- **NO Hardware / MQTT Gateways in Stage 1–4**: Telemetry is ingested via batch datasets and standard REST ingestion.
- **NO Unapproved Databases**: No MongoDB, Cassandra, or proprietary cloud document databases.

---

## 5. Machine Learning Requirements

### 5.1 Problem Formulations
1. **Binary Failure Classification**: Predict whether an asset will suffer a failure within an operational window $\Delta t$ (e.g., next 24 operating hours).
2. **Failure Mode Categorization**: Classify the failure mechanism (e.g., Tool Wear Failure, Heat Dissipation, Power Failure, Overstrain).
3. **Remaining Useful Life (RUL) Estimation**: Predict remaining cycles or hours before health index drops below critical threshold.

### 5.2 Feature Engineering Pipeline
- Rolling statistical aggregates (rolling mean, standard deviation, min, max, skewness) over operational time windows (e.g., 6h, 12h, 24h).
- Differential and lag features ($\Delta \text{temp} / \Delta t$, $\text{vibration}_{t} - \text{vibration}_{t-1}$).
- Domain interaction ratios (e.g., Power = Torque $\times$ Rotational Speed; Temperature differential = Process Temp - Air Temp).

### 5.3 Model Evaluation & Business Metrics
Standard classification metrics (Accuracy) are invalid due to severe class imbalance (industrial failures typically represent $< 2\%$ of operational data).
- **Primary Optimization Metrics**: PR-AUC (Precision-Recall Area Under Curve), F1-Score, and Recall (Sensitivity).
- **Custom Business Cost Metric**:
  $$\text{Cost} = C_{\text{FN}} \cdot \text{Count}(\text{FN}) + C_{\text{FP}} \cdot \text{Count}(\text{FP})$$
  Where $C_{\text{FN}} \gg C_{\text{FP}}$ (e.g., an unpredicted catastrophic failure costs \$10,000 in downtime and emergency repair, whereas a false alarm inspection costs \$200 in technician review).

---

## 6. Security, Compliance & Data Governance

1. **Secret Management**: No secrets, API keys, database credentials, or tokens in Git. All configuration is loaded from environment variables via `.env`.
2. **Dataset Privacy**: Raw industrial customer telemetry datasets must be ignored by `.gitignore` and never committed to version control.
3. **Model Reproducibility**: Fixed random seeds across data splitting, preprocessing, and model training to guarantee deterministic reproducibility.
4. **Data Isolation**: Support multi-tenant asset grouping at the database schema layer.

---

## 7. Phased Implementation Roadmap

- **Stage 1: Project Foundation & Environment (Current)**: Monolith structure, Python 3.10 virtual environment, dependencies, `.gitignore`, `.env.example`, documentation, smoke tests.
- **Stage 2: Data Ingestion & Feature Engineering**: Telemetry loaders, schema validation, missing value imputation, rolling statistics, exploratory data analysis notebooks.
- **Stage 3: ML Modeling & Baselines**: Baseline models (Logistic Regression, Random Forest), XGBoost gradient boosting classifier, cross-validation, PR-AUC / Cost optimization.
- **Stage 4: Explainability & Model Registry**: SHAP explainability pipelines, model serialization via Joblib, experiment logging.
- **Stage 5: FastAPI Backend**: REST API endpoints for asset management, telemetry ingestion, live inference, and health predictions.
- **Stage 6: React Frontend Dashboard**: Interactive UI with telemetry charts, risk badges, SHAP breakdown visualizers, and alert management.
- **Stage 7: Integration, Containerization & End-to-End Validation**: Docker Compose configuration, full pipeline verification, and production readiness audit.

