from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class SimulationRun(BaseModel):
    __tablename__ = "simulation_runs"

    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    insight_summary: Mapped[str] = mapped_column(Text, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_simulation_runs_session_id", "session_id", unique=True),
        Index("ix_simulation_runs_user_last_active", "user_id", "last_active_at"),
    )

    user = relationship("User")
