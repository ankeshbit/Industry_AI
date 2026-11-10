# INDUSTRIA AI — Industrial Predictive-Maintenance SaaS Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Stage%201%20Foundation-success.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-orange.svg)]()

---

## 1. Overview & Core Objective

**INDUSTRIA AI** is a predictive-maintenance SaaS platform built to safeguard mission-critical industrial machinery, reduce unplanned downtime, and optimize maintenance intervention schedules.

Industrial plants and asset operators typically rely on either reactive maintenance (fixing equipment after failure, causing expensive production stops) or static preventative maintenance (servicing equipment at arbitrary fixed intervals, causing needless part replacements).

### Main Objectives:
- **Continuous Condition Monitoring**: Analyze industrial sensor telemetry (temperatures, vibrations, rotational velocities, torque, pressures, and electrical draw) to identify early mechanical and electrical degradation.
- **Predictive Failure Classification**: Classify imminent failure types (tool wear, thermal dissipation, overstrain, power failure) with confidence intervals.
- **Remaining Useful Life (RUL)**: Estimate remaining operational hours or cycles before equipment exceeds critical failure thresholds.
- **Interpretable Root Cause Insights**: Provide plant reliability engineers with explainable AI (SHAP) attributions explaining *why* an asset was flagged.
- **Cost-Optimized Maintenance Decisions**: Weigh classification thresholds using realistic operational cost penalties ($C_{\text{FN}} \gg C_{\text{FP}}$).

---

## 2. Current Development Milestone

> **Current Status: Stage 1 — Project Foundation & ML Environment Setup**
>
> In Stage 1, we established the modular-monolith directory layout, configured the Python 3.10 virtual environment, pinned the initial machine learning dependencies, authored documentation templates, and implemented baseline environment smoke tests.

---

## 3. Project Architecture

INDUSTRIA AI follows a strict **modular monolith** design to ensure high velocity and clean domain separation without distributed microservices complexity:

```
industria-ai/
│
├── frontend/             # Single-Page Dashboard (React + TypeScript + Vite + Tailwind CSS)
├── backend/              # RESTful API Service (FastAPI + SQLAlchemy + Pydantic)
├── ml/                   # Machine Learning Core
│   ├── datasets/         # Telemetry data storage
│   │   ├── raw/          # Raw dataset files (excluded from Git)
│   │   └── processed/    # Cleaned, feature-engineered datasets
│   ├── notebooks/        # Exploratory analysis & prototyping notebooks
│   ├── experiments/      # Experiment configurations and run logs
│   ├── src/              # Production-grade ML pipeline modules
│   │   ├── data/         # Ingestion, validation, dataset loaders
│   │   ├── preprocessing/# Imputation, scaling, outlier filters
│   │   ├── features/     # Rolling statistics, lag features, interaction terms
│   │   ├── models/       # Estimators, XGBoost/tree models, serialization
│   │   ├── evaluation/   # Metrics (PR-AUC, F1, Cost matrix), SHAP attribution
│   │   └── utils/        # Paths, logging, seed configuration
│   ├── artifacts/        # Serialized model binaries (.joblib) and plots
│   ├── tests/            # ML-specific unit tests
│   └── requirements.txt  # ML package dependencies
│
├── docs/                 # Documentation & Governance
│   ├── PRD.md            # Master Product Requirements Document
│   ├── DATASET_NOTES.md  # Standardized telemetry dataset documentation template
│   └── ML_EXPERIMENT_LOG.md # Experiment tracking register
│
├── infra/                # Infrastructure & deployment
│   └── docker/           # Docker Compose and Dockerfile specifications
│
├── tests/                # System-level smoke tests
├── .env.example          # Environment variables template
├── .gitignore            # Git exclusion rules
├── requirements.txt      # Root entry-point requirements
└── README.md             # Project master overview
```

---

## 4. Development Environment Setup

### Prerequisites
- **Operating System**: Windows 10/11, macOS, or Linux (optimized for standard developer laptops, e.g. 16 GB RAM).
- **Python**: Python 3.10 (verified 64-bit).
- **Git**: Installed and configured.

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/ankeshbit/Industry_AI.git
cd Industry_AI
```

#### 2. Create the Python Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
```
On macOS / Linux:
```bash
python3 -m venv .venv
```

#### 3. Activate the Virtual Environment
On Windows (PowerShell):
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell displays an Execution Policy restriction, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`)*

On Windows (Command Prompt):
```cmd
.venv\Scripts\activate.bat
```

On macOS / Linux:
```bash
source .venv/bin/activate
```

#### 4. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r ml/requirements.txt
```
*(Alternatively, from root: `pip install -r requirements.txt`)*

#### 5. Verify Environment and Run Tests
```powershell
pytest
```

---

## 5. Technology Stack Decisions

| Component | Selected Technology | Purpose & Rationale |
|---|---|---|
| **Language** | Python 3.10+ | Robust data science, telemetry processing, and backend integration. |
| **Data Processing** | NumPy, Pandas | High-performance vectorized numerical and tabular operations. |
| **Machine Learning** | Scikit-learn, XGBoost | Industry standard gradient boosting suited for tabular sensor data. |
| **Explainability** | SHAP | Additive feature attribution providing operators with root-cause insights. |
| **Notebooks** | JupyterLab | Interactive data exploration and telemetry analysis. |
| **Backend API (Stage 5)**| FastAPI | Asynchronous REST endpoints, Pydantic typing, auto-generated OpenAPI docs. |
| **Database (Stage 5)** | PostgreSQL + SQLAlchemy | Relational storage for equipment metadata, maintenance logs, and cached telemetry. |
| **Frontend (Stage 6)** | React, TypeScript, Vite, Tailwind | Responsive, component-driven dashboard for live telemetry monitoring. |
| **Infrastructure (Stage 7)**| Docker Compose | Deterministic multi-container development and local orchestration. |

---

## 6. Planned Development Stages

1. **Stage 1: Project Foundation & ML Environment Setup** *(Completed)*
   - Initial modular-monolith structure.
   - Python virtual environment configuration and dependency pinning.
   - Project documentation (`PRD.md`, `DATASET_NOTES.md`, `ML_EXPERIMENT_LOG.md`).
   - Git and environment security rules (`.gitignore`, `.env.example`).
   - Smoke and environment verification test suites.

2. **Stage 2: Data Ingestion, EDA & Feature Engineering**
   - Telemetry dataset ingestion and schema validation.
   - Exploratory data analysis (EDA) for sensor correlation and failure trends.
   - Windowed feature extraction (rolling means, variances, physical interaction terms).

3. **Stage 3: ML Model Training & Baseline Benchmarking**
   - Baseline models (Logistic Regression, Random Forest).
   - Tuned XGBoost gradient boosted classifier.
   - Stratified evaluation using PR-AUC, Recall, and business cost functions.

4. **Stage 4: Model Explainability, Persistence & MLflow Tracking**
   - SHAP tree explainer integration.
   - Model artifact serialization with Joblib.
   - MLflow experiment logging and model artifact registry.

5. **Stage 5: FastAPI Backend Development**
   - REST endpoints for asset telemetry ingestion and real-time failure prediction.
   - SQLAlchemy ORM models and PostgreSQL schema migrations.

6. **Stage 6: React Dashboard & Visualization**
   - Telemetry time-series charts, equipment health status cards, and SHAP attribution views.

7. **Stage 7: Integration, Containerization & End-to-End Validation**
   - Docker Compose local stack orchestration, pipeline regression testing, and production deployment readiness.

