"""
Job Processing Endpoints (PRD v1.2 §8.5, §13.5, AC-JOB-1..5)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.job import Job
from backend.app.api.deps import get_current_user

router = APIRouter(tags=["Jobs"])

@router.get("/jobs/{id}", status_code=status.HTTP_200_OK)
def get_job(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns background job status and progress (AC-JOB-1)."""
    job = db.query(Job).filter(
        Job.id == id,
        Job.organisation_id == current_user.organisation_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_step": job.current_step,
        "attempt": job.attempt,
        "error_code": job.error_code,
        "user_message": job.user_message,
        "created_at": job.created_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at else None
    }

@router.get("/jobs", status_code=status.HTTP_200_OK)
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists recent background jobs for the organisation."""
    jobs = db.query(Job).filter(
        Job.organisation_id == current_user.organisation_id
    ).order_by(Job.created_at.desc()).limit(50).all()

    return [
        {
            "id": j.id,
            "job_type": j.job_type,
            "status": j.status,
            "progress_percent": j.progress_percent,
            "current_step": j.current_step,
            "created_at": j.created_at.isoformat()
        }
        for j in jobs
    ]

