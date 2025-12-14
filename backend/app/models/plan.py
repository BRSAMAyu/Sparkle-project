"""
计划模型
Plan Model - 冲刺计划和成长计划
"""
import enum
from sqlalchemy import (
    Column, String, Integer, Float, Text, Enum,
    ForeignKey, Date, Boolean, Index
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class PlanType(str, enum.Enum):
    """计划类型枚举"""
    SPRINT = "sprint"  # 冲刺计划(短期考试)
    GROWTH = "growth"  # 成长计划(长期技能)


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

    # 时间相关
    target_date = Column(Date, nullable=True)  # 冲刺计划的目标日期
    daily_available_minutes = Column(Integer, default=60, nullable=False)
    total_estimated_hours = Column(Float, nullable=True)

    # 学科/课程
    subject = Column(String(100), nullable=True)

    # 进度跟踪
    mastery_level = Column(Float, default=0.0, nullable=False)  # 范围 0-1
    progress = Column(Float, default=0.0, nullable=False)        # 进度百分比 0-1

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 关系定义
    user = relationship("User", back_populates="plans")
    tasks = relationship(
        "Task",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Plan(name={self.name}, type={self.type}, progress={self.progress})>"


# 创建索引
Index("idx_plans_user_id", Plan.user_id)
Index("idx_plans_is_active", Plan.is_active)
Index("idx_plans_type", Plan.type)
Index("idx_plans_target_date", Plan.target_date)
