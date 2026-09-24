"""
异步任务模型
Job Model - 用于处理耗时的后台任务
"""
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class JobType(enum.StrEnum):
    """任务类型枚举"""
    GENERATE_TASKS = "generate_tasks"       # 生成任务
    EXECUTE_ACTIONS = "execute_actions"     # 执行Action
    ANALYZE_ERROR = "analyze_error"         # 错误分析
    GENERATE_PLAN = "generate_plan"         # 生成计划

class JobStatus(enum.StrEnum):
    """任务状态枚举"""
    PENDING = "pending"       # 等待中
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败

class Job(BaseModel):
    """
    异步任务模型

    字段:
        user_id: 所属用户ID
        type: 任务类型
        status: 任务状态
        params: 任务参数(JSON)
        result: 任务结果(JSON)
        error_message: 错误信息
        progress: 进度(0-100)
        started_at: 开始时间
        completed_at: 完成时间
        timeout_at: 超时时间 (v2.1新增)
    """
    __tablename__ = "jobs"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=JobStatus.PENDING)

    params: Mapped[Any] = mapped_column(JSON, default={}, nullable=True)
    result: Mapped[Any] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # 🆕 v2.1: 超时时间
    timeout_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关系
    user = relationship("User", backref="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, type={self.type}, status={self.status})>"

# 索引
Index("idx_jobs_user_id", Job.user_id)
Index("idx_jobs_status", Job.status)
# 🆕 用于启动时扫描
Index("idx_jobs_status_timeout", Job.status, Job.timeout_at, postgresql_where=(Job.status == 'running'))
