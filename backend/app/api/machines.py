"""
Machine Registry Endpoints for INDUSTRIA AI (PRD v1.2 §8.2, §13.3, AC-MM-1..3)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.machine import MachineCategory
from backend.app.api.deps import get_current_user
from backend.app.services.machine_service import (
    create_machine, list_machines, get_machine, update_machine, archive_machine
)

router = APIRouter(tags=["Machines"])

class CreateMachineRequest(BaseModel):
    asset_tag: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    category_code: str = Field(..., min_length=1, max_length=50)
    plant_id: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    install_date: Optional[datetime] = None
    rated_parameters: Optional[Dict[str, Any]] = None

class UpdateMachineRequest(BaseModel):
    name: Optional[str] = None
    category_code: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    install_date: Optional[datetime] = None
    rated_parameters: Optional[Dict[str, Any]] = None

@router.post("/machines", status_code=status.HTTP_201_CREATED)
def create_new_machine(
    req: CreateMachineRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a machine in the tenant registry (AC-MM-1). Defaults plant_id to default plant."""
    machine = create_machine(
        db=db,
        org_id=current_user.organisation_id,
        asset_tag=req.asset_tag,
        name=req.name,
        category_code=req.category_code,
        plant_id=req.plant_id,
        manufacturer=req.manufacturer,
        model_number=req.model_number,
        serial_number=req.serial_number,
        install_date=req.install_date,
        rated_parameters=req.rated_parameters
    )
    return {
        "id": machine.id,
        "asset_tag": machine.asset_tag,
        "name": machine.name,
        "category_code": machine.category_code,
        "plant_id": machine.plant_id,
        "created_at": machine.created_at.isoformat()
    }

@router.get("/machines", status_code=status.HTTP_200_OK)
def get_all_machines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all machines for the tenant organisation."""
    machines = list_machines(db, current_user.organisation_id)
    return [
        {
            "id": m.id,
            "asset_tag": m.asset_tag,
            "name": m.name,
            "category_code": m.category_code,
            "plant_id": m.plant_id,
            "archived_at": m.archived_at.isoformat() if m.archived_at else None,
            "created_at": m.created_at.isoformat()
        }
        for m in machines
    ]

@router.get("/machines/{id}", status_code=status.HTTP_200_OK)
def get_machine_details(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gets details of a single machine. Returns 404 if out-of-tenant (AC-ORG-2)."""
    m = get_machine(db, current_user.organisation_id, id)
    return {
        "id": m.id,
        "asset_tag": m.asset_tag,
        "name": m.name,
        "category_code": m.category_code,
        "plant_id": m.plant_id,
        "manufacturer": m.manufacturer,
        "model_number": m.model_number,
        "serial_number": m.serial_number,
        "install_date": m.install_date.isoformat() if m.install_date else None,
        "rated_parameters": m.rated_parameters,
        "archived_at": m.archived_at.isoformat() if m.archived_at else None,
        "created_at": m.created_at.isoformat()
    }

@router.patch("/machines/{id}", status_code=status.HTTP_200_OK)
def patch_machine(
    id: str,
    req: UpdateMachineRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates machine details."""
    updates = req.model_dump(exclude_unset=True)
    # name is NOT NULL; ignore explicit nulls instead of causing a 500 IntegrityError
    if updates.get("name") is None:
        updates.pop("name", None)
    if updates.get("category_code") is None:
        updates.pop("category_code", None)
    m = update_machine(db, current_user.organisation_id, id, updates)
    return {"message": "Machine updated successfully.", "id": m.id}

@router.post("/machines/{id}/archive", status_code=status.HTTP_200_OK)
def archive_machine_endpoint(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archives machine. Archived machines reject new dataset creations (AC-MM-2)."""
    m = archive_machine(db, current_user.organisation_id, id)
    return {"message": "Machine archived successfully.", "id": m.id, "archived_at": m.archived_at.isoformat()}

@router.get("/machine-categories", status_code=status.HTTP_200_OK)
def get_categories(db: Session = Depends(get_db)):
    """Returns global machine categories with eligible dataset types and pipeline profiles (PRD §8.2.2)."""
    cats = db.query(MachineCategory).all()
    return [
        {
            "code": c.code,
            "name": c.name,
            "eligible_dataset_types": c.eligible_dataset_types,
            "eligible_profiles": c.eligible_profiles
        }
        for c in cats
    ]

