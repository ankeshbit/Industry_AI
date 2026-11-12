"""
Analysis Execution and Results Endpoints (PRD v1.2 §8.6, §13.5, AC-FP-1..8, AC-AP-1..5)
Enforces the job-creation gate, dispatches analysis execution, and returns
results with complete provenance, trust metadata, and OOD flags.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status, HTTPException, Header
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.compatibility import CompatibilityCheck
from backend.app.models.analysis import AnalysisResult
from backend.app.models.dataset import Dataset, DatasetVersion
from backend.app.models.model import ModelVersion
from backend.app.models.compatibility import WarningAcknowledgement, LimitationAcknowledgement
from backend.app.api.deps import get_current_user
from backend.app.services.compatibility_service import verify_job_creation_gate
from backend.app.services.queue_service import enqueue_job, execute_job_synchronous
from backend.app.services.inference_service import execute_analysis

router = APIRouter(tags=["Analyses"])

# Standing advisory mandated by PRD v1.2 §14.2: must accompany every prediction result (UI and API).
STANDING_ADVISORY = (
    "This analysis was produced using a reference model trained on the AI4I 2020 Predictive Maintenance Dataset. "
    "It reflects machine tool operating patterns from that reference dataset and has not been validated on your "
    "specific equipment or operating conditions. Predictions must be treated as advisory inputs to human "
    "maintenance decisions, not as definitive health assessments. The operator assumes full responsibility for "
    "maintenance decisions."
)

class CreateAnalysisRequest(BaseModel):
    compatibility_check_id: str
    acknowledged_reason_codes: List[str] = Field(default_factory=list)
    limitation_acknowledged: bool = False
    parameters: Optional[Dict[str, Any]] = None
    force_rerun: bool = False

def format_analysis_result(res: AnalysisResult, db: Session) -> Dict[str, Any]:
    # Resolve the dataset/version this result was actually computed from
    # (previously: the machine's first dataset, and result_version was shown as the dataset version).
    dv = db.query(DatasetVersion).filter(DatasetVersion.id == res.dataset_version_id).first()
    dataset = db.query(Dataset).filter(Dataset.id == dv.dataset_id).first() if dv else None
    model = db.query(ModelVersion).filter(ModelVersion.id == res.model_version_id).first() if res.model_version_id else None
    check = res.compatibility_check_id and db.query(CompatibilityCheck).filter(
        CompatibilityCheck.id == res.compatibility_check_id
    ).first()
    profile = check.profile if check else None

    default_registry = "ai4i_failure_clf_notype" if res.configuration == "NO_TYPE" else "ai4i_failure_clf_typed"
    return {
        "id": res.id,
        "machine_id": res.machine_id,
        "pipeline": res.pipeline,
        "configuration": res.configuration,
        "result_version": res.result_version,
        "is_latest": res.is_latest,
        "provenance": {
            "dataset": {
                "id": res.dataset_version_id,
                "name": dataset.name if dataset else "unknown",
                "version": dv.version_no if dv else None,
                "provenance": dataset.provenance if dataset else "CUSTOMER"
            },
            "profile": f"{profile.profile_id}@{profile.version}" if profile else f"{res.configuration}@1.0.0",
            "model": {
                "registry_name": model.registry_name if model else default_registry,
                "version": model.version if model else "1.0.0",
                "training_domain": res.training_domain,
                "trained_on": "AI4I 2020 (synthetic)"
            },
            "computed_at": res.created_at.isoformat()
        },
        "trust": {
            "compatibility": check.status if check else "COMPATIBLE",
            "applicability": res.applicability_level,
            "reliability_tier": res.reliability_tier,
            "label": "Reference-dataset-trained model – not validated on your equipment"
        },
        "semantics": "Reference-calibrated failure probability for the supplied operating state; no time horizon is implied.",
        "evaluation_sections": {
            # Expose the model card, not the server-side filesystem path of the model artifact
            "reference_dataset_evaluation": {"model_card_uri": model.model_card_uri if model else None},
            "customer_specific_validation": None
        },
        "summary": res.summary,
        "ood_summary": res.ood_summary,
        "limitations": res.limitations,
        "explanation_disclaimer": "Feature attributions describe model behaviour, not physical causation.",
        "advisory_notice": STANDING_ADVISORY,
        "created_at": res.created_at.isoformat()
    }

def _record_acknowledgements(db: Session, user: User, check: CompatibilityCheck) -> None:
    """
    Persist the warning/limitation acknowledgements that authorised this run (PRD §8.4.7, AC-CE-4, AC-AP-5).
    The UI sends them inline with the run request and never calls the dedicated acknowledge endpoints, so
    without this the audit tables stayed empty even though users had acknowledged.
    """
    already = {
        a.reason_code
        for a in db.query(WarningAcknowledgement).filter(
            WarningAcknowledgement.compatibility_check_id == check.id,
            WarningAcknowledgement.organisation_id == user.organisation_id,
        )
    }
    for r in check.reasons:
        code = r.get("code")
        if r.get("severity") == "WARNING" and code not in already:
            db.add(WarningAcknowledgement(
                organisation_id=user.organisation_id,
                compatibility_check_id=check.id,
                reason_code=code,
                acknowledged_by=user.id,
            ))
            already.add(code)

    model = db.query(ModelVersion).filter(
        ModelVersion.profile_uuid == check.profile_uuid, ModelVersion.stage == "PRODUCTION"
    ).first()
    model_id = model.id if model else None
    existing = db.query(LimitationAcknowledgement).filter(
        LimitationAcknowledgement.organisation_id == user.organisation_id,
        LimitationAcknowledgement.machine_id == check.machine_id,
        LimitationAcknowledgement.profile_uuid == check.profile_uuid,
        LimitationAcknowledgement.model_version_id == model_id,
        LimitationAcknowledgement.statement_version == "1.0.0",
    ).first()
    if not existing:
        db.add(LimitationAcknowledgement(
            organisation_id=user.organisation_id,
            machine_id=check.machine_id,
            profile_uuid=check.profile_uuid,
            model_version_id=model_id,
            statement_version="1.0.0",
            acknowledged_by=user.id,
        ))
    db.commit()


@router.post("/analyses", status_code=status.HTTP_202_ACCEPTED)
def request_analysis(
    req: CreateAnalysisRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authorizes and executes an analysis run (PRD §8.4.7, §13.5).
    Enforces the job-creation gate:
    - 422 INCOMPATIBLE / INSUFFICIENT_DATA / UNSUPPORTED_FORMAT
    - 422 APPLICABILITY_BLOCKED
    - 422 WARNINGS_NOT_ACKNOWLEDGED
    - 422 LIMITATIONS_NOT_ACKNOWLEDGED
    """
    check = verify_job_creation_gate(
        db=db,
        org_id=current_user.organisation_id,
        compatibility_check_id=req.compatibility_check_id,
        acknowledged_reason_codes=req.acknowledged_reason_codes,
        limitation_acknowledged=req.limitation_acknowledged
    )

    _record_acknowledgements(db, current_user, check)

    # Enqueue job
    payload = {
        "compatibility_check_id": check.id,
        "dataset_version_id": check.dataset_version_id,
        "machine_id": check.machine_id,
        "profile_uuid": check.profile_uuid,
        "configuration": check.profile.configuration,
        "params": req.parameters or {}
    }

    # A forced re-run must create a new job: reusing the idempotent job would attempt to insert a
    # second AnalysisResult with the same (unique) job_id and fail.
    job, is_new = enqueue_job(
        db=db,
        org_id=current_user.organisation_id,
        job_type="RUN_ANALYSIS",
        payload=payload,
        idempotency_key=None if req.force_rerun else idempotency_key,
        user_id=current_user.id
    )

    # For local/testing fast-path: execute immediately if new
    if is_new:
        job = execute_job_synchronous(db, job)

    # Fetch created result
    result = db.query(AnalysisResult).filter(
        AnalysisResult.job_id == job.id,
        AnalysisResult.organisation_id == current_user.organisation_id
    ).first()

    if not result:
        # Fallback if executed directly or queued
        result = db.query(AnalysisResult).filter(
            AnalysisResult.compatibility_check_id == check.id,
            AnalysisResult.organisation_id == current_user.organisation_id
        ).order_by(AnalysisResult.created_at.desc()).first()

    return {
        "job_id": job.id,
        "status": job.status,
        "analysis_result_id": result.id if result else None
    }

