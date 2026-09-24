from typing import Any

from sqlalchemy import JSON, Float, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ContextPackRun(BaseModel):
    __tablename__ = "context_pack_runs"

    user_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    intent: Mapped[str] = mapped_column(String(30), nullable=False)
    budgets: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    token_usage: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    memory_counts: Mapped[Any] = mapped_column(JSONBCompat, nullable=False)
    evidence_score_avg: Mapped[float] = mapped_column(Float, nullable=True)
    response_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    request_id: Mapped[str] = mapped_column(String(100), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=True)


Index("idx_context_pack_runs_user_created", ContextPackRun.user_id, ContextPackRun.created_at)
Index("idx_context_pack_runs_intent", ContextPackRun.intent)


class ContextBudgetProfile(BaseModel):
    __tablename__ = "context_budget_profiles"

    intent: Mapped[str] = mapped_column(String(30), nullable=False)
    bucket: Mapped[str] = mapped_column(String(30), nullable=False)
    multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


Index("idx_context_budget_profiles_intent", ContextBudgetProfile.intent)
UniqueConstraint("intent", "bucket", name="uq_context_budget_profiles_intent_bucket")


class ContextPackFeedback(BaseModel):
    __tablename__ = "context_pack_feedback"

    pack_run_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reasons: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)

