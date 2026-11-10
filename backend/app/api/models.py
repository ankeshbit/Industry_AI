"""
Model Registry and Pipeline Profile Template Endpoints (PRD v1.2 §10.1, §13.5)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.compatibility import PipelineProfile
from backend.app.models.model import ModelVersion, ModelEvaluation

router = APIRouter(tags=["Model Catalogue"])

@router.get("/models", status_code=status.HTTP_200_OK)
def list_models(db: Session = Depends(get_db)):
    """
    Returns registered models in Production with reference-dataset evaluations (PRD line 2096).
    Customer-specific validation is explicitly null for shared models.
    """
    models = db.query(ModelVersion).filter(ModelVersion.stage == "PRODUCTION").all()
    results = []
    for m in models:
        evals = [
            {
                "split": e.split,
                "metric_name": e.metric_name,
                "metric_value": e.metric_value,
                "ci_low": e.ci_low,
                "ci_high": e.ci_high,
                "n_samples": e.n_samples
            }
            for e in m.evaluations
            if e.evaluation_kind == "REFERENCE_DATASET"
        ]
        results.append({
            "id": m.id,
            "registry_name": m.registry_name,
            "version": m.version,
            "pipeline": m.pipeline,
            "configuration": m.configuration,
            "algorithm": m.algorithm,
            "stage": m.stage,
            "training_domain": m.training_domain,
            "reference_evaluations": evals,
            "customer_specific_validation": None,
            "model_card_uri": m.model_card_uri
        })
    return results

@router.get("/pipeline-profiles/{profile_id}/template", response_class=PlainTextResponse)
def get_profile_template(profile_id: str, db: Session = Depends(get_db)):
    """Returns downloadable CSV header template for the profile (PRD line 2007)."""
    profile = db.query(PipelineProfile).filter(PipelineProfile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Pipeline profile not found.")

    doc = profile.document
    headers = []
    for f in doc.get("required_features", []):
        name = f["name"]
        unit = f.get("unit_canonical", "")
        if unit:
            headers.append(f"{name} [{unit}]")
        else:
            headers.append(name)

    return ",".join(headers) + "\n"

