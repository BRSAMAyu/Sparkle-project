from typing import Any

from sqlalchemy import JSON, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel


class ResponseFeedback(BaseModel):
    __tablename__ = "response_feedback"

    FEEDBACK_UP = 1
    FEEDBACK_DOWN = 2

    user_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    response_id: Mapped[Any] = mapped_column(GUID(), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    feedback_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reasons: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    free_text: Mapped[str] = mapped_column(String, nullable=True)
    meta: Mapped[Any] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    intervention_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    scaffolding_level: Mapped[int] = mapped_column(Integer, nullable=True)
    template_variant_id: Mapped[str] = mapped_column(String(100), nullable=True)
    time_to_response: Mapped[int] = mapped_column(Integer, nullable=True)
    action_taken: Mapped[str] = mapped_column(String(40), nullable=True)

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
