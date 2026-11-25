"""
Comprehensive Job Concurrency and Robustness Test Suite
(PRD v1.2 §8.5, §13.5, §13.6, AC-JOB-1..5)

Demonstrates:
1. Two workers claiming simultaneously (SKIP LOCKED / CAS prevents double claim).
2. API and worker race conditions (atomic claim_job_by_id vs claim_next_job).
3. Worker crash / termination during analysis (heartbeat timeout and lease recovery).
4. Heartbeat periodic updates and timeout.
5. Bounded retries and exponential backoff exhaustion.
6. Duplicate requests with same/different idempotency keys.
7. Database transaction rollback on simulated crash (no orphan AnalysisResult).
8. Successful analysis result creation and verification.
"""

import io
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.models.job import Job
from backend.app.models.analysis import AnalysisResult
from backend.app.services.queue_service import (
    enqueue_job,
    claim_next_job,
    claim_job_by_id,
    execute_job_synchronous,
    requeue_stale_jobs,
    JobHeartbeatMonitor,
)

VALID_AI4I_CSV = (
    "Air temp,Process temp,RPM,Torque,Tool wear\n"
    "298.1,308.6,1551,42.8,0\n"
    "298.2,308.7,1408,46.3,3\n"
    "298.1,308.5,1498,49.4,5\n"
    "298.2,308.6,1433,39.5,7\n"
    "298.2,308.7,1408,40.0,9\n"
)


# ==============================================================================
# 1. Two workers claiming simultaneously (SKIP LOCKED / CAS prevents double claim)
# ==============================================================================
def test_1_concurrent_workers_claim_simultaneously(db_session, tenant_fixture):
    """
    Verification Requirement 1:
    Two workers querying the queue simultaneously must never claim the same job.
    CAS / SKIP LOCKED ensures exactly one worker gets the job lease.
    """
    job, is_new = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="VALIDATE_DATASET",
        payload={"dataset_version_id": "simultaneous-claim-test"}
    )
    assert is_new is True

    bind = db_session.get_bind()
    SessionFactory = sessionmaker(bind=bind, autocommit=False, autoflush=False)

    results = []
    barrier = threading.Barrier(2)

    def worker_claim_task(worker_id: str):
        session = SessionFactory()
        try:
            barrier.wait()  # Synchronize threads so they hit the queue at the exact same instant
            claimed = claim_next_job(session, worker_id=worker_id)
            results.append((worker_id, claimed.id if claimed else None))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_claim_task, "worker-alpha")
        f2 = executor.submit(worker_claim_task, "worker-beta")
        f1.result()
        f2.result()

    winners = [r for r in results if r[1] is not None]
    losers = [r for r in results if r[1] is None]

    assert len(winners) == 1, f"Expected exactly 1 winning worker, got: {results}"
    assert len(losers) == 1, f"Expected exactly 1 losing worker, got: {results}"
    assert winners[0][1] == job.id

    db_session.expire_all()
    refreshed_job = db_session.query(Job).filter(Job.id == job.id).first()
    assert refreshed_job.status == "RUNNING"
    assert refreshed_job.claimed_by == winners[0][0]
    assert refreshed_job.attempt == 1


# ==============================================================================
# 2. API and worker race conditions (atomic claim_job_by_id vs claim_next_job)
# ==============================================================================
def test_2_api_and_worker_race_conditions(db_session, tenant_fixture):
    """
    Verification Requirement 2:
    API (inline claim_job_by_id) and Background Worker (claim_next_job) racing
    for the exact same job must never both execute it.
    """
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload={"task": "race_api_vs_worker"}
    )

    bind = db_session.get_bind()
    SessionFactory = sessionmaker(bind=bind, autocommit=False, autoflush=False)

    results = {}
    barrier = threading.Barrier(2)

    def api_inline_task():
        session = SessionFactory()
        try:
            barrier.wait()
            claimed = claim_job_by_id(session, job_id=job.id, worker_id="api-inline-worker")
            results["api"] = claimed.id if claimed else None
        finally:
            session.close()

    def bg_worker_task():
        session = SessionFactory()
        try:
            barrier.wait()
            claimed = claim_next_job(session, worker_id="bg-worker-1")
            results["worker"] = claimed.id if claimed else None
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(api_inline_task)
        f2 = executor.submit(bg_worker_task)
        f1.result()
        f2.result()

    claimed_by_api = results["api"] is not None
    claimed_by_worker = results["worker"] is not None

    # XOR condition: exactly one must have succeeded
    assert claimed_by_api ^ claimed_by_worker, f"Expected XOR claim, got results: {results}"

    db_session.expire_all()
    refreshed = db_session.query(Job).filter(Job.id == job.id).first()
    assert refreshed.status == "RUNNING"
    expected_claimer = "api-inline-worker" if claimed_by_api else "bg-worker-1"
    assert refreshed.claimed_by == expected_claimer


