"""
Semantic Memory Models
Phase 2: Strategy nodes and evidence links.
"""
from sqlalchemy import Column, String, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class StrategyNode(BaseModel):
    __tablename__ = "strategy_nodes"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=True)
    subject_code = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    source_type = Column(String(20), default="llm", nullable=False)  # llm | user | seed
    evidence_refs = Column(JSON, nullable=True)

    user = relationship("User", backref="strategy_nodes")
    outgoing_links = relationship(
        "SemanticLink",
        foreign_keys="SemanticLink.source_id",
        primaryjoin="StrategyNode.id==foreign(SemanticLink.source_id)",
        viewonly=True,
    )


class SemanticLink(BaseModel):
    __tablename__ = "semantic_links"

    source_type = Column(String(30), nullable=False, index=True)  # error | concept | strategy
    source_id = Column(String(64), nullable=False, index=True)
    target_type = Column(String(30), nullable=False, index=True)
    target_id = Column(String(64), nullable=False, index=True)
    relation_type = Column(String(40), nullable=False, index=True)
    strength = Column(Float, default=0.5, nullable=False)
    created_by = Column(String(20), default="llm", nullable=False)
    evidence_refs = Column(JSON, nullable=True)
