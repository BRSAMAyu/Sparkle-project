"""
任务模型
Task Model - 学习任务卡片系统
"""
import enum
from sqlalchemy import (
    Column, String, Integer, Text, Enum,
    ForeignKey, DateTime, Date, Index, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID

class TaskType(str, enum.Enum):
    LEARNING = "LEARNING"
    TRAINING = "TRAINING"
    ERROR_FIX = "ERROR_FIX"
    REFLECTION = "REFLECTION"
    SOCIAL = "SOCIAL"
    PLANNING = "PLANNING"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"

class Task(BaseModel):
    __tablename__ = "tasks"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=True, index=True)

    # 任务基本信息
    title = Column(String(255), nullable=False)
    type = Column(Enum(TaskType), nullable=False)
    tags = Column(JSONB, default=list, nullable=False)  # 标签列表 (使用 JSONB)

    # 时间和难度
    estimated_minutes = Column(Integer, nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)  # 1-5
    energy_cost = Column(Integer, default=1, nullable=False)  # 1-5

    # AI生成内容
    guide_content = Column(Text, nullable=True)

    # 状态信息
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 追溯信息
    tool_result_id = Column(String(50), nullable=True, index=True)

    # 追溯信息
    tool_result_id = Column(String(50), nullable=True, index=True)

    # 完成信息
    actual_minutes = Column(Integer, nullable=True)
    user_note = Column(Text, nullable=True)

    # 优先级和截止日期
    priority = Column(Integer, default=0, nullable=False)
    due_date = Column(Date, nullable=True)

    # Knowledge Galaxy Integration
    knowledge_node_id = Column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=True)
    auto_expand_enabled = Column(Boolean, default=True)

    # 关系定义
    user = relationship("User", back_populates="tasks")
    plan = relationship("Plan", back_populates="tasks")
    knowledge_node = relationship("KnowledgeNode")
    chat_messages = relationship(
        "ChatMessage",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    curiosity_capsules = relationship(
        "CuriosityCapsule",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Task(title={self.title}, status={self.status})>"


# 创建索引
Index("idx_tasks_user_id", Task.user_id)
Index("idx_tasks_plan_id", Task.plan_id)
Index("idx_tasks_status", Task.status)
Index("idx_tasks_created_at", Task.created_at)
Index("idx_tasks_due_date", Task.due_date)