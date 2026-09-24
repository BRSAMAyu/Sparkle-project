from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class TheaterCandidateBundle(BaseModel):
    """自由/混合推演生成的候选入图包。"""

    __tablename__ = "theater_candidate_bundles"

    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prediction_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    target_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_resolution_mode: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review", index=True)
    nodes_payload: Mapped[Any] = mapped_column(JSON().with_variant(JSONB(astext_type=Text()), "postgresql"), nullable=False, default=list)
    edges_payload: Mapped[Any] = mapped_column(JSON().with_variant(JSONB(astext_type=Text()), "postgresql"), nullable=False, default=list)
    semantic_matches: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=list,
    )
    source_metadata: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(astext_type=Text()), "postgresql"),
        nullable=False,
        default=dict,
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<TheaterCandidateBundle(id={self.id}, prediction_id={self.prediction_id}, "
            f"mode={self.target_resolution_mode}, status={self.status})>"
        )
