"""
Curiosity Capsule Model
"""
import enum
from sqlalchemy import (
    Column, String, Text, Enum,
    ForeignKey, DateTime, Boolean
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID
from app.models.task import Task


class CuriosityCapsule(BaseModel):
    """
    好奇心胶囊模型

    字段:
        user_id: 所属用户ID
        title: 标题
        content: 内容（Markdown）
        related_subject: 相关科目 (Optional, String for now)
        related_task_id: 相关任务ID (Optional)
        is_read: 是否已读
    """

    __tablename__ = "curiosity_capsules"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    related_subject = Column(String(255), nullable=True) # e.g., "Math", "History"
    related_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True, index=True)
    is_read = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="curiosity_capsules")
    task = relationship("Task", back_populates="curiosity_capsules") # One-to-one or one-to-many? For now, one-to-many from capsule to task.

    def __repr__(self):
        return f"<CuriosityCapsule(title={self.title}, user_id={self.user_id})>"

# Add relationship to User and Task models if needed
# In User model: curiosity_capsules = relationship("CuriosityCapsule", back_populates="user")
# In Task model: curiosity_capsule = relationship("CuriosityCapsule", back_populates="task", uselist=False) # if one-to-one
