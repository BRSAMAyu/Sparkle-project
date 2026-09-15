"""Community strategy outcome tracking — COM-012 / GAP-P4-11.

Records when a user accepts, rejects, or dismisses a community-derived strategy
recommendation (CommunityDirective), closing the feedback loop.
"""

from __future__ import annotations

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class CommunityStrategyOutcome(BaseModel):
    __tablename__ = "community_strategy_outcomes"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    directive_id = Column(String(128), nullable=False, index=True)
    trigger_type = Column(
        String(64), nullable=False, index=True,
        comment="What triggered this: cohort_mistake, partner_feedback, resource_recommendation, accountability_checkin",
    )
    decision = Column(
        String(32), nullable=False,
        comment="User choice: accepted, rejected, dismissed, modified, auto_expired",
    )
    context_snapshot = Column(
        JSONBCompat, nullable=False, server_default="{}",
        comment="Snapshot of the directive payload at decision time",
    )
    time_to_decision_seconds = Column(Integer, nullable=True)
    user_feedback = Column(Text, nullable=True)
    source = Column(
        String(32), nullable=False, default="system",
        comment="How the decision was recorded: user_action, timeout, system",
    )

    __table_args__ = (
        Index("ix_cso_user_trigger", "user_id", "trigger_type"),
        Index("ix_cso_user_decision", "user_id", "decision"),
        Index("ix_cso_directive", "directive_id"),
    )
