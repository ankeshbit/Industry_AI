"""
Dataset and Versioning Models (PRD v1.2 §8.3, §12.2)
Includes Dataset, DatasetVersion, DatasetColumn, ColumnMapping, ValidationReport, DatasetEvent.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Integer, Float, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Dataset(Base):
    """Tenant-scoped dataset collection attached to a machine (PRD v1.2 §8.3, AC-DS-1..10)."""
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    machine_id = Column(String(36), ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dataset_type = Column(String(50), nullable=False, default="TABULAR_OPERATING_STATE")
    type_confirmed_by = Column(String(36), nullable=True)
    type_confirmed_at = Column(DateTime, nullable=True)
    objective = Column(String(100), default="FAILURE_PROBABILITY_CURRENT_STATE")
    provenance = Column(String(50), nullable=False, default="CUSTOMER")  # CUSTOMER, SIMULATED, PUBLIC_SAMPLE
    status = Column(String(50), nullable=False, default="ACTIVE")        # ACTIVE, PENDING_DELETION, DELETED
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    machine = relationship("Machine", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organisation_id", "machine_id", "name", name="uq_dataset_org_machine_name"),
    )

class DatasetVersion(Base):
    """Immutable version of an uploaded dataset (PRD v1.2 §8.3.4, §8.3.7, AC-DS-6)."""
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    derived_from_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True)
    derivation_recipe = Column(JSON, nullable=True)
    file_kind = Column(String(20), nullable=False, default="CSV")  # CSV only in MS1
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False, unique=True)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    scan_status = Column(String(30), nullable=False, default="CLEAN")  # PENDING, CLEAN, INFECTED, ERROR
    status = Column(String(50), nullable=False, default="UPLOADED")   # UPLOADING, UPLOADED, VALIDATING, VALIDATED, VALIDATION_FAILED, PENDING_DELETION, PURGED
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    uploaded_by = Column(String(36), nullable=True)
    retain_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="versions")
    columns = relationship("DatasetColumn", back_populates="dataset_version", cascade="all, delete-orphan")
    mappings = relationship("ColumnMapping", back_populates="dataset_version", cascade="all, delete-orphan")
    validation_reports = relationship("ValidationReport", back_populates="dataset_version", cascade="all, delete-orphan")
    events = relationship("DatasetEvent", back_populates="dataset_version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("dataset_id", "version_no", name="uq_dataset_version_no"),
    )

class DatasetColumn(Base):
    """Schema descriptor for a single column in a dataset version."""
    __tablename__ = "dataset_columns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    inferred_type = Column(String(50), nullable=False)  # numeric, categorical, datetime, text
    stats = Column(JSON, default=dict)

    dataset_version = relationship("DatasetVersion", back_populates="columns")

class ColumnMapping(Base):
    """Explicit mapping between customer columns and a profile's canonical features (PRD v1.2 §8.3.6)."""
    __tablename__ = "column_mappings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(String(100), nullable=False)
    mapping_version = Column(Integer, nullable=False, default=1)
    mappings = Column(JSON, nullable=False)  # canonical_feature -> {column, unit, conversion, asserted_equivalence}
    options = Column(JSON, default=dict)     # missing_policy, etc.
    confirmed_by = Column(String(36), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    mapping_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset_version = relationship("DatasetVersion", back_populates="mappings")

    __table_args__ = (
        UniqueConstraint("dataset_version_id", "profile_id", "mapping_version", name="uq_version_profile_mapping"),
    )

class ValidationReport(Base):
    """Immutable validation and quality report for a dataset version (PRD v1.2 §8.3.5)."""
    __tablename__ = "validation_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    mapping_id = Column(String(36), ForeignKey("column_mappings.id", ondelete="SET NULL"), nullable=True)
    validator_version = Column(String(50), nullable=False, default="1.0.0")
    quality_score = Column(Float, nullable=False)  # 0 to 100
    quality_components = Column(JSON, nullable=False)  # S_complete, S_valid, S_unique, S_consistent, S_outlier
    checks = Column(JSON, nullable=False)  # list of check findings
    preview = Column(JSON, nullable=True)  # first N rows
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset_version = relationship("DatasetVersion", back_populates="validation_reports")

class DatasetEvent(Base):
    """Append-only audit trail of dataset lifecycle events."""
    __tablename__ = "dataset_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # UPLOADED, VALIDATED, MAPPED, DERIVED, DELETED
    actor_id = Column(String(36), nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    dataset_version = relationship("DatasetVersion", back_populates="events")
