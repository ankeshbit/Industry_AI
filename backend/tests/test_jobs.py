"""
Job Processing and Queue Tests (PRD v1.2 §8.5, §13.5, AC-JOB-1..5)
"""

import pytest
from datetime import datetime, timedelta
from backend.app.models.job import Job
from backend.app.services.queue_service import (
    enqueue_job, claim_next_job, execute_job_synchronous, requeue_stale_jobs
)

def test_idempotency_key_returns_same_job(client, tenant_fixture, db_session):
    """AC-JOB-3: The same Idempotency-Key returns the same job."""
    payload = {"task": "test_computation"}
    key = "idem-key-unique-12345"

    job1, is_new1 = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload=payload,
        idempotency_key=key
    )
    assert is_new1 is True

    # Enqueue again with identical idempotency key
    job2, is_new2 = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload=payload,
        idempotency_key=key
    )
    assert is_new2 is False
    assert job1.id == job2.id

def test_concurrent_claim_never_double_claims(client, tenant_fixture, db_session):
    """AC-JOB-1: Two workers never execute the same job concurrently."""
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="VALIDATE_DATASET",
        payload={"dataset_version_id": "dummy-uuid"}
    )

    # Worker 1 claims
    claimed1 = claim_next_job(db_session, worker_id="worker-01")
    assert claimed1 is not None
    assert claimed1.id == job.id
    assert claimed1.status == "RUNNING"
    assert claimed1.claimed_by == "worker-01"

    # Worker 2 attempts to claim next job: queue is empty, returns None
    claimed2 = claim_next_job(db_session, worker_id="worker-02")
    assert claimed2 is None

def test_job_retry_backoff_and_max_attempts(db_session, tenant_fixture):
    """AC-JOB-2 / §8.5 line 1106: Transient error retries up to max_attempts with backoff, then marks FAILED."""
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="VALIDATE_DATASET",
        payload={"dataset_version_id": "non-existent-uuid"}
    )
    job.max_attempts = 2
    job.attempt = 1
    job.status = "RUNNING"
    db_session.commit()

    # Attempt 1: should transition to RETRY_WAIT with run_after in the future
    execute_job_synchronous(db_session, job)
    assert job.status == "RETRY_WAIT"
    assert job.error_code == "TRANSIENT_ERROR"
    assert job.run_after > datetime.utcnow()

    # Fast forward run_after and claim again as Attempt 2 (final attempt)
    job.run_after = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    claimed = claim_next_job(db_session, worker_id="worker-retry")
    assert claimed is not None
    assert claimed.attempt == 2

    # Attempt 2 fails: should transition to FAILED because attempt == max_attempts
    execute_job_synchronous(db_session, claimed)
    assert claimed.status == "FAILED"
    assert claimed.error_code == "EXECUTION_ERROR"

def test_stale_job_heartbeat_requeue(db_session, tenant_fixture):
    """AC-JOB-2 / §8.5 line 1104: Stale heartbeat re-queues job if attempts remain."""
    job, _ = enqueue_job(
        db=db_session,
        org_id=tenant_fixture["org"].id,
        job_type="RUN_ANALYSIS",
        payload={"task": "heartbeat_test"}
    )
    job.status = "RUNNING"
    job.attempt = 1
    job.max_attempts = 3
    # Stale heartbeat (older than 120s)
    job.heartbeat_at = datetime.utcnow() - timedelta(seconds=130)
    db_session.commit()

    requeued_count = requeue_stale_jobs(db_session, stale_timeout_seconds=120)
    assert requeued_count == 1

    db_session.refresh(job)
    assert job.status == "QUEUED"
    assert job.current_step == "REQUEUED_STALE_HEARTBEAT"

