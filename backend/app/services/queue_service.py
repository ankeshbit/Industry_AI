"""
Database-Backed Job Queue Service (PRD v1.2 §8.5, §13.6, AC-JOB-1..5)
Supports transaction-safe job enqueuing, idempotency checks, atomic claims (FOR UPDATE SKIP LOCKED),
periodic heartbeat monitoring, stale-job lease recovery, bounded retries with backoff,
and strict transactional consistency.
"""

import uuid
import hashlib
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, text
from fastapi import HTTPException, status

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models.job import Job
from backend.app.models.analysis import AnalysisResult
from backend.app.services.dataset_service import compute_quality_score_and_report
from backend.app.services.inference_service import execute_analysis

logger = logging.getLogger("queue_service")


class JobOwnershipLostError(Exception):
    """Raised when an active worker detects its lease/ownership was revoked or recovered."""
    pass


class JobHeartbeatMonitor:
    """
    Background heartbeat monitor that periodically writes heartbeat timestamps
    in a dedicated DB session while long-running jobs are executing.
    Guarantees that inference jobs running 10-60+ seconds do not time out as stale.
    """
    def __init__(
        self,
        job_id: str,
        worker_id: str,
        attempt: int,
        interval: float = 2.0,
        session_factory: Optional[sessionmaker] = None
    ):
        self.job_id = job_id
        self.worker_id = worker_id
        self.attempt = attempt
        self.interval = interval
        self.session_factory = session_factory or SessionLocal
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.ownership_lost = False

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval):
            if self._stop_event.is_set():
                break
            session = None
            try:
                session = self.session_factory()
                now = datetime.utcnow()
                # CAS: Only update if status is RUNNING, worker matches, and attempt matches
                updated = session.query(Job).filter(
                    Job.id == self.job_id,
                    Job.status == "RUNNING",
                    Job.claimed_by == self.worker_id,
                    Job.attempt == self.attempt
                ).update({"heartbeat_at": now}, synchronize_session=False)
                session.commit()

                if updated == 0:
                    if self._stop_event.is_set():
                        break
                    # Verify if ownership was genuinely revoked by sweeper or re-claimed
                    check_job = session.query(Job).filter(Job.id == self.job_id).first()
                    if check_job:
                        if check_job.status == "RUNNING" and (check_job.claimed_by != self.worker_id or check_job.attempt != self.attempt):
                            logger.warning(f"Heartbeat monitor detected ownership revoked for job {self.job_id} (claimed by {check_job.claimed_by})")
                            self.ownership_lost = True
                            break
                        elif check_job.status in ("FAILED", "CANCELLED", "QUEUED"):
                            logger.warning(f"Heartbeat monitor detected job {self.job_id} transitioned out of RUNNING ({check_job.status})")
                            self.ownership_lost = True
                            break
                        elif check_job.status == "SUCCEEDED":
                            break
            except Exception as e:
                logger.debug(f"Heartbeat write exception for job {self.job_id}: {e}")
                if session:
                    try:
                        session.rollback()
                    except Exception:
                        pass
            finally:
                if session:
                    session.close()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)


class PermanentJobError(Exception):
    """Explicitly non-retryable job failure."""
    pass


def is_permanent_error(exc: Exception) -> bool:
    """
    Distinguishes non-retryable (permanent) client/data errors from transient errors.
    Permanent errors: Explicit PermanentJobError or specific fatal profile incompatibilities.
    Transient/retryable errors: DB timeouts, deadlocks, temporary replication delays, worker interrupts.
    """
    if isinstance(exc, PermanentJobError):
        return True
    if isinstance(exc, HTTPException):
        # Specific fatal unprocessable schema codes that can never succeed on retry
        if isinstance(exc.detail, dict):
            err_code = exc.detail.get("error", {}).get("code", "")
            if err_code in ("E_FEATURE_NOT_IN_PROFILE", "FORBIDDEN_FEATURE", "UNSUPPORTED_FORMAT", "INCOMPATIBLE"):
                return True
        return False
    return False


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
    Enqueues a background job with race-safe idempotency verification (AC-JOB-3).
    Returns (job, is_new).
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
        max_attempts=settings.JOB_MAX_ATTEMPTS,
        run_after=datetime.utcnow(),
        progress_percent=0,
        current_step="QUEUED",
        created_by=user_id
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
        return job, True
    except IntegrityError:
        # Race condition: another concurrent thread committed the same idempotency_key
        db.rollback()
        if idempotency_key:
            existing = db.query(Job).filter(
                Job.organisation_id == org_id,
                Job.idempotency_key == idempotency_key
            ).first()
            if existing:
                return existing, False
        raise


