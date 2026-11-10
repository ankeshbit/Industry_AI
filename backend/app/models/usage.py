"""
Usage Event Model (PRD v1.2 §8.11, §12.2, line 2601)
Append-only log of tenant usage events recorded starting in MS1.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, JSON, Integer
)
from backend.app.database import Base

class UsageEvent(Base):
    """Append-only tenant usage event (PRD v1.2 line 2601)."""
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # DATASET_UPLOAD, ANALYSIS_EXECUTION, etc.
    quantity = Column(Integer, nullable=False, default=1)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

