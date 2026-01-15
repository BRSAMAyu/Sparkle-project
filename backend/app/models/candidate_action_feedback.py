"""
Candidate Action Feedback Model

Tracks user feedback on predicted candidate actions for learning loop.
Enables daily analysis to calibrate signal thresholds and improve predictions.
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, GUID


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

    id = Column(GUID, primary_key=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(String(64), nullable=False)  # "ca_timestamp"
    action_type = Column(String(32), nullable=False)  # "break", "review", "clarify", "plan_split"
    feedback_type = Column(String(16), nullable=False)  # "accept", "ignore", "dismiss"
    executed = Column(Boolean, nullable=False, default=False)  # Was action actually executed
    completion_result = Column(JSONB, nullable=True)  # Result of executed action (if any)
    context_snapshot = Column(JSONB, nullable=False)  # ContextEnvelope at time of feedback
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

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
