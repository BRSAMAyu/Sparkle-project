"""
Agent Execution Statistics Models
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AgentExecutionStats(Base):
    """Agent执行统计表"""
    __tablename__ = 'agent_execution_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    request_id = Column(String(255), nullable=False)

    # Agent information
    agent_type = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(100), nullable=True)

    # Execution metrics
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False)  # success, failed, timeout

    # Tool/operation details
    tool_name = Column(String(100), nullable=True)
    operation = Column(String(255), nullable=True)

    # Metadata (Use JSON for SQLite compatibility, JSONB for PostgreSQL)
    extra_metadata = Column(JSON, nullable=True, default={})
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('ix_agent_stats_user_agent_type', 'user_id', 'agent_type'),
    )

    def __repr__(self):
        return f"<AgentExecutionStats(id={self.id}, user={self.user_id}, agent={self.agent_type}, duration={self.duration_ms}ms)>"


# Materialized View representation (read-only)
class AgentStatsSummary:
    """Agent统计汇总（物化视图）"""
    # This is just a representation class for query results
    # The actual materialized view is created via Alembic migration

    def __init__(self, row):
        self.user_id = row.user_id
        self.agent_type = row.agent_type
        self.execution_count = row.execution_count
        self.avg_duration_ms = row.avg_duration_ms
        self.max_duration_ms = row.max_duration_ms
        self.min_duration_ms = row.min_duration_ms
        self.success_count = row.success_count
        self.failure_count = row.failure_count
        self.last_used_at = row.last_used_at

    @property
    def success_rate(self):
        if self.execution_count == 0:
            return 0
        return (self.success_count / self.execution_count) * 100

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'agent_type': self.agent_type,
            'execution_count': self.execution_count,
            'avg_duration_ms': int(self.avg_duration_ms) if self.avg_duration_ms else 0,
            'max_duration_ms': self.max_duration_ms or 0,
            'min_duration_ms': self.min_duration_ms or 0,
            'success_rate': round(self.success_rate, 2),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }
