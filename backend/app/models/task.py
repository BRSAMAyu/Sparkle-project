"""
任务模型
Task Model - 学习任务卡片系统
"""
import enum
from sqlalchemy import (
    Column, String, Integer, Text, Enum,
    ForeignKey, DateTime, Date, Index, JSON, Boolean
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class TaskType(str, enum.Enum):
    """任务类型枚举"""
    LEARNING = "learning"      # 学习
    TRAINING = "training"      # 训练
    ERROR_FIX = "error_fix"    # 改错
    REFLECTION = "reflection"  # 反思
    SOCIAL = "social"          # 社交
    PLANNING = "planning"      # 规划


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 待开始
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成
    ABANDONED = "abandoned"       # 已放弃


class Task(BaseModel):
    """
    任务模型

    字段:
        user_id: 所属用户ID
        plan_id: 关联计划ID（可选）
        title: 任务标题
        type: 任务类型
        tags: 标签列表(JSON)
        estimated_minutes: 预估时长(分钟)
        difficulty: 难度等级 (1-5)
        energy_cost: 能量消耗 (1-5)
        guide_content: 引导内容(AI生成)
        status: 任务状态
        started_at: 开始时间
        completed_at: 完成时间
        actual_minutes: 实际时长
        user_note: 用户笔记
        priority: 优先级
        due_date: 截止日期

    关系:
        user: 所属用户
        plan: 关联计划
        chat_messages: 相关聊天消息
    """

    __tablename__ = "tasks"

    # 关联关系
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=True, index=True)

    # 任务基本信息
    title = Column(String(255), nullable=False)
    type = Column(Enum(TaskType), nullable=False)
    tags = Column(JSON, default=list, nullable=False)  # 标签列表

    # 时间和难度
    estimated_minutes = Column(Integer, nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)  # 1-5
    energy_cost = Column(Integer, default=1, nullable=False)  # 1-5

    # AI生成内容
    guide_content = Column(Text, nullable=True)

    # 状态信息
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

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
