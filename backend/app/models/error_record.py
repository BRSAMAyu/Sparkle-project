"""
错误档案模型
ErrorRecord Model - 用户的错题和错误记录
"""
from sqlalchemy import (
    Column, String, Integer, Text,
    ForeignKey, DateTime, Boolean, Index, JSON
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class ErrorRecord(BaseModel):
    """
    错误档案模型

    字段:
        user_id: 所属用户ID
        task_id: 关联任务ID（可选）
        subject: 学科/课程
        topic: 知识点
        error_type: 错误类型
        description: 错误描述
        correct_approach: 正确解法
        image_urls: 题目图片URL列表（JSON）
        frequency: 出现频次
        last_occurred_at: 最近出现时间
        is_resolved: 是否已解决
        resolved_at: 解决时间

    关系:
        user: 所属用户
        task: 关联任务（可选）
    """

    __tablename__ = "error_records"

    # 关联关系
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)

    # 错误分类
    subject = Column(String(100), nullable=False, index=True)  # 学科/课程
    topic = Column(String(255), nullable=False, index=True)    # 知识点
    error_type = Column(String(100), nullable=False)           # 错误类型

    # 错误内容
    description = Column(Text, nullable=False)
    correct_approach = Column(Text, nullable=True)
    image_urls = Column(JSON, default=list, nullable=True)  # 题目图片列表

    # 统计信息
    frequency = Column(Integer, default=1, nullable=False)
    last_occurred_at = Column(DateTime, nullable=False)

    # 解决状态
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    # 关系定义
    user = relationship("User", back_populates="error_records")
    task = relationship("Task")

    def __repr__(self):
        return f"<ErrorRecord(subject={self.subject}, topic={self.topic}, resolved={self.is_resolved})>"


# 创建索引
Index("idx_error_user_id", ErrorRecord.user_id)
Index("idx_error_task_id", ErrorRecord.task_id)
Index("idx_error_subject", ErrorRecord.subject)
Index("idx_error_topic", ErrorRecord.topic)
Index("idx_error_subject_topic", ErrorRecord.subject, ErrorRecord.topic)
Index("idx_error_is_resolved", ErrorRecord.is_resolved)
Index("idx_error_last_occurred", ErrorRecord.last_occurred_at)
