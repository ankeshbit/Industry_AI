INDUSTRIA AI – Product Requirements Document v1.2
Pure-Software, Multi-Tenant B2B SaaS for Industrial Predictive Maintenance Analytics
Version 1.2 · Supersedes v1.1 (kept in the previous tab) · Status: Pre-development baseline · Audience: engineering team and AI coding agents
What changed in v1.2. (1) AI4I Type is no longer a universal required feature: two AI4I configurations (with and without Type) are defined. (2) Dataset compatibility, model applicability and model reliability are now three separate concepts with separate outputs, and every model is labelled as reference-dataset-trained. (3) The roadmap is rebuilt as six realistic milestones, with minimum authentication and tenant isolation in Milestone 1. (4) Motor current signature analysis (MCSA) is added as a future, software-only enhancement. (5) Local development and production SaaS architectures are distinguished. Version history, change summary, consistency audit and open decisions are in Appendices A–E.
Reading guide. Requirements carry IDs (e.g. FR-DS-04) and a milestone tag MS1–MS6 (§18). No model-performance claim is made anywhere: metrics are reporting requirements, not promises, and no experimental result is stated in this document.
1. Executive Summary
INDUSTRIA AI is a pure software-based, multi-tenant B2B SaaS platform for predictive maintenance and machine failure analysis. It is not an IoT product: it needs no sensors, devices, messaging protocols, hardware installation or live streams. Engineers and analysts use the web interface to upload existing industrial datasets (tabular files, vibration signal files, audio recordings). The platform validates them, decides which independent ML pipeline can process them, runs the analysis as a background job, explains the result, recommends maintenance actions, and tracks outcomes.
The central experience is:
Upload industrial datasets → validate and understand the data → select a compatible ML pipeline → generate predictions and diagnostics → explain results and their limits → recommend maintenance actions → track and report outcomes.
The platform is built on independent ML pipelines, each with its own schema, preprocessing, models and evaluation:
Pipeline
Reference (training) dataset
Output
Milestone
A – Failure prediction
AI4I 2020 (synthetic)
Failure probability for the supplied operating state (no time horizon), failure-mode probabilities, risk class, SHAP. Two configurations: with and without the AI4I Type feature
MS1–MS2
B – Remaining Useful Life
NASA C-MAPSS (simulated turbofan)
RUL in cycles with interval
MS4
C – Bearing fault diagnosis
Paderborn University (laboratory)
Bearing condition class from vibration windows
MS4
E – Sensor anomaly detection (supplementary)
None (fitted on the user's normal reference segment)
Deviation from the user's own reference
MS4
D – Acoustic anomaly detection
MIMII (laboratory sound)
Anomaly score and label per recording
MS6
F – Motor current signature analysis
Future enhancement, not in any milestone (§21.3)
–
Future
Three questions are kept strictly separate (§4.4): Is this dataset compatible with the pipeline? (format, schema, units, sampling). Is the trained model applicable to this machine and data distribution? (reference-domain coverage, warnings). Is there evidence that the model is reliable for this application? (validation evidence). Passing the first never implies the other two. Every model in v1.2 is a reference-dataset-trained model, and every result says so.
Honest scope statement. Public datasets are synthetic, simulated or laboratory-generated. Their evaluation metrics describe behaviour on those datasets, not on a customer's equipment. INDUSTRIA AI provides advisory, explainable analysis; it is not a safety system and never controls, shuts down or modifies machinery.
2. Product Vision
Vision: give maintenance and reliability teams a trustworthy way to turn the industrial data they already hold into explainable condition assessments and prioritised maintenance actions, with complete provenance and honest statements about what the analysis can and cannot support.
Non-negotiable principles
1. INDUSTRIA AI is a pure software-based, multi-tenant B2B SaaS platform.
2. Engineers and analysts interact through the web interface.
3. Users upload existing industrial datasets for analysis.
4. The system validates data and selects compatible ML pipelines.
5. ML inference and analysis run through background processing where appropriate.
6. Users receive insights, explanations, maintenance recommendations and reports.
7. Multiple independent ML pipelines are supported, each with its own input schema and preprocessing.
8. The platform never claims real-time monitoring when only uploaded or historical data exists.
9. The platform never automatically controls, shuts down or modifies physical machinery.
10. Predictions are advisory and are never represented as safety-critical guarantees.
11. Simulated data, where supported, is explicitly labelled as simulated and never presented as real measurements.
12. Hardware integration, IoT connectivity, MQTT, live streaming and device registration are not part of the product, now or later.
Design principles
• Compatibility, applicability and reliability are different things and are reported separately.
• No invented features. The platform never creates, infers or assigns a feature a dataset does not contain; equivalence between a customer column and a reference feature is only ever asserted by the user, explicitly, and recorded.
• Provenance everywhere: every result states its dataset version, mapping, pipeline profile, model configuration and version, and training domain.
• Reference-trained, stated plainly. Models trained on public data are labelled as such wherever results appear.
• Tenant isolation first: minimum isolation exists from the first milestone, before more than one organisation can use the system.
• Local-first, SaaS-shaped: the first implementation runs locally on a 16 GB laptop behind interfaces that map to a production SaaS deployment without a rewrite.
3. Problem Statement
Teams hold exports, test campaigns, vibration files and recordings, but converting them into decisions is hard: ad-hoc notebooks, inconsistent preprocessing, no audit trail, unclear model applicability, black-box scores without explanation, and results disconnected from maintenance actions.
Constraints that shape the solution
• The reference datasets are public and partly synthetic or laboratory-generated. Their metrics cannot be assumed to hold on any customer's machines, and the platform must never present them as such.
• Real customer data will often not match the narrow reference schemas. INCOMPATIBLE and INSUFFICIENT_DATA outcomes, with actionable feedback, are a normal and correct result of the product working properly.
• Even compatible data can fall outside what a model has seen. Applicability warnings are signals, not guarantees.
• A software-only product cannot verify how data was collected; plausibility checks are explicit and visible.
• The initial team is small; the roadmap must deliver a useful, honest product incrementally.
4. Objectives, Success Metrics and Scope
4.1 Objectives
ID
Objective
OBJ-1
Deliver a secure workflow from dataset upload to validated, versioned analysis results, starting with Pipeline A in Milestone 1.
OBJ-2
Provide independent, reproducibly trained and evaluated ML pipelines, with baselines before advanced models and fair comparison of alternative configurations.
OBJ-3
Provide a compatibility engine with five explicit statuses, separate applicability and reliability assessments, and machine-readable reasons.
OBJ-4
Provide SHAP explanations for tabular models with a non-causality disclaimer.
OBJ-5
Provide a maintenance workflow from recommendation to engineer decision, scheduling, outcome and report.
OBJ-6
Establish tenant isolation at the data layer before any multi-organisation access.
OBJ-7
Define (but not require for the MVP) customer-specific validation and retraining.
OBJ-8
Run end to end locally on a 16 GB laptop, with an architecture that evolves into a production SaaS deployment without a rewrite.
4.2 Success metrics
Process metrics have fixed targets. Model metrics are reporting requirements only.
ID
Metric
Target
SM-1
Every registered model has a complete MLflow run (parameters, metrics with CI, data hash, git commit, artifacts, model card)
100%
SM-2
Baseline reported before any advanced model, per pipeline
100%
SM-3
Both AI4I configurations (with and without Type) evaluated on the identical split, folds and test set before either is promoted
100%
SM-4
Cross-tenant reads or writes in automated isolation tests
0
SM-5
Analyses started on data with a non-runnable compatibility status or a blocked applicability level
0 (enforced server-side)
SM-6
Results shown without the reference-model label, applicability level and reliability tier
0 (UI and report tests)
SM-7
Backend line coverage: compatibility engine and tenant layer ≥ 85%; other services ≥ 80%
Met by MS3
SM-8
Upload-to-validation-report for a 50 MB CSV on the reference laptop
≤ 60 s
SM-9
Fresh clone to running local stack via Docker Compose (excluding dataset downloads)
≤ 20 minutes
SM-10
Assistant numeric claims absent from tool outputs on the 50-question set (MS6)
0
4.3 Scope
In scope (long-term product vision): organisation, plant, user and machine management; dataset management; compatibility, applicability and reliability assessment; asynchronous batch analysis; Pipelines A, B, C, D and E; explainability; maintenance recommendations and management; reports; plans, quotas and usage; assistant; customer-specific validation. Delivery order is defined by the milestones in §18. The MVP is Milestones 1–3 only; Milestones 4–6 are post-MVP expansion. The long-term vision is not the MVP.
Out of scope: see §21.1.
4.4 Compatibility, applicability and reliability
Concept
Question
Decided by
Output
Can block a run?
What a good result does not prove
Dataset compatibility
Does the dataset have the required format, features, units, sampling characteristics and schema for this pipeline profile?
Compatibility engine (§8.4)
One of COMPATIBLE, COMPATIBLE_WITH_WARNINGS, INCOMPATIBLE, INSUFFICIENT_DATA, UNSUPPORTED_FORMAT, with reasons
Yes (non-runnable statuses)
That the model suits this machine or that its predictions are trustworthy
Model applicability
Is the reference-trained model plausibly appropriate for this machine category, operating conditions and data distribution?
Applicability assessment (§8.4.4)
Level: IN_REFERENCE_RANGE, PARTLY_OUTSIDE_REFERENCE_RANGE, MOSTLY_OUTSIDE_REFERENCE_RANGE, plus domain-transfer notes
Only at MOSTLY_OUTSIDE_REFERENCE_RANGE (configurable)
That the model is reliable. An out-of-distribution (OOD) check is a warning mechanism: inputs inside the reference ranges can still be mis-predicted, and inputs outside may still be predicted acceptably
Model reliability
Is there validation evidence that the model's predictions can be trusted for this intended application?
Validation evidence (§10.7)
Tier: REFERENCE_ONLY (all results in MS1–MS5) or CUSTOMER_VALIDATED (future, MS6, scoped to a machine/profile/model version)
No, but the tier is always displayed and cannot be hidden
That performance on public datasets equals performance on customer equipment
Rules that follow: (a) compatibility never raises reliability; (b) research-dataset metrics and customer-specific validation results are shown in separate, labelled sections; (c) results on customer data always read Reference-dataset-trained model – not validated on your equipment unless the tier is CUSTOMER_VALIDATED; (d) a first analysis per machine, profile and model version requires an explicit acknowledgement of these limits.
4.5 Primary user workflow
Step
Actor
Action
System behaviour
1
User
Registers and creates an organisation
Creates the organisation and first admin (MS1: minimal tenant boundary; second organisations are disabled until the MS3 isolation gate passes, §18.4)
2
User
Creates or selects a plant
MS1 uses an automatically created default plant; plant management UI arrives in MS3
3
User
Registers a machine with category and metadata
The category determines which pipelines may be offered
4
User
Uploads one or more datasets for the machine
Streamed, scanned, hashed, versioned; limits enforced
5
System / User
Dataset type and objective identified or confirmed
The system proposes; the user confirms
6
System
Validates schema, types, units, timestamps, quality and compatibility
Produces a validation report and a compatibility result per eligible profile
7
System
Assesses applicability and states the reliability tier
Applicability level and REFERENCE_ONLY shown beside the compatibility status
8
User
Selects a runnable pipeline profile, acknowledges warnings and the reference-model limitation
Only runnable combinations can be started
9
System
Preprocesses and runs the background inference job
Progress, retry, cancellation, idempotency
10
System
Stores results linked to machine, dataset version, profile, configuration, model version
Immutable; re-runs create new versions
11
User
Explores results with explanations and the trust panel
Provenance and limitations on every result
12
User
Reviews recommendations and manages maintenance
Advisory; engineer decision (MS5)
13
User
Exports reports
PDF and CSV with provenance and limitations
Unsupported, incomplete or incompatible data ends in specific, actionable messages and, where fixable, the onboarding wizard. A model is never run "best effort" on incompatible data.
5. Target Users, Roles and Personas
5.1 Roles
Roles are organisation-scoped; a user belongs to one organisation in v1.x. Role introduction by milestone: MS1 has a single role (ORG_ADMIN, held by the user who created the organisation); MS3 introduces the four-role model and invitations. The full matrix below is the MS3 target.
Capability
Org Admin
Maintenance Engineer
Data Analyst
Viewer
Manage organisation, plan, usage view
✔
–
–
–
Invite and deactivate users, assign roles and plants
✔
–
–
–
Create/edit plants
✔
–
–
–
Create/edit/archive machines
✔
✔
–
–
Upload datasets; edit mappings, units, dataset type
✔
✔
✔
–
Delete datasets
✔
✔ (own)
✔ (own)
–
Run analyses; cancel/retry own jobs
✔
✔
✔
–
Acknowledge compatibility warnings and the reference-model limitation
✔
✔
✔
–
View results, explanations, dashboards
✔
✔
✔
✔
Approve / reject / defer recommendations (MS5)
✔
✔
–
–
Create and update maintenance records (MS5)
✔
✔
–
–
Generate and download reports
✔
✔
✔
✔ (read-only types)
Request customer-specific validation (MS6)
✔
✔
✔
–
View audit log
✔
–
–
–
View model catalogue and model cards
✔
✔
✔
✔
Platform roles (not tenant users): Platform Operator (model releases, plans, platform health; no standing access to tenant data; audited, time-limited support grants) and ML Engineer (trains and registers models on public data only).
5.2 Personas
Asha – Organisation Admin. Sets up the organisation, users and plants; watches usage and audit logs. Needs assurance of isolation and clear limits.
Ravi – Maintenance Engineer. Uploads machine data, reads validation feedback, runs compatible analyses, reads explanations and limitations, approves or rejects recommendations with reasons.
Dev – Data Analyst. Maps columns and units, assesses quality, compares dataset versions and results, and (from MS6) validates models against the organisation's own labelled history.
Meera – Viewer. Reads dashboards and reports; needs unambiguous provenance and a clear statement of what the numbers mean.
6. Functional Requirements (index)
The MS column gives the milestone in which the requirement is delivered (§18). MS1–MS3 form the MVP. Section 8 gives behaviour; Appendix B maps IDs to specifications, APIs, tables and acceptance criteria.
6.1 Organisation, tenancy and machines
ID
Requirement
MS
FR-ORG-01
Registration creates an organisation and its first admin; password rules, lockout, refresh-token rotation
1
FR-ORG-02
Minimum tenant boundary: every tenant-owned row carries organisation_id; all data access goes through a TenantContext; PostgreSQL RLS policies on all tenant tables; cross-tenant access returns 404
1
FR-ORG-03
Single-organisation mode: until the MS3 isolation gate passes, creating a second organisation is disabled by configuration
1
FR-ORG-04
Organisation settings (name, timezone, retention, default units)
3
FR-ORG-05
Plant management (an automatic default plant exists from MS1)
3
FR-ORG-06
Four tenant roles with the permission matrix of §5.1; invitations with expiring single-use tokens; email verification
3
FR-ORG-07
Audit log (append-only) for security-relevant actions and an Org Admin view
3
FR-ORG-08
Dataset ownership and access controls: creator, plant-level access, role-based edit/delete rules
3
FR-ORG-09
Full tenant-isolation test suite is a CI gate; second organisations are enabled only after it passes
3
FR-ORG-10
User deactivation; an organisation cannot lose its last active Org Admin
3
FR-MM-01
Register machines with category, identifiers and metadata (MS1: attached to the default plant)
1
FR-MM-02
Machine categories define which dataset types and pipelines may be offered
1
FR-MM-03
Archive (soft-delete) machines
1
FR-MM-04
Machine health assessment derived from the latest completed analyses by the documented rule (§8.2.3), always with an as-of data date and the reliability tier of the contributing results
2
FR-MM-05
A machine may have several datasets; they are never combined without a defined and validated fusion strategy (none exists)
1
FR-MM-06
Bulk machine import from CSV
5
6.2 Dataset management (major module)
ID
Requirement
MS
FR-DS-01
Upload CSV (MS1); Excel .xlsx and Parquet (MS4); vibration signal .mat/.wav (MS4); audio WAV and ZIP of WAV (MS6)
1/4/6
FR-DS-02
Per-file size and row limits (configuration in MS1–MS4); plan-based storage, upload and dataset quotas (MS5)
1/5
FR-DS-03
Secure upload handling: streaming, quarantine, magic-byte validation, sanitised keys, scan hook
1
FR-DS-04
Dataset metadata and machine association
1
FR-DS-05
Immutable dataset versions with change summary
1
FR-DS-06
Dataset preview (rows and column statistics; later waveform, spectrum, spectrogram)
1
FR-DS-07
Dataset type and objective proposed by the system and confirmed by the user
1
FR-DS-08
Column mapping to a profile's canonical features, saved as mapping versions. Suggestions are never auto-applied; the platform never creates, infers or assigns a feature the dataset does not contain (§8.3.6)
1
FR-DS-09
Unit selection and conversion with plausibility checks
1
FR-DS-10
Timestamp, cycle-index and sampling validation
1 (basic), 4 (cycles, signals)
FR-DS-11
Missing-value assessment
1
FR-DS-12
Duplicate detection
1
FR-DS-13
Outlier assessment (flag only)
1
FR-DS-14
Data quality score with documented calculation
1
FR-DS-15
Validation report (stored, versioned, exportable)
1
FR-DS-16
Processing history per dataset version
1
FR-DS-17
Dataset deletion (30-day grace) and retention policies
1 (deletion), 3 (org settings)
FR-DS-18
Guided onboarding wizard for non-matching schemas
1
FR-DS-19
Downloadable schema templates per pipeline profile
2
6.3 Compatibility, applicability, reliability and jobs
ID
Requirement
MS
FR-CE-01
Versioned pipeline profiles: machine categories, dataset types, required/optional/forbidden features, units, sampling, preprocessing recipe, model configurations and versions
1
FR-CE-02
Compatibility status is exactly one of COMPATIBLE, COMPATIBLE_WITH_WARNINGS, INCOMPATIBLE, INSUFFICIENT_DATA, UNSUPPORTED_FORMAT
1
FR-CE-03
Machine-readable reasons (code, severity, feature, observed, expected, remedy)
1
FR-CE-04
Server-side gate: no job is created unless compatibility is runnable, applicability is not blocked, warnings are acknowledged, and the reference-model limitation is acknowledged
1
FR-CE-05
Compatibility is evaluated per profile; for Pipeline A both configuration profiles are evaluated and the runnable ones offered (§8.4.5)
1
FR-CE-06
No implicit multi-dataset fusion
1
FR-CE-07
New profiles are versioned configuration plus tests
4
FR-AP-01
Applicability assessment (§8.4.4) separate from compatibility: reference-range coverage, domain notes, level
1
FR-AP-02
OOD flags per row/window; documented as a warning mechanism, never as proof of reliability
1
FR-AP-03
Reliability tier on every result: REFERENCE_ONLY in MS1–MS5; CUSTOMER_VALIDATED only through the MS6 mechanism
1
FR-AP-04
Every model is labelled reference-dataset-trained in UI, API, reports and model cards
1
FR-AP-05
First analysis per (machine, profile, model version) requires an explicit limitation acknowledgement, stored with user and time
1
FR-AP-06
Trust panel on every result showing compatibility, applicability, reliability and limitation text
2
FR-AP-07
Model cards and result views keep reference-dataset evaluation and customer-specific validation in separate sections
2
FR-JOB-01
Asynchronous background jobs for validation and inference (PostgreSQL queue)
1
FR-JOB-02
Job states, progress, step names
1
FR-JOB-03
Retry only for transient errors
1
FR-JOB-04
Idempotent job creation
1
FR-JOB-05
Cancellation
2
FR-JOB-06
Error reporting with user message, remedy and diagnostic id
1
FR-JOB-07
Result versioning; re-runs never overwrite results
1
FR-JOB-08
Per-job usage events (metering records), quota enforcement from MS5
5
6.4 Analysis pipelines
ID
Requirement
MS
FR-FP-01
Pipeline A: failure probability for the supplied operating-state rows (no future horizon is claimed)
1
FR-FP-02
Two AI4I model configurations: with Type and without Type; selected by available features, never by inference (§10.1)
1
FR-FP-03
Risk class from the reference-calibrated probability and model-version thresholds, labelled as a reference-model class
1
FR-FP-04
Per-row and aggregate results with OOD flags
1
FR-FP-05
Failure-mode probabilities (TWF, HDF, PWF, OSF) where the minimum-positives gate is met
2
FR-FP-06
Limitations panel on every result
2
FR-RUL-01
Pipeline B: RUL in cycles with interval
4
FR-RUL-02
RUL cap and capped convention shown
4
FR-RUL-03
Degradation trend visualisation
4
FR-RUL-04
Only compatible turbofan-type datasets or machine profiles
4
FR-FD-01
Pipeline C: bearing condition classification from vibration windows
4
FR-FD-02
FFT, PSD and envelope visualisation
4
FR-FD-03
Signal-quality checks
4
FR-SA-01
Capability E: user-designated normal reference segment
4
FR-SA-02
Unsupervised scoring (Isolation Forest, One-Class SVM, Autoencoder) fitted per analysis
4
FR-SA-03
Severity and event grouping
4
FR-AC-01
Pipeline D: acoustic anomaly score and label per recording
6
FR-AC-02
Waveform and spectrogram visualisation
6
FR-AC-03
Supported machine categories limited to the training profile
6
FR-CV-01
Customer-specific validation runs against the organisation's own labelled history
6
FR-CV-02
Validation criteria, minimum positives and proper splits defined and stored
6
FR-CV-03
Scoped reliability-tier upgrade to CUSTOMER_VALIDATED per machine, profile and model version
6
FR-CV-04
Optional tenant-private retraining/fine-tuning producing tenant-private model versions; never shared across tenants
6
FR-CV-05
Customer-specific validation and retraining are optional and never required for any milestone before MS6
6
6.5 Explainability, maintenance, plans, reports, assistant
ID
Requirement
MS
FR-XAI-01
SHAP explanations for tree models (local top-k and global importance)
2
FR-XAI-02
Non-causality disclaimer in every explanation view and report
2
FR-XAI-03
Anomaly insights (Capability E; Pipeline D reconstruction-error maps)
4 / 6
FR-MR-01
Rules-based recommendations from analysis results, labelled as based on uploaded data and a reference-trained model, not real-time monitoring
2
FR-MR-02
Approve / reject (reason code) / defer by an engineer
5
FR-MR-03
Maintenance task management and scheduling
5
FR-MR-04
Maintenance history and outcome capture
5
FR-MR-05
Findings (result-derived notifications) with acknowledgement and deduplication
5
FR-RPT-01
PDF report for an analysis/machine including provenance, trust panel and limitations
2
FR-RPT-02
Plant report and CSV exports
5
FR-RPT-03
Advanced analytics and cross-analysis reporting
6
FR-SUB-01
Configurable plans, limits and entitlements
5
FR-SUB-02
Quota enforcement with clear messages
5
FR-SUB-03
Usage tracking and usage view
5
FR-SUB-04
Billing foundations: subscription state, BillingProvider interface (no-op implementation); payment-provider integration is later
5
FR-AI-01
Read-only, tenant-scoped, tool-calling assistant
6
FR-AI-02
System Data and Assistant Explanation shown separately; verifier
6
FR-AI-03
Retrieval over uploaded documents with citations
Future
7. Non-Functional Requirements
Targets are split between the local development environment (student laptop, 16 GB RAM, Docker Desktop with 8 GB allocated) and future production SaaS (design intent, not tested in v1.x).
ID
Category
Local development target
Future production
NFR-PERF-01
Upload throughput
≥ 20 MB/s on localhost
Network-bound
NFR-PERF-02
Validation of a 50 MB CSV (~500k rows × 20 columns)
≤ 60 s, worker peak memory ≤ 2 GB
≤ 20 s
NFR-PERF-03
Pipeline A inference, 100,000 rows, no SHAP
≤ 60 s
≤ 15 s
NFR-PERF-04
Single-row SHAP (tree models)
≤ 1.5 s p95
≤ 500 ms
NFR-PERF-05
Pipeline B inference, 260 units (MS4)
≤ 60 s
≤ 20 s
NFR-PERF-06
Job queue wait with idle workers
≤ 5 s
≤ 2 s
NFR-PERF-07
Dashboard load (50 machines, 200 datasets)
≤ 3 s p95
≤ 2 s
NFR-PERF-08
CRUD API latency
≤ 300 ms p95
≤ 150 ms
NFR-SCAL-01
Scale
5 tenants, 100 machines, 1,000 datasets, 20 GB
1,000+ tenants
NFR-SCAL-02
Concurrency
2 workers (configurable), queue bounded per tenant
Autoscaled workers
NFR-REL-01
Job durability
Jobs persisted in PostgreSQL; restarts never lose a queued job; running jobs re-queued after heartbeat timeout
Same, possibly managed queue
NFR-REL-02
Result integrity
Results written transactionally with job completion
Same
NFR-REL-03
Failure containment
A failing or out-of-memory job cannot take down the API
Same
NFR-AVAIL-01
Availability
Best effort
99.5% monthly (API)
NFR-SEC-01
Tenant isolation
Zero cross-tenant leakage in automated tests, from MS1
Plus external penetration test
NFR-SEC-02
Isolation gate
Multi-organisation mode cannot be enabled unless the isolation suite passes in CI
Same
NFR-MAINT-01
Code quality
Ruff, mypy (strict on services and compatibility engine), ESLint, tsc strict in CI
Same
NFR-MAINT-02
Reproducibility
Any result is reproducible from dataset hash, mapping version, recipe version, profile version and model version
Same
NFR-MAINT-03
Portability
Storage, queue, secrets, email, model store and billing are accessed only through interfaces (§11.9) so local implementations can be replaced without changing business logic
Same
NFR-USAB-01
Usability
From a fresh login a user can upload a valid AI4I-schema CSV and see a result in ≤ 8 clicks
Usability study
NFR-USAB-02
Accessibility
WCAG 2.1 AA contrast; status never by colour alone
Audited
NFR-DATA-01
Consistency
Results immutable; each stores dataset version, mapping version, profile version, configuration, model version, applicability and reliability tier
Same
NFR-TIME-01
Time handling
UTC storage; source timezone kept as metadata
Same
8. Detailed Module Specifications
8.1 Organisation and Tenant Management
Design: shared database, shared schema, organisation_id on every tenant-owned row, PostgreSQL Row-Level Security (RLS) as defence in depth, organisation-prefixed object storage keys. This is built in Milestone 1 in its minimal form and hardened in Milestone 3.
Aspect
MS1 (minimum boundary)
MS3 (SaaS foundation)
Identity
Registration, login, Argon2id passwords, lockout, refresh rotation
Email verification, invitations, four roles, user deactivation
Tenant context
JWT carries org_id; a TenantContext is the only way repositories obtain a session; SET LOCAL app.current_org per transaction
Same, plus plant-level access and role checks
Database
organisation_id on all tenant tables; RLS policies enabled; app role without BYPASSRLS; schema test that every tenant table has a policy
Same, plus composite foreign keys including organisation_id where practical
Storage
Keys org/{organisation_id}/... built only from the context
Same, plus per-tenant retention and deletion controls
Tests
Two-organisation fixtures in the test suite verify no cross-tenant reads/writes (organisations created by fixtures, not by the product)
Full suite across every endpoint and role; becomes a CI gate (FR-ORG-09)
Multi-organisation access
Disabled: MULTI_ORG_ENABLED=false; the deployment serves a single organisation
Enabled only when the isolation gate passes (§18.4)
Rules
• Cross-tenant requests return 404; existence is never confirmed.
• A registration that uses an email already in use returns the same generic response as a new address.
• Platform Operators have no standing access to tenant data; support access is a break-glass, audited, time-limited grant (MS3).
• Removing the last Org Admin returns 409 (MS3).
8.2 Plants and Machines
8.2.1 Plants
MS1 creates one default plant per organisation automatically, so the schema is stable. MS3 adds plant management and per-user plant access.
8.2.2 Machine registry
Asset tag (unique per organisation), name, plant, category, manufacturer, model number, serial number, install date, rated parameters, notes, archived_at. No connectivity, device or hardware fields exist. Categories are platform-maintained and only offer pipelines; the compatibility engine decides whether a given dataset can run.
Category code
Description
Eligible dataset types
Pipelines
GENERAL_MACHINE_TOOL
Machine with operating-state features comparable to those the AI4I-trained models use
TABULAR_OPERATING_STATE, TABULAR_TIMESERIES
A (MS1), E (MS4)
TURBOFAN_ENGINE
Run-to-failure engine data in C-MAPSS channel format
RUN_TO_FAILURE_MULTIVARIATE
B, E (MS4)
BEARING_ROTATING
Rotating machine with a bearing and a high-rate vibration recording
VIBRATION_SIGNAL
C (MS4)
ACOUSTIC_MACHINE
Valve, pump, fan or slide rail
AUDIO_RECORDING
D (MS6)
OTHER
Anything else
TABULAR_TIMESERIES
E only
A category names a kind of machine; it never implies that an AI4I-trained model is appropriate for a particular machine within the category (that is applicability and reliability, §4.4).
8.2.3 Machine health assessment (MS2)
A deterministic rule derives condition from the latest completed, non-superseded result per pipeline:
1. No analysis if no completed result exists.
2. Critical if any latest result has risk class HIGH, anomaly severity HIGH, a non-healthy fault class above its threshold, or RUL below the critical cycles (later milestones add the latter three).
3. Warning if any latest result has risk MEDIUM, anomaly severity MEDIUM, or RUL below the warning cycles.
4. No concern in analysed data otherwise (the wording never says healthy machine).
5. A result is stale when its source dataset version is older than the organisation setting (default 90 days); stale results do not by themselves create Critical.
The assessment always displays as of <data date>, the contributing results, and the reliability tier of each (REFERENCE_ONLY in MS1–MS5). It is an advisory summary of uploaded data, not a live status.
8.3 Dataset Management
8.3.1 Supported formats
Kind
Formats
Constraints
MS
Tabular
CSV/TSV (UTF-8 or detectable encoding; comma, semicolon, tab)
Header required; ≤ 2,000 columns; ≤ 5,000,000 rows
1
Tabular
Excel .xlsx (one selected sheet; .xlsm, .xls, external links rejected), Parquet (flat schema; justified for large columnar exports)
Same caps
4
Vibration signal
.mat (MATLAB v5/v7 and v7.3, restricted loaders, Paderborn-layout profile), .wav, CSV/Parquet single-signal with declared sample rate
Sample rate and channel mapping mandatory
4
Audio
.wav PCM 16/24-bit; ZIP of WAV
ZIP limits below
6
Other formats return UNSUPPORTED_FORMAT.
8.3.2 Limits (configuration values; placeholders until set by the product owner)
Limit
MS1–MS4 (global configuration)
MS5 onward (per plan)
Tabular file
100 MB
Plan-defined (e.g. 25 MB trial, 100 MB standard)
Signal file
250 MB
Plan-defined
Single audio file / ZIP
50 MB / 500 MB (≤ 1,000 files, ≤ 2 GB uncompressed, expansion ≤ 20:1)
Plan-defined
Datasets and storage per organisation
500 datasets / 20 GB
Plan-defined
Uploads per day per organisation
200
Plan-defined
Before plans exist (MS1–MS4) these are enforced as global configuration because upload limits are a security control, not only a commercial one.
8.3.3 Dataset types
TABULAR_OPERATING_STATE (independent rows; Pipeline A), RUN_TO_FAILURE_MULTIVARIATE (Pipeline B), VIBRATION_SIGNAL (Pipeline C), AUDIO_RECORDING (Pipeline D), TABULAR_TIMESERIES (Capability E), UNKNOWN. The system proposes a type from the format and header profile; the user must confirm; the compatibility engine verifies.
8.3.4 Upload and security handling
1. The client requests an upload session; the server checks permission and limits.
2. The file is streamed to a quarantine location; memory use is constant; SHA-256 is computed while streaming; the byte limit aborts oversized uploads.
3. Extension allow-list and content verification by magic bytes or parsing; mismatch → UNSUPPORTED_FORMAT.
4. Original filenames are never used in storage paths; storage keys are generated.
5. A ScanService step (CLEAN / INFECTED / ERROR) runs before release. Local: structural, archive and macro checks, with an optional ClamAV container; production: ClamAV mandatory. Files are unreadable by workers until CLEAN.
6. Excel: formulas not evaluated, macros and external links rejected. ZIP: no nested archives, no path traversal, expansion and count limits.
7. Released objects are stored read-only; the version moves to UPLOADED; a validation job is queued.
8. An identical SHA-256 within the same dataset returns the existing version.
8.3.5 Validation checks and report
Validation is a deterministic function of (file, dataset type, mapping, unit selections, pipeline profile) and runs in streaming or chunked mode.
Area
Checks
Codes
Structure
Parseable; header; unique column names; counts; encoding; delimiter
E_PARSE, E_HEADER, E_EMPTY
Types
Inferred type per column; numeric parseability; mixed types
W_MIXED_TYPE, E_NON_NUMERIC
Units
User-declared unit per mapped column; conversion; plausibility after conversion
E_UNIT_REQUIRED, W_UNIT_IMPLAUSIBLE
Timestamps / cycles
Format, timezone, ordering, duplicates, gaps, regularity; contiguous cycles per unit
E_TS_PARSE, W_TS_GAPS, E_CYCLE_ORDER
Missing values
Per-column rate; patterns; required-feature rate
W_MISSING, E_REQUIRED_MISSING
Duplicates
Exact duplicate rows; duplicate keys
W_DUP_ROWS, E_DUP_KEYS
Outliers
Robust z (median/MAD), IQR fences, physical ranges; flags only
W_OUTLIERS, E_RANGE_VIOLATION
Signals and audio
Sample rate known; duration; clipping; flat-line; channels; silence
E_FS_UNKNOWN, W_CLIPPING, W_SILENCE
The validation report stores dataset identity and hash, type, mapping and units, check results with counts and at most 20 example indices, quality score and components, and per-profile compatibility, applicability and reliability results.
Data quality score. For a dataset version and target profile, using only the columns mapped to that profile's required and optional features:
Q = 100 \times \left( 0.30\,S_{complete} + 0.25\,S_{valid} + 0.15\,S_{unique} + 0.20\,S_{consistent} + 0.10\,S_{outlier} \right)
Component (each in [0, 1])
Definition
S_complete
1 minus the missing fraction over required-feature cells
S_valid
Fraction of required-feature cells that parse and lie in the profile's physical range after conversion
S_unique
1 minus the fraction of exact-duplicate or duplicate-key rows
S_consistent
Fraction of units/segments with valid ordering, contiguous cycles or regular sampling; for independent-row types, fraction of rows without internal contradiction; 1 if not applicable
S_outlier
1 minus min(1, outlier fraction / 0.05)
Bands: Good ≥ 85, Fair 60–84, Poor < 60. Weights are configuration and visible in the UI. The score summarises data health. It is not a model-accuracy predictor, does not decide compatibility, and says nothing about model applicability or reliability.
8.3.6 Column mapping rules and the onboarding wizard
Mapping principles
• A profile defines canonical features. A mapping pairs each canonical feature with a customer column and unit.
• The platform never creates, infers or assigns a feature that the dataset does not contain. A required feature with no column cannot be filled with a constant, default or derived guess.
• No artificial equivalence between datasets. Canonical features belong to one profile. For example product_type exists only in the ai4i_failure_with_type profile; it is not a universal industrial feature and is not offered in any other profile.
• Suggestions come from name normalisation and a synonym table, are marked suggested, and are never applied without user confirmation.
• Special rule for product_type: it may be suggested only if the column header normalises exactly to an AI4I name (Type, Product type) and all non-null values are in {L, M, H}. Confirming it requires the user to tick a statement that the column represents the AI4I-style quality variant. The platform cannot verify that meaning, so the confirmation is recorded and the result carries the warning W_TYPE_SEMANTICS_ASSERTED. The platform never derives a type from other columns (for example from a product ID).
• If the customer data has no such column, the user simply does not map it and the without Type configuration is used (§8.4.5).
Onboarding wizard (opens when validation finds mapping, unit or type issues)
1. Confirm the dataset type and objective.
2. Choose the target pipeline profile; the wizard lists each required and optional feature, its allowed units and the status of its mapping.
3. Map columns (suggestions flagged; confirmation required).
4. Declare units; the wizard previews converted ranges and warns on implausible values.
5. Resolve data issues: timestamp format, cycle column, unit ID, missing-value policy (only policies the profile supports), removal of exact duplicates into a derived version.
6. Re-validate; a new mapping version and compatibility check result.
7. If still INCOMPATIBLE or INSUFFICIENT_DATA, list exactly which features or conditions are missing and offer the schema template, re-upload, or Request support for this data type (logged; no custom model is created automatically).
8.3.7 Versioning, history, deletion and retention
• Versioning: a dataset is linked to one machine; each upload is an immutable version with its hash; derived versions keep derived_from_version_id and recipe; a change summary compares versions; results reference the exact version.
• Processing history: append-only events per version.
• Deletion: 30-day grace (restorable by an admin), then purge of the raw file, previews and derived arrays. Results derived from it keep provenance metadata marked source dataset deleted (default), or are deleted with it if the organisation setting says so.
• Retention defaults (organisation-configurable within bounds from MS3): raw datasets kept until deleted (optional auto-purge 12 months after last use, minimum 30 days); validation reports and results 24 months; audit logs 24 months; job logs 90 days. Organisation deletion purges tenant data within 30 days; backups age out within 35 days.
8.4 Compatibility, Applicability and Reliability Engine
A backend library (compat/) evaluates, for one dataset version, one mapping and one pipeline profile, three separate things and stores them in one immutable compatibility_check record. It is the only component allowed to authorise an analysis job (FR-CE-04).
flowchart TD
  D[Dataset version + mapping + units] --> C1[Stage 1: Dataset compatibility<br/>format, schema, units, sampling, quantity]
  C1 -->|UNSUPPORTED_FORMAT / INCOMPATIBLE / INSUFFICIENT_DATA| X1[Run refused with reasons and remedies]
  C1 -->|COMPATIBLE / COMPATIBLE_WITH_WARNINGS| C2[Stage 2: Model applicability<br/>reference-range coverage, domain notes - warning mechanism]
  C2 -->|MOSTLY_OUTSIDE_REFERENCE_RANGE| X2[Run refused: APPLICABILITY_BLOCKED]
  C2 -->|IN or PARTLY outside reference range| C3[Stage 3: Model reliability tier<br/>REFERENCE_ONLY unless validated on customer data]
  C3 --> A[User acknowledges warnings and the reference-model limitation]
  A --> J[Analysis job created]
Passing Stage 1 never implies Stage 2 or Stage 3. Stage 2 never implies Stage 3.
8.4.1 Pipeline profile (versioned configuration)
Each model configuration has its own profile, stored immutably in pipeline_profiles and shipped with the model artifact. A change to the feature schema is a new profile (or profile version).
profile_id: ai4i_failure_no_type
profile_version: 1.0.0
pipeline: A
configuration: NO_TYPE
objective: FAILURE_PROBABILITY_CURRENT_STATE
training_domain: REFERENCE_DATASET   # AI4I 2020, synthetic
machine_categories: [GENERAL_MACHINE_TOOL]
dataset_types: [TABULAR_OPERATING_STATE]
allowed_formats: [csv, xlsx, parquet]
required_features:
  - {name: air_temperature,     unit_canonical: K,   allowed_units: [K, degC, degF]}
  - {name: process_temperature, unit_canonical: K,   allowed_units: [K, degC, degF]}
  - {name: rotational_speed,    unit_canonical: rpm, allowed_units: [rpm, rad_s, Hz]}
  - {name: torque,              unit_canonical: Nm,  allowed_units: [Nm, lbf_ft]}
  - {name: tool_wear,           unit_canonical: min, allowed_units: [min, h]}
optional_features: []
forbidden_features: [machine_failure, TWF, HDF, PWF, OSF, RNF, UDI, product_id, product_type]
minimums: {rows: 1, required_feature_completeness: 0.95}
reference_ranges_ref: model_artifact://reference_ranges.json   # computed at training time
applicability: {margin_fraction: 0.10, warn_row_fraction: 0.01, block_row_fraction: 0.30}
preprocessing_recipe: ai4i_features_no_type@1.0.0
model_versions: [ai4i_failure_clf_notype@Production]
---
profile_id: ai4i_failure_with_type
configuration: WITH_TYPE
# identical to the above except:
required_features: [...same five numeric features..., {name: product_type, kind: categorical, allowed_values: [L, M, H], ai4i_specific: true}]
forbidden_features: [machine_failure, TWF, HDF, PWF, OSF, RNF, UDI, product_id]
warnings_on_use: [W_TYPE_SEMANTICS_ASSERTED]
preprocessing_recipe: ai4i_features_with_type@1.0.0
model_versions: [ai4i_failure_clf_typed@Production]
Numeric reference ranges are computed when the model is trained and stored with the artifact; they are not typed into this PRD. Both AI4I profiles are separate so that a customer dataset without a Type equivalent is fully supported rather than treated as incomplete.
Other profiles differ as follows:
Profile
MS
Dataset type
Key requirements
Sampling / history
Notable limits
B cmapss_rul
4
RUN_TO_FAILURE_MULTIVARIATE
Unit ID, cycle index, operational-setting channels and the retained sensor channels of the chosen C-MAPSS-trained model, on the same raw scale as training (C-MAPSS channels are anonymised)
At least the window length L contiguous cycles per unit
Turbofan-type data or machine profiles with explicitly equivalent channels only
C paderborn_bearing
4
VIBRATION_SIGNAL
One vibration channel at the exact training sampling rate, minimum window length, declared bearing configuration
Rate mismatch is INCOMPATIBLE (no silent resampling)
One bearing type, laboratory conditions
E sensor_anomaly
4
TABULAR_TIMESERIES
≥ k numeric features (default 3), ordered index or timestamp, designated normal reference segment
Reference segment ≥ profile minimum (default 500 rows)
No pretrained model; scores are relative to the user's reference
D mimii_acoustic
6
AUDIO_RECORDING
WAV at the training sample rate, supported machine type, channel selected
Clip duration ≥ profile minimum
Per machine type; first use always carries an applicability warning
8.4.2 Stage 1 – dataset compatibility
1. Format gate: file kind parsed and allowed by the profile, else UNSUPPORTED_FORMAT.
2. Category and type gate: machine category and confirmed dataset type listed in the profile, else INCOMPATIBLE (E_CATEGORY, E_DATASET_TYPE).
3. Schema gate: every required feature mapped to an existing column of the right kind with an allowed, convertible unit; no forbidden feature mapped as an input, else INCOMPATIBLE (E_MISSING_FEATURE, E_UNIT_UNCONVERTIBLE, E_FORBIDDEN_FEATURE).
4. Sampling gate: signal and audio sample rates equal the profile; time-series interval estimable and consistent, else INCOMPATIBLE (E_SAMPLING_RATE) or INSUFFICIENT_DATA (E_HISTORY_TOO_SHORT).
5. Quantity gate: row, cycle, duration minimums and required-feature completeness, else INSUFFICIENT_DATA.
6. Warning rules: optional features absent; allowed imputation required; outliers above threshold; quality score Poor; user-overridden unit plausibility warning; W_TYPE_SEMANTICS_ASSERTED; machine category OTHER.
7. Decision: the worst finding in the precedence UNSUPPORTED_FORMAT > INCOMPATIBLE > INSUFFICIENT_DATA > COMPATIBLE_WITH_WARNINGS > COMPATIBLE.
Status
Meaning
Job allowed?
COMPATIBLE
All Stage 1 gates pass, no warnings
Yes, subject to Stages 2–3
COMPATIBLE_WITH_WARNINGS
Runnable with listed limitations
Yes, after warning acknowledgement
INCOMPATIBLE
Structure, semantics, units or sampling do not match
No
INSUFFICIENT_DATA
Schema fits but there is not enough data or history
No
UNSUPPORTED_FORMAT
File kind or content not readable or not allowed
No
The reason object is {code, severity: ERROR|WARNING|INFO, feature?, observed?, expected?, message, remedy}. COMPATIBLE does not mean suitable for reliable predictions; the UI never uses wording such as approved, validated or safe for it.
8.4.3 Invariants
• A check is bound to the exact dataset version, mapping version, unit selections, profile version and thresholds; changing any requires a new check.
• A job stores the compatibility_check_id that authorised it; the worker re-verifies that the hashes still match.
• Several datasets per machine are allowed and each is checked independently. Profiles have exactly one dataset input; no analysis combines datasets. A fusion strategy would need a profile defining alignment (keys, time base, units), its own validation study and its own model.
• Promoting a new model for a profile requires an unchanged feature schema; otherwise a new profile version and new checks.
8.4.4 Stage 2 – model applicability assessment
Purpose: warn when the reference-trained model is being asked to work outside what it has seen. It is a warning mechanism, not evidence of reliability.
Check
Method
Output
Per-feature reference-range coverage
A row is flagged if any required feature lies outside [min − m·range, max + m·range] of the stored training reference (m = margin_fraction)
Flagged-row fraction, per-feature breakdown
Joint-domain check (optional per profile)
A reference-fitted multivariate distance or isolation score flags rows that are individually in range but jointly unusual
Additional flagged fraction, labelled joint-domain warning
Operating-condition coverage
The profile can declare unsupported conditions (e.g. operating regimes absent from training; for Pipeline B, a multi-condition dataset when only a single-condition model exists)
W_UNSUPPORTED_CONDITION or E_UNSUPPORTED_CONDITION
Machine-domain note
Always states the training domain (AI4I 2020 synthetic data, C-MAPSS simulated turbofans, …) and that the customer machine may differ
Mandatory note on every result
Levels (thresholds are configuration, recorded with the check):
Level
Rule
Effect
IN_REFERENCE_RANGE
Flagged fraction ≤ warn_row_fraction (default 1%)
Rows still flagged individually; no claim of reliability
PARTLY_OUTSIDE_REFERENCE_RANGE
Between warn_row_fraction and block_row_fraction (default 30%)
Warning W_OOD must be acknowledged; flagged rows shown separately in results
MOSTLY_OUTSIDE_REFERENCE_RANGE
Above block_row_fraction
Run refused with APPLICABILITY_BLOCKED, because outputs would be extrapolation; remedy text explains
Why a model can still be unreliable inside the range: a joint operating point can be unrepresentative, the machine's failure physics can differ, labels and wear definitions can differ, and calibration was measured on a different distribution. These statements appear in the help text beside the level.
8.4.5 AI4I configuration selection
Mapped features
Runnable configurations
Behaviour
Five numeric features only (no Type)
NO_TYPE
Only ai4i_failure_no_type is offered; the UI says no product-type feature is required
Five numeric features plus a confirmed Type column with values in {L, M, H}
NO_TYPE and WITH_TYPE
Both offered; the user may run either or both; results are stored and shown separately and are never averaged or merged
Type mapped but values outside {L, M, H}
NO_TYPE
WITH_TYPE is INCOMPATIBLE (E_CATEGORY_VALUES)
Any required numeric feature missing
none
INCOMPATIBLE
Pre-selection when both are runnable: the model catalogue carries a default_when_both_runnable field. Until the experiments of §10.1.5 are complete and a documented decision exists, the pre-selected configuration is NO_TYPE because it requires no feature that may not exist in customer data. This is a feasibility rule, not a performance claim; no statement is made about which configuration predicts better. The platform never infers, defaults or assigns a product type.
8.4.6 Stage 3 – model reliability tier
Tier
Meaning
When
REFERENCE_ONLY
Evidence exists only from evaluation on the public reference dataset the model was trained on. No evidence about the customer's equipment.
Every result in MS1–MS5, and every result without a successful customer validation
CUSTOMER_VALIDATED
A customer-specific validation (§10.7) met its criteria for this machine, profile, model version and dataset scope
MS6 and later, optional
The tier is displayed in the trust panel and reports, can't be hidden, and is never raised by compatibility or applicability results.
8.4.7 Job-creation gate (all must hold)
1. Stage 1 status is COMPATIBLE or COMPATIBLE_WITH_WARNINGS.
2. Stage 2 level is not MOSTLY_OUTSIDE_REFERENCE_RANGE.
3. Every warning code in the check is acknowledged by the user.
4. The limitation acknowledgement exists for this (machine, profile, model version) — text: This is a reference-dataset-trained model. It has not been validated on your equipment. Results are advisory.
5. The check is current (hashes match), the organisation is entitled and within quota (from MS5).
Failures return INCOMPATIBLE, INSUFFICIENT_DATA, UNSUPPORTED_FORMAT, APPLICABILITY_BLOCKED, WARNINGS_NOT_ACKNOWLEDGED, LIMITATIONS_NOT_ACKNOWLEDGED, COMPAT_CHECK_STALE, QUOTA_EXCEEDED or FEATURE_NOT_ENTITLED (§13).
8.5 Background Processing and Job Architecture
Local development implementation: PostgreSQL-backed queue. A jobs table and separate worker processes that claim work with SELECT ... FOR UPDATE SKIP LOCKED. Jobs, results and (later) usage change in one transaction; no extra service on a 16 GB laptop. The queue is accessed through a JobQueue interface so a managed queue can replace it in production. Redis and Celery are not used; revisit only if sustained load exceeds ~50 jobs/min, more than ~10 workers are needed, delayed fan-out workflows appear, or claim latency is measurably a problem.
stateDiagram-v2
  [*] --> QUEUED
  QUEUED --> RUNNING: claimed by worker
  QUEUED --> CANCELLED: cancel before start
  RUNNING --> SUCCEEDED: result committed
  RUNNING --> FAILED: deterministic error or retries exhausted
  RUNNING --> RETRY_WAIT: transient error, attempts left
  RETRY_WAIT --> QUEUED: backoff elapsed
  RUNNING --> CANCEL_REQUESTED: user cancels
  CANCEL_REQUESTED --> CANCELLED: stops at next checkpoint
  RUNNING --> QUEUED: heartbeat timeout, attempts left
Aspect
Specification
Job types
SCAN_UPLOAD, VALIDATE_DATASET, RUN_ANALYSIS (load → recheck gate → preprocess → infer → explain → store), GENERATE_REPORT, PURGE_DATASET; MS6 adds VALIDATE_ON_CUSTOMER_DATA and RETRAIN_TENANT_MODEL
Priorities
Validation and scan above analysis above reports
Concurrency
Worker pool default 2; per-tenant running cap 2; queue cap per tenant 200 (429 QUEUE_FULL)
Progress
progress_percent and current_step; UI polls every 2 s
Heartbeat
Every 15 s; stale after 120 s → re-queue with attempt + 1
Retries
Transient errors only, max 3, backoff 10 s / 60 s / 300 s with jitter. Never retried: validation failures, incompatibility, applicability blocks, model errors, out-of-memory (E_RESOURCE)
Idempotency
Idempotency-Key unique per organisation; natural key (dataset version, mapping version, profile version, model version, params hash) returns the existing job or result unless force_rerun
Cancellation
Cooperative at checkpoints; partial output discarded
Timeouts
Validation 10 min, analysis 30 min, report 10 min
Errors
error_code, user_message, remedy, diagnostic_id; no stack traces to clients
Result versioning
Increasing result_version per (machine, dataset version, profile, configuration); one is_latest
Resource protection
Worker container memory limit (default 4 GB), chunked reads, temp-disk caps
8.6 Analysis Modules (summary; algorithms in §10)
Module
MS
Output stored
Visualisations
A Failure prediction (configuration WITH_TYPE or NO_TYPE)
1–2
Per-row reference-calibrated probability, risk class, mode probabilities (MS2), OOD flags, aggregates, configuration, applicability level, reliability tier
Risk distribution, top-risk rows, feature distributions against the training range, SHAP summary and waterfall
B RUL
4
Per unit capped RUL, 80% interval, degradation index
Ranking, trajectory with interval band and cap, sensor trends
C Bearing diagnosis
4
Per window/recording class probabilities, quality checks, features
Waveform, FFT/PSD, envelope spectrum, class bars
E Sensor anomaly
4
Per-timestamp scores, severity, events, feature contributions
Score timeline, events, contributions
D Acoustic anomaly
6
Per-clip score and label
Waveform, spectrogram, error map
Storage rule: summary and top-N rows (default 500) in PostgreSQL JSONB; full row-level output as a Parquet artifact in file/object storage referenced by artifact_uri.
8.7 Explainable AI (MS2)
• SHAP TreeExplainer for tree models in Pipelines A and C (handcrafted features) and tree-based RUL models. Neural RUL models show degradation and sensor-trend visuals instead.
• Compute policy: SHAP for the top-N rows, any row the user opens (on demand, cached), and a random sample of up to 2,000 rows for global importance.
• Every explanation view and report carries Feature attributions describe model behaviour, not physical causation. Correlated features (air and process temperature) are flagged. In explanations for the WITH_TYPE configuration, product_type is described as an AI4I-specific category.
• Explanations describe the reference-trained model's behaviour on your data, not the machine's physics.
8.8 Maintenance Intelligence
Principle. Recommendations are generated from uploaded dataset evidence and the outputs of a reference-dataset-trained model. They are not real-time monitoring, not safety guarantees, and always shown with the trust panel.
Rule code
Trigger (latest result)
Recommendation template
Default priority
A_HIGH_RISK
Rows with reference-model risk class HIGH, or HIGH share above threshold
Review the listed operating states and top contributing features; consider an inspection
HIGH
A_MODE_TWF
Tool-wear mode probability above threshold
Review tooling condition and tool-wear data
MEDIUM
A_OOD_HEAVY
Applicability PARTLY_OUTSIDE_REFERENCE_RANGE with high flagged share
Treat the result as low-confidence; consider customer-specific validation
LOW
B_RUL_LOW (MS4)
Capped RUL below warning/critical cycles
Plan an inspection; confirm with condition data
HIGH / MEDIUM
C_FAULT_CLASS (MS4)
Non-healthy bearing class above threshold
Inspect the bearing; consider re-measurement under similar conditions
HIGH
E_ANOMALY_HIGH (MS4)
Severity HIGH relative to the user's reference
Investigate the deviating features
MEDIUM
D_ACOUSTIC_HIGH (MS6)
Acoustic severity HIGH
Inspect for abnormal noise sources; re-record under comparable conditions
MEDIUM
DQ_POOR
Quality score Poor
Improve data quality before relying on the result
LOW
Rules are versioned configuration and require domain-expert review before real use. MS2: recommendations are generated and displayed (status PROPOSED, read-only). MS5: engineer approve/reject (reason code)/defer, scheduling, task management, history and outcome capture, findings with deduplication. Outcomes feed per-tenant statistics (with sample size) and the customer-validation mechanism (MS6); they never retrain shared models.
8.9 AI Maintenance Assistant (MS6)
Read-only, tenant-scoped tools: get_machine_summary, get_dataset_summary, get_validation_report, get_compatibility_result (including applicability and reliability), get_analysis_result, list_highest_risk_machines, get_recommendations, get_maintenance_history. All facts come from tools; a verifier checks numbers and IDs; responses have separate System Data and Assistant Explanation blocks; dataset rows are never sent to the LLM provider; uploaded content (file names, column names, notes) is untrusted; the assistant must repeat the reliability tier when discussing a prediction and may not describe a reference-only result as validated.
8.10 Reports (PDF from MS2; CSV, plant reports MS5)
Every report includes: organisation, plant, machine; source dataset name, version and SHA-256; mapping and unit selections; preprocessing recipe version; pipeline, configuration and model version; the label reference-dataset-trained model; training domain; computed-at date; data quality score; compatibility status and acknowledged warnings; applicability level and flagged-row summary; reliability tier; results; explanations with the non-causality disclaimer; recommendations; and two clearly separated sections: Reference-dataset evaluation (public data) and Customer-specific validation (stating none performed when applicable). Each report ends with Analysis of uploaded datasets with a reference-trained model; advisory; not a real-time monitoring report and not a safety assessment. CSV exports neutralise formula injection.
8.11 Plans, Quotas and Usage (MS5)
Concept
Specification
Plan
plans rows with limits (users, machines, storage, per-file sizes, uploads/day, analyses/month, assistant messages) and entitlements (pipelines, assistant, reports, customer validation) as JSONB
Subscription
One per organisation: plan, status (TRIALING, ACTIVE, SUSPENDED, CANCELLED), period, overrides
Usage tracking
Append-only usage_events (written from MS1 for analyses and uploads so history exists), monthly usage_counters; 1 analysis = 1 SUCCEEDED RUN_ANALYSIS job
Enforcement
Invites, machine creation, uploads, analysis creation, assistant messages, reports; 80% warning, hard stop at 100% with 403 QUOTA_EXCEEDED; existing data never deleted for exceeding a quota
Billing foundations
Subscription state machine and a provider-neutral BillingProvider interface with a no-op implementation. Payment-provider integration, invoicing and tax are not part of MS5 (Appendix E)
9. Dataset and Data Strategy
9.1 Reference datasets versus tenant datasets
Kind
Owner
Purpose
Location
Reference (training) datasets: AI4I 2020, NASA C-MAPSS, Paderborn, MIMII
Platform (public data; licences recorded)
Train and evaluate the shared pretrained models
ML workspace only; never mixed with tenant data
Tenant datasets
The customer organisation
Inference input; the reference segment for Capability E; (MS6, optional) labelled history for customer-specific validation
Tenant-isolated storage and database; never used to train shared models
Every shared model is therefore a reference-dataset-trained model. A tenant dataset can be analysed by Pipelines A–D only if it matches the corresponding reference schema, units, scale and operating range closely enough to pass the compatibility engine, and even then the applicability and reliability limits of §4.4 apply. Metrics measured on reference datasets are research-dataset evaluation metrics; they are never presented as performance on a customer's equipment.
Global rules
1. One dataset family → one preprocessing module → one feature schema → one model family → one or more profiles. Never merge datasets with incompatible feature spaces or targets. Canonical features are defined per profile; no feature equivalence is assumed across profiles.
2. Feature schemas and reference ranges are versioned artifacts shipped with each model.
3. Raw downloads are never modified; processed training data is tracked by content hash.
4. Dataset facts below come from providers' public documentation and must be verified in the first milestone that uses each dataset against the real files, with discrepancies recorded in DATASET_NOTES.md.
5. Licences and citation obligations are recorded before use.
9.2 Pipeline A: AI4I 2020 Predictive Maintenance Dataset (UCI #601)
Item
Specification
Purpose
Failure classification, failure-mode prediction, baseline experimentation
Nature
Synthetic data designed to resemble real predictive-maintenance data
Format
One CSV, about 10,000 rows (verify)
Columns
UDI, Product ID, Type (L/M/H), air temperature [K], process temperature [K], rotational speed [rpm], torque [Nm], tool wear [min], Machine failure, TWF, HDF, PWF, OSF, RNF
Type
A feature specific to AI4I (a product quality variant). It is not a universal industrial feature, is not required for Pipeline A in general, and is offered only in the WITH_TYPE configuration. The dataset description indicates that some generating rules depend on the variant (verify); therefore Type may carry information in this synthetic data that does not exist in other data
Targets
Machine failure (binary); mode flags TWF, HDF, PWF, OSF, RNF
Leakage
Mode columns compose Machine failure and are forbidden as inputs to the binary model; UDI and Product ID are dropped and forbidden
Known quirks
RNF is random by construction (excluded from mode scoring); documented generating rules mean tree models may recover them, so strong scores show rule recovery on synthetic data, not real-world predictive power
Preprocessing
Unit canonicalisation (K, rpm, Nm, min); engineered features (temperature difference, power proxy = torque × angular speed, wear × torque); Type one-hot encoded only in WITH_TYPE; scaler fitted on training folds only
Split
Not a time series: stratified train/validation/test (e.g. 60/20/20, fixed seed, indices stored and hashed); repeated stratified CV; test touched once. Identical splits and folds for both configurations
Imbalance
Class weights, threshold tuning; resampling only inside folds; calibration after reweighting
Metrics
PR-AUC (primary), ROC-AUC, precision, recall, F2, MCC, Brier score, calibration curve, confusion matrix; per-mode recall; bootstrap CIs; prevalence always shown; accuracy never alone
Limitations
Synthetic; few positives; five physical features (six with Type); no future time horizon: the label is failed in this record; calibration is specific to the reference data
9.3 Pipeline B: NASA C-MAPSS (MS4)
Item
Specification
Purpose
RUL prediction, degradation modelling
Source
NASA Prognostics Center of Excellence repository (record URL and checksum)
Format
Space-separated text: train_FD00x, test_FD00x, RUL_FD00x, subsets FD001–FD004
Columns
unit, cycle, 3 operational settings, 21 sensor channels (anonymised, no stated physical units)
Subsets
FD001 one condition/one fault mode; FD002 six conditions/one; FD003 one/two; FD004 six/two (verify counts)
Target
RUL = last cycle of unit − current cycle, with a piecewise-linear cap (tuned on validation, shown in UI)
Preprocessing
Remove near-constant sensors (decided on training data); per-condition normalisation for multi-condition subsets; sliding windows of length L (default 30); rolling statistics for tree models
Split
By unit, never by row; official test set for final evaluation
Metrics
RMSE, MAE, NASA asymmetric score on the last-window protocol; per subset; interval coverage
Limitations
Simulated; turbofan-specific; channels carry no physical units, so a tenant dataset matches only through explicit channel mapping and scale; not generalisable to unrelated machines
9.4 Pipeline C: Paderborn University Bearing Data (MS4)
Item
Specification
Purpose
Bearing fault diagnosis from vibration
Format
MATLAB .mat per bearing code and measurement (verify structure)
Content (per provider)
Synchronous high-rate vibration and motor phase-current signals plus slow process quantities for healthy, artificially damaged and really damaged bearings under several operating conditions. v1.2 Pipeline C uses the vibration signal only; the current signals are reserved for the future MCSA enhancement (§21.3)
Target
Bearing condition class (healthy, inner-race, outer-race damage; artificial and real damage treated separately)
Preprocessing
Fixed windows (e.g. 1 s); DC removal; band-pass and envelope analysis; FFT/PSD; time- and frequency-domain features; characteristic-frequency band energies (need geometry and speed; verify)
Split
By bearing/experiment code, never by window; cross-operating-condition and artificial-to-real transfer reported separately
Metrics
Macro-F1, per-class recall, confusion matrix, fold variance
Limitations
Laboratory rig; few distinct bearings; artificial damage may not transfer to real damage; one bearing type
9.5 Pipeline D: MIMII (MS6)
Item
Specification
Purpose
Acoustic anomaly detection
Format
WAV, 10 s segments, multi-channel array recordings (verify)
Content (per provider)
Normal and anomalous sounds of valve, pump, fan and slide rail, several model IDs each, mixed with factory noise at several SNRs (record exactly which SNR records are used)
Target
Anomalous/normal for evaluation only; training on normal clips only
Preprocessing
Channel selection; fixed log-mel spectrogram; frame stacking; normalisation per machine type/ID from training normals
Split
Per machine ID; thresholds from validation normals
Metrics
ROC-AUC and partial AUC per machine ID; mean and spread
Limitations
Laboratory recordings with added noise; strong dependence on machine ID and SNR; first use on a customer machine always flagged
9.6 Capability E: sensor anomaly detection on tenant data (MS4)
No reference dataset and no shared pretrained model. For each analysis the user designates a normal reference segment; Isolation Forest, One-Class SVM and a small autoencoder are fitted on that segment only and score the remainder. Output is explicitly deviation from the user's reference, not a failure prediction, and its reliability tier is REFERENCE_ONLY-equivalent not applicable (there is no reference-trained model); the result is labelled Unsupervised, user-reference based.
9.7 Development utilities and simulated data
Sample dataset packs derived from the public datasets and an optional dataset simulator write files only. Every such file carries provenance = SIMULATED | PUBLIC_SAMPLE, shown as a badge in the UI and reports, and never mixed with CUSTOMER datasets in any aggregate or report without separation.
10. AI/ML Technical Specifications
10.0 Cross-cutting rules
Stages (every pipeline): ingestion → validation → compatibility → applicability → preprocessing → feature engineering → training (offline, public data) → evaluation → tracking → registry → deployment → monitoring. Training code, the shared industria_features library and the production worker are separate packages.
Risk
Required control
Data leakage
Transforms fitted inside sklearn pipelines on training folds only; forbidden-feature lists in profiles; test that fails if a transformer sees test indices
Training-serving skew
Single feature library; schema stored with the model; parity test
Overfitting
Nested/repeated CV, early stopping, learning curves, train–validation gaps logged
Improper time-series validation
Group-by-unit and group-by-bearing splits; no shuffled splits over time
Misleading accuracy
Prevalence and majority baseline in every report; PR-AUC and calibration; bootstrap CIs
Class imbalance
Class weights, thresholds, in-fold resampling, calibration after reweighting
Baseline-first
Registration gate rejects advanced models without a baseline on the same split
Unfair configuration comparison
Both AI4I configurations use identical splits, folds, search budgets and metrics (§10.1.5)
Reproducibility
Seeds, configs, library versions, dataset hash, git commit in MLflow
Domain shift on tenant data
Reference ranges and applicability assessment (warning only); reliability tier; reference-model label
Over-claiming
Model cards, results and reports keep research-dataset metrics separate from customer validation and state limits
Serialisation: scikit-learn pipelines and XGBoost via MLflow flavours (loaded only from the trusted registry); PyTorch as state_dict plus architecture config, exported to TorchScript or ONNX. Every artifact bundle contains: model, feature_schema.json, reference_ranges.json, preprocessing parameters, metrics.json, thresholds.json, SHAP background sample, the pipeline profile, and MODEL_CARD.md.
Model card required sections: intended use and non-use; training domain (reference dataset, synthetic/simulated/laboratory); configuration and features; Reference-dataset evaluation (public data) with CIs, baselines and prevalence (populated only from actual experiments); Customer-specific validation (none for shared models); calibration scope (reference data only); reference ranges; known limitations; explanation methods; version history.
Batch inference (worker): load the profile and model versions recorded on the job → re-verify the gate → stream data in chunks → apply mapping and unit conversion → validate against the schema → compute features → predict → calibrate (reference calibration) → compute applicability flags → explanations per policy → write artifact and summary → commit result and job state in one transaction.
Inference error contract
Condition
Outcome
Model artifact missing or corrupt
FAILED E_MODEL_UNAVAILABLE (no silent fallback to another version)
Run-time schema or range failure
FAILED E_INPUT_INVALID with examples
Check stale
FAILED E_COMPAT_STALE
Applicability blocked
Refused at creation with APPLICABILITY_BLOCKED
Missing data beyond profile policy
FAILED E_INSUFFICIENT_DATA
OOD rows
Result succeeds with rows flagged ood_warning
Out of memory / timeout
FAILED E_RESOURCE / E_TIMEOUT
10.1 Pipeline A: Failure prediction (AI4I-trained)
10.1.1 Semantics
Rows are independent snapshots. The output is a reference-calibrated failure probability for the supplied operating state. No time-to-failure or within the next N days claim appears for this pipeline. On customer data the probability is a model score; it is not the customer machine's failure frequency, because calibration was measured on the synthetic reference data.
10.1.2 Two model configurations

Configuration NO_TYPE
Configuration WITH_TYPE
Registry names
ai4i_failure_clf_notype, ai4i_mode_clf_notype
ai4i_failure_clf_typed, ai4i_mode_clf_typed
Profile
ai4i_failure_no_type
ai4i_failure_with_type
Input features
air temperature, process temperature, rotational speed, torque, tool wear
the five above plus product_type (L/M/H)
Engineered features
temperature difference, power proxy, wear × torque
same engineered features
Runnable when
the five numeric features are mapped
the five numeric features and a confirmed Type column with values in {L, M, H} are mapped
Extra warning
none
W_TYPE_SEMANTICS_ASSERTED
Missing Type
Not an issue
The configuration is simply not offered; no type is inferred or assigned
Both configurations share the same algorithm ladder, training procedure and evaluation, and differ only in the input feature set and its preprocessing.
10.1.3 Model ladder (per configuration)
Stage
Model
Rationale
B0
Majority-class / prevalence predictor
Floor; shows why accuracy misleads
B1
Logistic Regression (L2, class-weighted, standardised)
Interpretable baseline
M1
Random Forest (class-weighted)
Non-linear interactions
M2
XGBoost (scale_pos_weight, early stopping)
Strong on tabular data; TreeSHAP
Optional
Other boosted trees or small MLP
Only if justified in the model card by non-overlapping CIs
10.1.4 Training procedure
Validate and split (stratified, locked test) → repeated stratified CV with a fixed search budget → choose by CV PR-AUC → calibrate (isotonic or Platt) on the validation partition → choose the threshold by a configured cost ratio (placeholder, Appendix E) → evaluate once on the test partition with CIs, curves and SHAP summary → registration gate. The mode classifier uses one-vs-rest models for TWF, HDF, PWF, OSF (RNF excluded); a mode is enabled only if its test positives reach a minimum count (default 20), otherwise the UI says insufficient labelled data for this mode.
10.1.5 Comparing the two configurations (protocol; no results in this document)
1. Same data handling: identical cleaning, one stratified split with stored and hashed indices, identical repeated-CV fold indices, identical seeds.
2. Same procedure: identical algorithm ladder, search budgets, calibration method, threshold rule and metrics.
3. Paired evaluation: report each configuration's metrics with bootstrap CIs on the same test partition, plus paired bootstrap differences (PR-AUC, recall at fixed precision, Brier score) and paired fold-wise differences on validation.
4. Pre-declared decision rule for default_when_both_runnable: choose WITH_TYPE only if the paired PR-AUC difference has a confidence interval entirely above zero and calibration is not worse; otherwise keep NO_TYPE. Whatever the outcome, both configurations remain available where their features exist.
5. Interpretation guard: because the data is synthetic and its generating rules may depend on the variant, any advantage of WITH_TYPE demonstrates rule recovery, not transferable benefit. The model card says so.
6. Documentation: results are written to the model cards and the Model Performance page only after the experiments are run. This PRD contains no performance figures for either configuration.
10.1.6 Edge cases
Missing Type values in the WITH_TYPE configuration: rows excluded and counted, never filled. Out-of-range torque or speed: ood_warning. Kelvin/Celsius confusion: prevented by mandatory unit declaration and plausibility checks. Configuration selection never changes silently between runs; the configuration is stored on the result.
10.2 Pipeline B: Remaining Useful Life (C-MAPSS-trained, MS4)
Inputs: last L cycles of retained sensors and settings per unit. Output: capped RUL (cycles) and an 80% interval. Windows end at each cycle t ≥ L; inference uses the last window per unit.
Stage
Model
Input
B0
Training-mean constant
–
B1
Ridge regression
Last-cycle features
M1
Random Forest Regressor
Window statistics
M2
XGBoost Regressor
Same
M3
GRU (1–2 layers, dropout)
Raw normalised window
M4
LSTM
Comparison; kept only if it adds value over GRU
Training: group-by-unit K-fold for tree models; fixed unit-level validation split with early stopping for neural nets; AdamW, gradient clipping; hyperparameters tuned on validation units only. Uncertainty: conformal prediction on held-out calibration units (coverage verified on test units) or quantile regression. Evaluation: RMSE, MAE, NASA score on the last-window protocol per subset, error by true-RUL bucket, interval coverage. Edge cases: unit shorter than L → INSUFFICIENT_DATA; non-contiguous cycles → E_CYCLE_ORDER; predictions clipped to [0, cap] and flagged. Applicability: sensor scale and operating-condition coverage are the main warnings.
10.3 Pipeline C: Bearing fault diagnosis (Paderborn-trained, vibration only, MS4)
Inputs: vibration windows at the profile sampling rate. Features: time-domain (RMS, peak, crest factor, kurtosis, skewness), frequency-domain (Welch band energies, spectral centroid/entropy), envelope-spectrum energy near characteristic bearing frequencies (needs geometry and speed; verify). Models: B0 majority; B1 Logistic Regression; M1 Random Forest; M2 XGBoost; optional 1-D CNN if handcrafted features plateau. Validation: leave-bearing-out GroupKFold plus cross-operating-condition tests; window-level random-split accuracy is never a headline. Explainability: SHAP on the handcrafted features against spectral bands. Edge cases: clipped or flat windows rejected; rate mismatch INCOMPATIBLE; long recordings are segmented with majority vote and mean probability both shown. Motor current analysis is not part of this pipeline (§21.3).
10.4 Pipeline D: Acoustic anomaly detection (MIMII-trained, MS6)
Log-mel frames of a clip → anomaly score, label and severity. Baselines: Isolation Forest / One-Class SVM on summary spectral statistics; main model: dense or convolutional autoencoder per machine type (and model ID where specified), trained on normal clips only; thresholds from validation-normal percentiles. Evaluation: AUC and partial AUC per machine ID. Explanation: reconstruction-error map (where the clip deviates from learned normal sound).
10.5 Capability E: Sensor anomaly detection (MS4)
Isolation Forest (inverted score_samples), One-Class SVM (RBF decision function) and a dense autoencoder (reconstruction error, per-feature error), all fitted on the user's reference segment with features scaled on that segment. Thresholds and severity come from percentiles of held-out reference scores, so the false-alarm rate on the reference is controlled and reported. Events require K consecutive anomalous windows (default 3) and close after R normal windows (default 5). Output states which features deviate from the reference, not why.
10.6 Model registry, versioning and release
• MLflow Model Registry with one registered model per pipeline and configuration: ai4i_failure_clf_notype, ai4i_failure_clf_typed, ai4i_mode_clf_notype, ai4i_mode_clf_typed, cmapss_rul, paderborn_fault_clf, mimii_anomaly_<machine_type>. Capability E has an algorithm/configuration version instead.
• Stages Staging → Production → Archived; semantic versions (MAJOR schema/profile change, MINOR retrain, PATCH threshold or calibration).
• Registration gate: baseline on the same split; metrics with CIs; leakage and parity tests green; model card with the required sections; no forbidden features; artifact reproduces a stored reference prediction in a clean worker image; profile and reference ranges present; for Pipeline A both configurations evaluated under §10.1.5 before either is promoted.
• A Platform Operator promotes a version after a recorded comparison with the current Production model. Tenants see only Production versions. Results keep their original model version permanently.
10.7 Customer-specific validation and retraining (MS6, optional)
Purpose: let an organisation obtain evidence about how a model behaves on its own equipment, and optionally adapt a model, without ever making this mandatory and without sharing customer data.
flowchart TD
  A[Organisation uploads labelled history: outcomes or failure labels] --> B[Label and leakage checks, split design: time- or group-aware]
  B --> C[Admin pre-registers validation criteria within platform minimum bounds]
  C --> D[Validation job: frozen reference model scored on held-out customer data]
  D --> E[Customer validation report: metrics with CIs, calibration, baselines, minimum-positives check]
  E -->|criteria met| F[Reliability tier CUSTOMER_VALIDATED, scoped to machines, profile, model version, data scope, expiry]
  E -->|not met or inconclusive| G[Tier stays REFERENCE_ONLY; report explains why]
  E --> H{Optional: retrain or fine-tune on customer training partition}
  H --> I[Tenant-private model version evaluated on untouched holdout; own profile and model card]
  I --> E
Requirements
1. Prerequisites: a labelled dataset of a new type TABULAR_LABELLED with documented label definition, a minimum number of positives and rows (platform defaults, configurable), and no label-derived input columns. The compatibility engine checks it like any dataset.
2. Split design: temporal or group-aware (by machine/unit); no row in two partitions; the holdout is used once per validation run; reuse after tuning is rejected.
3. Criteria pre-registered before the run (metric thresholds on the lower confidence bound, calibration tolerance, minimum positives). Criteria cannot be edited after seeing results; a new run requires new criteria.
4. Evaluation compares the frozen reference model with baselines (prevalence, and a customer-trained logistic baseline if retraining is enabled) using the same metrics as §10.1.
5. Outcome: CUSTOMER_VALIDATED is scoped (machines, profile and configuration, model version, data scope) and expires on model-version change, after a configurable period, or when applicability flags show a shift. It never becomes a safety claim, and the report states that historical validation does not guarantee future performance.
6. Retraining (optional): produces tenant-private model versions in a tenant namespace; trained on the customer's training partition only; evaluated on the untouched holdout; has its own customer-specific profile derived from the customer's confirmed mapping; promoted by an Org Admin; never visible to or used by other tenants; subject to plan entitlement and explicit data-use terms.
7. Not required: no milestone before MS6 depends on this, and all analyses remain available without it.
8. Separate reporting: results and reports show Reference-dataset evaluation (public data) and Customer-specific validation in separate sections.
11. System Architecture
11.1 Architecture for the local development environment (Milestones 1–6)
Data enters only through authenticated browser or API uploads. There are no device, streaming or messaging components. Training never runs inside the API or worker processes.
flowchart LR
  subgraph Client
    UI[React + TypeScript SPA]
  end
  subgraph App[Application tier]
    API[FastAPI API: auth, tenancy, datasets, machines, compatibility, results, reports]
  end
  subgraph Proc[Processing tier - separate container]
    W[Worker: scan, validation, compatibility, applicability, analysis, reports]
  end
  subgraph Data[Data tier]
    PG[(PostgreSQL: relational data, job queue, RLS)]
    FS[(Local file storage via StorageService, per-tenant prefixes)]
  end
  subgraph ML[ML workspace - offline, public reference data]
    TR[Training scripts and containers]
    MLF[MLflow tracking + registry]
    ART[(Model artifacts + pipeline profiles)]
  end
  UI -->|HTTPS REST| API
  API <--> PG
  API -->|stream upload| FS
  W <-->|claim jobs, write results| PG
  W <--> FS
  W -->|load Production models + profiles| ART
  TR --> MLF
  MLF --> ART
Optional additions by milestone: ClamAV scan container (optional profile), MinIO behind the same StorageService interface (parity testing), assistant service and LLM provider (MS6). Redis, Celery, Kubernetes, microservice meshes, MQTT and device gateways are not components.
11.2 Dataset upload-to-result flow
sequenceDiagram
  participant U as User (browser)
  participant API as FastAPI
  participant ST as StorageService
  participant DB as PostgreSQL
  participant W as Worker
  U->>API: Create dataset for machine (declared type)
  API->>DB: Check auth, tenant, limits; create dataset + version (UPLOADING)
  U->>API: Stream file content
  API->>ST: Quarantine, hash, magic-byte and structure checks, scan hook
  API->>DB: Version UPLOADED; enqueue VALIDATE_DATASET
  W->>DB: Claim job
  W->>ST: Read file in chunks
  W->>DB: Validation report, quality score, compatibility + applicability + reliability per eligible profile
  U->>API: Review report; confirm type, mapping, units (wizard if needed)
  API->>DB: New mapping version; enqueue re-validation
  U->>API: POST /analyses (check id, acknowledged warnings, limitation acknowledgement, Idempotency-Key)
  API->>DB: Verify gate (§8.4.7); create RUN_ANALYSIS job
  W->>DB: Claim job; re-verify check hashes
  W->>ST: Read data; preprocess; infer; explain; write result artifact
  W->>DB: Commit result + job SUCCEEDED + usage event (one transaction)
  U->>API: View result with trust panel, explanations, recommendations
11.3 Tenant isolation architecture
flowchart TD
  R[HTTP request with JWT: sub, org_id, role] --> V[Validate token and role]
  V --> T[Build TenantContext]
  T --> D[Repository layer requires TenantContext]
  D --> S[Transaction: SET LOCAL app.current_org]
  S --> Q[Query with explicit organisation_id filter]
  Q --> P[PostgreSQL RLS policy re-checks organisation_id]
  D --> O[Storage key built from org_id prefix only]
Three layers (explicit predicates, RLS, context-derived storage keys). Delivered from Milestone 1 in minimal form; hardened and made a CI gate in Milestone 3. Until the gate passes, MULTI_ORG_ENABLED=false.
11.4 Frontend architecture
React 18 + TypeScript (strict) + Vite; Tailwind CSS; Recharts (Chart.js or Plotly only where a needed chart type is missing). Feature-based folders, TanStack Query with polling for job status, React Router with role-aware guards (convenience only), API client generated from the OpenAPI schema. A shared TrustPanel component renders compatibility, applicability, reliability and the limitation text, and is required on every result view. Large tables are server-paginated; charts receive downsampled arrays; every data panel has loading, empty and error states.
11.5 Backend architecture
Layer
Responsibility
api/routers
HTTP routing, Pydantic v2 models, TenantContext and permission dependencies
services
Organisation, dataset, validation and analysis orchestration, recommendations, reports, usage
compat
Compatibility, applicability and reliability engine; profiles (pure Python, heavily tested)
repositories
SQLAlchemy 2.0, tenant-scoped; no repository method exists without a TenantContext
workers
Job claim loop, step executors, heartbeats, cancellation checks
ml_runtime
Model loading, industria_features, inference, SHAP
adapters
Implementations of the interfaces in §11.9 (storage, queue, secrets, email, model store, billing)
core
Config, security, logging, rate limiting, error handlers
The application is a modular monolith (one API codebase, one worker image sharing the same packages). It is split only along the lines already present (API / worker / ML workspace).
11.6 Machine learning architecture
flowchart TD
  A[Public reference dataset + checksum] --> B[Validation and per-dataset preprocessing]
  B --> C[Stratified or grouped split, test locked, indices hashed]
  C --> D[Feature library]
  D --> E[Baselines B0 B1 per configuration]
  E --> F[Advanced models with CV, identical folds across configurations]
  F --> G[Calibration, thresholds, reference ranges]
  G --> H[One-time test evaluation + CIs + paired comparison + SHAP]
  H --> I[MLflow run + model card: reference-dataset evaluation section]
  I --> J{Registration gate}
  J -->|fail| K[Archive run]
  J -->|pass| L[Registry: Staging]
  L --> M[Operator promotes to Production]
  M --> N[Worker loads Production by version]
  N --> O[Result summaries: applicability flags, drift of inputs vs reference ranges]
11.7 Assistant architecture (MS6)
Grounded, read-only, tenant-scoped tool layer as specified in §8.9. Tool queries use the same TenantContext and RLS path as the API. Retrieval over documents is a future item.
11.8 Authentication and authorisation flow
sequenceDiagram
  participant B as Browser
  participant API as FastAPI
  participant DB as PostgreSQL
  B->>API: POST /auth/login
  API->>DB: Load user and organisation
  API->>API: Verify Argon2id hash, active user, organisation status
  API->>DB: Store hashed refresh token (rotating family)
  API-->>B: Access JWT 15 min (sub, org_id, role) + HttpOnly refresh cookie
  B->>API: Request with Bearer token
  API->>API: Verify token, role permission (MS3: plant access), entitlement (MS5)
  API->>DB: Tenant-scoped query under RLS
  API-->>B: Response, or 404 for out-of-tenant resources
11.9 Local development versus future production SaaS
The product is a multi-tenant B2B SaaS by design; its first implementation is local-first. Business logic depends only on interfaces, so each local adapter can be replaced by a production adapter without a rewrite.
Concern
Local development environment
Future production deployment
Interface that isolates the change
Frontend
Vite dev server or nginx container serving the React build
Static hosting/CDN behind TLS and WAF
–
Backend
FastAPI container(s) under Docker Compose
Container hosting (managed container service) behind a load balancer; horizontal replicas
–
Database
PostgreSQL container, one instance
Managed PostgreSQL with backups, PITR, read replica if needed
SQLAlchemy / Alembic
File storage
Local volume via StorageService (MinIO optional)
Secure object storage (S3-compatible), server-side encryption with managed keys, lifecycle rules
StorageService
Background processing
PostgreSQL job queue, 1–2 worker containers
Same queue pattern scaled out, or a managed queue; autoscaled worker pool
JobQueue
Authentication
Built-in email/password, local email catcher
Production auth hardening (verified email provider, optional SSO later), key rotation
AuthProvider, EmailProvider
Secrets
.env file (git-ignored)
Secrets manager with rotation; no secrets in images
SecretsProvider
ML training
Local scripts or one-off containers, outside the app stack
Scheduled or on-demand training infrastructure with GPU where justified, isolated from tenant data
ModelStore (MLflow)
Model serving
In-worker inference from the registry cache
Scalable inference workers (or a separate inference service if latency or isolation requires it)
ModelStore, InferenceRunner
Monitoring and logging
Structured logs to console/files; basic health endpoints
Central logging, metrics, tracing, alerting, uptime checks
Logging and metrics adapters
Backups
Nightly script, 14-day retention, restore drill
Automated backups, PITR, cross-region copies, restore drills
Backup tooling
Deployment
docker compose up, GitHub Actions for tests and image builds
CI/CD pipeline with environments, migrations as a release step, infrastructure as code
–
Billing
No-op BillingProvider
Payment provider integration
BillingProvider
Virus scanning
Structural checks, optional ClamAV
ClamAV (or equivalent) mandatory
ScanService
flowchart LR
  subgraph Future[Future production SaaS]
    CDN[CDN + WAF + TLS] --> APIp[API replicas]
    APIp --> PGm[(Managed PostgreSQL)]
    APIp --> OBJ[(Secure object storage)]
    WP[Autoscaled worker pool] --> PGm
    WP --> OBJ
    WP --> MS[(Model store / registry)]
    TRp[Training infrastructure - public reference data] --> MS
    APIp --> SEC[Secrets manager]
    APIp --> MON[Monitoring, logging, alerting]
  end
Evolution rules. No Kubernetes, Redis, service mesh or additional microservices unless a measured requirement is documented (for example sustained queue load, strict inference isolation, or compliance). Infrastructure choices are deferred to the production phase and recorded as decisions.
Local memory plan (16 GB laptop, 8 GB for Docker): PostgreSQL 1 GB, API 0.5 GB, worker 4 GB (limit), MLflow 0.5 GB, optional MinIO 0.5 GB, optional ClamAV 1 GB, frontend 0.1 GB. Training runs outside this budget and never concurrently with heavy analysis jobs.
Dependency justification
Technology
Responsibility
Required?
React, TypeScript, Tailwind, Recharts
UI and charts
Yes
FastAPI, Pydantic, SQLAlchemy, Alembic
API, validation, ORM, migrations
Yes
PostgreSQL
Relational data, job queue, RLS, JSONB results
Yes
scikit-learn, XGBoost, PyTorch, SHAP, NumPy, Pandas, SciPy, pyarrow, openpyxl, h5py, librosa
ML, parsing, signal and audio processing
Yes, introduced per milestone (PyTorch from MS4, librosa MS6)
MLflow
Tracking and registry
Yes
Docker, Docker Compose, GitHub Actions
Packaging and CI
Yes
MinIO, ClamAV
Object storage parity, malware scanning
Optional locally
Redis, Celery, Kubernetes
–
Not used
MQTT, ESP32, Arduino, device gateways
–
Not part of the product
12. Database Schema
Conventions. PostgreSQL 15+. UUID primary keys. timestamptz in UTC. Enumerations as text with CHECK. Every tenant table has organisation_id uuid NOT NULL REFERENCES organisations(id) and an RLS policy USING (organisation_id = current_setting('app.current_org')::uuid). Global tables have no organisation_id and are read-only for the application role. The minimum tenant boundary (MS1) covers all tenant tables that exist in MS1; later tables follow the same pattern. Tables are tagged with the milestone that creates them.
12.1 Entity-relationship diagram
erDiagram
  organisations ||--o{ users : employs
  organisations ||--o{ plants : owns
  plants ||--o{ machines : contains
  machine_categories ||--o{ machines : classifies
  machines ||--o{ datasets : has
  datasets ||--o{ dataset_versions : versioned_as
  dataset_versions ||--o{ column_mappings : mapped_by
  dataset_versions ||--o{ validation_reports : validated_in
  dataset_versions ||--o{ dataset_events : history
  pipeline_profiles ||--o{ compatibility_checks : evaluated_against
  column_mappings ||--o{ compatibility_checks : used_in
  compatibility_checks ||--o{ warning_acknowledgements : acknowledged_by
  compatibility_checks ||--o{ jobs : authorises
  machines ||--o{ limitation_acknowledgements : acknowledged_for
  model_versions ||--o{ limitation_acknowledgements : refers_to
  jobs ||--o| analysis_results : produces
  model_versions ||--o{ analysis_results : generated_by
  pipeline_profiles ||--o{ model_versions : describes
  model_versions ||--o{ model_evaluations : evaluated_on_reference_data
  experiment_records ||--o{ model_versions : produced
  analysis_results ||--o{ recommendations : triggers
  analysis_results ||--o{ findings : raises
  recommendations ||--o{ maintenance_logs : leads_to
  machines ||--o{ maintenance_logs : history
  organisations ||--o{ audit_logs : audited
  organisations ||--|| subscriptions : has
  plans ||--o{ subscriptions : defines
  organisations ||--o{ usage_events : metered
  organisations ||--o{ reports : requests
  machines ||--o{ customer_validations : validated_in
  customer_validations ||--o{ model_versions : may_produce_tenant_private
  users ||--o{ assistant_conversations : owns
12.2 Tables
Legend: PK, FK, NN (not null), UQ (unique), T tenant table, G global table; (MSn) = created in that milestone.
organisations (MS1): id PK; name NN; slug NN UQ; status CHECK in (ACTIVE, SUSPENDED, PENDING_DELETION); timezone; settings jsonb; created_at.
users (T, MS1): id PK; organisation_id FK NN; email citext NN UQ; full_name; password_hash NN (Argon2id); role CHECK in (ORG_ADMIN, ENGINEER, ANALYST, VIEWER) (MS1 uses ORG_ADMIN only); is_active; failed_login_count; locked_until; email_verified_at (MS3); last_login_at. Index (organisation_id, role). refresh_tokens (T, MS1): id, user_id, family_id, token_hash UQ, expires_at, revoked_at. invitations (T, MS3): id, organisation_id, email, role, plant_ids uuid[], token_hash UQ, expires_at, accepted_at, invited_by.
plants (T, MS1): id, organisation_id, code NN, name NN, is_default bool, country, timezone; UQ(organisation_id, code). user_plant_access (T, MS3): PK(user_id, plant_id).
machine_categories (G, MS1): code PK, name, eligible_dataset_types text[], eligible_profiles text[].
machines (T, MS1): id PK; organisation_id; plant_id FK NN; asset_tag NN, UQ(organisation_id, asset_tag); name NN; category_code FK NN; manufacturer, model_number, serial_number; install_date; rated_parameters jsonb; acoustic_machine_type (MS6); bearing_designation (MS4); condition CHECK in (NO_ANALYSIS, WARNING, CRITICAL, NO_CONCERN) (MS2); condition_basis jsonb (result ids, rule version, reliability tiers); condition_as_of; archived_at. No device, connection or protocol columns exist.
datasets (T, MS1): id, organisation_id, machine_id FK NN, name NN, description, dataset_type CHECK in (TABULAR_OPERATING_STATE, RUN_TO_FAILURE_MULTIVARIATE, VIBRATION_SIGNAL, AUDIO_RECORDING, TABULAR_TIMESERIES, TABULAR_LABELLED (MS6), UNKNOWN), type_confirmed_by, type_confirmed_at, objective, provenance NN default CUSTOMER CHECK in (CUSTOMER, SIMULATED, PUBLIC_SAMPLE), status CHECK in (ACTIVE, PENDING_DELETION, DELETED), created_by; UQ(organisation_id, machine_id, name).
dataset_versions (T, MS1): id; organisation_id; dataset_id FK; version_no UQ(dataset_id, version_no); derived_from_version_id; derivation_recipe jsonb; file_kind CHECK in (CSV, XLSX, PARQUET, MAT, WAV, ZIP_WAV) (CSV only in MS1); original_filename (display only); storage_key NN UQ (org/{org}/datasets/{id}/v{n}/{uuid}); size_bytes > 0; sha256 char(64) NN; scan_status CHECK in (PENDING, CLEAN, INFECTED, ERROR); status CHECK in (UPLOADING, UPLOADED, VALIDATING, VALIDATED, VALIDATION_FAILED, PENDING_DELETION, PURGED); row_count; column_count; uploaded_by; retain_until.
dataset_columns (T, MS1): dataset_version_id, position, name, inferred_type, stats jsonb. column_mappings (T, MS1): id, organisation_id, dataset_version_id, profile_id, mapping_version int, mappings jsonb (canonical feature → {column, unit, conversion, asserted_equivalence bool}), options jsonb, confirmed_by, confirmed_at, mapping_hash; UQ(dataset_version_id, profile_id, mapping_version). validation_reports (T, MS1): id, dataset_version_id, mapping_id, validator_version, quality_score numeric(5,2), quality_components jsonb, checks jsonb, preview jsonb, created_at; immutable. dataset_events (T, MS1, append-only): id bigserial, dataset_version_id, event_type, actor_id, details jsonb, created_at.
pipeline_profiles (G, MS1): id, profile_id NN (e.g. ai4i_failure_no_type, ai4i_failure_with_type, cmapss_rul, paderborn_bearing, sensor_anomaly, mimii_acoustic), version, pipeline CHECK in (A, B, C, D, E), configuration text, training_domain text NN CHECK in (REFERENCE_DATASET, USER_REFERENCE_SEGMENT, TENANT_PRIVATE), document jsonb NN, is_active; UQ(profile_id, version). Tenant-private profiles (MS6) additionally carry organisation_id (T).
compatibility_checks (T, MS1)
Field
Type
Constraints
id
uuid
PK
organisation_id, dataset_version_id, machine_id
uuid
NN FK
mapping_id
uuid
FK
profile_uuid
uuid
NN FK pipeline_profiles
status
text
NN CHECK in (COMPATIBLE, COMPATIBLE_WITH_WARNINGS, INCOMPATIBLE, INSUFFICIENT_DATA, UNSUPPORTED_FORMAT)
reasons
jsonb
NN (array of reason objects)
applicability_level
text
CHECK in (IN_REFERENCE_RANGE, PARTLY_OUTSIDE_REFERENCE_RANGE, MOSTLY_OUTSIDE_REFERENCE_RANGE, NOT_ASSESSED); NOT_ASSESSED when status is not runnable
applicability_detail
jsonb
flagged fractions, per-feature breakdown, joint-domain result, thresholds, domain notes
reliability_tier
text
NN CHECK in (REFERENCE_ONLY, CUSTOMER_VALIDATED, NOT_APPLICABLE)
reliability_basis
jsonb
evidence references (reference evaluation id, customer validation id)
inputs_hash
char(64)
NN
created_at
timestamptz
NN
Index (organisation_id, dataset_version_id, profile_uuid, created_at DESC). Immutable. warning_acknowledgements (T, MS1): id, compatibility_check_id, reason_code, acknowledged_by, acknowledged_at. limitation_acknowledgements (T, MS1): id, organisation_id, machine_id, profile_uuid, model_version_id, statement_version text, acknowledged_by, acknowledged_at; UQ(machine_id, profile_uuid, model_version_id, statement_version).
jobs (T, MS1): id; organisation_id; job_type CHECK in (SCAN_UPLOAD, VALIDATE_DATASET, RUN_ANALYSIS, GENERATE_REPORT, PURGE_DATASET, VALIDATE_ON_CUSTOMER_DATA, RETRAIN_TENANT_MODEL); status CHECK in (QUEUED, RUNNING, RETRY_WAIT, CANCEL_REQUESTED, SUCCEEDED, FAILED, CANCELLED); priority; payload jsonb (dataset_version_id, compatibility_check_id, model_version_id, configuration, params); params_hash; idempotency_key UQ(organisation_id, idempotency_key); attempt, max_attempts; run_after; claimed_by, heartbeat_at; progress_percent 0–100; current_step; cancel_requested; error_code, user_message, remedy, diagnostic_id; created_by; created_at, started_at, finished_at. Indexes: partial (priority DESC, run_after) WHERE status = QUEUED; (organisation_id, status, created_at DESC).
analysis_results (T, MS1): id; organisation_id, machine_id, dataset_version_id NN FK; job_id NN UQ; compatibility_check_id NN FK; profile_uuid NN FK; configuration text (WITH_TYPE, NO_TYPE, or null); model_version_id FK (null for Capability E, which stores algorithm_version); pipeline char(1); result_version int, UQ(machine_id, dataset_version_id, profile_uuid, result_version); is_latest (partial UQ per machine, dataset version, profile); training_domain NN; applicability_level NN; reliability_tier NN; ood_summary jsonb; summary jsonb; top_rows jsonb; artifact_uri; explanation_meta jsonb; limitations jsonb NN (copied from the model card); created_at. Immutable. Index (organisation_id, machine_id, pipeline, created_at DESC) (prediction history, MS2).
model_versions (G; tenant-private rows in MS6 carry organisation_id): id; registry_name; version; mlflow_run_id; experiment_id FK; pipeline; configuration; task; algorithm; stage CHECK in (STAGING, PRODUCTION, ARCHIVED); profile_uuid FK; training_domain NN; model_scope CHECK in (SHARED, TENANT_PRIVATE); default_when_both_runnable bool (AI4I); reference_ranges_uri; thresholds jsonb; dataset_hash; model_card_uri; promoted_by, promoted_at. model_evaluations (G): model_version_id, evaluation_kind NN CHECK in (REFERENCE_DATASET, CUSTOMER_SPECIFIC), split, metric_name, metric_value, ci_low, ci_high, n_samples, subset, paired_comparison_ref; evaluation_kind keeps research-dataset metrics and customer-specific results separate. experiment_records (G): MLflow mirror.
recommendation_rules (G, MS2): rule_code PK, pipeline, trigger jsonb, template, default_priority, version, reviewed_by, reviewed_at. recommendations (T, MS2): id, organisation_id, machine_id, analysis_result_id NN, rule_code, rule_version, text NN, priority, status CHECK in (PROPOSED, APPROVED, REJECTED, DEFERRED, SCHEDULED, DONE) (only PROPOSED before MS5), decided_by, decided_at, rejection_reason_code, evidence jsonb (dataset version, model version, tier). reports (T, MS2): id, report_type CHECK in (ANALYSIS, MACHINE, PLANT, PROVENANCE, CSV_EXPORT), parameters, status, artifact_uri, requested_by, created_at, expires_at.
audit_logs (T-with-null-org, MS3, append-only): id bigserial, organisation_id, actor_id, action, entity_type, entity_id, before jsonb, after jsonb, ip, created_at. findings (T, MS5) and maintenance_logs (T, MS5) as in v1.1 (findings deduplicated per machine and rule; maintenance logs with type, status, schedule, assignee, outcome, downtime, cost). plans (G, MS5), subscriptions (T, MS5), usage_events (T, append-only; written from MS1), usage_counters (T, MS5) as in v1.1. assistant_conversations / assistant_messages (T, MS6).
customer_validations (T, MS6): id, organisation_id, machine_scope uuid[], profile_uuid, model_version_id, labelled_dataset_version_id FK, split_design jsonb, criteria jsonb NN (frozen before the run), criteria_frozen_at NN, status CHECK in (DRAFT, RUNNING, PASSED, FAILED, INCONCLUSIVE, EXPIRED), metrics jsonb, report_uri, valid_until, created_by, created_at. A PASSED validation sets reliability_tier = CUSTOMER_VALIDATED on subsequent checks and results within its scope until it expires.
12.3 Integrity rules
• Large objects live in storage; the database holds keys, hashes, sizes. Keys always start org/{organisation_id}/.
• Append-only tables (audit_logs, dataset_events, usage_events, analysis_results, validation_reports, compatibility_checks) have no UPDATE/DELETE privilege for the application role, except the controlled is_latest flip.
• Foreign keys use ON DELETE RESTRICT along provenance chains; deletion is soft plus the purge job.
• Nightly integrity job: every tenant table has an RLS policy; no orphaned object keys; every result has a model or algorithm version, training domain, applicability level and reliability tier; no CUSTOMER_VALIDATED result without a non-expired PASSED validation in scope.
13. API Specifications
13.1 Conventions
• Base path /api/v1; JSON except uploads and downloads. The OpenAPI schema generated by FastAPI is the machine-readable contract; the tables below are authoritative for behaviour. Endpoints are tagged with their milestone.
• Auth: Authorization: Bearer <access_jwt> with claims sub, org_id, role.
• Tenant scoping: every resource is resolved inside the caller's organisation; other tenants' resources return 404.
• Pagination page, page_size (max 200). Idempotency-Key accepted on POSTs that create jobs or records.
• Rate limits: auth 10/min per IP; uploads and analyses by limits (global configuration in MS1–MS4, plans from MS5).
• No hardware or live endpoints exist: no device, telemetry, MQTT or sensor-streaming routes.
{"error": {"code": "APPLICABILITY_BLOCKED", "message": "Most rows lie outside the range the model was trained on.", "details": [{"field": "torque", "issue": "48% of rows outside reference range"}], "request_id": "b6a1c0e2"}}
HTTP
Codes
401
UNAUTHENTICATED, TOKEN_EXPIRED
403
FORBIDDEN, QUOTA_EXCEEDED, FEATURE_NOT_ENTITLED, SUBSCRIPTION_SUSPENDED, MULTI_ORG_DISABLED (MS1–MS2)
404
NOT_FOUND (including out-of-tenant)
409
CONFLICT, INVALID_STATE_TRANSITION, MACHINE_ARCHIVED, JOB_NOT_CANCELLABLE
413 / 415
PAYLOAD_TOO_LARGE / UNSUPPORTED_FORMAT
422
VALIDATION_ERROR, INCOMPATIBLE, INSUFFICIENT_DATA, APPLICABILITY_BLOCKED, COMPAT_CHECK_STALE, WARNINGS_NOT_ACKNOWLEDGED, LIMITATIONS_NOT_ACKNOWLEDGED
429
RATE_LIMITED, QUEUE_FULL
503
MODEL_UNAVAILABLE, ASSISTANT_UNAVAILABLE
500
INTERNAL_ERROR
13.2 Authentication, organisation, users
Method + URL
MS
Roles
Request
Response
Rules and errors
POST /auth/register
1
Public
{email, full_name, password, organisation_name}
201 generic message
Password ≥ 12 chars, not common; generic response for existing email; 403 MULTI_ORG_DISABLED if an organisation already exists and MULTI_ORG_ENABLED=false; email verification enforced from MS3
POST /auth/login, /auth/refresh, /auth/logout
1
Public / cookie / Bearer
credentials
200 {access_token, expires_in: 900, user:{id, role, organisation}}
401 generic; 423 lockout after 5 failures; refresh rotation with reuse detection
GET /users/me, PATCH /users/me
1
All
profile fields
200
Password change needs the current password
GET /organisation, PATCH /organisation
3
Org Admin
name, timezone, settings
200
Retention within bounds
GET /organisation/users, POST /organisation/invitations, PATCH /organisation/users/{id}, POST /auth/accept-invitation
3
Org Admin / Public
{email, role, plant_ids}
200/201
409 when removing the last Org Admin
GET/POST/PATCH /plants
3
Org Admin
{code, name, country, timezone}
200/201
MS1 exposes only the default plant read-only
GET /organisation/audit-log
3
Org Admin
filters
200 paginated
Read-only
GET /organisation/usage
5
Org Admin
–
200 {plan, quotas:[{name, used, limit}]}

13.3 Machines
Method + URL
MS
Roles
Request
Response
Rules
POST /machines
1
Org Admin (MS3: + Engineer)
{asset_tag, name, category_code, plant_id?, manufacturer?, model_number?, install_date?, rated_parameters?}
201
plant_id defaults to the default plant; 409 duplicate tag
GET /machines, GET /machines/{id}
1
All
filters, paging
200; detail includes condition, condition_as_of, latest result per pipeline with trust summary (MS2)

PATCH /machines/{id}, POST /machines/{id}/archive
1
as above
partial / {reason}
200
Category cannot change once datasets exist
GET /machine-categories
1
All
–
200 categories with eligible dataset types and pipelines

13.4 Datasets
Method + URL
MS
Roles
Request
Response
Validation and errors
POST /machines/{id}/datasets
1
Org Admin (MS3: + Engineer, Analyst)
{name, description?, dataset_type?, objective?}
201
409 duplicate name
POST /datasets/{id}/versions
1
same
{file_name, file_kind, size_bytes, sha256?}
201 {version_id, upload_url}
413 over limit; 415 unsupported kind; 403 quota (MS5)
PUT /dataset-versions/{vid}/content
1
same
binary stream (or Content-Range chunks)
200 {status: "UPLOADED", sha256, job_id}
415 magic-byte mismatch; 422 hash mismatch; 400 FILE_REJECTED on scan failure
GET /datasets, GET /machines/{id}/datasets, GET /datasets/{id}
1
All
filters
200

GET /dataset-versions/{vid}
1
All
–
200 {status, file_kind, size_bytes, sha256, row_count, columns, quality_score, latest_validation_report_id, compatibility:[{profile_id, status, applicability_level, reliability_tier}]}

GET /dataset-versions/{vid}/preview
1
All
rows ≤ 1000
200

PATCH /datasets/{id}
1
Editors
{dataset_type, objective, name, description}
200
Confirming type triggers re-validation
PUT /dataset-versions/{vid}/mappings/{profile_id}
1
Editors
ColumnMapping
200 {mapping_id, mapping_version, validation_job_id}
422 unknown column; unit not allowed; a mapping for product_type is accepted only under ai4i_failure_with_type and requires asserted_equivalence: true; any other profile rejects it (422 E_FEATURE_NOT_IN_PROFILE)
GET /dataset-versions/{vid}/mappings/{profile_id}/suggestions
1
Editors
–
200 suggestions flagged suggested: true
Never auto-applied
GET /dataset-versions/{vid}/validation-reports, GET /validation-reports/{id}
1
All
–
200

GET /dataset-versions/{vid}/history
1
All
–
200

POST /dataset-versions/{vid}/derive
1
Editors
{recipe:{drop_exact_duplicates:true}}
202 {job_id}
Original unchanged
DELETE /dataset-versions/{vid}, POST .../restore
1
Admin; owner
–
202 {status:"PENDING_DELETION", purge_after}
30-day grace
GET /pipeline-profiles/{profile_id}/template
2
All
format=csv
200 header template

ColumnMapping for the without-Type AI4I profile (no product_type):
{
  "mappings": {
    "air_temperature":     {"column": "Air temp", "unit": "degC"},
    "process_temperature": {"column": "Process temp", "unit": "degC"},
    "rotational_speed":    {"column": "RPM", "unit": "rpm"},
    "torque":              {"column": "Torque", "unit": "Nm"},
    "tool_wear":           {"column": "Tool wear", "unit": "min"}
  },
  "options": {"missing_policy": "EXCLUDE_ROWS"}
}
For ai4i_failure_with_type the mapping adds "product_type": {"column": "Type", "asserted_equivalence": true}.
13.5 Compatibility, applicability, reliability and analyses
Method + URL
MS
Roles
Request
Response
Rules and errors
POST /dataset-versions/{vid}/compatibility-checks
1
Editors
{profile_id?, mapping_id?}; omitted profile_id evaluates every eligible profile (both AI4I configurations for a general machine tool)
201 list of CompatibilityCheck
New immutable checks; 202 with job_id when heavy
GET /dataset-versions/{vid}/compatibility-checks, GET /compatibility-checks/{id}
1
All
profile_id?
200

POST /analyses
1
Editors
{compatibility_check_id, acknowledged_reason_codes: [], limitation_acknowledged: true, parameters?, force_rerun?: false} + Idempotency-Key
202 {job_id, status:"QUEUED"}
422 INCOMPATIBLE, INSUFFICIENT_DATA, UNSUPPORTED_FORMAT; 422 APPLICABILITY_BLOCKED; 422 WARNINGS_NOT_ACKNOWLEDGED listing missing codes; 422 LIMITATIONS_NOT_ACKNOWLEDGED; 422 COMPAT_CHECK_STALE; 403 FEATURE_NOT_ENTITLED / QUOTA_EXCEEDED (MS5); 429 QUEUE_FULL; 200 with the existing job/result when the natural key matches and force_rerun is false
GET /jobs/{id}, GET /jobs
1
Creator/Admin
filters
200

POST /jobs/{id}/cancel
2
Creator/Admin
–
202
409 JOB_NOT_CANCELLABLE
POST /jobs/{id}/retry
2
Creator/Admin
–
202
Only FAILED jobs with retryable codes
GET /machines/{id}/analyses (prediction history)
2
All
pipeline, configuration, latest_only, paging
200

GET /analyses/{result_id}
1
All
–
200 AnalysisResult with provenance and trust block

GET /analyses/{result_id}/rows
1
All
sort, risk_class, ood_only, paging
200

GET /analyses/{result_id}/explanations
2
All
row_index? or global=true
200 (may be 202 if computed on demand)

GET /models, GET /models/{id}
2
All
–
200 Production models: configuration, training domain, reference-dataset evaluation metrics with CIs (only once experiments exist), limitations, model card; customer-specific validation: none for shared models

CompatibilityCheck example (illustrative values only, not experiment results):
{
  "id": "0c7e...",
  "dataset_version_id": "91ab...",
  "profile": {"profile_id": "ai4i_failure_no_type", "version": "1.0.0", "pipeline": "A", "configuration": "NO_TYPE"},
  "compatibility": {"status": "COMPATIBLE_WITH_WARNINGS", "reasons": [
    {"code": "W_QUALITY_POOR", "severity": "WARNING", "message": "Data quality score is below 60.", "remedy": "Resolve missing values or duplicates."}]},
  "applicability": {"level": "PARTLY_OUTSIDE_REFERENCE_RANGE", "flagged_row_fraction": 0.074, "per_feature": {"torque": 0.061},
    "domain_note": "Model trained on AI4I 2020 synthetic data; your machine and operating conditions may differ.",
    "disclaimer": "This level is a warning mechanism, not evidence that predictions are reliable or unreliable.",
    "reasons": [{"code": "W_OOD", "severity": "WARNING"}]},
  "reliability": {"tier": "REFERENCE_ONLY", "statement": "Reference-dataset-trained model; not validated on your equipment."},
  "requires_acknowledgement": ["W_QUALITY_POOR", "W_OOD"],
  "requires_limitation_acknowledgement": true,
  "quality_score": 58.4,
  "created_at": "2026-11-10T08:15:30Z"
}
Both AI4I configurations are returned as separate checks when a confirmed Type column exists; the response never merges them. If there is no Type column the ai4i_failure_with_type check is returned as INCOMPATIBLE with E_MISSING_FEATURE for product_type and the UI presents NO_TYPE as the supported path.
Blocked-run example:
POST /api/v1/analyses   {"compatibility_check_id": "5d2f...", "limitation_acknowledged": true}
422 Unprocessable Entity
{"error": {"code": "APPLICABILITY_BLOCKED", "message": "Most rows lie outside the model's reference range; results would be extrapolation.",
  "details": [{"code": "E_OOD_MAJORITY", "observed": "flagged fraction exceeds block threshold", "remedy": "Check units and scaling, or analyse a subset within the supported range."}], "request_id": "e19c..."}}
AnalysisResult excerpt:
{
  "id": "a41d...", "machine_id": "7d1f...", "pipeline": "A", "configuration": "NO_TYPE", "result_version": 2, "is_latest": true,
  "provenance": {"dataset": {"name": "line2_test_run", "version": 3, "sha256": "ab12...", "provenance": "CUSTOMER"}, "mapping_version": 2,
    "profile": "ai4i_failure_no_type@1.0.0", "model": {"registry_name": "ai4i_failure_clf_notype", "version": "1.0.0", "training_domain": "REFERENCE_DATASET", "trained_on": "AI4I 2020 (synthetic)"},
    "computed_at": "2026-11-10T08:21:44Z", "acknowledged_warnings": ["W_OOD"]},
  "trust": {"compatibility": "COMPATIBLE_WITH_WARNINGS", "applicability": "PARTLY_OUTSIDE_REFERENCE_RANGE", "reliability_tier": "REFERENCE_ONLY",
    "label": "Reference-dataset-trained model – not validated on your equipment"},
  "semantics": "Reference-calibrated failure probability for the supplied operating state; no time horizon is implied.",
  "evaluation_sections": {"reference_dataset_evaluation": {"model_card_uri": "..."}, "customer_specific_validation": null},
  "limitations": ["Trained on synthetic data", "Calibration measured on the reference dataset only"],
  "explanation_disclaimer": "Feature attributions describe model behaviour, not physical causation."
}
13.6 Recommendations, maintenance, findings
Method + URL
MS
Roles
Notes
GET /recommendations, GET /recommendations/{id}
2
All
Read-only in MS2; each carries evidence (dataset version, model version, tier) and the text based on uploaded data and a reference-trained model
POST /recommendations/{id}/decision
5
Org Admin, Engineer
`{decision: APPROVE
POST /machines/{id}/maintenance, PATCH /maintenance/{id}, GET /maintenance, GET /machines/{id}/maintenance
5
Org Admin, Engineer (read: all)
SCHEDULED → IN_PROGRESS → COMPLETED; completion requires outcome; illegal transitions 409
GET /findings, POST /findings/{id}/acknowledge
5
All / Org Admin, Engineer
OPEN → ACKNOWLEDGED only
13.7 Reports
Method + URL
MS
Request
Response
POST /reports/analysis
2
{analysis_result_id}
202 {report_id}; PDF with provenance, trust panel and separated evaluation sections
POST /reports/machine, POST /reports/plant, POST /exports/analysis-csv
5
machine/plant/result ids
202
GET /reports/{id}, GET /reports/{id}/download
2
–
200 / signed expiring URL (15 min)
13.8 Customer-specific validation (MS6, optional)
Method + URL
Roles
Request
Response
Rules
POST /customer-validations
Org Admin, Engineer, Analyst
{profile_id, model_version_id, machine_ids, labelled_dataset_version_id, split_design, criteria}
201 {id, status: "DRAFT"}
Criteria must satisfy platform minimum bounds; 422 on label leakage or too few positives
POST /customer-validations/{id}/run
same
–
202 {job_id}
Freezes criteria at run time; holdout single-use
GET /customer-validations, GET /customer-validations/{id}
All
–
200 report, metrics with CIs, scope, expiry
Shown separately from reference-dataset evaluation
POST /customer-validations/{id}/retrain
Org Admin
`{approach: FINE_TUNE
REFIT}`
202 {job_id}
13.9 Assistant (MS6)
POST /assistant/messages, POST /assistant/conversations/{id}/messages ({content, machine_id?}) return {message_id, system_data, explanation, verifier_status}; GET/DELETE /assistant/conversations* for the caller's own conversations. 503 ASSISTANT_UNAVAILABLE returns system data only.
13.10 Platform operator and health (internal)
GET /health, GET /ready (public); operator-only POST /platform/models/{id}/promote, PUT /platform/organisations/{id}/subscription (MS5), POST /platform/support-grants (MS3). Operator endpoints are not part of the tenant API.
14. Frontend UI/UX Specifications
14.1 Design direction
• Professional industrial SaaS: dense, legible, neutral graphite surfaces, one accent colour; status colours reserved for result states and always paired with icon and text; tabular numerals and units next to values.
• No fake live data, connection indicators or device status anywhere. Time series are historical datasets on analysis timelines; every chart header names the dataset, version and model.
• A persistent provenance strip on every result: dataset · version · mapping · profile · configuration · model version · computed at · data-source badge (CUSTOMER / SIMULATED / PUBLIC_SAMPLE).
• No hard-coded statistics: empty organisations see onboarding with Load sample data (labelled public-sample packs).
14.2 Trust panel (required on every result, machine card and report)
Element
Content
Model label
Badge Reference-dataset-trained model with the training domain (e.g. AI4I 2020, synthetic)
Compatibility
Status chip with reasons (dataset format and schema fit this pipeline)
Applicability
Level chip with flagged-row share and per-feature breakdown, plus the line A warning mechanism, not proof of reliability
Reliability
Tier chip: REFERENCE_ONLY reads No validation on your equipment; CUSTOMER_VALIDATED shows scope and expiry
Evidence
Two separate expandable sections: Reference-dataset evaluation (public data) and Customer-specific validation (none performed by default)
Limits
Standing text: Advisory. Predictions from public-data-trained models do not represent performance on your equipment. Not a safety assessment.
A result view that lacks any element is a defect (SM-6, AC-AP-4).
14.3 Global behaviours
Concern
Specification
Loading
Skeletons; long operations show job progress and step names
Empty
Explains why and offers the next step
Error
Inline card with message, request_id, Retry; error boundary per page; validation messages quote stored reason objects
Staleness
Results older than the organisation setting show Stale analysis
Responsive
≥ 1280 px full; 768–1279 px collapsed navigation, two-column grids; < 768 px single column, tables as cards; mobile is read-only for results
Permissions
Controls unavailable to the role are hidden or disabled with a tooltip
Accessibility
Keyboard navigable, ARIA labels, table alternative for each chart
14.4 Pages by milestone
#
Page
MS
Layout and components
Data and interactions
Loading / empty / error
1
Registration and login
1
Card; Create organisation / Sign in; in single-organisation mode the registration tab explains that registration is closed after the first organisation
Password strength; lockout messages
Generic errors
2
Machine inventory and detail (basic)
1
Table; detail with datasets and latest results
Create/archive machines; upload entry point
Empty states
3
Dataset upload centre
1
Drag-and-drop zone with format and size limits, upload queue, recent uploads
Chunked upload, cancel; client pre-check (server authoritative)
Errors map to 413, 415, FILE_REJECTED
4
Dataset validation interface
1
Tabs: Preview, Schema and mapping, Quality checks, Compatibility, History; Compatibility tab lists each eligible profile with the three-part trust summary; for AI4I it shows both configurations side by side and states that Type is optional and AI4I-specific
Edit type, mapping, units; wizard; acknowledge warnings; Run analysis enabled only when the gate allows
Progress states; INCOMPATIBLE and INSUFFICIENT_DATA show reasons and remedies without extra clicks
5
Analysis job monitoring
1
Job table with status, progress, attempt; detail drawer
Retry (MS2: cancel)
Failed jobs show remedy
6
Failure prediction results (A)
1–2
MS1: result table with probability, risk class, OOD flags, provenance strip. MS2 adds: probability visualisations, per-row drawer with SHAP waterfall, mode probabilities, prediction history, limitations, trust panel
Sort, filter, export
OOD rows flagged by icon
7
Machine health and recommendations
2
Machine overview with condition as of date and contributing results with tiers; recommendation list marked Advisory
View, filter; (decisions arrive in MS5)
Staleness badges
8
Model explanation
2
Global importance, local contributions, correlation note, disclaimer, model-card link
Row/global switch
Availability messages
9
Reports
2
Generate analysis PDF; list with status
Download
Retry on failure
10
Model catalogue
2
Production models, configuration, training domain, reference-dataset evaluation (when experiments exist), limitations; banner Metrics come from public-dataset test splits and do not predict accuracy on your machines
Open model card
Empty if none released
11
Organisation, users, plants, audit log
3
Tabs for organisation, users and roles, plants and access, retention, audit log
Invite, roles, deactivate; read-only audit
Role-gated tabs
12
RUL, bearing and sensor-anomaly pages
4
Pipeline-specific charts as in §8.6, each with trust panel
Select units/windows/reference segment
First-use warnings
13
Maintenance management
5
Queue, schedule, in progress, history; approve/reject/defer
Complete tasks with outcomes
Empty tabs; 409 handling
14
Plan, usage and quotas
5
Meters per quota; plan details
Warnings at 80%
Quota-blocked actions explain limits
15
Acoustic pages, assistant, customer validation, advanced analytics
6
As specified
–
–
14.5 Key UI acceptance behaviours
• No page displays a live reading, connection state, heartbeat or device name.
• Every result shows the provenance strip and the trust panel.
• A dataset with a non-runnable status never shows an enabled Run analysis control, and the reasons are visible without extra clicks.
• Compatible data is never described as validated, approved or reliable; wording uses compatible with this pipeline.
• For a dataset without a Type column, the UI never asks for, suggests or fabricates one.
15. Security Requirements
Sequencing rule. Authentication and the minimum tenant boundary (SEC-01 to SEC-05, SEC-08, SEC-12) are delivered in Milestone 1, before any dataset is accepted. Multi-organisation access (a second organisation) is disabled by configuration until the Milestone 3 isolation gate passes. Security is never postponed until after multi-tenancy exists.
ID
Area
Requirement
MS
SEC-01
Passwords and sessions
Argon2id; minimum 12 characters; common-password check; lockout after 5 failures for 15 min; refresh-token rotation with reuse detection; HttpOnly, Secure, SameSite=Strict cookie
1
SEC-02
JWT
15-minute access tokens (asymmetric signing, or a ≥ 256-bit secret locally); claims sub, org_id, role, jti, exp
1
SEC-03
Minimum tenant boundary
organisation_id on every tenant table; TenantContext-only repositories; SET LOCAL app.current_org per transaction; RLS policies; non-superuser app role without BYPASSRLS; context-derived storage keys; cross-tenant access returns 404
1
SEC-04
Single-organisation mode
MULTI_ORG_ENABLED=false by default; POST /auth/register returns MULTI_ORG_DISABLED after the first organisation exists; enabling requires the isolation gate (SEC-06) to be green
1
SEC-05
Secure upload handling
Streaming with hard byte limits; quarantine; extension allow-list and magic-byte/structure checks; generated storage keys; Content-Type from content; per-file, per-day and storage limits (global configuration, later plans); resumable sessions expire after 24 h
1
SEC-06
Tenant isolation verification (CI gate)
Two-organisation fixtures: for every endpoint and ID parameter, tenant B receives 404 for tenant A; an unfiltered query under the app role returns no foreign rows; schema test fails if a tenant table lacks RLS; storage-key tests; worker-context tests. MS1: core subset; MS3: complete suite and mandatory merge gate
1/3
SEC-07
File content safety
CSV caps and delimiter/encoding checks and formula neutralisation on export; Excel .xlsx only without macros/external links/formula evaluation; Parquet flat schemas only; MAT via restricted loaders, no pickle; WAV header validation; ZIP without nesting, path traversal, with expansion limits
1 (CSV), 4–6
SEC-08
Input validation and errors
Pydantic strict models; parameterised SQL only; consistent error envelope; no stack traces to clients
1
SEC-09
Malware scanning strategy
ScanService (CLEAN/INFECTED/ERROR). Local: structural checks plus optional ClamAV container. ClamAV mandatory for any non-local deployment. Quarantined files are unreadable by workers
1 (hook), production (mandatory)
SEC-10
Worker sandboxing
Separate container, non-root, memory/CPU/temp-disk limits, no outbound network; parsers run only in workers
1
SEC-11
Roles and permissions
Four tenant roles (§5.1) enforced by dependencies and re-checked in services; plant-level access; dataset ownership rules
3
SEC-12
Secrets
Environment variables via pydantic-settings locally; .env git-ignored; CI secret scanning; production uses a secrets manager (§11.9)
1
SEC-13
Encryption
In transit: TLS 1.2+ outside localhost, private internal network. At rest: production uses storage-level encryption with managed keys and encrypted backups; local development requires an encrypted disk and documents it
1 (docs), production
SEC-14
Audit logging
Append-only audit_logs for logins and failures, user and role changes, invitations, uploads, deletions and restores, mapping and type changes, warning and limitation acknowledgements, analysis requests, customer-validation criteria, recommendation decisions, report downloads, plan changes, support grants, model promotions; 24-month retention; Org Admin view
3 (security events recorded from MS1 to the application log)
SEC-15
Data retention and deletion
§8.3.7; purge removes objects, previews, artifacts; organisation deletion within 30 days; logs never contain dataset content
1/3
SEC-16
Backup and recovery
Nightly pg_dump and storage mirror locally (14-day retention, scripted restore, quarterly drill); production: PITR and automated backups with deletion-ledger replay
1 (script), production
SEC-17
Support access
No standing operator access to tenant data; break-glass, time-limited, audited
3
SEC-18
Rate limiting
Per IP, user and organisation
1
SEC-19
LLM safety
Read-only tenant-scoped tools; rows never sent to the provider; untrusted-content handling; verifier; per-user budgets
6
SEC-20
Supply chain
Model artifacts only from the trusted registry; lockfiles; pip-audit, npm audit, Trivy
1
SEC-21
Billing data
No card data stored; webhook signature verification when a provider is integrated
5 foundations / later
SEC-22
Tenant-private models
Customer-validation data and tenant-private model versions live in the tenant namespace, are never read by other tenants or by shared training, and are deleted with the organisation
6
16. Testing Strategy
Layer
Tooling
Scope and requirements
From
Unit (backend)
Pytest, pytest-cov
Services, validators, quality-score calculation (hand-computed fixtures), unit conversion, condition derivation, rules engine, state machines
MS1
Compatibility / applicability / reliability
Pytest + Hypothesis
Every status and reason code reachable; precedence; stale checks; mutation tests (drop a column, change a unit, shift scale); compatibility results never alter reliability tier; applicability levels follow thresholds; product_type never required, suggested or inferred outside the with_type profile; ≥ 85% coverage
MS1
Tenant isolation
Pytest + two-tenant fixtures
SEC-06; MS1 core subset, MS3 complete and gating
MS1/MS3
Milestone gate tests
Pytest
MULTI_ORG_ENABLED=false blocks a second organisation; enabling the flag in CI fails if the isolation suite is not green
MS1
Integration
Pytest + Testcontainers (PostgreSQL)
Upload → scan → validate → compatibility → analysis → result on sample packs; migrations up/down
MS1
Job system
Pytest
Concurrent claim with SKIP LOCKED; heartbeat re-queue; retry/backoff; idempotency; cancellation; crash recovery
MS1
Upload security
Pytest + crafted files
EICAR string, zip bomb, nested archive, path-traversal ZIP, macro workbook renamed .xlsx, polyglot files, truncated/oversized files, wrong magic bytes, formula-injection CSV, Parquet with nested types, MAT with object arrays
MS1 (CSV cases), MS4–MS6
Parser fuzzing
Hypothesis / Atheris
No crash, bounded memory
MS1+
API
Pytest + httpx; Schemathesis
All §13 endpoints, RBAC matrix (from MS3), error envelope, 422 gates
MS1+
Trust and wording
Pytest + frontend tests + text scans
Every result view and report contains the trust panel elements; compatible data is never labelled validated/approved/reliable; no real-time/live wording; no horizon wording for Pipeline A; no hardware terms anywhere
MS2
ML unit and pipeline
Pytest on small fixtures
Metrics, split utilities (no group overlap), leakage detector, feature determinism, serialisation round-trip, MLflow completeness
MS1+
AI4I configuration fairness
Pytest
Both configurations use identical split indices and fold indices (hash equality), identical seeds, search budgets and metrics; paired-comparison code verified on synthetic data; registration blocked unless both exist
MS1
Training-serving parity
Pytest
Offline and worker features identical on sampled rows
MS1
Data validation
Pandera / Great Expectations
Reference-dataset schemas, ranges, null rates, class balance
MS1+
Model regression
Nightly gate
Re-evaluate candidates on frozen test sets; fail if headline metrics fall beyond the tolerance derived from bootstrap CIs
MS1
Frontend
Vitest, React Testing Library, Playwright, axe-core
Component states; E2E per milestone (§18)
MS1+
Database
Pytest + SQL assertions
Constraints, partial unique indexes, append-only privileges, RLS, purge job
MS1+
Quota and entitlement
Pytest
Enforcement at all points
MS5
Customer validation
Pytest
Criteria frozen before the run; holdout single-use; leakage rejection; scope and expiry of CUSTOMER_VALIDATED; tenant-private models invisible to other tenants
MS6
Assistant
Pytest + ≥ 50-question set
Grounding, tenant isolation, injection via file/column names, tier is stated
MS6
Security
Bandit, pip-audit, npm audit, Trivy, OWASP ZAP baseline
No unresolved high findings
MS1+
Performance
Locust/k6 and timed jobs
NFR-PERF targets on the reference laptop
per milestone
Backup and restore
Scripted drill
Restore, verify counts/hashes, replay deletion ledger
MS3
CI gates: lint (ruff, mypy, ESLint, tsc) → unit → compatibility → tenant isolation → integration → upload security → API → trust/wording scan → frontend → image build → security scans. Nightly: model regression, E2E, performance smoke.
17. MLOps Strategy
17.1 Reproducible training (offline, public data only)
One CLI per pipeline (python -m ml.<pipeline>.train --config <yaml>); all hyperparameters, seeds and split definitions in YAML. Every run logs parameters, config, git commit and dirty flag, dataset hash, library versions, metrics with CIs, plots, SHAP summaries, the artifact bundle (profile and reference ranges included) and a model card whose Reference-dataset evaluation section is filled from real runs only. Training containers are separate from the API and worker images and run outside the application stack.
17.2 Tracking, registry and release
MLflow with a PostgreSQL backend store (separate schema) and a local artifact volume (MinIO optional). One registered model per pipeline and configuration (§10.6). The registration gate, Staging → Production promotion by a Platform Operator after a recorded comparison, and rollback to an archived version are as in §10.6. Tenants see only Production versions of shared models. Results keep the model version that produced them permanently.
17.3 Worker deployment of models
Workers load the exact model and profile versions named on the job into a local cache keyed by version hash. A missing or corrupt artifact fails the job (E_MODEL_UNAVAILABLE); there is no silent fallback.
17.4 Monitoring (privacy-preserving)
Signal
Method
Source
Action
Applicability flags
Per-analysis flagged-row fractions stored in result summaries; aggregated across tenants without row data (opt-in, Appendix E)
Result summaries
If flagged fractions are persistently high for a profile, review thresholds or model scope; this is monitoring of input shift, not of correctness
Prediction distribution
Risk-class shares, RUL and anomaly-score histograms per model version
Result summaries
Investigate sudden shifts
Job health
Failure rate by error code, duration, queue wait, OOM rate
jobs
Operator alerts
Validation friction
Share of uploads ending INCOMPATIBLE or INSUFFICIENT_DATA by reason
compatibility_checks
Improve templates and wizard; consider new profiles
Outcome feedback
Tenant-local comparison of recommendations with maintenance outcomes, with sample size and CI
maintenance_logs (MS5)
Informational; feeds customer validation (MS6); never retrains shared models
17.5 Retraining, validation and new profiles
Shared models are retrained only on public reference data with recorded licences, when evidence justifies it. Customer-specific validation and optional tenant-private retraining follow §10.7 (MS6) and never touch shared models or other tenants. A new supported dataset type means a new profile with its own reference data, schema, models and evaluation; it never extends an existing pipeline by pooling incompatible data.
17.6 Docker and CI/CD
Images: frontend, api, worker, trainer, optional scan. Multi-stage, non-root, pinned bases. GitHub Actions: ci.yml (lint, tests, build), security.yml (scans), nightly.yml (model regression, E2E), release.yml (tagged image build). Production deployment automation is a later-phase item (§11.9).
18. Development Roadmap
The long-term product is broad; the roadmap delivers it in six milestones that a small team can finish one at a time. The MVP is Milestones 1–3. Milestones 4–6 are post-MVP expansion. The long-term vision is not the MVP.
18.1 Milestone dependency overview
flowchart LR
  M1[MS1 Core AI4I predictive maintenance<br/>auth, minimal tenant boundary, upload, validation, compatibility, Pipeline A]
  M2[MS2 Results and explainability<br/>health, SHAP, history, recommendations, PDF, trust panel]
  M3[MS3 SaaS foundation<br/>orgs, plants, roles, strict isolation, audit]
  G{{Isolation gate: multi-organisation access allowed}}
  M4[MS4 ML pipeline expansion<br/>RUL, bearing diagnosis, sensor anomaly]
  M5[MS5 Maintenance management and SaaS operations<br/>tasks, approvals, usage, quotas, billing foundations]
  M6[MS6 Advanced AI<br/>MIMII, assistant, analytics, customer validation and retraining]
  M1 --> M2 --> M3 --> G
  G --> M4
  G --> M5
  M4 --> M6
  M5 --> M6
MS4 and MS5 depend only on MS3 and may be built in either order or in parallel by separate people; MS6 needs both (outcome capture from MS5 and the full pipeline set from MS4).
18.2 Refinements to the suggested sequence (explained)
The suggested milestone sequence is kept. The following small, dependency-driven refinements were needed; none moves a feature across a milestone boundary that the suggestion defined.
Refinement
Reason
A machine registry and an automatic default plant exist in MS1; plant management UI is MS3
Datasets must attach to a machine, and the schema should not change when plants become manageable
A single role (ORG_ADMIN) in MS1; four roles in MS3
Matches “basic authentication” in MS1 without building the permission matrix early
Background processing (PostgreSQL queue and one worker) is built in MS1; job cancellation arrives in MS2
Validation and inference of uploaded datasets already need asynchronous execution
Global upload and size limits are enforced from MS1; plan-based quotas arrive in MS5
Upload limits are a security control and cannot wait for subscriptions
usage_events rows are written from MS1; usage views and quotas arrive in MS5
Gives MS5 real history without building billing early
Single-organisation mode (MULTI_ORG_ENABLED=false) in MS1–MS2
Satisfies “minimum tenant isolation before multi-organisation access”: the isolation layers exist from MS1, and a second organisation cannot be created until the MS3 gate passes
Excel, Parquet, MAT and WAV parsers arrive with the pipelines that need them (MS4); audio in MS6
Keeps the MS1 attack surface small (CSV only)
Findings (result-derived notifications) are MS5, not MS2
They rely on result history and acknowledgement workflows that belong with maintenance management
Customer-specific validation depends on MS5 outcome capture and MS4/MS5 data types, so it stays in MS6
Technical dependency
18.3 Milestone specifications
Milestone 1 – Core AI4I Predictive Maintenance
Scope
• Basic authentication (registration, login, lockout, refresh rotation) and the minimum tenant boundary (§8.1): organisation_id, TenantContext, RLS, single-organisation mode.
• Machine registry (default plant), dataset upload (CSV), versioning, preview, validation, quality score, mapping, unit conversion, wizard.
• Pipeline profiles and the compatibility, applicability and reliability engine for both AI4I configurations; limitation acknowledgement; PostgreSQL job queue and worker.
• Data preprocessing and feature validation; failure prediction with baseline and selected models for both AI4I configurations, trained and compared under the protocol of §10.1.5.
• Results stored with dataset, mapping, profile, configuration and model provenance, plus applicability level and reliability tier; basic result table, OOD flags.
Dependencies: verified AI4I facts (DATASET_NOTES.md); MLflow; Docker Compose stack.
Major deliverables: running local stack; registered ai4i_failure_clf_notype and ai4i_failure_clf_typed in Staging with model cards (reference-dataset evaluation filled from real runs); validation report format; sample pack; upload-security tests for CSV; two-tenant isolation fixtures.
Acceptance criteria: AC-ORG-1, 2 (core subset), 3; AC-MM-1–3; AC-DS-1–7, 9, 10; AC-CE-1–7; AC-AP-1–5, 7; AC-FP-1–6, 8; AC-JOB-1–5; AC-SEC-1, 3, 4; AC-PLAT-1. Exit test: register an organisation → attempt to register a second (refused, MULTI_ORG_DISABLED) → create a machine → upload an AI4I-schema CSV with renamed columns and Celsius temperatures and no Type column → wizard maps and sets units → only NO_TYPE is offered → acknowledge warnings and the limitation → run → view stored result with provenance and trust fields; then upload a CSV missing torque and verify refusal with remedies; then upload a CSV containing a Type column and verify both configurations are offered separately.
Explicitly excluded: SHAP views, health assessment, recommendations, reports, roles beyond Org Admin, invitations, plant management, audit-log UI, Excel/Parquet/signal/audio uploads, plans and quotas, other pipelines, assistant, customer validation.
Milestone 2 – Results and Explainability
Scope: machine health assessment (§8.2.3); failure-probability visualisations; SHAP explanations (local and global); prediction history; failure-mode probabilities (where the minimum-positives gate is met); basic rules-based recommendations (display only); PDF analysis report; trust panel everywhere; job cancellation; schema templates; model catalogue.
Dependencies: MS1.
Major deliverables: results pages, explanation views, health assessment, recommendation list, PDF report including provenance, trust panel and separated evaluation sections.
Acceptance criteria: AC-MM-4, 5; AC-FP-7; AC-XAI-1–3; AC-AP-6; AC-MR-1; AC-RPT-1; AC-UI-1–4. Exit test: open a completed result, read the trust panel, inspect SHAP drivers and the disclaimer, see the machine's health as of the data date with the reliability tier, read advisory recommendations, and download a PDF that contains the provenance and Customer-specific validation: none performed.
Explicitly excluded: recommendation approval, scheduling, maintenance tasks, findings, roles, multi-organisation access, new pipelines.
Milestone 3 – SaaS Foundation
Scope: organisation settings; plant management; four roles and permissions; invitations and email verification; strict tenant-level data isolation with the complete CI isolation suite; audit logs; dataset ownership and access controls; retention settings; backup and restore drill; support-grant mechanism.
Dependencies: MS2 (results exist to protect). Security work from MS1 is extended, not started.
Major deliverables: role matrix enforced across all endpoints; audit-log view; isolation suite as a mandatory merge gate; restore script and drill report.
Acceptance criteria: AC-ORG-1–8; AC-SEC-2, 5; AC-PLAT-2; AC-GATE-1–3. Exit test: create two organisations with the multi-organisation flag enabled only after the gate passes; invite users with each role; verify role matrix and that organisation B cannot read, infer the existence of, or modify any organisation A resource through any endpoint or storage key; review the audit trail.
Explicitly excluded: new pipelines, maintenance workflow, quotas, billing, assistant.
MVP complete after Milestone 3 (core AI4I analysis, results and explainability, multi-tenant SaaS foundation).
Milestone 4 – Remaining ML Pipeline Expansion
Scope: NASA C-MAPSS RUL (Profile B); Paderborn vibration bearing diagnosis (Profile C); uploaded sensor-data anomaly detection (Capability E / Profile E); Excel, Parquet, .mat and .wav signal upload with hardened parsers; run-to-failure and signal dataset types; per-pipeline trust panel content; recommendation rules for the new pipelines.
Dependencies: MS3 gate; verified C-MAPSS and Paderborn facts.
Major deliverables: registered cmapss_rul and paderborn_fault_clf with model cards; profiles B, C, E; result pages with visualisations; parser fuzz tests.
Acceptance criteria: AC-RUL-1–3; AC-FD-1–2; AC-SA-1–2; AC-DS-11; AC-CE-8; AC-AP-8. Exit test: analyse a C-MAPSS-format file, a vibration recording at the training sampling rate, and a time-series file with a designated reference segment; verify that a wrong sampling rate and a non-turbofan dataset are refused.
Explicitly excluded: audio/MIMII, current-signature analysis, assistant, quotas and billing, customer validation.
Milestone 5 – Maintenance Management and SaaS Operations
Scope: maintenance task management; recommendation approval, rejection (reason code) and deferral; scheduling; maintenance history and outcome capture; findings; plant report and CSV export; usage tracking and quotas; plans, entitlements and subscription state; billing foundations (BillingProvider interface, no-op implementation); bulk machine import.
Dependencies: MS3 (roles, audit); MS4 optional for richer recommendations.
Major deliverables: maintenance workflow UI and API; plan and quota engine with seeded plans; usage view.
Acceptance criteria: AC-MR-2–4; AC-RPT-2; AC-SUB-1–4. Exit test: approve a recommendation with a schedule, complete the task with an outcome, see the finding deduplicate across result versions, hit an 80% and a 100% quota and observe the specified behaviour.
Explicitly excluded: payment-provider integration, invoices, assistant, MIMII, customer validation.
Milestone 6 – Advanced AI Capabilities
Scope: MIMII acoustic anomaly detection (Profile D, audio upload); AI maintenance assistant; advanced analytics and cross-analysis reporting; customer-specific model validation and optional tenant-private retraining (§10.7); ClamAV hardening.
Dependencies: MS4 and MS5 (pipelines, outcome capture, quotas and entitlements).
Major deliverables: registered MIMII models; assistant with evaluation set; customer-validation workflow and reports; tenant-private model namespace.
Acceptance criteria: AC-AC-1; AC-AI-1–4; AC-CV-1–6; AC-RPT-3. Exit test: run an audio analysis with its first-use warnings; ask the assistant why a dataset was incompatible and confirm it repeats the reliability tier; run a customer validation on labelled history with pre-registered criteria, observe CUSTOMER_VALIDATED scoped to its machines and expiring, and verify other organisations cannot see it.
Explicitly excluded: hardware or live data, current-signature analysis (future enhancement), autonomous actions, cross-tenant model sharing.
18.4 Multi-organisation gate
Multi-organisation access is a deployment setting, not a milestone side effect. MULTI_ORG_ENABLED may be set to true only when (a) the complete isolation suite (SEC-06) is green in CI, (b) the role matrix tests pass, and (c) the audit log is recording the events in SEC-14. Milestones 1–2 therefore run as single-organisation deployments (a team's own instance or a demo), and no customer data from a second organisation can enter the system before the gate.
18.5 Cross-milestone rules
Baselines before advanced models; test sets touched once; both AI4I configurations compared fairly before either is promoted; no result without provenance, applicability and reliability tier; no hardware, live-data or device code anywhere; every milestone ends with a demo on the sample packs; model cards and profile documentation are updated in the same milestone as the code; unresolved decisions (Appendix E) are resolved before the milestone that needs them.
19. Acceptance Criteria
Each criterion is testable; IDs are referenced in §18 and Appendix B.
19.1 Tenancy, security and milestone gates
• AC-ORG-1 (MS1): Registering creates one organisation and one admin; with MULTI_ORG_ENABLED=false a second registration returns 403 MULTI_ORG_DISABLED; an existing email yields the generic response.
• AC-ORG-2 (MS1 core, MS3 full): With two-organisation fixtures, every ID-parameterised endpoint returns 404 for the other organisation's resources, and an unfiltered SQL query under the app role returns zero foreign rows.
• AC-ORG-3 (MS1): A schema test fails if any tenant table lacks an RLS policy.
• AC-ORG-4 (MS3): The role matrix in §5.1 is enforced for every endpoint and role (generated test).
• AC-ORG-5 (MS3): The last active Org Admin cannot be removed (409).
• AC-ORG-6 (MS3): Invitations are single-use, expire after 7 days, and create users only in the inviting organisation.
• AC-ORG-7 (MS3): Audit entries exist for each action in SEC-14 (generated test).
• AC-ORG-8 (MS3): Dataset edit/delete rules by ownership and role match §5.1.
• AC-GATE-1 (MS3): CI fails any attempt to enable MULTI_ORG_ENABLED when the isolation suite is not green.
• AC-GATE-2 (MS3): Cross-organisation access through storage keys, job payloads and report URLs is impossible in tests.
• AC-GATE-3 (MS3): A restore drill reproduces counts and hashes and replays the deletion ledger.
• AC-SEC-1 (MS1): Passwords are Argon2id; lockout and refresh-token reuse revocation work as specified.
• AC-SEC-2 (MS3): Break-glass support access is time-limited, scoped and audited.
• AC-SEC-3 (MS1): The upload-security suite passes for CSV; the extended suite passes in the milestone that introduces each format.
• AC-SEC-4 (MS1): No secrets in the repository; logs contain no dataset content.
• AC-SEC-5 (MS3): The Org Admin audit view lists events with filters and cannot edit them.
19.2 Machines and datasets
• AC-MM-1 (MS1): Duplicate asset tags in an organisation return 409; the same tag in another organisation succeeds (fixture).
• AC-MM-2 (MS1): Archived machines reject new datasets with 409 and remain readable.
• AC-MM-3 (MS1): No schema field, route or UI text refers to devices, hardware sensors, protocols or live streams (static scan).
• AC-MM-4 (MS2): Machine condition equals the rule table of §8.2.3 on at least 15 fixtures, always carries condition_as_of and the contributing tiers, and is never worded live or healthy machine.
• AC-MM-5 (MS2): Stale results do not create Critical by themselves.
• AC-DS-1 (MS1): CSV uploads succeed; renamed executables, wrong magic bytes and unsupported types are rejected with UNSUPPORTED_FORMAT or FILE_REJECTED.
• AC-DS-2 (MS1): Oversized files are rejected with 413 before being fully stored; limits come from configuration (MS1–MS4) and plans (MS5).
• AC-DS-3 (MS1): A 50 MB CSV validates within NFR-PERF-02.
• AC-DS-4 (MS1): The quality score equals the documented formula on 10 hand-computed fixtures.
• AC-DS-5 (MS1): Duplicates, missing values, outliers, timestamp issues and unit-plausibility issues are detected on seeded fixtures; nothing is auto-removed or auto-imputed.
• AC-DS-6 (MS1): Re-uploading creates a new immutable version; results reference the exact version; a change summary is shown.
• AC-DS-7 (MS1): Deleting enters a 30-day grace period; after purge the file and previews are gone and results show source dataset deleted.
• AC-DS-9 (MS1): Mapping suggestions are never applied without confirmation; a required feature with no column cannot be satisfied with constants.
• AC-DS-10 (MS1): The wizard takes a dataset with renamed columns and Celsius temperatures to a runnable status, and ends INCOMPATIBLE with remedies when torque is truly absent.
• AC-DS-11 (MS4): Excel, Parquet, MAT and WAV hardening tests pass (macro workbook, nested Parquet, MAT object arrays, malformed WAV).
19.3 Compatibility, applicability, reliability, jobs
• AC-CE-1 (MS1): Fixtures reach each of the five compatibility statuses for every available profile.
• AC-CE-2 (MS1): Status precedence is UNSUPPORTED_FORMAT > INCOMPATIBLE > INSUFFICIENT_DATA > COMPATIBLE_WITH_WARNINGS > COMPATIBLE.
• AC-CE-3 (MS1): POST /analyses on a non-runnable check returns 422 with stored reasons and creates no job row.
• AC-CE-4 (MS1): Missing warning acknowledgements return WARNINGS_NOT_ACKNOWLEDGED; acknowledgements are stored.
• AC-CE-5 (MS1): Changing mapping, units or dataset version makes a check stale; worker re-verification failure ends E_COMPAT_STALE.
• AC-CE-6 (MS1): Each analysis uses exactly one dataset version; a request referencing two is rejected.
• AC-CE-7 (MS1): A forbidden feature (failure-mode columns, identifiers) mapped as an input yields INCOMPATIBLE.
• AC-CE-8 (MS4): Profiles B, C, E meet AC-CE-1 and AC-CE-2.
• AC-AP-1 (MS1): The compatibility check record keeps compatibility, applicability and reliability as separate fields; changing a compatibility warning never changes the reliability tier (property test).
• AC-AP-2 (MS1): Applicability levels follow the thresholds of §8.4.4; MOSTLY_OUTSIDE_REFERENCE_RANGE returns APPLICABILITY_BLOCKED; IN_REFERENCE_RANGE still displays the warning-mechanism disclaimer.
• AC-AP-3 (MS1): Every result in MS1–MS5 has reliability_tier = REFERENCE_ONLY (or NOT_APPLICABLE for Capability E) and training_domain populated.
• AC-AP-4 (MS1 API, MS2 UI): API responses, result views and reports contain the reference-model label, applicability level, reliability tier and limitation text; a UI/report test fails if any is missing.
• AC-AP-5 (MS1): The first analysis per (machine, profile, model version) without limitation_acknowledged returns LIMITATIONS_NOT_ACKNOWLEDGED; the acknowledgement is stored with user and time.
• AC-AP-6 (MS2): Reference-dataset evaluation and customer-specific validation are rendered in separate sections in the UI, model cards and PDFs.
• AC-AP-7 (MS1): A text scan finds no wording that calls compatible data validated, approved, safe or reliable in UI strings, API messages or reports.
• AC-AP-8 (MS4): Each new pipeline's profile declares its training domain, reference ranges and unsupported conditions, and shows first-use or domain-transfer warnings where specified.
• AC-JOB-1 (MS1): Two workers never execute the same job concurrently (stress test, 1,000 jobs).
• AC-JOB-2 (MS1): Killing a worker mid-job re-queues it after the heartbeat timeout; attempts never exceed max_attempts.
• AC-JOB-3 (MS1): The same Idempotency-Key returns the same job; force_rerun creates a new result version and keeps the old one.
• AC-JOB-4 (MS2): Cancelling a running job ends CANCELLED with no partial result visible.
• AC-JOB-5 (MS1): An out-of-memory worker kill yields FAILED E_RESOURCE while the API stays healthy.
19.4 Pipeline A (two configurations) and explainability
• AC-FP-1 (MS1): A baseline run (majority class, Logistic Regression) exists on the identical split before Random Forest/XGBoost registration, for each configuration.
• AC-FP-2 (MS1): Test metrics (PR-AUC, ROC-AUC, precision, recall, F2, MCC, Brier) with bootstrap CIs and prevalence are reported; accuracy is never shown alone.
• AC-FP-3 (MS1): Failure-mode columns and identifiers are absent from both configurations' feature lists; product_type is absent from NO_TYPE (automated test).
• AC-FP-4 (MS1): product_type is not required by any profile except ai4i_failure_with_type; a dataset with the five numeric features and no Type is COMPATIBLE for NO_TYPE; no code path creates, infers or defaults a type (test with a dataset containing a product-ID column that must be ignored).
• AC-FP-5 (MS1): Results show probability labelled reference-calibrated, risk class, provenance and the sentence that no time horizon is implied; a text scan finds no horizon wording for Pipeline A.
• AC-FP-6 (MS1): Both configurations are trained and evaluated on identical split and fold indices (hash equality) with the same seeds, budgets and metrics; a paired-comparison report exists before either is promoted; registration is blocked otherwise; no performance figure appears in this PRD or in code defaults.
• AC-FP-7 (MS2): Mode probabilities are enabled only for modes whose test positives reach the minimum; others show insufficient labelled data for this mode.
• AC-FP-8 (MS1): Rows outside the reference range carry ood_warning and are counted; the result never states that in-range rows are reliable.
• AC-XAI-1 (MS2): SHAP values plus base value reconstruct tree-model output within tolerance on sampled rows.
• AC-XAI-2 (MS2): The non-causality disclaimer appears in every explanation view and report.
• AC-XAI-3 (MS2): Explanation computation follows §8.7 and meets NFR-PERF-04.
19.5 Other pipelines (MS4, MS6)
• AC-RUL-1: Splits are by unit; any unit in two partitions fails a test.
• AC-RUL-2: RMSE, MAE, NASA score and interval coverage are reported per subset on the last-window protocol.
• AC-RUL-3: RUL views show the cap and the simulated turbofan data notice; a non-turbofan dataset cannot run Pipeline B.
• AC-FD-1: Evaluation is leave-bearing-out; no bearing code appears on both sides.
• AC-FD-2: A sampling-rate mismatch returns INCOMPATIBLE naming the required rate; clipped or flat windows are rejected.
• AC-SA-1: Capability E requires a reference segment of at least the profile minimum; results read deviation from your reference; held-out reference false-alarm rate is reported.
• AC-SA-2: Event grouping follows the K/R rules without flapping on fixtures.
• AC-AC-1 (MS6): First use of Pipeline D on a new machine is COMPATIBLE_WITH_WARNINGS at best, with an applicability warning; thresholds come from validation normals.
19.6 Maintenance, reports, subscription, advanced
• AC-MR-1 (MS2): Recommendations show dataset version, result, model version and tier, and the text based on uploaded data and a reference-trained model; before MS5 they are read-only.
• AC-MR-2 (MS5): Illegal transitions return 409; rejection without a reason code returns 422; approval with a schedule creates the maintenance record atomically.
• AC-MR-3 (MS5): Findings deduplicate per (machine, rule) across result versions.
• AC-MR-4 (MS5): Completed maintenance records capture outcome, downtime and cost.
• AC-RPT-1 (MS2): PDFs include every item in §8.10, including Customer-specific validation: none performed by default, and the advisory/non-real-time statement.
• AC-RPT-2 (MS5): CSV exports neutralise formula-leading characters.
• AC-RPT-3 (MS6): Advanced analytics respect tenant scoping and never mix CUSTOMER with SIMULATED or PUBLIC_SAMPLE data without labelling.
• AC-SUB-1 (MS5): Changing a plan's limits changes enforcement without a code change or migration.
• AC-SUB-2 (MS5): At 80% the UI warns; at 100% the action returns QUOTA_EXCEEDED with usage details; existing data stays.
• AC-SUB-3 (MS5): Out-of-plan features return FEATURE_NOT_ENTITLED.
• AC-SUB-4 (MS5): The platform runs with no payment provider; the no-op BillingProvider is used.
• AC-AI-1 (MS6): No assistant response contains a numeric claim absent from tool outputs on the 50-question set.
• AC-AI-2 (MS6): Missing and unauthorised resources get identical answers.
• AC-AI-3 (MS6): Injection text in file names, column names or notes does not change tool use or reveal other organisations' data.
• AC-AI-4 (MS6): The assistant states the reliability tier when discussing a prediction and never calls a reference-only result validated.
• AC-CV-1 (MS6): Validation criteria are frozen before the run and cannot be edited afterwards.
• AC-CV-2 (MS6): The holdout cannot be reused after tuning (second use is rejected).
• AC-CV-3 (MS6): Validations with label-derived input columns or too few positives are rejected.
• AC-CV-4 (MS6): CUSTOMER_VALIDATED applies only within scope and ends on expiry or model-version change.
• AC-CV-5 (MS6): Tenant-private model versions are invisible to other organisations and to shared training.
• AC-CV-6 (MS6): All analyses remain runnable without any customer validation.
19.7 UI, architecture and platform
• AC-UI-1 (MS2): Every result page and report shows the provenance strip and trust panel.
• AC-UI-2 (MS1): A non-runnable dataset never shows an enabled Run analysis control.
• AC-UI-3 (MS1): For a dataset without Type, the UI never asks for, suggests or fabricates one.
• AC-UI-4 (MS2): No page displays live readings, connection state or device names.
• AC-ARCH-1 (MS1): Storage, queue, secrets and email are accessed only through the interfaces in §11.9 (static import-rule test); swapping the local storage adapter for another passes the same adapter contract tests.
• AC-ARCH-2 (MS1): The stack contains no Redis, Celery, Kubernetes manifests or MQTT components.
• AC-PLAT-1 (MS1): docker compose up on a fresh clone starts all required services healthy within SM-9.
• AC-PLAT-2 (MS3): The backup restore drill passes (see AC-GATE-3).
• AC-PLAT-3 (all): A repository scan finds no ESP32, Arduino, MQTT, device-registration, heartbeat-device, live-streaming, or MCSA implementation code (an allow-list covers this PRD's own statements).
20. Risks and Limitations
ID
Risk or limitation
Likelihood
Impact
Mitigation
R1
Models are trained on public, synthetic, simulated or laboratory data and do not transfer to real machines
High
High
Reference-model label everywhere; applicability warnings; reliability tier REFERENCE_ONLY; separate reference-dataset and customer-specific evidence; optional customer validation (MS6); no performance claims about customer equipment
R2
Users read compatible or an in-range OOD check as reliable
High
High
Three separate concepts (§4.4); wording rules and text scans (AC-AP-7); trust panel on every result; OOD documented as a warning mechanism only
R3
Customer files rarely match the narrow reference schemas, so many uploads end INCOMPATIBLE
High
High
Actionable validation feedback, wizard, templates; measure validation friction; add profiles deliberately; position the product honestly
R4
AI4I Type and other AI4I-specific features are mistaken for universal features, or artificially equated with customer columns
Medium
High
Two configurations; product_type only in ai4i_failure_with_type; explicit user assertion recorded; never inferred; tests (AC-FP-4)
R5
tool_wear is also AI4I-specific and may be absent in customer data
High
Medium
Flagged in Appendix E (E-22); remains required in both configurations; absent data is INCOMPATIBLE with a clear message rather than approximated
R6
The two AI4I configurations are compared unfairly, or a gain is read as real-world benefit
Medium
Medium
Identical splits and folds, paired CIs, pre-declared decision rule, interpretation guard (§10.1.5)
R7
AI4I rule recovery inflates scores and invites over-claiming
High
Medium
Document generating rules; baselines and CIs; wording current operating state; no horizon
R8
The roadmap is still too broad for a small team
Medium
High
Six milestones, MVP = MS1–MS3, explicit exclusions, MS4/MS5 parallelisable; scope reviewed at each milestone exit
R9
Cross-tenant data leakage
Low–Medium
Critical
Minimum boundary in MS1, three layers, isolation suite as CI gate in MS3, single-organisation mode until the gate passes
R10
Security work slips behind features
Medium
High
Sequencing rule in §15; MS1 exit includes authentication, RLS and upload hardening for CSV
R11
Malicious or malformed uploads
Medium
High
Layered upload security, sandboxed workers, fuzz tests, ClamAV before production, formats added only with hardening tests
R12
Large files exhaust a 16 GB laptop
Medium
Medium
Streaming/chunked processing, limits, worker memory cap, job caps, performance tests
R13
PostgreSQL queue becomes a bottleneck
Low
Medium
JobQueue interface; documented triggers for a managed queue
R14
Unit confusion and wrong mappings silently change meaning
Medium
High
Mandatory units, plausibility checks, mapping confirmation, versioned mappings, results show units used
R15
Leakage, split mistakes or training-serving skew in ML
Medium
High
Group-aware splits, leak detector, shared feature library, parity tests, baseline-first gate
R16
Over-trust of SHAP as causation
Medium
Medium
Mandatory disclaimer and wording
R17
Recommendation rules misleading without domain review
Medium
High
Advisory labelling, expert review before real use, engineer approval (MS5), outcome capture
R18
LLM fabrication or data exposure
Medium
High
Read-only scoped tools, verifier, no rows to provider, evaluation suite (MS6)
R19
Customer validation is misused (tuning on the holdout, tiny samples)
Medium
High
Frozen criteria, single-use holdout, minimum positives, scoped and expiring tier
R20
Dataset licence or citation obligations missed
Low
Medium
Licence file per dataset, citations in docs and model cards
R21
Quota logic errors block customers or leak free usage
Medium
Medium
Config-driven plans, enforcement tests, counters reconciled nightly
R22
Scope creep back to hardware or live data
Low
Medium
Out-of-scope list, CI scan AC-PLAT-3
R23
Retention and deletion obligations conflict with backups
Medium
Medium
Deletion ledger replayed after restore; bounded backup retention
Standing limitations of v1.2: the platform analyses uploaded historical datasets; it does not monitor machines; its shared models are reference-dataset-trained; AI4I-based results describe the supplied operating state without a time horizon; results are advisory and are not safety assessments.
21. Future Enhancements and Out of Scope
21.1 Out of scope for v1.x
• Any hardware, device or live-telemetry capability (ESP32, Arduino, sensors, MQTT, device registration, streaming). Not retained as a future phase.
• PLC/SCADA/OPC integration, control actions, autonomous shutdown, safety functions.
• Real-time or streaming analysis; the product analyses uploaded datasets in batch.
• Training shared models on tenant data; cross-tenant model sharing; transfer across incompatible feature spaces.
• Multi-dataset fusion (needs a defined and validated fusion profile).
• Payment-provider integration (billing foundations only in MS5).
• Multi-organisation membership per user, SSO/SAML, SCIM, custom roles.
• Native mobile apps, push notifications, CMMS/ERP integration.
• Kubernetes, Redis, service meshes and extra microservices without a documented, measured requirement.
21.2 Future extensions (software only)
1. Additional pipeline profiles for new reference datasets, each with its own schema, models and evaluation.
2. Validated resampling of vibration data as a new profile version.
3. A NO_TOOL_WEAR AI4I-derived configuration if evidence and customer need justify it (Appendix E, E-22).
4. Horizon-based failure prediction trained on genuine time-series failure labels.
5. Survival-analysis RUL; transformer sequence models.
6. Tenant API keys and a public upload/result API.
7. Scheduled re-analysis of new dataset versions; import from cloud storage buckets.
8. SSO, fine-grained permissions, multi-organisation membership.
9. Production cloud deployment, autoscaling, external penetration test.
10. Queue migration if the §8.5 triggers are met.
11. Document retrieval for the assistant (FR-AI-03).
21.3 Future enhancement: Motor Current Signature Analysis (MCSA) – not part of any milestone
Status: clearly marked future, software-only, and not in the MVP or Milestones 1–6. No implementation code, schema or UI for MCSA exists until it is added to a milestone by a later PRD revision. INDUSTRIA AI would analyse uploaded motor-current waveform files; it requires no ESP32, Arduino, sensors, MQTT, hardware installation or machine connectivity, and does not care how the user's file was obtained.
Separation. MCSA would be its own pipeline (Pipeline F), with a separate dataset type CURRENT_SIGNAL, profile mcsa_current, preprocessing and feature extraction, models and evaluation. It is not an extension of the vibration-based Pipeline C and is never fused with it. The Paderborn current channels may serve as a reference dataset for a distinct, separately evaluated model, split by bearing/experiment code.
Suitability is never assumed. A current waveform is analysed only if the compatibility engine confirms the conditions below; otherwise the result is INCOMPATIBLE or INSUFFICIENT_DATA with remedies.
Requirement
Definition (values are set in the design phase and stored in the profile)
File formats
WAV (multi-channel PCM), CSV/Parquet with one column per phase and a declared sample rate, MAT in a declared layout; same upload-security rules as other signal files
Units
Amperes (A), or raw digital counts with a declared scale factor and unit; unknown units are E_UNITS_UNKNOWN
Channels
At least one phase current; three phases enable symmetrical-component and Park's-vector analysis; channel-to-phase mapping is mandatory
Required metadata
Nominal supply frequency (50/60 Hz), number of pole pairs, rated or measured speed (to derive slip), declared load condition, and the sampling frequency
Sampling frequency
Must exceed twice the highest frequency of interest with margin; the minimum is profile-defined per target indicator (for example, supply harmonics versus bearing-related sidebands)
Record length
Long enough that the frequency resolution (1/duration) is well below the smallest sideband spacing of interest, which depends on slip; low-slip machines typically need long records (tens of seconds); minimum is profile-defined
Operating state
Approximately steady speed and load during the record, verified by a stationarity check (fundamental frequency and amplitude stability within a tolerance); drives with variable supply frequency are unsupported (E_VFD_UNSUPPORTED) unless a profile explicitly supports them
Minimum data quality
Detectable fundamental near the declared supply frequency (E_NO_FUNDAMENTAL); clipping fraction below a limit (W_CLIPPING/E_CLIPPING); no gaps or dropouts; small DC offset; adequate effective resolution and signal-to-noise ratio estimated from the spectrum; non-stationary records yield W_NON_STATIONARY or an error depending on severity
Feature extraction (separate pipeline). Windowed spectral estimation (Hann window, Welch or long FFT); fundamental and harmonic amplitudes and total harmonic distortion; sideband amplitudes around the supply frequency, expressed in dB relative to the fundamental, at positions associated with rotor-bar faults (for example (1 ± 2ks)·f_s), eccentricity (f_s ± k·f_r) and bearing damage (f_s ± k·f_bearing); negative-sequence and unbalance indicators for three-phase data; optional Park's-vector (including extended Park's vector) features; envelope-based features. Fault indicators are suggestive, load-dependent and not diagnostic proof; the UI and reports say so.
Models and evaluation. Baselines first (indicator thresholds, Logistic Regression, Random Forest on spectral features), group-wise validation, calibration where probabilities are shown, SHAP on the handcrafted features, a model card with a Reference-dataset evaluation section, and the same applicability and reliability-tier mechanisms as every other pipeline.
Acceptance conditions for a future milestone: profiles reject records below the sampling, duration, stationarity and quality limits with specific codes; unit declaration is mandatory; results show the trust panel; no hardware or device concept is introduced.
22. Glossary
Term
Definition
Acceptance criterion
A testable statement with an ID in §19
AI4I 2020
UCI synthetic predictive-maintenance dataset used for Pipeline A
Applicability (model applicability)
Whether a reference-trained model is plausibly appropriate for a machine, its operating conditions and data distribution; assessed as a warning mechanism (§8.4.4)
CUSTOMER_VALIDATED
Reliability tier granted only by a passed customer-specific validation, scoped and expiring
Compatibility check
Immutable evaluation of a dataset version, mapping and units against one pipeline profile, yielding one of five statuses, an applicability level and a reliability tier
Compatibility (dataset compatibility)
Whether a dataset has the required format, features, units, sampling and schema for a pipeline profile
Configuration (WITH_TYPE, NO_TYPE)
The two AI4I model variants, with and without the AI4I-specific Type feature
Customer-specific validation
Optional MS6 mechanism evaluating a model on an organisation's own labelled history with pre-registered criteria
C-MAPSS
NASA turbofan run-to-failure simulation dataset used for Pipeline B
Dataset / dataset version
Logical container linked to a machine / immutable uploaded or derived file with its hash
Data quality score
0–100 data-health indicator (§8.3.5); not a model-accuracy predictor
Finding
Result-derived notification (MS5); states what analysed data show, not live status
Fusion strategy
A defined and validated method of combining datasets; none exists
Isolation gate
The set of conditions that must hold before MULTI_ORG_ENABLED can be true (§18.4)
Job
Background task tracked in the PostgreSQL queue
MCSA
Motor Current Signature Analysis; a future enhancement (§21.3)
MIMII
Industrial machine sound dataset used for Pipeline D
MS1–MS6
Milestones in §18; MVP = MS1–MS3
OOD
Out-of-distribution: input outside the ranges the model saw in training; used here only as a warning signal
Organisation / tenant
A customer account that owns users, plants, machines, datasets and results in isolation
Paderborn
University of Paderborn bearing dataset used for Pipeline C (vibration)
Pipeline profile
Versioned specification of what a pipeline accepts: categories, dataset types, features, units, sampling, preprocessing, models
Provenance
Recorded chain from a result to dataset version, mapping, profile, configuration and model version
Reference-dataset-trained model
A shared model trained and evaluated on a public dataset; the label attached to every shared model
Reference segment
User-designated normal portion of a dataset used by Capability E
Reliability (model reliability)
Existence of validation evidence supporting trust in predictions for a specific application; expressed by the reliability tier
Reliability tier
REFERENCE_ONLY or CUSTOMER_VALIDATED (NOT_APPLICABLE for Capability E)
RLS
PostgreSQL Row-Level Security
RUL
Remaining Useful Life, in operating cycles for C-MAPSS
SHAP
Method attributing a model's output to input features; describes the model, not physical causes
Single-organisation mode
Deployment mode with MULTI_ORG_ENABLED=false used until the isolation gate passes
Trust panel
UI/report component showing model label, compatibility, applicability, reliability, evidence sections and limits
Training-serving skew
Mismatch between training-time and inference-time features
TWF, HDF, PWF, OSF, RNF
AI4I failure modes: tool wear, heat dissipation, power, overstrain, random
Appendix A. Version History
Version
Summary
1.0
Initial PRD: predictive-maintenance platform with live telemetry, MQTT/IoT hardware extension and four ML pipelines
1.1
Redefined as a pure-software multi-tenant B2B SaaS driven by dataset uploads; added dataset management, compatibility engine, job architecture, tenancy, plans; removed hardware and live streaming
1.2
AI4I Type made optional with two model configurations; compatibility, applicability and reliability separated; reference-dataset-trained labelling and trust panel; six realistic milestones with minimum tenant isolation in MS1; MCSA future enhancement; local versus production architecture; customer-specific validation mechanism defined (MS6)
Appendix B. Requirements Traceability Matrix
Requirement IDs
Spec
API
Tables
Acceptance
MS
FR-ORG-01–03
§8.1
/auth/*
organisations, users, refresh_tokens
AC-ORG-1, AC-SEC-1
1
FR-ORG-02, 09
§8.1, §11.3
all
all tenant tables, RLS
AC-ORG-2, 3, AC-GATE-1–2
1/3
FR-ORG-04–08, 10
§5, §8.1
/organisation*, /plants
invitations, plants, user_plant_access, audit_logs
AC-ORG-4–8
3
FR-MM-01–03, 05
§8.2
/machines*
machines, machine_categories
AC-MM-1–3
1
FR-MM-04
§8.2.3
/machines/{id}
machines.condition*
AC-MM-4, 5
2
FR-DS-01–07
§8.3.1–§8.3.4, 8.3.7
/datasets*, /dataset-versions*
datasets, dataset_versions
AC-DS-1–3, 6, 7
1 (CSV), 4, 6
FR-DS-08–09, 18
§8.3.6
mapping endpoints
column_mappings
AC-DS-9, 10, AC-FP-4
1
FR-DS-10–16
§8.3.5
/validation-reports*
validation_reports, dataset_events
AC-DS-3–5
1
FR-DS-19
§8.3.6
template endpoint
pipeline_profiles
–
2
FR-CE-01–06
§8.4.1–§8.4.3
/compatibility-checks*, /analyses
pipeline_profiles, compatibility_checks
AC-CE-1–7
1
FR-AP-01–05
§4.4, §8.4.4–§8.4.7
check and result payloads
compatibility_checks, limitation_acknowledgements, analysis_results
AC-AP-1–5, 7, AC-FP-8
1
FR-AP-06–07
§14.2, §8.10
–
model_evaluations.evaluation_kind
AC-AP-4, 6, AC-UI-1
2
FR-JOB-01–04, 06–07
§8.5
/jobs*, /analyses
jobs, analysis_results
AC-JOB-1–3, 5
1
FR-JOB-05
§8.5
/jobs/{id}/cancel
jobs
AC-JOB-4
2
FR-JOB-08
§8.11
–
usage_events, usage_counters
AC-SUB-2
5
FR-FP-01–04
§8.6, §10.1
/analyses*
analysis_results, model_versions
AC-FP-1–6, 8
1
FR-FP-05–06
§10.1.4, §14.2
/analyses/{id}
analysis_results
AC-FP-7
2
FR-XAI-01–02
§8.7
/analyses/{id}/explanations
analysis_results.top_rows
AC-XAI-1–3
2
FR-MR-01
§8.8
/recommendations
recommendations, recommendation_rules
AC-MR-1
2
FR-RPT-01
§8.10
/reports/analysis
reports
AC-RPT-1
2
FR-RUL-01–04, FR-FD-01–03, FR-SA-01–03
§10.2, 10.3, 10.5
/analyses*
analysis_results
AC-RUL-, AC-FD-, AC-SA-*, AC-CE-8, AC-AP-8
4
FR-MR-02–05, FR-RPT-02, FR-MM-06
§8.8
/recommendations/{id}/decision, /maintenance*, /findings*
maintenance_logs, findings
AC-MR-2–4, AC-RPT-2
5
FR-SUB-01–04
§8.11
/organisation/usage
plans, subscriptions, usage_*
AC-SUB-1–4
5
FR-AC-01–03
§10.4
/analyses*
analysis_results
AC-AC-1
6
FR-AI-01–02
§8.9
/assistant/*
assistant_*
AC-AI-1–4
6
FR-CV-01–05
§10.7
/customer-validations*
customer_validations, model_versions
AC-CV-1–6
6
FR-RPT-03
§8.10
reports
reports
AC-RPT-3
6
NFR-PERF, SCAL, REL
§7
all
jobs, results
AC-DS-3, AC-JOB-5
1+
NFR-SEC-01–02, NFR-MAINT-03
§7, §11.9
–
–
AC-GATE-1, AC-ARCH-1
1/3
SEC-01–22
§15
all
users, audit_logs
AC-SEC-1–5, AC-ORG-2
1–6
Removal of hardware concepts
§2, §21.1
–
–
AC-MM-3, AC-PLAT-3
all
MCSA (future)
§21.3
–
–
AC-PLAT-3 (absence)
none
Appendix C. Change Summary (v1.1 → v1.2)
Section
Change
Why
Front matter, §1
Pipeline table with milestones; two AI4I configurations; three-concept statement; reference-trained honesty
Corrections 1, 2, 3
§2
Twelve non-negotiable principles listed verbatim in substance; design principles revised
Preserve vision; consistency
§3
Constraints expanded (narrow schemas, applicability, small team)
Corrections 2, 3
§4
New §4.4 (compatibility, applicability, reliability); metrics SM-3, SM-4, SM-6; scope states MVP = MS1–MS3; workflow adds applicability and acknowledgement steps
Corrections 1–3
§5
Role introduction by milestone (single role in MS1)
Correction 3
§6
Milestone column; new FR-AP and FR-CV groups; FR-FP-02 two configurations; FR-ORG-02/03 minimum tenant boundary; FR-DS-08 no invented features
Corrections 1–3
§7
Local vs production columns; NFR-SEC-02, NFR-MAINT-03
Correction 5
§8.1
Minimum boundary (MS1) versus full SaaS foundation (MS3); single-organisation mode
Correction 3
§8.2
Default plant; condition wording; reliability tiers in health assessment
Corrections 2, 3
§8.3
Formats by milestone; mapping principles; product_type rule; limits as configuration before plans
Corrections 1, 3
§8.4
Rebuilt as three-stage engine; profiles for both AI4I configurations; applicability levels and blocking; reliability tiers; job-creation gate
Corrections 1, 2
§8.5–8.11
Milestone tags; recommendations display-only in MS2; reports with separated evidence; plans in MS5
Corrections 2, 3
§9
Reference versus tenant datasets; AI4I Type described as dataset-specific; Paderborn current channels reserved for MCSA
Corrections 1, 2, 4
§10
New §10.1.2–10.1.5 (configurations and comparison protocol); model-card sections; §10.7 customer validation and retraining
Corrections 1, 2
§11
Local architecture diagram, interface table for production evolution, production target diagram
Correction 5
§12
Applicability and reliability fields; limitation_acknowledgements; customer_validations; configuration and training-domain fields; milestone tags
Corrections 1, 2, 3
§13
Responses with trust blocks; new error codes; limitation_acknowledged; mapping rule for product_type; customer-validation endpoints
Corrections 1, 2
§14
Trust panel; pages by milestone; wording rules
Correction 2
§15–17
Security sequencing rule; isolation gate; tests for fairness, wording and gates; privacy-preserving monitoring
Corrections 2, 3
§18
Rebuilt as six milestones with scope, dependencies, deliverables, acceptance criteria, exclusions, refinements and gate
Correction 3
§19
Criteria regrouped and extended (AC-AP, AC-CV, AC-GATE, AC-ARCH, AC-FP-4/6)
All corrections
§20–22
Risks R1–R23; MCSA future enhancement §21.3; glossary additions
Corrections 1–5
Appendices
Version history, traceability, change summary, consistency audit, unresolved decisions (replaces v1.1 Appendices A–D)
Deliverables
Appendix D. Final Consistency Audit
Performed by reviewing this document against each statement below. Automated enforcement of the checkable items is specified in the cited acceptance criteria and CI scans; no scan has been run, because no code exists yet.
#
Check
Result
Where
1
AI4I Type is no longer a universal mandatory feature
Pass: required only in ai4i_failure_with_type; absent from all other profiles
§8.3.6, §8.4.1, §8.4.5, §9.2, AC-FP-4
2
Two AI4I configurations documented, with schema, mapping, compatibility, preprocessing, inference and model-card consequences
Pass
§8.4.5, §10.1.2, §12, §13.4–13.5, §17
3
Both configurations evaluated by one methodology; no performance stated before experiments
Pass: protocol only, no figures
§10.1.5, AC-FP-6
4
Platform never invents or infers a product type
Pass
§8.3.6, §8.4.5, AC-FP-4, AC-UI-3
5
Compatibility, applicability and reliability are separate
Pass: separate fields, outputs, UI sections and API objects
§4.4, §8.4, §12, §13, §14.2
6
Public-dataset performance is not presented as customer-plant validation
Pass: separate evidence sections; model-card and report structure
§10.0, §8.10, §14.2, AC-AP-6
7
OOD warnings are not described as proof of reliability
Pass: standing disclaimer and wording rule
§4.4, §8.4.4, AC-AP-2, AC-AP-7
8
Future customer-specific validation and retraining defined and optional
Pass
§10.7, FR-CV-05, AC-CV-6
9
MVP split into realistic milestones; long-term vision not labelled MVP
Pass: MVP = MS1–MS3
§4.3, §18
10
Minimum tenant isolation precedes multi-organisation access
Pass: MS1 boundary, single-organisation mode, MS3 gate
§8.1, §15, §18.4, AC-ORG-1, AC-GATE-1
11
MCSA is a clearly marked future, software-only enhancement
Pass
§21.3
12
Local development and production SaaS are distinguished without new heavy infrastructure
Pass
§11.9
13
No hardware-dependent requirement introduced
Pass: only statements of removal remain
§2, §21.1, AC-PLAT-3
14
No unsupported ML performance claims or fabricated results
Pass: example JSON values are labelled illustrative; defaults such as thresholds are marked placeholders
§13.5, Appendix E
15
All requirements have testable acceptance criteria
Pass at group level (Appendix B maps every FR group to criteria); FR-AI-03 and MCSA are future and have no criteria yet
Appendix B
16
Diagrams and API contracts match the requirements
Pass by review: architecture, flow, ERD, state and milestone diagrams use the same component names, statuses and milestone tags
§8.4, §8.5, §11, §12, §13, §18
Known residual items (not defects, but to watch): acceptance-criterion numbering has deliberate gaps (for example AC-DS-8 was retired when the retention criteria were merged into AC-DS-7); example payload numbers are illustrative; priority tags from earlier versions were replaced by milestone tags everywhere in §6 and §13.
Appendix E. Assumptions and Unresolved Technical Decisions
E.1 Assumptions
1. Dataset facts in §9 reflect the providers' public documentation and are unverified until the milestone that first uses each dataset checks the real files.
2. The product owner will set plan limits, risk thresholds, cost ratios and rule content before the milestone that needs them.
3. A single developer or small team builds the product on 16 GB machines; training workloads run outside the application stack.
4. Customers accept that analyses are advisory and based on reference-trained models until customer-specific validation exists.
E.2 Unresolved decisions
#
Decision
Options
Recommendation
Needed by
E-1
Default configuration when both AI4I configurations are runnable
NO_TYPE; WITH_TYPE; user choice only
Interim NO_TYPE (feasibility, not performance); final rule per §10.1.5 after experiments
MS1
E-2
Applicability thresholds (1% warning, 30% block, 10% margin) and whether to include the joint-domain check
Fixed defaults; per-profile; per-organisation
Per-profile defaults tuned on reference data; revisit with usage data
MS1
E-3
Standing limitation text and acknowledgement frequency
Once per (machine, profile, model version); every run
Once per combination, with the statement version stored; re-ask when text changes
MS1
E-4
Plan limits and global upload limits
§8.3.2 placeholders; derived from storage cost
Keep placeholders; product owner decides
MS1 (global), MS5 (plans)
E-5
Risk thresholds and failure-vs-false-inspection cost ratio
Default 10:1; configurable
Platform default with expert review
MS1
E-6
Recommendation rule authorship and review
Product team with an external reliability expert; customer-editable
Platform-owned, expert-reviewed
MS2
E-7
Cross-tenant aggregate monitoring consent
Opt-out; opt-in
Opt-in, counts only, no row data
MS3
E-8
Users in several organisations
One per user; membership model
One per user until SSO
MS3
E-9
Local storage adapter
Local volume; MinIO
Local volume behind StorageService; MinIO profile for parity tests
MS1
E-10
C-MAPSS subsets shipped
FD001 only; all four
FD001 first, others as separate profile versions
MS4
E-11
Vibration resampling
Reject mismatched rates; validated resampling
Reject in v1.2
MS4
E-12
Excel and Parquet hardening readiness
MS4; defer
MS4 if parser hardening tests pass
MS4
E-13
MIMII model granularity
Per machine type; per model ID
Per machine type with model ID as a warning
MS6
E-14
Billing provider, tax and invoicing
Provider-neutral interface only; choose later
Decide after MS5; no card data stored
after MS5
E-15
LLM provider and data-processing terms
Hosted; local model
Configurable, local option retained
MS6
E-16
Condition thresholds (RUL cycles, anomaly and fault cut-offs)
Fixed; per-category
Per-category from evaluation results and expert review
MS2/MS4
E-17
Customer-validation defaults (minimum positives, CI rule, calibration tolerance, expiry period) and allowed retraining approaches
Strict platform minimums with admin tightening; configurable freely
Strict minimums; admin can only tighten; fine-tune and refit both evaluated in a pilot
MS6
E-18
Production hosting vendor and infrastructure choices
Deferred
Record when production planning starts; follow §11.9 interfaces
post-MVP
E-19
Production authentication hardening and SSO timing
Built-in only; add OIDC/SAML
Built-in for v1.x; SSO later
post-MVP
E-20
Data residency/region
Single region; selectable
Defer until a customer requires it
post-MVP
E-21
MCSA: whether and when to build; sampling and duration minimums; reference data
Do not build; build as Pipeline F
Decide after MS6 using validation-friction data and customer demand
after MS6
E-22
tool_wear is also AI4I-specific and required in both configurations
Keep required; add a NO_TOOL_WEAR configuration later; make optional
Keep required in v1.2 and report absent data as INCOMPATIBLE; evaluate a NO_TOOL_WEAR configuration after MS2 if customer files commonly lack it. Not part of the requested correction, so no design change was made
after MS2
E.3 Early feasibility checks (Milestone 1)
Peak memory when validating a 5-million-row CSV in chunks; SHAP throughput on 100,000 rows with the chosen XGBoost configuration; whether two workers plus PostgreSQL stay inside the 8 GB Docker allocation; whether the isolation fixtures and RLS add acceptable latency to common queries.