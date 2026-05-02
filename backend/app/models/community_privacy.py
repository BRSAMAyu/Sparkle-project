from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String

from app.aurora.runtime_v1.models import JSONBCompat
from app.models.base import BaseModel


class CommunityAggregateSignal(BaseModel):
    """Durable, privacy-safe cohort signal.

    The row stores only anonymized aggregate output. Raw member values and raw
    contributor identities must never be persisted here.
    """

    __tablename__ = "community_aggregate_signals"

    signal_id = Column(String(128), nullable=False, unique=True, index=True)
    cohort_id = Column(String(128), nullable=False, index=True)
    cohort_key = Column(String(256), nullable=False, index=True)
    cohort_criteria = Column(JSONBCompat, nullable=False, default=dict)
    signal_type = Column(String(64), nullable=False, index=True)
    stat_name = Column(String(128), nullable=False, index=True)
    cohort_size = Column(Integer, nullable=False, default=0)
    min_cohort_size = Column(Integer, nullable=False, default=5)
    privacy_tier = Column(String(32), nullable=False, default="suppressed", index=True)
    value = Column(Float, nullable=True)
    noise_std = Column(Float, nullable=False, default=0.0)
    confidence_interval = Column(JSONBCompat, nullable=False, default=list)
    pattern = Column(JSONBCompat, nullable=False, default=dict)
    observation = Column(JSONBCompat, nullable=False, default=dict)
    privacy_cost = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="candidate", index=True)
    generated_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_community_aggregate_cohort_stat", "cohort_key", "stat_name", "generated_at"),
        Index("idx_community_aggregate_status_generated", "status", "generated_at"),
    )


class PrivacyBudgetLedger(BaseModel):
    """Persistent differential-privacy budget spending ledger."""

    __tablename__ = "privacy_budget_ledger"

    subject_id = Column(String(128), nullable=False, index=True)
    subject_type = Column(String(32), nullable=False, default="user", index=True)
    query_type = Column(String(64), nullable=False, index=True)
    epsilon_spent = Column(Float, nullable=False, default=0.0)
    max_epsilon = Column(Float, nullable=False, default=3.0)
    remaining_epsilon = Column(Float, nullable=False, default=3.0)
    window_key = Column(String(64), nullable=False, index=True)
    allowed = Column(Boolean, nullable=False, default=True, index=True)
    denial_reason = Column(String(128), nullable=False, default="")
    spent_at = Column(DateTime, nullable=False, index=True)
    runtime_metadata = Column("metadata", JSONBCompat, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_privacy_budget_subject_window", "subject_id", "window_key", "query_type"),
        Index("idx_privacy_budget_allowed_spent", "allowed", "spent_at"),
    )