def requeue_stale_jobs(db: Session, stale_timeout_seconds: Optional[int] = None) -> int:
    """
    Finds running jobs whose heartbeat has timed out and safely recovers them (PRD §8.5, AC-JOB-2).
    Uses atomic CAS so stale sweepers do not race with active workers or other sweepers.
    Fails jobs that have exhausted their max_attempts.
    """
    if stale_timeout_seconds is None:
        stale_timeout_seconds = settings.JOB_STALE_TIMEOUT_SECONDS

    cutoff = datetime.utcnow() - timedelta(seconds=stale_timeout_seconds)
    now = datetime.utcnow()

    # Query stale jobs
    stale_jobs = db.query(Job).filter(
        Job.status == "RUNNING",
        Job.heartbeat_at <= cutoff
    ).all()

    count = 0
    for job in stale_jobs:
        if job.attempt < job.max_attempts:
            # Requeue with backoff / immediate retry
            recovered = db.query(Job).filter(
                Job.id == job.id,
                Job.status == "RUNNING",
                Job.claimed_by == job.claimed_by,
                Job.attempt == job.attempt,
                Job.heartbeat_at <= cutoff
            ).update(
                {
                    "status": "QUEUED",
                    "claimed_by": None,
                    "current_step": "REQUEUED_STALE_HEARTBEAT",
                    "run_after": now
                },
                synchronize_session=False
            )
            if recovered == 1:
                count += 1
                logger.info(f"Requeued stale job {job.id} (worker {job.claimed_by} heartbeat expired > {stale_timeout_seconds}s)")
        else:
            # Exhausted attempts
            recovered = db.query(Job).filter(
                Job.id == job.id,
                Job.status == "RUNNING",
                Job.claimed_by == job.claimed_by,
                Job.attempt == job.attempt,
                Job.heartbeat_at <= cutoff
            ).update(
                {
                    "status": "FAILED",
                    "error_code": "HEARTBEAT_TIMEOUT",
                    "user_message": f"Job heartbeat timed out after {stale_timeout_seconds}s and reached maximum attempts.",
                    "finished_at": now
                },
                synchronize_session=False
            )
            if recovered == 1:
                count += 1
                logger.warning(f"Failed stale job {job.id} after reaching max attempts ({job.max_attempts})")

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
    db.query(Job).filter(
        Job.status == "RETRY_WAIT",
        Job.run_after <= now
    ).update(
        {"status": "QUEUED", "current_step": "RETRY_READY"},
        synchronize_session=False
    )
    db.commit()

    # 2. Recover stale jobs whose worker died / timed out
    requeue_stale_jobs(db)

    # 3. Find candidate job using dialect-appropriate locking
    is_postgres = False
    try:
        bind = db.get_bind()
        is_postgres = bind.dialect.name == "postgresql"
    except Exception:
        is_postgres = "postgresql" in settings.DATABASE_URL

    query = db.query(Job).filter(
        Job.status == "QUEUED",
        Job.run_after <= now
    ).order_by(Job.priority.desc(), Job.run_after.asc(), Job.created_at.asc())

    if is_postgres:
        job = query.with_for_update(skip_locked=True).first()
    else:
        job = query.first()

    if not job:
        return None

    # Atomic compare-and-set: update only matches while the row is still QUEUED
    claimed = db.query(Job).filter(
        Job.id == job.id,
        Job.status == "QUEUED"
    ).update(
        {
            "status": "RUNNING",
            "claimed_by": worker_id,
            "started_at": now,
            "heartbeat_at": now,
            "attempt": Job.attempt + 1,
            "current_step": "CLAIMED",
        },
        synchronize_session=False,
    )
    db.commit()
    if claimed != 1:
        return None

    db.refresh(job)
    return job


def claim_job_by_id(db: Session, job_id: str, worker_id: str) -> Optional[Job]:
    """
    Atomically claims a specific job by ID if and only if it is in QUEUED state.
    Used for inline API execution and targeted worker dispatch.
    Returns the Job if claim was won, or None if already claimed / running.
    """
    now = datetime.utcnow()

    is_postgres = False
    try:
        bind = db.get_bind()
        is_postgres = bind.dialect.name == "postgresql"
    except Exception:
        is_postgres = "postgresql" in settings.DATABASE_URL

    query = db.query(Job).filter(Job.id == job_id, Job.status == "QUEUED")
    if is_postgres:
        job = query.with_for_update(skip_locked=True).first()
    else:
        job = query.first()

    if not job:
        return None

    claimed = db.query(Job).filter(
        Job.id == job.id,
        Job.status == "QUEUED"
    ).update(
        {
            "status": "RUNNING",
            "claimed_by": worker_id,
            "started_at": now,
            "heartbeat_at": now,
            "attempt": Job.attempt + 1,
            "current_step": "CLAIMED",
        },
        synchronize_session=False,
    )
    db.commit()
    if claimed != 1:
        return None

    db.refresh(job)
    return job


