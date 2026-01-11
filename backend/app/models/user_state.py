"""
User State Snapshot Models
Phase 1 estimator output.
"""
from sqlalchemy import Column, Boolean, JSON, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class UserStateSnapshot(BaseModel):
    __tablename__ = "user_state_snapshots"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    snapshot_at = Column(DateTime, nullable=False, index=True)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)

    cognitive_load = Column(Float, nullable=False)
    interruptibility = Column(Float, nullable=False)
    strain_index = Column(Float, nullable=False)
    focus_mode = Column(Boolean, default=False, nullable=False)
    sprint_mode = Column(Boolean, default=False, nullable=False)

    knowledge_state = Column(JSON, nullable=True)
    time_context = Column(JSON, nullable=True)
    derived_event_ids = Column(JSON, nullable=True)

    user = relationship("User", backref="state_snapshots")
