from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String

from app.models.base import GUID, BaseModel


class SRLPhaseStateRecord(BaseModel):
    __tablename__ = "srl_phase_states"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    current_phase = Column(String(32), nullable=False, default="UNKNOWN")
    phase_started_at = Column(DateTime, nullable=False)
    previous_phase = Column(String(32), nullable=True)
    transition_evidence_ids = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.0)
    source = Column(String(32), nullable=False, default="default")

