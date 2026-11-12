# INDUSTRIA AI — Industrial Predictive-Maintenance SaaS Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Milestone%201%20Complete-success.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-orange.svg)]()
[![License](https://img.shields.io/badge/PRD%20Version-v1.2%20Authoritative-purple.svg)]()

---

## 1. Overview & Authoritative Specification

**INDUSTRIA AI** is an industrial predictive-maintenance software platform designed to safeguard mission-critical machinery, reduce unplanned downtime, and optimize maintenance intervention schedules.

The platform is specified authoritatively by **INDUSTRIA AI PRD v1.2** (`PRD.md`), which mandates:
- **Modular Monolith SaaS Architecture:** Pure software design with zero IoT hardware, zero MQTT/streaming overhead, and zero microservices complexity.
- **Reference-Only Reliability Tier:** The initial reference dataset (AI4I 2020 Predictive Maintenance Dataset) and trained baseline models (`ai4i_failure_clf_notype` and `ai4i_failure_clf_typed`) operate strictly under the `REFERENCE_ONLY` reliability tier. Advisory notices and limitation acknowledgements are enforced across all APIs and UIs.
- **Defense-in-Depth Multi-Tenancy:** Single shared database schema with tenant isolation enforced via `organisation_id` on every tenant table. Single-organisation mode is enabled by default (`MULTI_ORG_ENABLED=false`).

---

## 2. Milestone 1 Status: COMPLETE

Milestone 1 — Core AI4I Predictive Maintenance (§18.3, lines 2612–2622) is fully implemented, verified, and audited:

| Requirement Area | PRD v1.2 Clauses | Status | Verification |
| :--- | :--- | :--- | :--- |
| **Multi-Tenancy & Auth** | AC-ORG-1..3, AC-SEC-1..4 | Verified | 10 tests passing; Argon2id, JWT refresh rotation, 5-failure lockout, single-org mode enforcement |
| **Machine Registry** | AC-MM-1..3 | Verified | 6 tests passing; 5 standard categories seeded, unique asset tags per tenant, default plant mapping |
| **Dataset Ingestion** | AC-DS-1..7, 9, 10 | Verified | 6 tests passing; 50 MB stream limit, magic bytes validation, SHA-256 deduplication, Quality Score $Q$, forbidden feature blocking |
| **Compatibility Engine** | AC-CE-1..7, AC-AP-1..5 | Verified | 6 tests passing; 3-stage validation, reference range OOD applicability check ($\le 1\%$ clean, $>30\%$ blocked), asserted equivalence |
| **Inference & Risk Engine** | AC-FP-1..6, 8 | Verified | XGBoost pipelines for `NO_TYPE` and `WITH_TYPE`, threshold $\tau=0.45$, unit normalization (degC $\rightarrow$ K), top highest-risk operating states |
| **Job Queue & Worker** | AC-JOB-1..5 | Verified | 2 tests passing; transactional idempotency, polling worker process, status tracking |
| **Container & Deployment** | AC-PLAT-1 | Verified | `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml` (API, worker, PostgreSQL, React SPA) |
| **Frontend SPA** | PRD §14, §18.3 | Verified | React + Vite + Tailwind CSS dashboard with mandatory Trust Panel, wizard, and warning acknowledgement |
| **Authoritative Exit Test** | PRD v1.2 §18.3 (11 steps) | Verified | 100% pass on exact 11-step end-to-end integration test (`backend/tests/test_milestone1_exit.py`) |

---

## 3. Architecture & Directory Structure

```
Industry_AI/
├── PRD.md                    # Master Authoritative PRD v1.2 (3,484 lines)
├── docker-compose.yml        # Full-stack composition (Postgres, API, Worker, Web)
├── Dockerfile.backend        # Multi-stage Python 3.10 backend container
├── Dockerfile.frontend       # Multi-stage Node/Nginx frontend container
│
├── backend/                  # RESTful API & Queue Worker (FastAPI + SQLAlchemy 2.0)
│   ├── app/
│   │   ├── api/              # API Route Handlers (auth, machines, datasets, compatibility, analyses, jobs)
│   │   ├── models/           # SQLAlchemy 2.0 models with organisation_id
│   │   ├── schemas/          # Pydantic v2 schemas and validation models
│   │   ├── services/         # Domain services (auth, machine, dataset, compatibility, inference, queue, worker)
│   │   ├── config.py         # App configuration & environment variables
│   │   ├── database.py       # DB engine, session factory, context vars
│   │   ├── seed.py           # Database initial seeds (categories, profiles, models)
│   │   └── main.py           # FastAPI application entry point
│   ├── requirements.txt      # Backend production dependencies
│   └── tests/                # Automated pytest suites for backend
│
├── frontend/                 # Web Dashboard SPA (React 18 + TypeScript + Vite + Tailwind CSS)
│   ├── src/
│   │   ├── components/       # TrustPanel, MachineRegistry, DatasetUploadWizard, CompatibilityModal, AnalysisView
│   │   ├── api.ts            # Typed REST API client
│   │   ├── App.tsx           # Application shell & navigation
│   │   └── main.tsx          # Client entry point
│   ├── package.json
│   └── vite.config.ts
│
├── ml/                       # Machine Learning Core
│   ├── artifacts/models/     # Serialized reference models (EXP-008 NO_TYPE, EXP-004 WITH_TYPE)
│   ├── src/                  # ML pipeline, features, evaluation, training
│   └── tests/                # Baseline and feature engineering test suites
│
├── docs/                     # Documentation & Model Cards
│   ├── PRD.md                # Mirrored PRD v1.2
│   ├── model_cards/          # ai4i_failure_clf_notype.md & ai4i_failure_clf_typed.md
│   └── DATASET_NOTES.md      # AI4I 2020 telemetry dataset documentation
│
└── samples/                  # Authoritative Test CSV Files
    ├── ai4i_sample_clean_celsius_no_type.csv
    ├── ai4i_sample_missing_torque.csv
    └── ai4i_sample_typed_operating_data.csv
```

---

## 4. Running the Platform

### Option A: Local Development Setup

#### 1. Backend & ML Environment
Activate the virtual environment and install dependencies:
```powershell
# Windows
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Run the backend API server:
```powershell
uvicorn backend.app.main:app --reload --port 8000
```
*API documentation is available at `http://localhost:8000/docs`.*

In a separate terminal, run the asynchronous job worker:
```powershell
python -m backend.app.services.worker
```

#### 2. Frontend Development Server
```powershell
cd frontend
npm install
npm run dev
```
*The React SPA will be accessible at `http://localhost:3000` (port set in `vite.config.ts`; `/api` is proxied to the backend on port 8000).*

---

### Option B: Docker Compose (Full Stack)

> **Prerequisite:** the reference model files (`ml/artifacts/models/*.joblib`) are gitignored. Place `ai4i2020.csv` in `ml/datasets/raw/` and run `python ml/experiments/run_baseline_experiments.py` *before* `docker compose up --build`, otherwise the image has no models and analyses fail with `Model artifact not found`.

To run the complete production-like stack (PostgreSQL, Backend API, Worker, and Frontend Nginx):
```bash
docker compose up --build
```
- Web Application: `http://localhost:3000`
- API & Docs: `http://localhost:8000/docs`
- Database: PostgreSQL on port 5432

---

## 5. Automated Verification & Testing

Run the automated test suite (ML baselines, smoke tests, and backend suites):

```powershell
.venv\Scripts\python -m pytest
```

### Milestone 1 Authoritative Exit Test
To specifically execute the exact 11-step end-to-end integration exit test (§18.3):
```powershell
.venv\Scripts\python -m pytest backend/tests/test_milestone1_exit.py -v
```

This exit test verifies:
1. First organisation registration succeeds.
2. Second registration is refused with `403 MULTI_ORG_DISABLED`.
3. Machine creation and asset tag assignment.
4. Upload of AI4I CSV with renamed headers, Celsius temperatures, and no Type column.
5. Column mapping wizard suggestions and unit conversion ($\text{degC} \rightarrow \text{K}$).
6. Pipeline evaluation offering only `NO_TYPE` (`WITH_TYPE` is marked `INCOMPATIBLE` due to missing `product_type`).
7. User warning and reference model limitation acknowledgement.
8. Asynchronous failure prediction analysis execution.
9. Result persistence with Trust Panel provenance, OOD domain summary, and top highest-risk operating states.
10. Refusal with remedies on CSV missing torque (`E_MISSING_FEATURE`).
11. Full compatibility and dual configuration offer on CSV containing Type column with asserted equivalence.

---

## 6. Trust & Transparency Framework

As mandated by PRD v1.2 §14.2, every prediction result displayed in the UI and returned by the API is accompanied by the standing advisory notice:

> **Reference Model Standing Advisory**  
> "This analysis was produced using a reference model trained on the AI4I 2020 Predictive Maintenance Dataset. It reflects machine tool operating patterns from that reference dataset and has not been validated on your specific equipment or operating conditions. Predictions must be treated as advisory inputs to human maintenance decisions, not as definitive health assessments. The operator assumes full responsibility for maintenance decisions."
