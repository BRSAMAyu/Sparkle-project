from sqlalchemy import JSON, Column, Float, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ContextPackRun(BaseModel):
    __tablename__ = "context_pack_runs"

    user_id = Column(GUID(), nullable=False, index=True)
    intent = Column(String(30), nullable=False)
    budgets = Column(JSONBCompat, nullable=False)
    token_usage = Column(JSONBCompat, nullable=False)
    memory_counts = Column(JSONBCompat, nullable=False)
    evidence_score_avg = Column(Float, nullable=True)
    response_id = Column(GUID(), nullable=True)
    request_id = Column(String(100), nullable=True)
    trace_id = Column(String(100), nullable=True)


Index("idx_context_pack_runs_user_created", ContextPackRun.user_id, ContextPackRun.created_at)
Index("idx_context_pack_runs_intent", ContextPackRun.intent)


class ContextBudgetProfile(BaseModel):
    __tablename__ = "context_budget_profiles"

    intent = Column(String(30), nullable=False)
    bucket = Column(String(30), nullable=False)
    multiplier = Column(Float, nullable=False, default=1.0)


Index("idx_context_budget_profiles_intent", ContextBudgetProfile.intent)
UniqueConstraint("intent", "bucket", name="uq_context_budget_profiles_intent_bucket")


class ContextPackFeedback(BaseModel):
    __tablename__ = "context_pack_feedback"

    pack_run_id = Column(GUID(), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)
    reasons = Column(JSONBCompat, nullable=True)
    score = Column(Float, nullable=True)

