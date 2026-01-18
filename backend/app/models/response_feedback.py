from sqlalchemy import Column, String, SmallInteger, Index, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel, GUID


class ResponseFeedback(BaseModel):
    __tablename__ = "response_feedback"

    FEEDBACK_UP = 1
    FEEDBACK_DOWN = 2

    user_id = Column(GUID(), nullable=False, index=True)
    response_id = Column(GUID(), nullable=False, index=True)
    trace_id = Column(String, nullable=False)
    workflow_id = Column(String(64), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    feedback_type = Column(SmallInteger, nullable=False)
    reasons = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    free_text = Column(String, nullable=True)
    meta = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "response_id", name="uq_response_feedback_user_response"),
        Index(
            "ix_response_feedback_workflow_prompt_created",
            "workflow_id",
            "prompt_version",
            "created_at",
        ),
        Index("ix_response_feedback_created_at", "created_at"),
    )
