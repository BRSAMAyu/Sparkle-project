from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class TheaterPrediction(BaseModel):
    """Persisted Theater prediction record.

    The graph (nodes/edges) is stored separately in TheaterCandidateBundle;
    this model stores everything else needed for history and accuracy tracking.
    Redis remains the hot cache; DB is the durable source of truth.
    """

    __tablename__ = "theater_predictions"

    # --- Core identity (separate columns for indexing / querying) ---
    prediction_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    target_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_node_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    target_resolution_mode: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    preview_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # --- References ---
    candidate_bundle_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("theater_candidate_bundles.id", ondelete="SET NULL"),
        nullable=True,
    )
    simulation_session_id: Mapped[str] = mapped_column(String(128), nullable=True)
    recommended_route_id: Mapped[str] = mapped_column(String(64), nullable=True)

    # --- Adoption state ---
    adopted_plan_id: Mapped[Any] = mapped_column(GUID(), nullable=True)
    adopted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # --- Accuracy tracking (lifted to columns for Celery queries) ---
    accuracy_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_feedback", index=True,
    )
    accuracy_due_on: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)

    # --- Nested data (JSONB, not queried by inner keys) ---
    paths: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    discussion_turns: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    timeline: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    selected_prediction: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=True,
    )
    routing_notes: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=dict,
    )
    accuracy_tracking: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=dict,
    )
    accuracy_summary: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=True,
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<TheaterPrediction(id={self.id}, prediction_id={self.prediction_id}, "
            f"topic={self.topic!r}, accuracy_status={self.accuracy_status})>"
        )
