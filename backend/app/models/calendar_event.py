"""
日历事件模型
Calendar Event Model - 日历事件系统
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB()


class EventSource:
    """事件来源常量"""

    MANUAL = "manual"  # 手动创建
    AI = "ai"  # AI 生成
    IMPORT = "import"  # 外部导入


class CalendarEvent(BaseModel):
    """日历事件模型"""

    __tablename__ = "calendar_events"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 事件基本信息
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 时间信息
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_all_day = Column(Boolean, default=False, nullable=False)

    # 地点和颜色
    location = Column(String(255), nullable=True)
    color = Column(String(32), nullable=True)  # Hex color or color name

    # 重复事件支持 (RRULE format)
    recurrence_rule = Column(String(512), nullable=True)
    recurrence_end_date = Column(DateTime(timezone=True), nullable=True)

    # 提醒设置 (分钟数列表，如 [0, 15, 60] 表示开始时、15分钟前、1小时前)
    reminder_minutes = Column(JSONBCompat, default=list, nullable=False)

    # 事件来源和元数据
    source = Column(String(32), default=EventSource.MANUAL, nullable=False)
    source_metadata = Column(JSONBCompat, nullable=True)

    # 关联的任务或计划
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_id = Column(GUID(), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)

    # 关系
    user = relationship("User", backref="calendar_events")
    task = relationship("Task", backref="calendar_event")
    plan = relationship("Plan", backref="calendar_events")

    def __repr__(self):
        return f"<CalendarEvent(title={self.title}, start_time={self.start_time})>"

    @property
    def duration_minutes(self) -> int:
        """计算事件时长（分钟）"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def is_recurring(self) -> bool:
        """检查是否为重复事件"""
        return self.recurrence_rule is not None


# 创建索引
Index("ix_calendar_events_user_time", CalendarEvent.user_id, CalendarEvent.start_time)
Index("ix_calendar_events_user_deleted", CalendarEvent.user_id, CalendarEvent.deleted_at)
