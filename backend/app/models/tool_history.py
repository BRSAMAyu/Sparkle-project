"""
User Tool History Model - 用户工具执行历史记录
用于追踪工具执行的成功率、性能指标和偏好学习
"""
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index, ForeignKey, Float, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, GUID


class UserToolHistory(Base):
    """用户工具执行历史表

    用途:
    - 计算工具成功率
    - 追踪工具执行性能
    - 学习用户偏好工具
    - 优化路由决策
    """
    __tablename__ = 'user_tool_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to users table
    user_id = Column(GUID(), ForeignKey('users.id'), nullable=False, index=True)

    # Tool information
    tool_name = Column(String(100), nullable=False, index=True)
    tool_category = Column(String(50), nullable=True)  # plan, task, focus, etc.

    # Execution result
    success = Column(Boolean, nullable=False, index=True)
    execution_time_ms = Column(Integer, nullable=True)  # 执行时间（毫秒）

    # Error tracking
    error_message = Column(String(500), nullable=True)
    error_type = Column(String(100), nullable=True)

    # Context at execution time (for learning)
    context_snapshot = Column(JSON, nullable=True)  # user_state, task_state, etc.

    # Input parameters (for replay/analysis)
    input_args = Column(JSON, nullable=True)

    # Output result (for analysis)
    output_summary = Column(Text, nullable=True)

    # Learning metrics
    user_satisfaction = Column(Integer, nullable=True)  # 1-5 rating if user provided
    was_helpful = Column(Boolean, nullable=True)  # Derived from downstream actions

    # Temporal info
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_user_tool_history_user_id', 'user_id'),
        Index('ix_user_tool_history_tool_name', 'tool_name'),
        Index('ix_user_tool_history_success', 'user_id', 'tool_name', 'success'),
        Index('ix_user_tool_history_created_at', 'created_at'),
        Index('ix_user_tool_history_user_created', 'user_id', 'created_at'),
        Index('ix_user_tool_history_metrics', 'user_id', 'tool_name', 'success', 'created_at'),
    )

    def __repr__(self):
        return (f"<UserToolHistory(id={self.id}, user={self.user_id}, "
                f"tool={self.tool_name}, success={self.success}, "
                f"time={self.execution_time_ms}ms)>")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'tool_name': self.tool_name,
            'tool_category': self.tool_category,
            'success': self.success,
            'execution_time_ms': self.execution_time_ms,
            'error_message': self.error_message,
            'user_satisfaction': self.user_satisfaction,
            'was_helpful': self.was_helpful,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ToolSuccessRateView:
    """工具成功率统计视图（用于查询）"""

    def __init__(self, tool_name: str, success_rate: float, usage_count: int,
                 avg_time_ms: float, last_used_at: datetime = None):
        self.tool_name = tool_name
        self.success_rate = success_rate  # 0-100
        self.usage_count = usage_count
        self.avg_time_ms = avg_time_ms
        self.last_used_at = last_used_at

    def to_dict(self):
        return {
            'tool_name': self.tool_name,
            'success_rate': round(self.success_rate, 2),
            'usage_count': self.usage_count,
            'avg_time_ms': int(self.avg_time_ms) if self.avg_time_ms else 0,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
        }

    @staticmethod
    def from_row(row):
        """从数据库查询结果创建视图对象"""
        return ToolSuccessRateView(
            tool_name=row.tool_name,
            success_rate=float(row.success_rate or 0),
            usage_count=int(row.usage_count or 0),
            avg_time_ms=float(row.avg_time_ms or 0),
            last_used_at=row.last_used_at
        )


class UserToolPreference:
    """用户工具偏好统计（用于路由学习）"""

    def __init__(self, user_id: uuid.UUID, tool_name: str, preference_score: float,
                 last_30d_success_rate: float, last_30d_usage: int):
        self.user_id = user_id
        self.tool_name = tool_name
        self.preference_score = preference_score  # 0-1, based on success rate + usage
        self.last_30d_success_rate = last_30d_success_rate
        self.last_30d_usage = last_30d_usage

    def to_dict(self):
        return {
            'tool_name': self.tool_name,
            'preference_score': round(self.preference_score, 3),
            'last_30d_success_rate': round(self.last_30d_success_rate, 2),
            'last_30d_usage': self.last_30d_usage,
        }
