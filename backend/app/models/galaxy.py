"""
Knowledge Galaxy Models
知识星图相关模型
"""
from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.db.session import Base
from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")

class CollaborativeGalaxy(BaseModel):
    """
    协作星图表 (Collaborative Galaxies)
    支持多用户共享和协作编辑的主题星图
    """
    __tablename__ = "collaborative_galaxies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    galaxy_scope: Mapped[str] = mapped_column(String(32), default="shared", nullable=False, index=True)

    # 可见性: private, shared, public
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)

    # 关联学科 (可选)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id"), nullable=True)

    # 关系
    creator = relationship("User", foreign_keys=[created_by])
    group = relationship("Group")
    subject = relationship("Subject")
    permissions = relationship("GalaxyUserPermission", back_populates="galaxy", cascade="all, delete-orphan")


class GalaxyUserPermission(Base):
    """
    协作星图用户权限表
    """
    __tablename__ = "galaxy_user_permissions"

    galaxy_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("collaborative_galaxies.id"), primary_key=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), primary_key=True)

    # 权限等级: owner, editor, viewer, contrib
    permission_level: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # 关系
    galaxy = relationship("CollaborativeGalaxy", back_populates="permissions")
    user = relationship("User")


class CRDTSnapshot(Base):
    """
    CRDT 状态快照表
    存储 Yjs 文档的二进制状态
    """
    __tablename__ = "crdt_snapshots"

    galaxy_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("collaborative_galaxies.id"), primary_key=True)
    state_data: Mapped[Any] = mapped_column(LargeBinary, nullable=False)  # Yjs 二进制更新
    operation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class CRDTOperationLog(Base):
    """
    协作操作日志表
    用于审计和冲突回溯
    """
    __tablename__ = "crdt_operation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    galaxy_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("collaborative_galaxies.id"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    # 操作类型: add_node, update_mastery, delete_node, etc.
    operation_type: Mapped[str] = mapped_column(String(50), nullable=True)
    operation_data: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False, index=True)


class KnowledgeNode(BaseModel):
    """
    知识节点表 (Knowledge Nodes)
    星图中的"星辰"，支持无限层级结构
    """
    __tablename__ = "knowledge_nodes"

    # 关联学科 (Subject) - 注意: Subject 使用 Integer ID
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)

    # 父节点 (Parent Node) - 自关联
    parent_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=True, index=True)

    # 节点名称
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=True) # 英文名

    # 描述
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 关键词 (使用 JSONB 优化搜索)
    keywords: Mapped[Any] = mapped_column(JSONBCompat, default=list, nullable=True)

    # 重要性等级 (1-5), 决定星星大小
    importance_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 节点来源
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default='seed', nullable=True) # seed | user_created | llm_expanded | document_import
    source_task_id: Mapped[Any] = mapped_column(GUID(), nullable=True) # 来源任务ID

    # Phase 5B: Document Engine Traceability
    source_file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id"), nullable=True)
    chunk_refs: Mapped[Any] = mapped_column(JSONBCompat, nullable=True) # List of chunk IDs or {chunk_id: score}
    status: Mapped[str] = mapped_column(String(20), default='published', index=True, nullable=True) # draft | published | needs_review

    # AI 属性 (向量)
    # 注意: SQLite 不支持 Vector，需要处理兼容性，或者仅在 PG 环境使用
    embedding = deferred(Column(VectorCompat, nullable=True))

    # E-05 Embedding 版本溯源（同 document_chunks.embedding_model）
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=True)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=True)

    # Layout Coordinates (for Viewport Query)
    position_x: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    position_y: Mapped[float] = mapped_column(Float, nullable=True, index=True)

    # 多星域归属
    sector_weights: Mapped[Any] = mapped_column(JSONBCompat, default=dict, nullable=True)
    dominant_sector_code: Mapped[str] = mapped_column(String(20), default="VOID", nullable=False, server_default="VOID", index=True)
    sector_classification_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, server_default="pending", index=True)
    sector_classification_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sector_classified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # P2-24: Exam attributes for retrieval ranking (KG-001)
    exam_weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="考试权重 0-1")
    difficulty: Mapped[float] = mapped_column(Float, default=0.5, nullable=False, comment="难度 0-1")
    trainability: Mapped[float] = mapped_column(Float, default=0.5, nullable=False, comment="可训练性 0-1")
    mistakes: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="累计错误次数")

    # Collaborative Data
    global_spark_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    community_signal: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)

    # 关系
    subject = relationship("Subject", backref="knowledge_nodes")
    source_file = relationship("StoredFile", backref="knowledge_nodes")
    parent = relationship("KnowledgeNode", remote_side="KnowledgeNode.id", backref="children")
    user_statuses = relationship("UserNodeStatus", back_populates="node", cascade="all, delete-orphan")
    source_relations = relationship("NodeRelation", foreign_keys="NodeRelation.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    target_relations = relationship("NodeRelation", foreign_keys="NodeRelation.target_node_id", back_populates="target_node", cascade="all, delete-orphan")
    document_links = relationship("KnowledgeNodeDocument", back_populates="node", cascade="all, delete-orphan")


class KnowledgeNodeDocument(BaseModel):
    """
    User-managed document attachments for knowledge nodes.

    `KnowledgeNode.source_file_id` remains the legacy/primary provenance pointer;
    this table stores the full many-to-many attachment surface.
    """
    __tablename__ = "knowledge_node_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "node_id", "file_id", name="uq_knowledge_node_documents_user_node_file"),
    )

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    user = relationship("User")
    node = relationship("KnowledgeNode", back_populates="document_links")
    file = relationship("StoredFile", backref="knowledge_node_links")


