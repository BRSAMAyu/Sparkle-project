"""
通知模型
Notification Model - 系统主动发送给用户的消息
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Index, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel, GUID

class Notification(BaseModel):
    """
    通知模型
    """
    __tablename__ = "notifications"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    content = Column(String(1000), nullable=False)
    type = Column(String(50), default="fragmented_time", nullable=False) # fragmented_time, system, reminder
    
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    
    # 关联的数据，比如推荐的任务ID
    data = Column(JSON, nullable=True)

    # 关系
    user = relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification(title={self.title}, user_id={self.user_id})>"