@router.get("/analyses/{result_id}", status_code=status.HTTP_200_OK)
def get_analysis_result(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns AnalysisResult with complete provenance, trust block, and limitations (AC-FP-5, AC-AP-4)."""
    res = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id,
        AnalysisResult.organisation_id == current_user.organisation_id
    ).first()
    if not res:
        raise HTTPException(status_code=404, detail="Analysis result not found.")
    return format_analysis_result(res, db)

@router.get("/analyses/{result_id}/rows", status_code=status.HTTP_200_OK)
def get_analysis_rows(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns top rows with failure probabilities, risk classes, and OOD flags (AC-FP-8)."""
    res = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id,
        AnalysisResult.organisation_id == current_user.organisation_id
    ).first()
    if not res:
        raise HTTPException(status_code=404, detail="Analysis result not found.")
    return {
        "analysis_id": res.id,
        "total_rows": res.summary.get("total_rows", 0),
        "top_rows": res.top_rows
    }

@router.get("/machines/{id}/analyses", status_code=status.HTTP_200_OK)
def get_machine_analyses(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns historical prediction results for a machine."""
    results = db.query(AnalysisResult).filter(
        AnalysisResult.machine_id == id,
        AnalysisResult.organisation_id == current_user.organisation_id
    ).order_by(AnalysisResult.created_at.desc()).all()
    return [format_analysis_result(r, db) for r in results]
