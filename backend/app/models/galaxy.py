"""
Knowledge Galaxy Models
知识星图相关模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base
from app.models.base import BaseModel, GUID


class KnowledgeNode(BaseModel):
    """
    知识节点表 (Knowledge Nodes)
    星图中的"星辰"，支持无限层级结构
    """
    __tablename__ = "knowledge_nodes"

    # 关联学科 (Subject) - 注意: Subject 使用 Integer ID
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    
    # 父节点 (Parent Node) - 自关联
    parent_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=True, index=True)

    # 节点名称
    name = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True) # 英文名
    
    # 描述
    description = Column(Text, nullable=True)
    
    # 关键词 (使用 JSONB 优化搜索)
    keywords = Column(JSONB, default=list, nullable=True)
    
    # 重要性等级 (1-5), 决定星星大小
    importance_level = Column(Integer, default=1, nullable=False)

    # 节点来源
    is_seed = Column(Boolean, default=False)
    source_type = Column(String(20), default='seed') # seed | user_created | llm_expanded
    source_task_id = Column(GUID(), nullable=True) # 来源任务ID (这里不强关联 Task 表以免循环依赖，或者使用字符串)

    # AI 属性 (向量)
    # 注意: SQLite 不支持 Vector，需要处理兼容性，或者仅在 PG 环境使用
    embedding = Column(Vector(1536), nullable=True)
    
    # Layout Coordinates (for Viewport Query)
    position_x = Column(Float, nullable=True, index=True)
    position_y = Column(Float, nullable=True, index=True)

    # Collaborative Data
    global_spark_count = Column(Integer, default=0, nullable=False)

    # 关系
    subject = relationship("Subject", backref="knowledge_nodes")
    parent = relationship("KnowledgeNode", remote_side="KnowledgeNode.id", backref="children")
    user_statuses = relationship("UserNodeStatus", back_populates="node", cascade="all, delete-orphan")
    source_relations = relationship("NodeRelation", foreign_keys="NodeRelation.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    target_relations = relationship("NodeRelation", foreign_keys="NodeRelation.target_node_id", back_populates="target_node", cascade="all, delete-orphan")


class NodeRelation(BaseModel):
    """
    知识点关系表 (星座连线)
    """
    __tablename__ = "node_relations"

    source_node_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    target_node_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)

    # 关系类型: prerequisite, related, application, composition, evolution
    relation_type = Column(String(30), nullable=False)
    
    # 关系强度 (0-1)
    strength = Column(Float, default=0.5)

    created_by = Column(String(20), default='seed') # seed | user | llm

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

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True, nullable=False)
    node_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), primary_key=True, nullable=False)

    # 掌握度/亮度 (0-100)
    mastery_score = Column(Float, default=0, nullable=False)
    
    # 投入时间 (分钟)
    total_minutes = Column(Integer, default=0, nullable=False)
    total_study_minutes = Column(Integer, default=0, nullable=False) # 别名/冗余? Doc 用 total_study_minutes
    
    study_count = Column(Integer, default=0) # 学习次数
    
    # 状态标记
    is_unlocked = Column(Boolean, default=False, nullable=False)
    is_collapsed = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    
    # 遗忘曲线相关
    last_study_at = Column(DateTime, nullable=True) # Doc uses last_study_at
    last_interacted_at = Column(DateTime, default=datetime.utcnow, nullable=False) # Keep for compatibility or remove?
    decay_paused = Column(Boolean, default=False)
    next_review_at = Column(DateTime, nullable=True, index=True)
    
    # 元数据
    first_unlock_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    node_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True) # 关联 Task

    study_minutes = Column(Integer, nullable=False)
    mastery_delta = Column(Float, nullable=False)
    
    # record_type: task_complete, review, exploration
    record_type = Column(String(20), default='task_complete')

    # 关系
    user = relationship("User")
    node = relationship("KnowledgeNode")
    task = relationship("Task")


class NodeExpansionQueue(BaseModel):
    """
    节点拓展队列表 (LLM 拓展任务队列)
    """
    __tablename__ = "node_expansion_queue"

    trigger_node_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=False)
    trigger_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    expansion_context = Column(Text, nullable=False)
    
    # status: pending, processing, completed, failed
    status = Column(String(20), default='pending', index=True)
    
    expanded_nodes = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    processed_at = Column(DateTime, nullable=True)

    # 关系
    trigger_node = relationship("KnowledgeNode")
    user = relationship("User")
    trigger_task = relationship("Task")