def execute_job_synchronous(db: Session, job: Job, worker_id: Optional[str] = None) -> Job:
    """
    Executes a claimed job, updating status, progress, heartbeat, and handling retries (AC-JOB-1..5).
    Enforces atomic transaction consistency: AnalysisResult and Job(status=SUCCEEDED) are committed together.
    """
    current_worker = worker_id or job.claimed_by or "worker-default"
    current_attempt = job.attempt

    # Enforce atomic claim requirement: Cannot execute a job that isn't RUNNING
    if job.status != "RUNNING":
        logger.error(f"Cannot execute job {job.id} in state {job.status}; must be claimed into RUNNING state first.")
        return job

    session_factory = None
    try:
        bind = db.get_bind()
        session_factory = sessionmaker(bind=bind, autocommit=False, autoflush=False)
    except Exception as e:
        logger.debug(f"Could not bind session_factory from db session: {e}")

    monitor = JobHeartbeatMonitor(
        job_id=job.id,
        worker_id=current_worker,
        attempt=current_attempt,
        interval=settings.JOB_HEARTBEAT_INTERVAL_SECONDS,
        session_factory=session_factory
    )
    monitor.start()

    try:
        update_job_heartbeat(db, job, progress=15, step="PROCESSING")

        if job.job_type == "VALIDATE_DATASET":
            dv_id = job.payload.get("dataset_version_id")
            mapping_id = job.payload.get("mapping_id")
            report = compute_quality_score_and_report(db, dv_id, mapping_id=mapping_id, org_id=job.organisation_id)

            # Check if lease was revoked during processing
            if monitor.ownership_lost:
                raise JobOwnershipLostError(f"Worker {current_worker} lost ownership of job {job.id} during validation.")

            # Fencing check & atomic commit
            now = datetime.utcnow()
            completed = db.query(Job).filter(
                Job.id == job.id,
                Job.status == "RUNNING",
                Job.claimed_by == current_worker,
                Job.attempt == current_attempt
            ).update(
                {
                    "status": "SUCCEEDED",
                    "progress_percent": 100,
                    "current_step": "VALIDATED",
                    "finished_at": now
                },
                synchronize_session=False
            )
            if completed != 1:
                db.rollback()
                raise JobOwnershipLostError(f"Job {job.id} ownership lost at completion.")
            db.commit()
            db.refresh(job)

        elif job.job_type == "RUN_ANALYSIS":
            check_id = job.payload.get("compatibility_check_id")
            update_job_heartbeat(db, job, progress=40, step="INFERRING")

            # Execute inference without committing immediately to maintain atomic transaction boundary
            result = execute_analysis(db, job.organisation_id, check_id, job_id=job.id, commit=False)

            if monitor.ownership_lost:
                raise JobOwnershipLostError(f"Worker {current_worker} lost ownership of job {job.id} during inference.")

            # Fencing check & atomic commit of both AnalysisResult and Job status
            now = datetime.utcnow()
            completed = db.query(Job).filter(
                Job.id == job.id,
                Job.status == "RUNNING",
                Job.claimed_by == current_worker,
                Job.attempt == current_attempt
            ).update(
                {
                    "status": "SUCCEEDED",
                    "progress_percent": 100,
                    "current_step": "COMPLETED",
                    "finished_at": now
                },
                synchronize_session=False
            )
            if completed != 1:
                db.rollback()
                raise JobOwnershipLostError(f"Job {job.id} ownership lost at completion.")

            db.commit()
            db.refresh(job)
            db.refresh(result)

        else:
            # Unsupported job type is a permanent failure
            job.status = "FAILED"
            job.error_code = "UNKNOWN_JOB_TYPE"
            job.user_message = f"Job type '{job.job_type}' is not supported."
            job.finished_at = datetime.utcnow()
            db.commit()

    except JobOwnershipLostError as jole:
        logger.warning(f"Aborting execution: {jole}")
        db.rollback()
        # Do not modify job row; recovered worker now owns it

    except Exception as e:
        db.rollback()
        logger.error(f"Execution error on job {job.id}: {e}", exc_info=True)

        # Distinguish permanent client/data errors from transient errors
        if is_permanent_error(e):
            err_code = "EXECUTION_ERROR"
            err_msg = str(e)
            if isinstance(e, HTTPException):
                if isinstance(e.detail, dict):
                    err_code = e.detail.get("error", {}).get("code", "HTTP_ERROR")
                    err_msg = e.detail.get("error", {}).get("message", str(e.detail))
                else:
                    err_msg = str(e.detail)
            
            job.status = "FAILED"
            job.error_code = err_code
            job.user_message = err_msg
            job.finished_at = datetime.utcnow()
            db.commit()

        else:
            # Bounded retry backoff for transient errors (10s, 60s, 300s)
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
                job.user_message = f"Job failed after {job.attempt} attempts. Last error: {str(e)}"
                job.finished_at = datetime.utcnow()
                db.commit()

    finally:
        monitor.stop()

    return job
