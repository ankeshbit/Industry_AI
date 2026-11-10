"""
Machine Registry Service (PRD v1.2 §8.2, §13.3, AC-MM-1..3)
Handles machine management, asset tag uniqueness per organisation,
default plant association, and archiving.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.machine import Machine, MachineCategory
from backend.app.models.auth import Plant
from backend.app.models.dataset import Dataset

def create_machine(
    db: Session,
    org_id: str,
    asset_tag: str,
    name: str,
    category_code: str,
    plant_id: Optional[str] = None,
    manufacturer: Optional[str] = None,
    model_number: Optional[str] = None,
    serial_number: Optional[str] = None,
    install_date: Optional[datetime] = None,
    rated_parameters: Optional[dict] = None
) -> Machine:
    """
    Creates a machine registry entry scoped to the tenant organisation (AC-MM-1).
    """
    # 1. Verify category exists
    category = db.query(MachineCategory).filter(MachineCategory.code == category_code).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "INVALID_CATEGORY", "message": f"Machine category '{category_code}' is not supported."}}
        )

    # 2. Check duplicate asset tag within the organisation (AC-MM-1)
    existing_machine = db.query(Machine).filter(
        Machine.organisation_id == org_id,
        Machine.asset_tag == asset_tag
    ).first()
    if existing_machine:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "DUPLICATE_ASSET_TAG", "message": f"Asset tag '{asset_tag}' already exists in this organisation."}}
        )

    # 3. Resolve plant (defaults to default plant per PRD §13.3)
    if not plant_id:
        default_plant = db.query(Plant).filter(
            Plant.organisation_id == org_id,
            Plant.is_default == True
        ).first()
        if not default_plant:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": {"code": "NO_DEFAULT_PLANT", "message": "Organisation lacks a default plant."}}
            )
        plant_id = default_plant.id
    else:
        # Verify plant belongs to this organisation
        plant = db.query(Plant).filter(Plant.id == plant_id, Plant.organisation_id == org_id).first()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "Specified plant not found."}}
            )

    machine = Machine(
        organisation_id=org_id,
        plant_id=plant_id,
        asset_tag=asset_tag,
        name=name,
        category_code=category_code,
        manufacturer=manufacturer,
        model_number=model_number,
        serial_number=serial_number,
        install_date=install_date,
        rated_parameters=rated_parameters or {}
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine

def list_machines(db: Session, org_id: str) -> List[Machine]:
    """Lists all active and archived machines for the tenant."""
    return db.query(Machine).filter(Machine.organisation_id == org_id).all()

def get_machine(db: Session, org_id: str, machine_id: str) -> Machine:
    """Returns machine if owned by tenant; raises 404 otherwise (AC-ORG-2)."""
    machine = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.organisation_id == org_id
    ).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Machine not found."}}
        )
    return machine

def update_machine(
    db: Session,
    org_id: str,
    machine_id: str,
    updates: dict
) -> Machine:
    """Updates machine details. Category cannot be changed if datasets exist (PRD line 1915)."""
    machine = get_machine(db, org_id, machine_id)

    if "category_code" in updates and updates["category_code"] != machine.category_code:
        dataset_count = db.query(Dataset).filter(Dataset.machine_id == machine_id).count()
        if dataset_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "CATEGORY_IMMUTABLE", "message": "Machine category cannot be modified once datasets exist."}}
            )
        # Verify new category
        cat = db.query(MachineCategory).filter(MachineCategory.code == updates["category_code"]).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "INVALID_CATEGORY", "message": "New category code does not exist."}}
            )
        machine.category_code = updates["category_code"]

    for field in ["name", "manufacturer", "model_number", "serial_number", "install_date", "rated_parameters"]:
        if field in updates:
            setattr(machine, field, updates[field])

    db.commit()
    db.refresh(machine)
    return machine

def archive_machine(db: Session, org_id: str, machine_id: str) -> Machine:
    """Archives machine. Archived machines reject new dataset creations (AC-MM-2)."""
    machine = get_machine(db, org_id, machine_id)
    machine.archived_at = datetime.utcnow()
    db.commit()
    db.refresh(machine)
    return machine