# ==============================================================================
# 3. Worker crash / termination during analysis (heartbeat timeout and lease recovery)
# ==============================================================================
def test_3_worker_crash_and_lease_recovery(db_session, tenant_fixture):
    """
    Verification Requirement 3:
    When a worker crashes midway through execution and stops sending heartbeats,
    stale job recovery safely revokes its lease and requeues the job.
    """
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="VALIDATE_DATASET",
        payload={"dataset_version_id": "crash-recovery-test"}
    )

    # Worker crashes: claim job, set attempt=1, and simulate dead worker whose heartbeat expired
    job.status = "RUNNING"
    job.claimed_by = "worker-crashed-pid-9999"
    job.attempt = 1
    job.max_attempts = 3
    job.heartbeat_at = datetime.utcnow() - timedelta(seconds=120)  # Expired > 60s
    db_session.commit()

    # Stale recovery sweeper runs
    recovered_count = requeue_stale_jobs(db_session, stale_timeout_seconds=60)
    assert recovered_count == 1

    db_session.expire_all()
    requeued_job = db_session.query(Job).filter(Job.id == job.id).first()
    assert requeued_job.status == "QUEUED"
    assert requeued_job.claimed_by is None
    assert requeued_job.current_step == "REQUEUED_STALE_HEARTBEAT"

    # Next healthy worker claims the recovered job
    healthy_worker = claim_next_job(db_session, worker_id="worker-healthy-pid-1001")
    assert healthy_worker is not None
    assert healthy_worker.id == job.id
    assert healthy_worker.claimed_by == "worker-healthy-pid-1001"
    assert healthy_worker.attempt == 2


# ==============================================================================
# 4. Heartbeat periodic updates and timeout
# ==============================================================================
def test_4_heartbeat_periodic_updates_and_timeout(db_session, tenant_fixture):
    """
    Verification Requirement 4:
    JobHeartbeatMonitor updates heartbeat_at in the background on interval ticks,
    preventing long-running jobs from becoming stale.
    """
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload={"task": "heartbeat_monitor_test"}
    )
    job.status = "RUNNING"
    job.claimed_by = "worker-hb-test"
    job.attempt = 1
    initial_heartbeat = datetime.utcnow() - timedelta(seconds=10)
    job.heartbeat_at = initial_heartbeat
    db_session.commit()

    bind = db_session.get_bind()
    session_factory = sessionmaker(bind=bind, autocommit=False, autoflush=False)

    monitor = JobHeartbeatMonitor(
        job_id=job.id,
        worker_id="worker-hb-test",
        attempt=1,
        interval=0.1,  # 100ms ticks for fast test
        session_factory=session_factory
    )
    monitor.start()

    try:
        # Allow monitor thread to perform 2-3 heartbeat ticks
        time.sleep(0.35)
    finally:
        monitor.stop()

    db_session.expire_all()
    refreshed_job = db_session.query(Job).filter(Job.id == job.id).first()
    assert refreshed_job.heartbeat_at > initial_heartbeat, (
        f"Heartbeat should have been updated. Initial: {initial_heartbeat}, Current: {refreshed_job.heartbeat_at}"
    )


