"""
Task resource linking models.

Provides structured associations between tasks and learning resources,
seed content, and knowledge graph nodes.
"""
import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class TaskResourceType(str, enum.Enum):
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

    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(GUID(), nullable=True, index=True)

    title = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    resource_metadata = Column("metadata", JSONBCompat, nullable=True)

    order_index = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    task = relationship("Task", back_populates="resource_links")

    def __repr__(self) -> str:
        return f"<TaskResourceLink(task_id={self.task_id}, type={self.resource_type})>"


class TaskKnowledgeLink(BaseModel):
    """
    Link table for task-to-knowledge-node relations.
    """
    __tablename__ = "task_knowledge_links"

    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_node_id = Column(
        GUID(), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type = Column(String(50), nullable=False, default="related")
    strength = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    order_index = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    task = relationship("Task", back_populates="knowledge_links")
    knowledge_node = relationship("KnowledgeNode")

    def __repr__(self) -> str:
        return f"<TaskKnowledgeLink(task_id={self.task_id}, node_id={self.knowledge_node_id})>"


Index("idx_task_resource_links_task_type", TaskResourceLink.task_id, TaskResourceLink.resource_type)
Index("idx_task_knowledge_links_task_node", TaskKnowledgeLink.task_id, TaskKnowledgeLink.knowledge_node_id)
