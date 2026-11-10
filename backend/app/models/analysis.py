"""
Analysis Results Model (PRD v1.2 §8.6, §12.2, AC-FP-1..8, AC-AP-1..5)
Stores immutable failure prediction results with complete provenance, trust panel metadata, and OOD flags.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Boolean, Integer, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class AnalysisResult(Base):
    """Immutable failure prediction analysis result (PRD v1.2 §8.6, §12.2)."""
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    machine_id = Column(String(36), ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id = Column(String(36), ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=True, unique=True)
    compatibility_check_id = Column(String(36), ForeignKey("compatibility_checks.id", ondelete="RESTRICT"), nullable=False)
    profile_uuid = Column(String(36), ForeignKey("pipeline_profiles.id", ondelete="RESTRICT"), nullable=False)
    configuration = Column(String(50), nullable=False)  # NO_TYPE, WITH_TYPE
    model_version_id = Column(String(36), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=True)
    pipeline = Column(String(10), nullable=False, default="A")
    result_version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, default=True, nullable=False)
    
    # Trust panel fields (PRD v1.2 §4.4, §8.4.6, AC-AP-3, AC-AP-4)
    training_domain = Column(String(50), nullable=False, default="REFERENCE_DATASET")
    applicability_level = Column(String(50), nullable=False)  # IN_REFERENCE_RANGE, PARTLY_OUTSIDE_REFERENCE_RANGE
    reliability_tier = Column(String(50), nullable=False, default="REFERENCE_ONLY")  # strictly REFERENCE_ONLY in MS1
    
    ood_summary = Column(JSON, nullable=False, default=dict)
    summary = Column(JSON, nullable=False, default=dict)       # total_rows, predicted_failures, mean_probability, risk_distribution
    top_rows = Column(JSON, nullable=False, default=list)      # top highest-risk rows with probabilities and features
    artifact_uri = Column(String(500), nullable=True)
    explanation_meta = Column(JSON, nullable=True)
    limitations = Column(JSON, nullable=False, default=list)   # copied directly from model card
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    machine = relationship("Machine", back_populates="analyses")

    __table_args__ = (
        UniqueConstraint("machine_id", "dataset_version_id", "profile_uuid", "result_version", name="uq_analysis_version"),
    )

