"""
User State Snapshot Models
Phase 1 estimator output.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class UserStateSnapshot(BaseModel):
    __tablename__ = "user_state_snapshots"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    cognitive_load: Mapped[float] = mapped_column(Float, nullable=False)
    interruptibility: Mapped[float] = mapped_column(Float, nullable=False)
    strain_index: Mapped[float] = mapped_column(Float, nullable=False)
    focus_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sprint_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    knowledge_state: Mapped[Any] = mapped_column(JSON, nullable=True)
    time_context: Mapped[Any] = mapped_column(JSON, nullable=True)
    derived_event_ids: Mapped[Any] = mapped_column(JSON, nullable=True)

    user = relationship("User", backref="state_snapshots")
