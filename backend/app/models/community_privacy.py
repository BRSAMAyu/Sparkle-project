"""Persistent privacy-preserving community aggregate models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String

from app.models.base import BaseModel


class CommunityAggregateSignal(BaseModel):
    """Differentially private aggregate that is safe to cross user boundaries."""

    __tablename__ = "community_aggregate_signals"

    cohort_key = Column(String(160), nullable=False, index=True)
    cohort_type = Column(String(64), nullable=False, index=True)
    cohort_criteria = Column(JSON, nullable=False, default=dict)
    stat_name = Column(String(96), nullable=False, index=True)
    privacy_tier = Column(String(32), nullable=False, index=True)
    cohort_size = Column(Integer, nullable=False, default=0)
    min_cohort_size = Column(Integer, nullable=False, default=5)
    noised_value = Column(Float, nullable=True)
    noise_std = Column(Float, nullable=False, default=0.0)
    confidence_interval = Column(JSON, nullable=False, default=list)
    pattern = Column(JSON, nullable=False, default=dict)
    directive_payload = Column(JSON, nullable=False, default=dict)
    source_window_start = Column(DateTime, nullable=True)
    source_window_end = Column(DateTime, nullable=True)
    epsilon_spent = Column(Float, nullable=False, default=0.0)
    generated_by = Column(String(64), nullable=False, default="privacy_community_engine")
    policy_bias_only = Column(Boolean, nullable=False, default=True)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class PrivacyBudgetLedger(BaseModel):
    """Append-only epsilon spend ledger for privacy-preserving aggregate queries."""

    __tablename__ = "privacy_budget_ledger"

    requester_user_id = Column(String(128), nullable=True, index=True)
    budget_subject = Column(String(160), nullable=False, index=True)
    query_type = Column(String(64), nullable=False, index=True)
    epsilon_spent = Column(Float, nullable=False, default=0.0)
    epsilon_remaining = Column(Float, nullable=False, default=0.0)
    max_epsilon = Column(Float, nullable=False, default=10.0)
    status = Column(String(24), nullable=False, default="accepted", index=True)
    denial_reason = Column(String(160), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)


Index(
    "idx_community_aggregate_latest",
    CommunityAggregateSignal.cohort_type,
    CommunityAggregateSignal.stat_name,
    CommunityAggregateSignal.generated_at,
)
Index(
    "idx_privacy_budget_subject_status",
    PrivacyBudgetLedger.budget_subject,
    PrivacyBudgetLedger.status,
    PrivacyBudgetLedger.created_at,
)
