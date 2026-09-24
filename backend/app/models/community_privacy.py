from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.aurora.runtime_v1.models import JSONBCompat
from app.models.base import BaseModel


class CommunityAggregateSignal(BaseModel):
    """Durable, privacy-safe cohort signal.

    The row stores only anonymized aggregate output. Raw member values and raw
    contributor identities must never be persisted here.
    """

    __tablename__ = "community_aggregate_signals"

    signal_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    cohort_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    cohort_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    cohort_criteria: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stat_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    cohort_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_cohort_size: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    privacy_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="suppressed", index=True)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    noise_std: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_interval: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=list)
    pattern: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    observation: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, default=dict)
    privacy_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate", index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    runtime_metadata: Mapped[Any] = mapped_column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_community_aggregate_cohort_stat", "cohort_key", "stat_name", "generated_at"),
        Index("idx_community_aggregate_status_generated", "status", "generated_at"),
    )


class PrivacyBudgetLedger(BaseModel):
    """Persistent differential-privacy budget spending ledger."""

    __tablename__ = "privacy_budget_ledger"

    subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user", index=True)
    query_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    epsilon_spent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_epsilon: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    remaining_epsilon: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    window_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    denial_reason: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    spent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    runtime_metadata: Mapped[Any] = mapped_column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_privacy_budget_subject_window", "subject_id", "window_key", "query_type"),
        Index("idx_privacy_budget_allowed_spent", "allowed", "spent_at"),
    )