# ==============================================================================
# 5. Bounded retries and exponential backoff exhaustion
# ==============================================================================
def test_5_bounded_retries_and_exponential_backoff_exhaustion(db_session, tenant_fixture):
    """
    Verification Requirement 5:
    Transient execution errors retry with backoff (10s, 60s, 300s) up to max_attempts,
    then strictly terminate with status FAILED.
    """
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="VALIDATE_DATASET",
        payload={"dataset_version_id": "nonexistent-dv-id"}
    )
    job.max_attempts = 3
    db_session.commit()

    # --- Attempt 1 ---
    claimed1 = claim_next_job(db_session, worker_id="worker-retry-1")
    assert claimed1 is not None
    assert claimed1.attempt == 1

    # Execute and fail
    execute_job_synchronous(db_session, claimed1)
    assert claimed1.status == "RETRY_WAIT"
    assert claimed1.error_code == "TRANSIENT_ERROR"
    # Backoff for attempt 1 is 10s: run_after must be > now
    assert claimed1.run_after > datetime.utcnow() + timedelta(seconds=5)

    # --- Attempt 2 ---
    # Fast forward run_after to make it immediately eligible
    claimed1.run_after = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    claimed2 = claim_next_job(db_session, worker_id="worker-retry-2")
    assert claimed2 is not None
    assert claimed2.attempt == 2

    # Execute and fail
    execute_job_synchronous(db_session, claimed2)
    assert claimed2.status == "RETRY_WAIT"
    # Backoff for attempt 2 is 60s: run_after must be > now + 30s
    assert claimed2.run_after > datetime.utcnow() + timedelta(seconds=30)

    # --- Attempt 3 (Final attempt) ---
    claimed2.run_after = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    claimed3 = claim_next_job(db_session, worker_id="worker-retry-3")
    assert claimed3 is not None
    assert claimed3.attempt == 3

    # Execute and fail: exhausts max_attempts (3)
    execute_job_synchronous(db_session, claimed3)
    assert claimed3.status == "FAILED"
    assert claimed3.error_code == "EXECUTION_ERROR"
    assert "Job failed after 3 attempts" in claimed3.user_message
    assert claimed3.finished_at is not None

    # Verify no more claims can occur on this job
    no_more_claim = claim_next_job(db_session, worker_id="worker-retry-4")
    assert no_more_claim is None


# ==============================================================================
# 6. Duplicate requests with same/different idempotency keys
# ==============================================================================
def test_6_duplicate_requests_with_idempotency_keys(db_session, tenant_fixture):
    """
    Verification Requirement 6:
    Enqueuing with identical idempotency key returns the existing job without creating duplicates,
    even under concurrent race condition attempts.
    Different idempotency keys produce separate distinct jobs.
    """
    payload = {"analysis_target": "motor_bearing_3"}
    key_shared = "unique-key-abc-123"

    bind = db_session.get_bind()
    SessionFactory = sessionmaker(bind=bind, autocommit=False, autoflush=False)

    results = []
    barrier = threading.Barrier(2)

    def race_enqueue_task(thread_id: int):
        session = SessionFactory()
        try:
            barrier.wait()
            job_obj, is_new = enqueue_job(
                db=session,
                org_id=tenant_fixture["org"].id,
                job_type="RUN_ANALYSIS",
                payload=payload,
                idempotency_key=key_shared
            )
            results.append((thread_id, job_obj.id, is_new))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(race_enqueue_task, 1)
        f2 = executor.submit(race_enqueue_task, 2)
        f1.result()
        f2.result()

    # Both threads must have received the EXACT same job ID
    assert results[0][1] == results[1][1]
    # Exactly one thread got is_new=True, the other got is_new=False
    is_new_flags = [r[2] for r in results]
    assert True in is_new_flags and False in is_new_flags

    # Different idempotency key produces a separate job
    job_diff, is_new_diff = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload=payload,
        idempotency_key="unique-key-xyz-789"
    )
    assert is_new_diff is True
    assert job_diff.id != results[0][1]


# ==============================================================================
# 7. Database transaction rollback on simulated crash (no orphan AnalysisResult)
# ==============================================================================
def test_7_transaction_rollback_on_crash_no_orphan_analysis_result(db_session, tenant_fixture):
    """
    Verification Requirement 7:
    If a failure occurs during execution before atomic completion commit,
    the transaction is rolled back cleanly. No orphan AnalysisResult remains in the database.
    """
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload={"compatibility_check_id": "dummy-check-id"}
    )
    job.status = "RUNNING"
    job.claimed_by = "worker-rollback-test"
    job.attempt = 1
    db_session.commit()

    # Simulate execute_analysis raising a crash midway through inference
    with patch("backend.app.services.queue_service.execute_analysis") as mock_exec:
        mock_exec.side_effect = RuntimeError("Simulated crash during tree SHAP computation")
        execute_job_synchronous(db_session, job, worker_id="worker-rollback-test")

    db_session.expire_all()
    # Verify no orphan AnalysisResult was committed
    orphans = db_session.query(AnalysisResult).filter(AnalysisResult.job_id == job.id).all()
    assert len(orphans) == 0, f"Found {len(orphans)} orphan AnalysisResults; should be 0"

    # Job status updated to retry wait or failed without state corruption
    refreshed_job = db_session.query(Job).filter(Job.id == job.id).first()
    assert refreshed_job.status in ("RETRY_WAIT", "FAILED")
    assert refreshed_job.error_code in ("TRANSIENT_ERROR", "EXECUTION_ERROR")


