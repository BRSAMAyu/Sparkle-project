"""
Review system persistence models.
审查系统持久化模型
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import GUID, BaseModel


class ReviewHistory(BaseModel):
    __tablename__ = "review_history"

    review_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)

    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metrics: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    issues_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    reflection_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reflection_outcome: Mapped[str] = mapped_column(String(64), nullable=True)
    score_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    user_feedback: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_satisfied: Mapped[bool] = mapped_column(Boolean, nullable=True)
    feedback_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    reviewer_model: Mapped[str] = mapped_column(String(100), nullable=True)
    review_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_reflection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user_query: Mapped[str] = mapped_column(Text, nullable=True)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=True)


class ReviewFeedback(BaseModel):
    __tablename__ = "review_feedback"

    feedback_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    review_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues_reported: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    original_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    original_decision: Mapped[str] = mapped_column(String(32), nullable=True)
    was_reflected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    was_helpful: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_accurate: Mapped[bool] = mapped_column(Boolean, nullable=True)
    inaccurate_points: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    specificity_level: Mapped[str] = mapped_column(String(32), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)


class ReviewOverride(BaseModel):
    __tablename__ = "review_overrides"

    override_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    review_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)

    original_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    new_decision: Mapped[str] = mapped_column(String(32), nullable=False)
    override_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    admin_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ReviewAppeal(BaseModel):
    __tablename__ = "appeals"

    appeal_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    review_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)

    appeal_reason: Mapped[str] = mapped_column(Text, nullable=False)
    issues_with_review: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    assigned_to: Mapped[str] = mapped_column(String(64), nullable=True)

    secondary_review_id: Mapped[str] = mapped_column(String(64), nullable=True)
    secondary_decision: Mapped[str] = mapped_column(String(32), nullable=True)
    secondary_score: Mapped[float] = mapped_column(Float, nullable=True)

    resolution: Mapped[str] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ArbitrationCase(BaseModel):
    __tablename__ = "arbitration_cases"

    case_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    appeal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    review_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)

    escalation_reason: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)

    assigned_to: Mapped[str] = mapped_column(String(64), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    original_review_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    secondary_review_score: Mapped[float] = mapped_column(Float, nullable=True)
    score_discrepancy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    resolution: Mapped[str] = mapped_column(Text, nullable=True)
    final_decision: Mapped[str] = mapped_column(String(32), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(64), nullable=True)

    notes: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    evidence: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)


class ArbitrationDecision(BaseModel):
    __tablename__ = "arbitration_decisions"

    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    arbitrator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    arbitrator_role: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    feedback_for_model: Mapped[str] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
