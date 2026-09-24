"""
Task resource linking models.

Provides structured associations between tasks and learning resources,
seed content, and knowledge graph nodes.
"""
import enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class TaskResourceType(enum.StrEnum):
    SEED_LIBRARY = "seed_library"
    SEED_ITEM = "seed_item"
    KNOWLEDGE_NODE = "knowledge_node"
    EXTERNAL_URL = "external_url"
    FILE = "file"
    NOTE = "note"


class TaskResourceLink(BaseModel):
    """
    Link table for task learning resources and seed content.
    """
    __tablename__ = "task_resource_links"

    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[Any] = mapped_column(GUID(), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    resource_metadata: Mapped[Any] = mapped_column("metadata", JSONBCompat, nullable=True)

    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task = relationship("Task", back_populates="resource_links")

    def __repr__(self) -> str:
        return f"<TaskResourceLink(task_id={self.task_id}, type={self.resource_type})>"


class TaskKnowledgeLink(BaseModel):
    """
    Link table for task-to-knowledge-node relations.
    """
    __tablename__ = "task_knowledge_links"

    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_node_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, default="related")
    strength: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task = relationship("Task", back_populates="knowledge_links")
    knowledge_node = relationship("KnowledgeNode")

    def __repr__(self) -> str:
        return f"<TaskKnowledgeLink(task_id={self.task_id}, node_id={self.knowledge_node_id})>"


Index("idx_task_resource_links_task_type", TaskResourceLink.task_id, TaskResourceLink.resource_type)
Index("idx_task_knowledge_links_task_node", TaskKnowledgeLink.task_id, TaskKnowledgeLink.knowledge_node_id)
