"""
Model Registry and Evaluation Metadata Models (PRD v1.2 §10.1, §12.2)
Includes ModelVersion (Global) and ModelEvaluation (Global).
Maintains strict separation between REFERENCE_DATASET and CUSTOMER_SPECIFIC evaluations.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Boolean, Float, Integer, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class ModelVersion(Base):
    """Global registered model artifact metadata (PRD v1.2 §10.1, §12.2)."""
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    registry_name = Column(String(100), nullable=False, index=True)  # ai4i_failure_clf_notype, ai4i_failure_clf_typed
    version = Column(String(20), nullable=False)                     # 1.0.0
    mlflow_run_id = Column(String(100), nullable=True)
    experiment_id = Column(String(100), nullable=True)
    pipeline = Column(String(10), nullable=False, default="A")
    configuration = Column(String(50), nullable=False)               # NO_TYPE, WITH_TYPE
    task = Column(String(50), nullable=False, default="BINARY_CLASSIFICATION")
    algorithm = Column(String(50), nullable=False)                   # XGBoost, LogisticRegression, etc.
    stage = Column(String(30), nullable=False, default="PRODUCTION") # STAGING, PRODUCTION, ARCHIVED
    profile_uuid = Column(String(36), ForeignKey("pipeline_profiles.id", ondelete="RESTRICT"), nullable=False)
    training_domain = Column(String(50), nullable=False, default="REFERENCE_DATASET")
    model_scope = Column(String(30), nullable=False, default="SHARED") # SHARED, TENANT_PRIVATE
    default_when_both_runnable = Column(Boolean, default=False, nullable=False)
    reference_ranges_uri = Column(String(500), nullable=True)
    thresholds = Column(JSON, default=dict)
    dataset_hash = Column(String(64), nullable=True)
    model_card_uri = Column(String(500), nullable=True)
    promoted_by = Column(String(36), nullable=True)
    promoted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("PipelineProfile", back_populates="models")
    evaluations = relationship("ModelEvaluation", back_populates="model", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("registry_name", "version", name="uq_model_registry_version"),
    )

class ModelEvaluation(Base):
    """Immutable evaluation metrics partitioned strictly by evaluation_kind (PRD v1.2 §12.2, AC-AP-6)."""
    __tablename__ = "model_evaluations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_version_id = Column(String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_kind = Column(String(50), nullable=False)  # REFERENCE_DATASET, CUSTOMER_SPECIFIC
    split = Column(String(50), nullable=False)            # test, validation_cv
    metric_name = Column(String(50), nullable=False)      # PR-AUC, ROC-AUC, Recall, Precision, etc.
    metric_value = Column(Float, nullable=False)
    ci_low = Column(Float, nullable=True)
    ci_high = Column(Float, nullable=True)
    n_samples = Column(Integer, nullable=False)
    subset = Column(String(50), nullable=True)
    paired_comparison_ref = Column(String(100), nullable=True)

    model = relationship("ModelVersion", back_populates="evaluations")

