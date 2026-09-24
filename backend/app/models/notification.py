"""
通知模型
Notification Model - 系统主动发送给用户的消息
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class Notification(BaseModel):
    """
    通知模型
    """
    __tablename__ = "notifications"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="fragmented_time", nullable=False) # fragmented_time, system, reminder

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关联的数据，比如推荐的任务ID
    data: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 关系
    user = relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification(title={self.title}, user_id={self.user_id})>"


class PushHistory(BaseModel):
    """
    推送历史记录 (用于频控和分析)
    """
    __tablename__ = "push_histories"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 触发类型: memory (记忆唤醒), sprint (冲刺提醒), inactivity (沉睡唤醒)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # 内容哈希，防止重复生成
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # 状态: sent, clicked, snoozed, dismissed
    status: Mapped[str] = mapped_column(String(50), default="sent", nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=True)
    interacted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    user = relationship("User", backref="push_histories")

    def __repr__(self):
        return f"<PushHistory(user_id={self.user_id}, type={self.trigger_type}, status={self.status})>"
