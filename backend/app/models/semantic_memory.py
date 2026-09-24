"""
Semantic Memory Models
Phase 2: Strategy nodes and evidence links.
"""
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class StrategyNode(BaseModel):
    __tablename__ = "strategy_nodes"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=True)
    subject_code: Mapped[str] = mapped_column(String(50), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(20), default="llm", nullable=False)  # llm | user | seed
    evidence_refs: Mapped[Any] = mapped_column(JSON, nullable=True)

    user = relationship("User", backref="strategy_nodes")
    outgoing_links = relationship(
        "SemanticLink",
        foreign_keys="SemanticLink.source_id",
        primaryjoin="StrategyNode.id==foreign(SemanticLink.source_id)",
        viewonly=True,
    )


class SemanticLink(BaseModel):
    __tablename__ = "semantic_links"

    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # error | concept | strategy
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    created_by: Mapped[str] = mapped_column(String(20), default="llm", nullable=False)
    evidence_refs: Mapped[Any] = mapped_column(JSON, nullable=True)
