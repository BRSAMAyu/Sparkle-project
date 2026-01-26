"""
Memory Evolution Models
记忆演化模型 - 支持记忆变化追踪和预测
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, JSON, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class MemoryEvolution(BaseModel):
    """
    Memory Evolution Record
    记忆演化记录表 - 追踪记忆的所有变化
    """
    __tablename__ = "memory_evolutions"

    # Memory reference
    memory_id = Column(
        GUID(),
        nullable=False,
        index=True,
        doc="关联的记忆ID"
    )
    memory_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="记忆类型: preference, goal, episodic"
    )

    # Change details
    old_value = Column(JSONBCompat, nullable=False, doc="旧值")
    new_value = Column(JSONBCompat, nullable=False, doc="新值")
    change_type = Column(
        String(50),
        nullable=False,
        doc="变化类型: create, update, delete, merge, split"
    )
    change_reason = Column(
        String(100),
        nullable=False,
        index=True,
        doc="变化原因: user_edit, system_inference, feedback_learning, conflict_resolution"
    )

    # Confidence changes
    confidence_delta = Column(Float, nullable=False, default=0.0, doc="置信度变化量")
    confidence_before = Column(Float, nullable=False, default=0.0, doc="变化前置信度")
    confidence_after = Column(Float, nullable=False, default=0.0, doc="变化后置信度")

    # Evidence changes
    evidence_count_before = Column(Integer, nullable=False, default=0, doc="变化前证据数量")
    evidence_count_after = Column(Integer, nullable=False, default=0, doc="变化后证据数量")
    new_evidence_ids = Column(ARRAY(GUID()), nullable=True, doc="新增证据ID列表")

    # Impact analysis
    impact_score = Column(
        Float,
        nullable=False,
        default=0.0,
        doc="影响分数 0-1"
    )
    affected_decisions = Column(
        ARRAY(GUID()),
        nullable=True,
        doc="受影响的决策ID列表"
    )
    affected_memories = Column(
        ARRAY(GUID()),
        nullable=True,
        doc="受影响的其他记忆ID列表"
    )

    # Context
    trigger_event = Column(String(100), nullable=True, doc="触发事件类型")
    trigger_source = Column(String(100), nullable=True, doc="触发来源: agent, tool, user")
    workflow_id = Column(String(100), nullable=True, doc="关联的工作流ID")

    # Timestamp
    created_at = Column(DateTime, nullable=False, index=True, doc="创建时间")

    def __repr__(self):
        return f"<MemoryEvolution(id={self.id}, memory_id={self.memory_id}, change_reason={self.change_reason})>"


class EvolutionPrediction(BaseModel):
    """
    Evolution Prediction
    演化预测表 - 预测记忆的未来变化
    """
    __tablename__ = "evolution_predictions"

    # Memory reference
    memory_id = Column(
        GUID(),
        nullable=False,
        index=True,
        doc="预测的记忆ID"
    )

    # Prediction details
    prediction_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="预测类型: decay, strengthen, conflict"
    )
    probability = Column(
        Float,
        nullable=False,
        doc="预测置信度 0-1"
    )
    time_horizon = Column(Integer, nullable=True, doc="预测时间范围（天）")

    # Predicted outcome
    predicted_value = Column(JSONBCompat, nullable=True, doc="预测的未来值")
    predicted_confidence = Column(Float, nullable=True, doc="预测的置信度")

    # Influencing factors
    factors = Column(JSONBCompat, nullable=True, doc="影响因素分析")
    similar_evolutions = Column(ARRAY(Integer()), nullable=True, doc="相似演化历史ID列表")

    # Validation
    created_at = Column(DateTime, nullable=False, index=True, doc="预测创建时间")
    actualized_at = Column(DateTime, nullable=True, index=True, doc="实际发生时间")
    actualization_error = Column(Float, nullable=True, doc="预测误差")

    def __repr__(self):
        return f"<EvolutionPrediction(id={self.id}, memory_id={self.memory_id}, type={self.prediction_type})>"
