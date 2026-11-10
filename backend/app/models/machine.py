"""
Machine and Machine Category Models (PRD v1.2 §8.2, §12.2)
Includes MachineCategory (Global) and Machine (Tenant-scoped).
Pure software predictive maintenance: strictly no IoT, MQTT, device, or hardware streaming fields.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class MachineCategory(Base):
    """Global reference table of machine categories (PRD v1.2 §8.2.2)."""
    __tablename__ = "machine_categories"

    code = Column(String(50), primary_key=True)  # GENERAL_MACHINE_TOOL, TURBOFAN_ENGINE, etc.
    name = Column(String(255), nullable=False)
    eligible_dataset_types = Column(JSON, nullable=False, default=list)
    eligible_profiles = Column(JSON, nullable=False, default=list)

    machines = relationship("Machine", back_populates="category")

class Machine(Base):
    """Tenant-scoped machine registry (PRD v1.2 §8.2.2, AC-MM-1..3)."""
    __tablename__ = "machines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    plant_id = Column(String(36), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True)
    asset_tag = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    category_code = Column(String(50), ForeignKey("machine_categories.code", ondelete="RESTRICT"), nullable=False)
    manufacturer = Column(String(255), nullable=True)
    model_number = Column(String(255), nullable=True)
    serial_number = Column(String(255), nullable=True)
    install_date = Column(DateTime, nullable=True)
    rated_parameters = Column(JSON, default=dict)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    plant = relationship("Plant", back_populates="machines")
    category = relationship("MachineCategory", back_populates="machines")
    datasets = relationship("Dataset", back_populates="machine", cascade="all, delete-orphan")
    analyses = relationship("AnalysisResult", back_populates="machine")

    __table_args__ = (
        UniqueConstraint("organisation_id", "asset_tag", name="uq_machine_org_asset_tag"),
    )

