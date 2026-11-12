"""
Compatibility, Applicability, and Reliability Endpoints (PRD v1.2 §8.4, §13.5, AC-CE-1..7, AC-AP-1..5)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.machine import Machine
from backend.app.models.dataset import DatasetVersion
from backend.app.models.compatibility import (
    CompatibilityCheck, PipelineProfile, WarningAcknowledgement, LimitationAcknowledgement
)
from backend.app.api.deps import get_current_user
from backend.app.services.compatibility_service import evaluate_compatibility

router = APIRouter(tags=["Compatibility Engine"])

class RunCompatibilityRequest(BaseModel):
    profile_id: Optional[str] = None
    mapping_id: Optional[str] = None

class AcknowledgeWarningsRequest(BaseModel):
    reason_codes: List[str]

class AcknowledgeLimitationRequest(BaseModel):
    machine_id: str
    profile_uuid: str
    model_version_id: Optional[str] = None
    statement_version: str = "1.0.0"

def format_check_response(check: CompatibilityCheck) -> Dict[str, Any]:
    active_warnings = [r["code"] for r in check.reasons if r.get("severity") == "WARNING"]
    doc = check.profile.document
    return {
        "id": check.id,
        "dataset_version_id": check.dataset_version_id,
        "machine_id": check.machine_id,
        "profile": {
            "id": check.profile.id,
            "profile_id": check.profile.profile_id,
            "version": check.profile.version,
            "pipeline": check.profile.pipeline,
            "configuration": check.profile.configuration
        },
        "compatibility": {
            "status": check.status,
            "reasons": check.reasons
        },
        "applicability": {
            "level": check.applicability_level,
            "flagged_row_fraction": check.applicability_detail.get("flagged_row_fraction", 0.0),
            "per_feature": check.applicability_detail.get("per_feature", {}),
            "domain_note": check.applicability_detail.get("domain_note", "Model trained on AI4I 2020 synthetic data; your machine may differ."),
            "disclaimer": check.applicability_detail.get("disclaimer", "This level is a warning mechanism, not evidence that predictions are reliable or unreliable.")
        },
        "reliability": {
            "tier": check.reliability_tier,
            "statement": check.reliability_basis.get("statement", "Reference-dataset-trained model; not validated on your equipment.")
        },
        "requires_acknowledgement": active_warnings,
        "requires_limitation_acknowledgement": True,
        "created_at": check.created_at.isoformat()
    }

@router.post("/dataset-versions/{vid}/compatibility-checks", status_code=status.HTTP_201_CREATED)
def run_checks_endpoint(
    vid: str,
    req: RunCompatibilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates dataset compatibility, reference-domain applicability, and reliability tier (PRD §8.4).
    If profile_id is omitted, evaluates every eligible profile (both AI4I configurations).
    """
    dv = db.query(DatasetVersion).filter(
        DatasetVersion.id == vid,
        DatasetVersion.organisation_id == current_user.organisation_id
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    machine = dv.dataset.machine
    category = machine.category

    # Determine profiles to check
    if req.profile_id:
        profiles = db.query(PipelineProfile).filter(PipelineProfile.profile_id == req.profile_id).all()
    else:
        # Evaluate all eligible profiles
        eligible_profile_ids = category.eligible_profiles if category else ["ai4i_failure_no_type", "ai4i_failure_with_type"]
        profiles = db.query(PipelineProfile).filter(PipelineProfile.profile_id.in_(eligible_profile_ids)).all()

    if not profiles:
        raise HTTPException(status_code=422, detail="No eligible pipeline profiles found for machine category.")

    results = []
    for prof in profiles:
        check = evaluate_compatibility(
            db=db,
            org_id=current_user.organisation_id,
            dataset_version_id=vid,
            profile_id=prof.profile_id,
            mapping_id=req.mapping_id
        )
        results.append(format_check_response(check))

    return results

@router.get("/dataset-versions/{vid}/compatibility-checks", status_code=status.HTTP_200_OK)
def get_checks_endpoint(
    vid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists compatibility checks for a dataset version."""
    checks = db.query(CompatibilityCheck).filter(
        CompatibilityCheck.dataset_version_id == vid,
        CompatibilityCheck.organisation_id == current_user.organisation_id
    ).order_by(CompatibilityCheck.created_at.desc()).all()

    return [format_check_response(c) for c in checks]

@router.get("/compatibility-checks/{id}", status_code=status.HTTP_200_OK)
def get_single_check(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gets details of an immutable compatibility check."""
    check = db.query(CompatibilityCheck).filter(
        CompatibilityCheck.id == id,
        CompatibilityCheck.organisation_id == current_user.organisation_id
    ).first()
    if not check:
        raise HTTPException(status_code=404, detail="Compatibility check not found.")
    return format_check_response(check)

@router.post("/compatibility-checks/{id}/acknowledge-warnings", status_code=status.HTTP_200_OK)
def acknowledge_warnings(
    id: str,
    req: AcknowledgeWarningsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Acknowledges active warning codes for a compatibility check (AC-CE-4)."""
    check = db.query(CompatibilityCheck).filter(
        CompatibilityCheck.id == id,
        CompatibilityCheck.organisation_id == current_user.organisation_id
    ).first()
    if not check:
        raise HTTPException(status_code=404, detail="Compatibility check not found.")

    # Only warnings that are actually active on this check can be acknowledged (arbitrary codes were accepted),
    # and repeating a request must not create duplicate audit rows.
    active = {r["code"] for r in check.reasons if r.get("severity") == "WARNING"}
    unknown = sorted(set(req.reason_codes) - active)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "UNKNOWN_WARNING_CODE", "message": "Codes are not active warnings on this check.", "details": unknown}}
        )
    already = {
        a.reason_code for a in db.query(WarningAcknowledgement).filter(
            WarningAcknowledgement.compatibility_check_id == check.id,
            WarningAcknowledgement.organisation_id == current_user.organisation_id,
        )
    }
    for code in dict.fromkeys(req.reason_codes):
        if code in already:
            continue
        db.add(WarningAcknowledgement(
            organisation_id=current_user.organisation_id,
            compatibility_check_id=check.id,
            reason_code=code,
            acknowledged_by=current_user.id
        ))
    db.commit()
    return {"message": "Warnings acknowledged successfully.", "acknowledged_codes": req.reason_codes}

@router.post("/limitations/acknowledge", status_code=status.HTTP_200_OK)
def acknowledge_limitation(
    req: AcknowledgeLimitationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records explicit acknowledgement of reference-dataset model limitations (AC-AP-5, AC-ORG-2)."""
    machine = db.query(Machine).filter(
        Machine.id == req.machine_id,
        Machine.organisation_id == current_user.organisation_id
    ).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found.")

    existing = db.query(LimitationAcknowledgement).filter(
        LimitationAcknowledgement.organisation_id == current_user.organisation_id,
        LimitationAcknowledgement.machine_id == req.machine_id,
        LimitationAcknowledgement.profile_uuid == req.profile_uuid,
        LimitationAcknowledgement.statement_version == req.statement_version
    ).first()

    if not existing:
        ack = LimitationAcknowledgement(
            organisation_id=current_user.organisation_id,
            machine_id=req.machine_id,
            profile_uuid=req.profile_uuid,
            model_version_id=req.model_version_id,
            statement_version=req.statement_version,
            acknowledged_by=current_user.id
        )
        db.add(ack)
        db.commit()

    return {"message": "Model limitations acknowledged successfully."}
