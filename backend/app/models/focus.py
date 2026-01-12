"""
专注模式数据模型
Focus Models - 番茄钟会话记录
"""
import enum
from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime, Enum, Index
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class FocusType(str, enum.Enum):
    """专注类型"""
    POMODORO = "pomodoro"    # 番茄钟
    STOPWATCH = "stopwatch"  # 正计时


class FocusStatus(str, enum.Enum):
    """专注状态"""
    COMPLETED = "completed"       # 完成
    INTERRUPTED = "interrupted"   # 中断/放弃


class FocusSession(BaseModel):
    """
    专注会话记录表
    记录每一次专注的时间、关联任务和状态
    """
    __tablename__ = "focus_sessions"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True, index=True)

    # 时间信息
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # 实际专注时长

    # 类型与状态
    focus_type = Column(Enum(FocusType), default=FocusType.POMODORO, nullable=False)
    status = Column(Enum(FocusStatus), default=FocusStatus.COMPLETED, nullable=False)

    # 白噪音 (可选记录)
    white_noise_type = Column(Integer, nullable=True) # ID or Enum Value

    # 关系
    user = relationship("User")
    task = relationship("Task")

    __table_args__ = (
        Index('idx_focus_user_time', 'user_id', 'start_time'),
    )
