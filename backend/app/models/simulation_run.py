from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class SimulationRun(BaseModel):
    __tablename__ = "simulation_runs"

    session_id = Column(String(128), nullable=False)
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_key = Column(String(64), nullable=False, index=True)
    topic = Column(Text, nullable=False)
    state = Column(String(32), nullable=False, index=True)
    payload = Column(JSONBCompat, nullable=False, default=dict)
    insight_summary = Column(Text, nullable=True)
    last_active_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_simulation_runs_session_id", "session_id", unique=True),
        Index("ix_simulation_runs_user_last_active", "user_id", "last_active_at"),
    )

    user = relationship("User")
