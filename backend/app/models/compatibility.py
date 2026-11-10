"""
Compatibility, Applicability, and Reliability Models (PRD v1.2 §8.4, §12.2)
Includes PipelineProfile (Global), CompatibilityCheck (Tenant), WarningAcknowledgement, and LimitationAcknowledgement.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Boolean, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class PipelineProfile(Base):
    """Global configuration profile for an ML pipeline and feature schema (PRD v1.2 §8.4.1)."""
    __tablename__ = "pipeline_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    profile_id = Column(String(100), nullable=False)  # ai4i_failure_no_type, ai4i_failure_with_type
    version = Column(String(20), nullable=False, default="1.0.0")
    pipeline = Column(String(10), nullable=False, default="A")  # A, B, C, D, E
    configuration = Column(String(50), nullable=False)           # NO_TYPE, WITH_TYPE
    training_domain = Column(String(50), nullable=False, default="REFERENCE_DATASET")
    document = Column(JSON, nullable=False)                      # Full YAML-spec as JSON
    is_active = Column(Boolean, default=True, nullable=False)

    compatibility_checks = relationship("CompatibilityCheck", back_populates="profile")
    models = relationship("ModelVersion", back_populates="profile")

    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_profile_id_version"),
    )

class CompatibilityCheck(Base):
    """
    Immutable compatibility check binding a dataset version, mapping, and pipeline profile (PRD v1.2 §8.4, AC-CE-1..7).
    This is the ONLY component allowed to authorize an analysis job.
    """
    __tablename__ = "compatibility_checks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    machine_id = Column(String(36), ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True)
    mapping_id = Column(String(36), ForeignKey("column_mappings.id", ondelete="SET NULL"), nullable=True)
    profile_uuid = Column(String(36), ForeignKey("pipeline_profiles.id", ondelete="RESTRICT"), nullable=False)
    
    # Stage 1: Dataset compatibility
    status = Column(String(50), nullable=False)  # COMPATIBLE, COMPATIBLE_WITH_WARNINGS, INCOMPATIBLE, INSUFFICIENT_DATA, UNSUPPORTED_FORMAT
    reasons = Column(JSON, nullable=False, default=list)  # list of {code, severity, feature, observed, expected, message, remedy}
    
    # Stage 2: Model applicability
    applicability_level = Column(String(50), nullable=False, default="NOT_ASSESSED")  # IN_REFERENCE_RANGE, PARTLY_OUTSIDE_REFERENCE_RANGE, MOSTLY_OUTSIDE_REFERENCE_RANGE, NOT_ASSESSED
    applicability_detail = Column(JSON, default=dict)
    
    # Stage 3: Model reliability
    reliability_tier = Column(String(50), nullable=False, default="REFERENCE_ONLY")  # REFERENCE_ONLY, CUSTOMER_VALIDATED, NOT_APPLICABLE
    reliability_basis = Column(JSON, default=dict)
    
    inputs_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("PipelineProfile", back_populates="compatibility_checks")
    warning_acknowledgements = relationship("WarningAcknowledgement", back_populates="compatibility_check", cascade="all, delete-orphan")

class WarningAcknowledgement(Base):
    """Explicit user acknowledgement of a warning code on a compatibility check (PRD v1.2 §8.4.7, AC-CE-4)."""
    __tablename__ = "warning_acknowledgements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    compatibility_check_id = Column(String(36), ForeignKey("compatibility_checks.id", ondelete="CASCADE"), nullable=False, index=True)
    reason_code = Column(String(50), nullable=False)
    acknowledged_by = Column(String(36), nullable=True)
    acknowledged_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    compatibility_check = relationship("CompatibilityCheck", back_populates="warning_acknowledgements")

class LimitationAcknowledgement(Base):
    """
    Explicit user acknowledgement of reference-dataset model limitations (PRD v1.2 §8.4.7, AC-AP-5).
    Statement: 'This is a reference-dataset-trained model. It has not been validated on your equipment. Results are advisory.'
    """
    __tablename__ = "limitation_acknowledgements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    machine_id = Column(String(36), ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True)
    profile_uuid = Column(String(36), ForeignKey("pipeline_profiles.id", ondelete="RESTRICT"), nullable=False)
    model_version_id = Column(String(36), nullable=True)
    statement_version = Column(String(20), nullable=False, default="1.0.0")
    acknowledged_by = Column(String(36), nullable=True)
    acknowledged_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("machine_id", "profile_uuid", "model_version_id", "statement_version", name="uq_limitation_ack"),
    )
