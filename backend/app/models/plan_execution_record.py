"""
PlanExecutionRecord - 方案执行记录模型

记录方案执行后的验证结果，用于反馈学习和分析
"""
from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class PlanExecutionRecord(BaseModel):
    """
    方案执行验证记录

    用于记录每次方案执行后的验证结果，支持：
    - 质量分数计算
    - 成功标准检查
    - 问题追踪
    - 反馈学习

    字段:
        plan_id: 关联的计划ID
        user_id: 用户ID
        validation_status: 验证状态 (passed/failed/partial)
        quality_score: 质量分数 (0-1)
        criteria_results: 成功标准检查结果 (JSONB)
        total_tools: 工具执行总数
        successful_tools: 成功执行的工具数
        failed_tools: 失败的工具数
        issues: 问题列表 (JSONB)
        user_satisfaction: 用户满意度 (1-5, 可选)
        user_feedback: 用户反馈文本 (可选)
        applied_to_learning: 是否已应用到学习系统
    """

    __tablename__ = "plan_execution_records"

    # 外键关联
    plan_id = Column(
        GUID(),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 验证结果
    validation_status = Column(
        String(20),
        nullable=False,
        index=True
    )  # passed, failed, partial
    quality_score = Column(Float, default=0.0)  # 0-1

    # 成功标准检查结果
    criteria_results = Column(JSONBCompat, default=dict)

    # 工具执行统计
    total_tools = Column(Integer, default=0)
    successful_tools = Column(Integer, default=0)
    failed_tools = Column(Integer, default=0)

    # 问题列表
    issues = Column(JSONBCompat, default=list)

    # 用户反馈 (后续收集)
    user_satisfaction = Column(Integer, nullable=True)  # 1-5
    user_feedback = Column(Text, nullable=True)

    # 学习标记
    applied_to_learning = Column(Boolean, default=False)

    # 关系
    plan = relationship("Plan", backref="execution_records")
    user = relationship("User", backref="plan_execution_records")

    # 索引
    __table_args__ = (
        Index("idx_execution_records_plan_user", "plan_id", "user_id"),
        Index("idx_execution_records_status", "validation_status"),
        Index("idx_execution_records_created", "created_at"),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id),
            "user_id": str(self.user_id),
            "validation_status": self.validation_status,
            "quality_score": self.quality_score,
            "criteria_results": self.criteria_results or {},
            "total_tools": self.total_tools,
            "successful_tools": self.successful_tools,
            "failed_tools": self.failed_tools,
            "issues": self.issues or [],
            "user_satisfaction": self.user_satisfaction,
            "user_feedback": self.user_feedback,
            "applied_to_learning": self.applied_to_learning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<PlanExecutionRecord("
            f"plan_id={self.plan_id}, "
            f"status={self.validation_status}, "
            f"score={self.quality_score:.2f}"
            f")>"
        )