# ==============================================================================
# 8. Successful analysis result creation and verification
# ==============================================================================
def test_8_successful_analysis_lifecycle_and_verification(client, tenant_fixture, db_session):
    """
    Verification Requirement 8:
    End-to-end integration test:
    Dataset upload -> mapping -> compatibility check -> analysis execution ->
    verification of Job (SUCCEEDED, progress 100, heartbeat) and AnalysisResult (provenance, trust).
    """
    # 1. Create Machine
    m_resp = client.post("/api/v1/machines", json={
        "asset_tag": "ROBUST-MACH-01",
        "name": "Robustness Verification Machine",
        "category_code": "GENERAL_MACHINE_TOOL"
    }, headers=tenant_fixture["headers"])
    assert m_resp.status_code == 201
    machine_id = m_resp.json()["id"]

    # 2. Create Dataset & Upload CSV
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Robustness Dataset"
    }, headers=tenant_fixture["headers"])
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    files = {"file": ("data.csv", io.BytesIO(VALID_AI4I_CSV.encode("utf-8")), "text/csv")}
    up_resp = client.post(
        f"/api/v1/datasets/{dataset_id}/versions/upload",
        files=files,
        headers=tenant_fixture["headers"]
    )
    assert up_resp.status_code == 201
    vid = up_resp.json()["dataset_version_id"]

    # 3. Put Feature Mapping
    mapping = {
        "mappings": {
            "air_temperature": {"column": "Air temp", "unit": "K"},
            "process_temperature": {"column": "Process temp", "unit": "K"},
            "rotational_speed": {"column": "RPM", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Tool wear", "unit": "min"}
        }
    }
    client.put(
        f"/api/v1/dataset-versions/{vid}/mappings/ai4i_failure_no_type",
        json=mapping,
        headers=tenant_fixture["headers"]
    )

    # 4. Run Compatibility Check
    chk_resp = client.post(
        f"/api/v1/dataset-versions/{vid}/compatibility-checks",
        json={"profile_id": "ai4i_failure_no_type"},
        headers=tenant_fixture["headers"]
    )
    assert chk_resp.status_code == 201
    check_id = chk_resp.json()[0]["id"]

    # 5. POST /analyses (Enqueues job, returns HTTP 202)
    run_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": check_id,
        "limitation_acknowledged": True
    }, headers=tenant_fixture["headers"])
    assert run_resp.status_code == 202
    run_data = run_resp.json()
    job_id = run_data["job_id"]
    analysis_result_id = run_data["analysis_result_id"]

    # 6. Verify Job State via GET /api/v1/jobs/{job_id}
    job_resp = client.get(f"/api/v1/jobs/{job_id}", headers=tenant_fixture["headers"])
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["id"] == job_id
    assert job_data["status"] == "SUCCEEDED"
    assert job_data["progress_percent"] == 100
    assert job_data["current_step"] == "COMPLETED"
    assert job_data["claimed_by"] is not None
    assert job_data["heartbeat_at"] is not None
    assert job_data["analysis_result_id"] == analysis_result_id

    # 7. Verify AnalysisResult via GET /api/v1/analyses/{analysis_result_id}
    res_resp = client.get(f"/api/v1/analyses/{analysis_result_id}", headers=tenant_fixture["headers"])
    assert res_resp.status_code == 200
    res_data = res_resp.json()

    assert res_data["id"] == analysis_result_id
    assert res_data["is_latest"] is True
    assert res_data["trust"]["compatibility"] == "COMPATIBLE"
    assert res_data["trust"]["reliability_tier"] == "REFERENCE_ONLY"
    assert res_data["provenance"]["model"]["registry_name"] == "ai4i_failure_clf_notype"
    assert res_data["summary"]["total_rows"] == 5
    assert "predicted_failures" in res_data["summary"]
    assert "mean_failure_probability" in res_data["summary"]

    # 8. Verify Analysis Rows via GET /api/v1/analyses/{analysis_result_id}/rows
    rows_resp = client.get(f"/api/v1/analyses/{analysis_result_id}/rows", headers=tenant_fixture["headers"])
    assert rows_resp.status_code == 200
    rows_data = rows_resp.json()
    assert len(rows_data["top_rows"]) == 5
    assert "failure_probability" in rows_data["top_rows"][0]
