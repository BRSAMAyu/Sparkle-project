"""Intervention outcome tracking model."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, String, Text

from app.models.base import GUID, BaseModel, _utcnow


class InterventionOutcome(BaseModel):
    __tablename__ = "intervention_outcomes"

    id = Column(GUID(), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(GUID(), nullable=False, index=True)
    plan_id = Column(GUID(), nullable=True)
    task_id = Column(GUID(), nullable=True)

    intervention_type = Column(String(64))
    trigger_reason = Column(String(128))
    target_concept = Column(String(256))
    target_node_id = Column(GUID(), nullable=True)

    triggered_at = Column(DateTime, nullable=False)
    follow_up_at = Column(DateTime, nullable=True)
    outcome_checked_at = Column(DateTime, nullable=True)

    outcome_status = Column(String(32), default="pending")

    mastery_before = Column(Float, nullable=True)
    mastery_after = Column(Float, nullable=True)
    effective = Column(Boolean, nullable=True)

    user_adopted = Column(Boolean, nullable=True)
    adopted_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
