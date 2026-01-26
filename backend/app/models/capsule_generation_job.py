"""
Capsule Generation Job Model
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, ARRAY, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class JobStatus(enum.Enum):
    """生成任务状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationType(enum.Enum):
    """生成类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"
    PUSH_TRIGGERED = "push_triggered"


class CapsuleGenerationJob(BaseModel):
    """
    胶囊生成任务模型

    用于追踪异步胶囊生成任务的状态
    """
    __tablename__ = "capsule_generation_jobs"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True, default=JobStatus.PENDING.value)
    generation_type = Column(String(50), nullable=False, index=True)  # daily/weekly/manual/push_triggered
    depth_preference = Column(Float, nullable=False)  # 0.0-1.0
    curiosity_preference = Column(Float, nullable=False)  # 0.0-1.0
    requested_count = Column(Integer, nullable=False)  # 请求生成的胶囊数量
    actual_count = Column(Integer, nullable=True)  # 实际生成的胶囊数量
    capsule_ids = Column(ARRAY(GUID()).with_variant(JSON(), "sqlite"), nullable=True)  # 生成的胶囊ID列表
    progress = Column(Float, nullable=False, default=0.0)  # 0.0-1.0 进度值
    error_message = Column(Text, nullable=True)  # 失败原因
    duration_ms = Column(Integer, nullable=True)  # 生成耗时（毫秒）
    model_used = Column(String(100), nullable=True)  # 使用的模型
    scheduled_for = Column(DateTime, nullable=True, index=True)  # 计划执行时间
    started_at = Column(DateTime, nullable=True)  # 实际开始时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间

    # Relationships
    user = relationship("User", back_populates="capsule_generation_jobs")

    def __repr__(self):
        return f"<CapsuleGenerationJob(id={self.id}, status={self.status}, type={self.generation_type})>"

    @property
    def status_enum(self) -> JobStatus:
        """获取状态枚举"""
        return JobStatus(self.status) if self.status else None

    def mark_started(self):
        """标记任务为进行中"""
        self.status = JobStatus.GENERATING.value
        self.started_at = datetime.utcnow()
        self.progress = 0.1

    def mark_completed(self, capsule_ids: list = None):
        """标记任务为完成"""
        self.status = JobStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        self.progress = 1.0
        if capsule_ids:
            self.capsule_ids = capsule_ids
            self.actual_count = len(capsule_ids)
        if self.started_at:
            self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)

    def mark_failed(self, error_message: str):
        """标记任务为失败"""
        self.status = JobStatus.FAILED.value
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def update_progress(self, progress: float):
        """更新进度"""
        self.progress = max(0.0, min(1.0, progress))
