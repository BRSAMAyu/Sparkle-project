"""
Memory Evolution Models
记忆演化模型 - 支持记忆变化追踪和预测
"""
from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, JSON, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, BaseModel

# SQLite compatibility for JSONB and ARRAY
JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
ArrayGUIDCompat = ARRAY(GUID()).with_variant(JSON(), "sqlite")
ArrayIntegerCompat = ARRAY(Integer()).with_variant(JSON(), "sqlite")


class MemoryEvolution(BaseModel):
    """
    Memory Evolution Record
    记忆演化记录表 - 追踪记忆的所有变化
    """
    __tablename__ = "memory_evolutions"

    # Memory reference
    memory_id: Mapped[Any] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
        doc="关联的记忆ID"
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="记忆类型: preference, goal, episodic"
    )

    # Change details
    old_value: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, doc="旧值")
    new_value: Mapped[Any] = mapped_column(JSONBCompat, nullable=False, doc="新值")
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="变化类型: create, update, delete, merge, split"
    )
    change_reason: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="变化原因: user_edit, system_inference, feedback_learning, conflict_resolution"
    )

    # Confidence changes
    confidence_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, doc="置信度变化量")
    confidence_before: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, doc="变化前置信度")
    confidence_after: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, doc="变化后置信度")

    # Evidence changes
    evidence_count_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0, doc="变化前证据数量")
    evidence_count_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0, doc="变化后证据数量")
    new_evidence_ids: Mapped[Any] = mapped_column(ArrayGUIDCompat, nullable=True, doc="新增证据ID列表")

    # Impact analysis
    impact_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="影响分数 0-1"
    )
    affected_decisions: Mapped[Any] = mapped_column(
        ArrayGUIDCompat,
        nullable=True,
        doc="受影响的决策ID列表"
    )
    affected_memories: Mapped[Any] = mapped_column(
        ArrayGUIDCompat,
        nullable=True,
        doc="受影响的其他记忆ID列表"
    )

    # Context
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=True, doc="触发事件类型")
    trigger_source: Mapped[str] = mapped_column(String(100), nullable=True, doc="触发来源: agent, tool, user")
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=True, doc="关联的工作流ID")

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="创建时间")

    def __repr__(self):
        return f"<MemoryEvolution(id={self.id}, memory_id={self.memory_id}, change_reason={self.change_reason})>"


class EvolutionPrediction(BaseModel):
    """
    Evolution Prediction
    演化预测表 - 预测记忆的未来变化
    """
    __tablename__ = "evolution_predictions"

    # Memory reference
    memory_id: Mapped[Any] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
        doc="预测的记忆ID"
    )

    # Prediction details
    prediction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="预测类型: decay, strengthen, conflict"
    )
    probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="预测置信度 0-1"
    )
    time_horizon: Mapped[int] = mapped_column(Integer, nullable=True, doc="预测时间范围（天）")

    # Predicted outcome
    predicted_value: Mapped[Any] = mapped_column(JSONBCompat, nullable=True, doc="预测的未来值")
    predicted_confidence: Mapped[float] = mapped_column(Float, nullable=True, doc="预测的置信度")

    # Influencing factors
    factors: Mapped[Any] = mapped_column(JSONBCompat, nullable=True, doc="影响因素分析")
    similar_evolutions: Mapped[Any] = mapped_column(ArrayIntegerCompat, nullable=True, doc="相似演化历史ID列表")

    # Validation
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, doc="预测创建时间")
    actualized_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True, doc="实际发生时间")
    actualization_error: Mapped[float] = mapped_column(Float, nullable=True, doc="预测误差")

    def __repr__(self):
        return f"<EvolutionPrediction(id={self.id}, memory_id={self.memory_id}, type={self.prediction_type})>"
