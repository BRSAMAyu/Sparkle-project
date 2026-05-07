"""Core: execution / Phase: clarify
Stage: Goal ORM Model (P0-7)

Previously goal data was fragmented across MemoryGoal, GoalWorldGraphSnapshot,
Plan, and Redis-only ActiveGoal. This model provides a single source of truth
for goals with minimum_acceptance_criteria — the key missing field from the
Full Vision audit.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class Goal(BaseModel):
    __tablename__ = "goals"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    goal_type = Column(
        String(64), nullable=False, default="general",
        comment="exam | project | job_search | fitness | startup | general",
    )
    description = Column(Text, nullable=True)

    status = Column(
        String(32), nullable=False, default="active",
        comment="draft | active | paused | completed | archived | cancelled",
    )

    # Deadline and progress
    target_date = Column(Date, nullable=True)
    mastery = Column(Float, default=0.0, comment="0-1 mastery level")
    progress = Column(Float, default=0.0, comment="0-1 overall progress")
    priority = Column(
        String(16), default="normal",
        comment="critical | high | normal | low",
    )
    is_primary = Column(Boolean, default=False)

    # Acceptance criteria — the key missing field (GOAL-004 score 0/5 → 5/5)
    minimum_acceptance_criteria = Column(
        JSON, nullable=True,
        comment="List of criteria that must be met for goal completion. "
                "e.g. [{'metric': 'exam_score', 'threshold': 85, 'unit': 'percent'}]",
    )

    # Associations
    domain_pack_id = Column(String(64), nullable=True)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=True)
    source = Column(String(32), nullable=True, comment="exam_sprint | manual | community")
    source_metadata = Column(JSON, nullable=True)

    # Lifecycle timestamps
    completed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    # Additional metadata
    metadata_payload = Column("metadata", JSON, nullable=True)

    user = relationship("User", backref="goals")
    plan = relationship("Plan", foreign_keys=[plan_id])

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "goal_type": self.goal_type,
            "description": self.description,
            "status": self.status,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "mastery": self.mastery,
            "progress": self.progress,
            "priority": self.priority,
            "is_primary": self.is_primary,
            "minimum_acceptance_criteria": self.minimum_acceptance_criteria,
            "domain_pack_id": self.domain_pack_id,
            "plan_id": str(self.plan_id) if self.plan_id else None,
            "source": self.source,
            "source_metadata": self.source_metadata,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "metadata": self.metadata_payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
