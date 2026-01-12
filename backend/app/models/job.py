"""
异步任务模型
Job Model - 用于处理耗时的后台任务
"""
import enum
from sqlalchemy import Column, String, Integer, Text, Enum, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
import uuid

from app.models.base import BaseModel, GUID

class JobType(str, enum.Enum):
    """任务类型枚举"""
    GENERATE_TASKS = "generate_tasks"       # 生成任务
    EXECUTE_ACTIONS = "execute_actions"     # 执行Action
    ANALYZE_ERROR = "analyze_error"         # 错误分析
    GENERATE_PLAN = "generate_plan"         # 生成计划

class JobStatus(str, enum.Enum):
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

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default=JobStatus.PENDING)
    
    params = Column(JSON, default={}, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    progress = Column(Integer, default=0)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 🆕 v2.1: 超时时间
    timeout_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    user = relationship("User", backref="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, type={self.type}, status={self.status})>"

# 索引
Index("idx_jobs_user_id", Job.user_id)
Index("idx_jobs_status", Job.status)
# 🆕 用于启动时扫描
Index("idx_jobs_status_timeout", Job.status, Job.timeout_at, postgresql_where=(Job.status == 'running'))
