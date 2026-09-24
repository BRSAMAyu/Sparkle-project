"""
Candidate Action Feedback Model

Tracks user feedback on predicted candidate actions for learning loop.
Enables daily analysis to calibrate signal thresholds and improve predictions.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class CandidateActionFeedback(Base):
    """
    User feedback on candidate actions

    Feedback types:
    - accept: User clicked on the candidate action
    - ignore: User saw but didn't interact
    - dismiss: User explicitly dismissed the candidate

    Used by signals_learning_worker for daily CTR/completion analysis.
    """
    __tablename__ = "candidate_action_feedback"

    id: Mapped[Any] = mapped_column(GUID, primary_key=True)
    user_id: Mapped[Any] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False)  # "ca_timestamp"
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "break", "review", "clarify", "plan_split"
    feedback_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "accept", "ignore", "dismiss"
    executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # Was action actually executed
    completion_result: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)  # Result of executed action (if any)
    context_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)  # ContextEnvelope at time of feedback
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="candidate_feedbacks")

    def __repr__(self):
        return (
            f"<CandidateActionFeedback(id={self.id}, user_id={self.user_id}, "
            f"action_type={self.action_type}, feedback_type={self.feedback_type}, "
            f"executed={self.executed})>"
        )

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "candidate_id": self.candidate_id,
            "action_type": self.action_type,
            "feedback_type": self.feedback_type,
            "executed": self.executed,
            "completion_result": self.completion_result,
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
