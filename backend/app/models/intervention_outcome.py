"""Intervention outcome tracking model."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel, _utcnow


class InterventionOutcome(BaseModel):
    __tablename__ = "intervention_outcomes"

    id: Mapped[Any] = mapped_column(GUID(), primary_key=True, default=uuid4, nullable=False)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    plan_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    task_id: Mapped[Any] = mapped_column(GUID(), nullable=True)

    intervention_type: Mapped[str] = mapped_column(String(64), nullable=True)
    trigger_reason: Mapped[str] = mapped_column(String(128), nullable=True)
    target_concept: Mapped[str] = mapped_column(String(256), nullable=True)
    target_node_id: Mapped[Any] = mapped_column(GUID(), nullable=True)

    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    follow_up_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    outcome_checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    outcome_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=True)

    mastery_before: Mapped[float] = mapped_column(Float, nullable=True)
    mastery_after: Mapped[float] = mapped_column(Float, nullable=True)
    effective: Mapped[bool] = mapped_column(Boolean, nullable=True)

    user_adopted: Mapped[bool] = mapped_column(Boolean, nullable=True)
    adopted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
