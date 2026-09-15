from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class TheaterPrediction(BaseModel):
    """Persisted Theater prediction record.

    The graph (nodes/edges) is stored separately in TheaterCandidateBundle;
    this model stores everything else needed for history and accuracy tracking.
    Redis remains the hot cache; DB is the durable source of truth.
    """

    __tablename__ = "theater_predictions"

    # --- Core identity (separate columns for indexing / querying) ---
    prediction_id = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic = Column(Text, nullable=False)
    target_name = Column(String(255), nullable=False)
    target_node_id = Column(GUID(), nullable=True)
    target_resolution_mode = Column(String(32), nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False, default=14)
    preview_mode = Column(Boolean, nullable=False, default=False)
    generated_at = Column(DateTime, nullable=False, index=True)

    # --- References ---
    candidate_bundle_id = Column(
        GUID(),
        ForeignKey("theater_candidate_bundles.id", ondelete="SET NULL"),
        nullable=True,
    )
    simulation_session_id = Column(String(128), nullable=True)
    recommended_route_id = Column(String(64), nullable=True)

    # --- Adoption state ---
    adopted_plan_id = Column(GUID(), nullable=True)
    adopted_at = Column(DateTime, nullable=True)

    # --- Accuracy tracking (lifted to columns for Celery queries) ---
    accuracy_status = Column(
        String(32), nullable=False, default="pending_feedback", index=True,
    )
    accuracy_due_on = Column(DateTime, nullable=True, index=True)

    # --- Nested data (JSONB, not queried by inner keys) ---
    paths = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    discussion_turns = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    timeline = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    selected_prediction = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=True,
    )
    routing_notes = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=dict,
    )
    accuracy_tracking = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=dict,
    )
    accuracy_summary = Column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=True,
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<TheaterPrediction(id={self.id}, prediction_id={self.prediction_id}, "
            f"topic={self.topic!r}, accuracy_status={self.accuracy_status})>"
        )
