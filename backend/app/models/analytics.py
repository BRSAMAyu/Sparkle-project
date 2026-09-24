"""
Analytics Models
数据分析相关模型
"""
from datetime import date
from typing import Any

from sqlalchemy import Date, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class UserDailyMetric(BaseModel):
    """
    用户每日指标表 (User Daily Metrics)
    每日聚合用户的各项关键指标，用于长期趋势分析
    """
    __tablename__ = "user_daily_metrics"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 参与度指标 (Engagement)
    total_focus_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 当日总专注时间
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 完成任务数
    tasks_created: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 创建任务数

    # 学习指标 (Learning)
    nodes_studied: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 学习的不同节点数
    mastery_gained: Mapped[float] = mapped_column(Float, default=0.0, nullable=True) # 当日获得的掌握度增量总和
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 复习次数

    # 认知/情绪指标 (Cognitive/Emotional)
    # 基于 CognitiveFragment 的聚合
    average_mood: Mapped[float] = mapped_column(Float, nullable=True) # 平均情绪值 (如果有量化)
    anxiety_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=True) # 焦虑指数 (0-1)

    # 系统交互 (System)
    chat_messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True) # 发送的消息数

    # 关系
    user = relationship("User", backref="daily_metrics")

    # 唯一约束: 每个用户每天只有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_user_daily_metric'),
    )

    def __repr__(self):
        return f"<UserDailyMetric(user_id={self.user_id}, date={self.date})>"