class NodeRelation(BaseModel):
    """
    知识点关系表 (星座连线)
    """
    __tablename__ = "node_relations"

    source_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    target_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)

    # 关系类型: prerequisite, related, application, composition, evolution
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # 关系强度 (0-1)
    strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=True)

    created_by: Mapped[str] = mapped_column(String(20), default='seed', nullable=True) # seed | user | llm

    # 关系
    source_node = relationship("KnowledgeNode", foreign_keys=[source_node_id], back_populates="source_relations")
    target_node = relationship("KnowledgeNode", foreign_keys=[target_node_id], back_populates="target_relations")


class UserNodeStatus(Base):
    """
    用户节点状态表 (User Node Status)
    记录用户与星辰的关系 (掌握度、投入时间等)
    使用复合主键 (user_id, node_id)
    """
    __tablename__ = "user_node_status"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), primary_key=True, nullable=False)
    node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), primary_key=True, nullable=False)

    # 掌握度/亮度 (0-100)
    mastery_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    # BKT 掌握概率 (0-1)
    bkt_mastery_prob: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bkt_last_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 投入时间 (分钟)
    total_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_study_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 别名/冗余? Doc 用 total_study_minutes

    study_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 学习次数

    # 状态标记
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_collapsed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    # 遗忘曲线相关
    last_study_at: Mapped[datetime] = mapped_column(DateTime, nullable=True) # Doc uses last_study_at
    last_interacted_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False) # Keep for compatibility or remove?
    decay_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    next_review_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)

    # Logical clock for conflict resolution
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 元数据
    first_unlock_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    learning_path_snapshot: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # 关系
    user = relationship("User", backref="node_statuses")
    node = relationship("KnowledgeNode", back_populates="user_statuses")

    def __repr__(self):
        return f"<UserNodeStatus(user_id={self.user_id}, node_id={self.node_id}, mastery={self.mastery_score})>"


class StudyRecord(BaseModel):
    """
    学习记录表 (详细学习历史)
    """
    __tablename__ = "study_records"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True) # 关联 Task

    study_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    mastery_delta: Mapped[float] = mapped_column(Float, nullable=False)
    initial_mastery: Mapped[float] = mapped_column(Float, nullable=True) # 学习前的掌握度

    # record_type: task_complete, review, exploration
    record_type: Mapped[str] = mapped_column(String(20), default='task_complete', nullable=True)

    # 关系
    user = relationship("User")
    node = relationship("KnowledgeNode")
    task = relationship("Task")


class NodeExpansionQueue(BaseModel):
    """
    节点拓展队列表 (LLM 拓展任务队列)
    """
    __tablename__ = "node_expansion_queue"

    trigger_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False)
    trigger_task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    expansion_context: Mapped[str] = mapped_column(Text, nullable=False)

    # status: pending, processing, completed, failed
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True, nullable=True)

    expanded_nodes: Mapped[Any] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=True)

    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    trigger_node = relationship("KnowledgeNode")
    user = relationship("User")
    trigger_task = relationship("Task")


class ExpansionFeedback(BaseModel):
    """
    知识拓展反馈表
    """
    __tablename__ = "expansion_feedback"

    expansion_queue_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("node_expansion_queue.id"), nullable=True, index=True)
    trigger_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # Explicit 1-5 rating, implicit signal (0-1)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    implicit_score: Mapped[float] = mapped_column(Float, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(20), default="explicit", nullable=True)  # explicit | implicit

    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=True)
    meta_data: Mapped[Any] = mapped_column(JSON, nullable=True)

    # Relations
    trigger_node = relationship("KnowledgeNode")
    user = relationship("User")
    expansion_queue = relationship("NodeExpansionQueue")
