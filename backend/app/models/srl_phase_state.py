from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel


class SRLPhaseStateRecord(BaseModel):
    __tablename__ = "srl_phase_states"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    current_phase: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    phase_started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    previous_phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transition_evidence_ids: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="default")

