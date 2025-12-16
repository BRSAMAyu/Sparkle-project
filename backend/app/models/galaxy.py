"""
Knowledge Galaxy Models
知识星图相关模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import BaseModel, GUID


class KnowledgeNode(BaseModel):
    """
    知识节点表 (Knowledge Nodes)
    星图中的"星辰"，支持无限层级结构
    """
    __tablename__ = "knowledge_nodes"

    # 关联学科 (Subject) - 注意: Subject 使用 Integer ID
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    
    # 父节点 (Parent Node) - 自关联
    parent_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=True, index=True)

    # 节点名称
    name = Column(String(255), nullable=False)
    
    # 描述
    description = Column(Text, nullable=True)
    
    # 重要性等级 (1-5), 决定星星大小
    importance_level = Column(Integer, default=1, nullable=False)

    # 关系
    subject = relationship("Subject", backref="knowledge_nodes")
    parent = relationship("KnowledgeNode", remote_side="KnowledgeNode.id", backref="children")
    user_statuses = relationship("UserNodeStatus", back_populates="node", cascade="all, delete-orphan")


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
    mastery_score = Column(Integer, default=0, nullable=False)
    
    # 投入时间 (分钟)
    total_minutes = Column(Integer, default=0, nullable=False)
    
    # 是否已点亮/解锁
    is_unlocked = Column(Boolean, default=False, nullable=False)
    
    # 最后交互时间
    last_interacted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 元数据 (尽管不是 BaseModel, 但保留时间戳是个好习惯)
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
