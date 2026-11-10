"""
Database-Backed Job Queue Service (PRD v1.2 §8.5, §13.6, AC-JOB-1..5)
Supports transaction-safe job enqueuing, idempotency checks, atomic claims,
heartbeat updates, and execution dispatching.
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from fastapi import HTTPException, status

from backend.app.config import settings
from backend.app.models.job import Job
from backend.app.services.dataset_service import compute_quality_score_and_report
from backend.app.services.inference_service import execute_analysis

def enqueue_job(
    db: Session,
    org_id: str,
    job_type: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    priority: int = 100,
    user_id: Optional[str] = None
) -> Tuple[Job, bool]:
    """
    Enqueues a background job.
    If idempotency_key is provided and an existing job matches, returns the existing job (AC-JOB-3).
    """
    if idempotency_key:
        existing = db.query(Job).filter(
            Job.organisation_id == org_id,
            Job.idempotency_key == idempotency_key
        ).first()
        if existing:
            return existing, False

    params_hash = hashlib.sha256(str(sorted(payload.items())).encode()).hexdigest()

    job = Job(
        organisation_id=org_id,
        job_type=job_type,
        status="QUEUED",
        priority=priority,
        payload=payload,
        params_hash=params_hash,
        idempotency_key=idempotency_key,
        attempt=0,
        max_attempts=3,
        run_after=datetime.utcnow(),
        progress_percent=0,
        current_step="QUEUED",
        created_by=user_id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, True

def requeue_stale_jobs(db: Session, stale_timeout_seconds: int = 120) -> int:
    """
    Finds running jobs whose heartbeat has timed out and re-queues or fails them (PRD §8.5, AC-JOB-2).
    """
    cutoff = datetime.utcnow() - timedelta(seconds=stale_timeout_seconds)
    stale_jobs = db.query(Job).filter(
        Job.status == "RUNNING",
        Job.heartbeat_at <= cutoff
    ).all()
    count = 0
    for job in stale_jobs:
        if job.attempt < job.max_attempts:
            job.status = "QUEUED"
            job.current_step = "REQUEUED_STALE_HEARTBEAT"
            job.run_after = datetime.utcnow()
        else:
            job.status = "FAILED"
            job.error_code = "HEARTBEAT_TIMEOUT"
            job.user_message = f"Job heartbeat timed out after {stale_timeout_seconds}s and reached maximum attempts."
            job.finished_at = datetime.utcnow()
        count += 1
    if count > 0:
        db.commit()
    return count

def update_job_heartbeat(db: Session, job: Job, progress: Optional[int] = None, step: Optional[str] = None) -> None:
    """Updates job heartbeat timestamp and optional progress (PRD §8.5 line 1104, AC-JOB-4)."""
    job.heartbeat_at = datetime.utcnow()
    if progress is not None:
        job.progress_percent = progress
    if step is not None:
        job.current_step = step
    db.commit()

def claim_next_job(db: Session, worker_id: str) -> Optional[Job]:
    """
    Atomically claims the next eligible QUEUED job (AC-JOB-1..2).
    Uses SELECT ... FOR UPDATE SKIP LOCKED on PostgreSQL, or atomic transaction check on SQLite.
    Also recovers stale jobs and promotes matured RETRY_WAIT jobs.
    """
    now = datetime.utcnow()

    # 1. Promote matured RETRY_WAIT jobs to QUEUED
    matured = db.query(Job).filter(
        Job.status == "RETRY_WAIT",
        Job.run_after <= now
    ).all()
    for j in matured:
        j.status = "QUEUED"
    if matured:
        db.commit()

    # 2. Recover stale jobs whose worker died / timed out
    requeue_stale_jobs(db, stale_timeout_seconds=120)

    # 3. Find candidate job
    if settings.DATABASE_URL.startswith("postgresql"):
        # PRD §8.5: SELECT ... FOR UPDATE SKIP LOCKED
        job = db.query(Job).filter(
            Job.status == "QUEUED",
            Job.run_after <= now
        ).order_by(Job.priority.desc(), Job.run_after.asc()).with_for_update(skip_locked=True).first()
    else:
        # SQLite transaction-locked check
        job = db.query(Job).filter(
            Job.status == "QUEUED",
            Job.run_after <= now
        ).order_by(Job.priority.desc(), Job.run_after.asc()).first()

    if not job:
        return None

    job.status = "RUNNING"
    job.claimed_by = worker_id
    job.started_at = now
    job.heartbeat_at = now
    job.attempt += 1
    job.current_step = "CLAIMED"
    db.commit()
    db.refresh(job)
    return job

def execute_job_synchronous(db: Session, job: Job) -> Job:
    """
    Executes a claimed job synchronously, updating status, progress, heartbeat, and handling retries (AC-JOB-1..5).
    """
    try:
        update_job_heartbeat(db, job, progress=25, step="PROCESSING")

        if job.job_type == "VALIDATE_DATASET":
            dv_id = job.payload.get("dataset_version_id")
            mapping_id = job.payload.get("mapping_id")
            report = compute_quality_score_and_report(db, dv_id, mapping_id=mapping_id, org_id=job.organisation_id)
            update_job_heartbeat(db, job, progress=100, step="VALIDATED")
            job.status = "SUCCEEDED"
            job.finished_at = datetime.utcnow()
            db.commit()

        elif job.job_type == "RUN_ANALYSIS":
            check_id = job.payload.get("compatibility_check_id")
            update_job_heartbeat(db, job, progress=50, step="INFERRING")
            result = execute_analysis(db, job.organisation_id, check_id, job_id=job.id)
            update_job_heartbeat(db, job, progress=100, step="COMPLETED")
            job.status = "SUCCEEDED"
            job.finished_at = datetime.utcnow()
            db.commit()

        else:
            job.status = "FAILED"
            job.error_code = "UNKNOWN_JOB_TYPE"
            job.user_message = f"Job type '{job.job_type}' is not supported."
            job.finished_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        db.rollback()
        # PRD §8.5 line 1106: Transient errors retry up to max_attempts (default 3) with backoff 10s / 60s / 300s
        if job.attempt < job.max_attempts:
            backoffs = [10, 60, 300]
            backoff_sec = backoffs[min(job.attempt - 1, len(backoffs) - 1)]
            job.status = "RETRY_WAIT"
            job.run_after = datetime.utcnow() + timedelta(seconds=backoff_sec)
            job.error_code = "TRANSIENT_ERROR"
            job.user_message = f"Attempt {job.attempt} failed: {str(e)}. Retrying after {backoff_sec}s."
            db.commit()
        else:
            job.status = "FAILED"
            job.error_code = "EXECUTION_ERROR"
            job.user_message = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()

    return job

