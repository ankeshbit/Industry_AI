"""
Dataset Ingestion, Preview, Mapping Wizard, and Validation Endpoints (PRD v1.2 §8.3, §13.4, AC-DS-1..10)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.dataset import Dataset, DatasetVersion, ColumnMapping, ValidationReport
from backend.app.api.deps import get_current_user
from backend.app.services.dataset_service import (
    create_dataset, upload_dataset_version_stream, compute_quality_score_and_report,
    generate_column_suggestions, save_column_mapping
)

router = APIRouter(tags=["Datasets"])

class CreateDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dataset_type: str = "TABULAR_OPERATING_STATE"
    objective: str = "FAILURE_PROBABILITY_CURRENT_STATE"

class SaveMappingRequest(BaseModel):
    mappings: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None

@router.post("/machines/{id}/datasets", status_code=status.HTTP_201_CREATED)
def create_dataset_endpoint(
    id: str,
    req: CreateDatasetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registers a dataset collection attached to a machine (AC-MM-2, AC-DS-1)."""
    dataset = create_dataset(
        db=db,
        org_id=current_user.organisation_id,
        machine_id=id,
        name=req.name,
        description=req.description,
        dataset_type=req.dataset_type,
        objective=req.objective,
        user_id=current_user.id
    )
    return {
        "id": dataset.id,
        "machine_id": dataset.machine_id,
        "name": dataset.name,
        "dataset_type": dataset.dataset_type,
        "objective": dataset.objective,
        "created_at": dataset.created_at.isoformat()
    }

@router.get("/machines/{id}/datasets", status_code=status.HTTP_200_OK)
def get_machine_datasets(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all datasets belonging to a machine."""
    datasets = db.query(Dataset).filter(
        Dataset.machine_id == id,
        Dataset.organisation_id == current_user.organisation_id
    ).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "dataset_type": d.dataset_type,
            "versions_count": len(d.versions),
            "created_at": d.created_at.isoformat()
        }
        for d in datasets
    ]

@router.get("/datasets/{id}", status_code=status.HTTP_200_OK)
def get_dataset_details(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns dataset details and version history."""
    d = db.query(Dataset).filter(
        Dataset.id == id,
        Dataset.organisation_id == current_user.organisation_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {
        "id": d.id,
        "machine_id": d.machine_id,
        "name": d.name,
        "description": d.description,
        "dataset_type": d.dataset_type,
        "versions": [
            {
                "id": v.id,
                "version_no": v.version_no,
                "file_kind": v.file_kind,
                "sha256": v.sha256,
                "row_count": v.row_count,
                "column_count": v.column_count,
                "created_at": v.created_at.isoformat()
            }
            for v in d.versions
        ]
    }

@router.post("/datasets/{id}/versions/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset_file(
    id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a CSV file for a dataset:
    - Enforces 50MB limit (413 PAYLOAD_TOO_LARGE)
    - Verifies CSV magic bytes/extension (415 UNSUPPORTED_FORMAT)
    - Computes SHA-256 and deduplicates
    - Ingests schema and computes baseline validation report
    """
    file_bytes = await file.read()
    dv, is_dedup = upload_dataset_version_stream(
        db=db,
        org_id=current_user.organisation_id,
        dataset_id=id,
        filename=file.filename or "upload.csv",
        file_bytes=file_bytes,
        user_id=current_user.id
    )

    # Trigger automatic validation report
    report = compute_quality_score_and_report(db, dv.id)

    return {
        "dataset_version_id": dv.id,
        "version_no": dv.version_no,
        "sha256": dv.sha256,
        "row_count": dv.row_count,
        "column_count": dv.column_count,
        "deduplicated": is_dedup,
        "quality_score": report.quality_score,
        "created_at": dv.created_at.isoformat()
    }

@router.get("/dataset-versions/{vid}", status_code=status.HTTP_200_OK)
def get_version_details(
    vid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns dataset version details and schema columns."""
    dv = db.query(DatasetVersion).filter(
        DatasetVersion.id == vid,
        DatasetVersion.organisation_id == current_user.organisation_id
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    latest_report = db.query(ValidationReport).filter(
        ValidationReport.dataset_version_id == vid
    ).order_by(ValidationReport.created_at.desc()).first()

    return {
        "id": dv.id,
        "dataset_id": dv.dataset_id,
        "version_no": dv.version_no,
        "file_kind": dv.file_kind,
        "size_bytes": dv.size_bytes,
        "sha256": dv.sha256,
        "status": dv.status,
        "row_count": dv.row_count,
        "column_count": dv.column_count,
        "quality_score": latest_report.quality_score if latest_report else None,
        "columns": [
            {
                "position": c.position,
                "name": c.name,
                "inferred_type": c.inferred_type,
                "stats": c.stats
            }
            for c in dv.columns
        ]
    }

@router.get("/dataset-versions/{vid}/preview", status_code=status.HTTP_200_OK)
def get_preview(
    vid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns dataset preview rows (first 10 rows). Verifies tenant ownership (AC-ORG-2)."""
    dv = db.query(DatasetVersion).filter(
        DatasetVersion.id == vid,
        DatasetVersion.organisation_id == current_user.organisation_id
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    report = db.query(ValidationReport).filter(
        ValidationReport.dataset_version_id == vid,
        ValidationReport.organisation_id == current_user.organisation_id
    ).order_by(ValidationReport.created_at.desc()).first()

    if not report or not report.preview:
        # Generate on demand
        report = compute_quality_score_and_report(db, vid, org_id=current_user.organisation_id)

    return {"preview": report.preview}

@router.get("/dataset-versions/{vid}/mappings/{profile_id}/suggestions", status_code=status.HTTP_200_OK)
def get_suggestions(
    vid: str,
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns mapping suggestions from column name normalization and synonyms (AC-DS-9, AC-ORG-2)."""
    return generate_column_suggestions(db, vid, profile_id, org_id=current_user.organisation_id)

@router.put("/dataset-versions/{vid}/mappings/{profile_id}", status_code=status.HTTP_200_OK)
def put_mapping(
    vid: str,
    profile_id: str,
    req: SaveMappingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves confirmed column mapping:
    - Enforces no forbidden features as inputs (AC-CE-7)
    - Enforces product_type accepted only under WITH_TYPE with asserted_equivalence=true (AC-FP-4)
    - Validates allowed units
    - Triggers validation report recomputation
    """
    mapping_record = save_column_mapping(
        db=db,
        org_id=current_user.organisation_id,
        dataset_version_id=vid,
        profile_id=profile_id,
        mappings=req.mappings,
        options=req.options,
        user_id=current_user.id
    )
    return {
        "mapping_id": mapping_record.id,
        "mapping_version": mapping_record.mapping_version,
        "status": "VALIDATED"
    }

@router.get("/dataset-versions/{vid}/validation-reports", status_code=status.HTTP_200_OK)
def get_validation_reports(
    vid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the latest validation report with quality score and check findings (AC-ORG-2)."""
    dv = db.query(DatasetVersion).filter(
        DatasetVersion.id == vid,
        DatasetVersion.organisation_id == current_user.organisation_id
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    report = db.query(ValidationReport).filter(
        ValidationReport.dataset_version_id == vid,
        ValidationReport.organisation_id == current_user.organisation_id
    ).order_by(ValidationReport.created_at.desc()).first()

    if not report:
        report = compute_quality_score_and_report(db, vid, org_id=current_user.organisation_id)

    return {
        "id": report.id,
        "quality_score": report.quality_score,
        "quality_components": report.quality_components,
        "checks": report.checks,
        "created_at": report.created_at.isoformat()
    }

