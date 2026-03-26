"""
计划模型
Plan Model - 冲刺计划和成长计划
"""

import enum

from sqlalchemy import JSON, Boolean, Column, Date, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class PlanType(str, enum.Enum):
    """计划类型枚举"""

    SPRINT = "sprint"  # 冲刺计划(短期考试)
    GROWTH = "growth"  # 成长计划(长期技能)


class PlanPriority(str, enum.Enum):
    """计划优先级枚举"""

    CRITICAL = "critical"  # 紧急/截止日期临近
    HIGH = "high"  # 重要
    NORMAL = "normal"  # 普通
    LOW = "low"  # 低优先级


class PlanStage(str, enum.Enum):
    """计划阶段枚举"""

    SPRINT = "sprint"
    DAILY = "daily"
    REVIEW = "review"
    PAUSED = "paused"


class PlanStatus(str, enum.Enum):
    """计划状态枚举"""

    DRAFT = "draft"  # 草稿
    PENDING_REVIEW = "pending_review"  # 待审核
    ACTIVE = "active"  # 激活
    PAUSED = "paused"  # 暂停
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"  # 已归档
    CANCELLED = "cancelled"  # 已取消


class Plan(BaseModel):
    """
    计划模型

    字段:
        user_id: 所属用户ID
        name: 计划名称
        type: 计划类型(冲刺/成长)
        description: 计划描述
        target_date: 目标日期(冲刺计划用)
        subject: 学科/课程
        daily_available_minutes: 每日可用时间(分钟)
        total_estimated_hours: 总预估时长(小时)
        mastery_level: 掌握程度 (0-1)
        progress: 进度百分比 (0-1)
        is_active: 是否激活

    关系:
        user: 所属用户
        tasks: 计划下的所有任务
    """

    __tablename__ = "plans"

    # 关联关系
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 计划基本信息
    name = Column(String(255), nullable=False)
    type = Column(Enum(PlanType), nullable=False)
    description = Column(Text, nullable=True)

    # 计划阶段
    plan_stage = Column(
        Enum(PlanStage, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=PlanStage.DAILY,
        index=True,
    )

    # 时间相关
    target_date = Column(Date, nullable=True)  # 冲刺计划的目标日期
    daily_available_minutes = Column(Integer, default=60, nullable=False)
    total_estimated_hours = Column(Float, nullable=True)

    # 学科/课程
    subject = Column(String(100), nullable=True)

    # 进度跟踪
    mastery_level = Column(Float, default=0.0, nullable=False)  # 范围 0-1
    progress = Column(Float, default=0.0, nullable=False)  # 进度百分比 0-1

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 优先级和主计划 (P0: 并行计划限制)
    priority = Column(
        Enum(PlanPriority, values_callable=lambda obj: [e.value for e in obj]),
        default=PlanPriority.NORMAL,
        nullable=False,
        index=True,
    )
    is_primary = Column(Boolean, default=False, nullable=False, index=True)

    # 来源标记 (Phase 4: 学习路径进度追踪)
    source = Column(String(32), nullable=True, index=True)
    source_metadata = Column(JSONBCompat, nullable=True)

    # 关系定义
    user = relationship("User", back_populates="plans")
    tasks = relationship("Task", back_populates="plan", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<Plan(name={self.name}, type={self.type}, progress={self.progress})>"


# 创建索引
Index("idx_plans_user_id", Plan.user_id)
Index("idx_plans_is_active", Plan.is_active)
Index("idx_plans_type", Plan.type)
Index("idx_plans_target_date", Plan.target_date)
Index("idx_plans_priority", Plan.priority)
Index("idx_plans_is_primary", Plan.is_primary)
Index("idx_plans_stage", Plan.plan_stage)
# 复合索引：用户活跃计划查询优化
Index("idx_plans_user_active", Plan.user_id, Plan.is_active)
