"""
Job Queue Model for INDUSTRIA AI (PRD v1.2 §8.5, §12.2, AC-JOB-1..5)
PostgreSQL / SQLite backed queue claiming work with transactional concurrency.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Integer, Boolean, Text, UniqueConstraint
)
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Job(Base):
    """Asynchronous processing job (PRD v1.2 §8.5)."""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # SCAN_UPLOAD, VALIDATE_DATASET, RUN_ANALYSIS, etc.
    status = Column(String(30), nullable=False, default="QUEUED", index=True)  # QUEUED, RUNNING, RETRY_WAIT, CANCEL_REQUESTED, SUCCEEDED, FAILED, CANCELLED
    priority = Column(Integer, default=100, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    params_hash = Column(String(64), nullable=True)
    idempotency_key = Column(String(255), nullable=True, index=True)
    attempt = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    run_after = Column(DateTime, default=datetime.utcnow, nullable=False)
    claimed_by = Column(String(100), nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    progress_percent = Column(Integer, default=0, nullable=False)
    current_step = Column(String(255), nullable=True)
    cancel_requested = Column(Boolean, default=False, nullable=False)
    error_code = Column(String(50), nullable=True)
    user_message = Column(Text, nullable=True)
    remedy = Column(Text, nullable=True)
    diagnostic_id = Column(String(36), nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organisation_id", "idempotency_key", name="uq_job_org_idempotency_key"),
    )

