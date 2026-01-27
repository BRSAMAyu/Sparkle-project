"""
Review system persistence models.
审查系统持久化模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.models.base import BaseModel, GUID


class ReviewHistory(BaseModel):
    __tablename__ = "review_history"

    review_id = Column(String(64), nullable=False, unique=True, index=True)
    target_id = Column(String(128), nullable=False, index=True)
    target_type = Column(String(50), nullable=False, index=True)
    user_id = Column(GUID(), nullable=True, index=True)
    session_id = Column(String(128), nullable=True, index=True)

    decision = Column(String(32), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, default=0.0)
    metrics = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    issues_count = Column(Integer, nullable=False, default=0)
    critical_count = Column(Integer, nullable=False, default=0)
    warning_count = Column(Integer, nullable=False, default=0)

    reflection_round = Column(Integer, nullable=False, default=0)
    reflection_outcome = Column(String(64), nullable=True)
    score_delta = Column(Float, nullable=False, default=0.0)

    user_feedback = Column(String(64), nullable=True)
    user_satisfied = Column(Boolean, nullable=True)
    feedback_timestamp = Column(DateTime, nullable=True)

    reviewer_model = Column(String(100), nullable=True)
    review_duration_ms = Column(Integer, nullable=False, default=0)
    requires_reflection = Column(Boolean, nullable=False, default=False)

    user_query = Column(Text, nullable=True)
    content_snapshot = Column(Text, nullable=True)


class ReviewFeedback(BaseModel):
    __tablename__ = "review_feedback"

    feedback_id = Column(String(64), nullable=False, unique=True, index=True)
    review_id = Column(String(64), nullable=False, index=True)
    user_id = Column(GUID(), nullable=True, index=True)
    feedback_type = Column(String(32), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    issues_reported = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    original_score = Column(Float, nullable=False, default=0.0)
    original_decision = Column(String(32), nullable=True)
    was_reflected = Column(Boolean, nullable=False, default=False)

    was_helpful = Column(Boolean, nullable=True)
    was_accurate = Column(Boolean, nullable=True)
    inaccurate_points = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    specificity_level = Column(String(32), nullable=True)
    tags = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)


class ReviewOverride(BaseModel):
    __tablename__ = "review_overrides"

    override_id = Column(String(64), nullable=False, unique=True, index=True)
    review_id = Column(String(64), nullable=False, index=True)
    user_id = Column(GUID(), nullable=True, index=True)

    original_decision = Column(String(32), nullable=False)
    new_decision = Column(String(32), nullable=False)
    override_type = Column(String(64), nullable=False)
    reason = Column(Text, nullable=True)

    was_correct = Column(Boolean, nullable=True)
    admin_reviewed = Column(Boolean, nullable=False, default=False)


class ReviewAppeal(BaseModel):
    __tablename__ = "appeals"

    appeal_id = Column(String(64), nullable=False, unique=True, index=True)
    review_id = Column(String(64), nullable=False, index=True)
    user_id = Column(GUID(), nullable=True, index=True)

    appeal_reason = Column(Text, nullable=False)
    issues_with_review = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    status = Column(String(32), nullable=False, default="pending", index=True)
    assigned_to = Column(String(64), nullable=True)

    secondary_review_id = Column(String(64), nullable=True)
    secondary_decision = Column(String(32), nullable=True)
    secondary_score = Column(Float, nullable=True)

    resolution = Column(Text, nullable=True)
    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class ArbitrationCase(BaseModel):
    __tablename__ = "arbitration_cases"

    case_id = Column(String(64), nullable=False, unique=True, index=True)
    appeal_id = Column(String(64), nullable=False, index=True)
    review_id = Column(String(64), nullable=False, index=True)
    user_id = Column(GUID(), nullable=True, index=True)

    escalation_reason = Column(String(64), nullable=False, index=True)
    priority = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)

    assigned_to = Column(String(64), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    original_review_score = Column(Float, nullable=False, default=0.0)
    secondary_review_score = Column(Float, nullable=True)
    score_discrepancy = Column(Float, nullable=False, default=0.0)

    resolution = Column(Text, nullable=True)
    final_decision = Column(String(32), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(64), nullable=True)

    notes = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    evidence = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)


class ArbitrationDecision(BaseModel):
    __tablename__ = "arbitration_decisions"

    case_id = Column(String(64), nullable=False, index=True)
    decision = Column(String(32), nullable=False)
    explanation = Column(Text, nullable=False)
    arbitrator_id = Column(String(64), nullable=False)
    arbitrator_role = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    feedback_for_model = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=False, default=datetime.utcnow)
