"""
A/B Test Experiment Models
A/B测试实验模型 - 支持实验生命周期管理、变体配置、指标跟踪
"""
import uuid
from enum import Enum
from typing import Optional, List, Any, Dict
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ExperimentStatus(str, Enum):
    """实验状态枚举"""
    CREATED = "created"  # 已创建
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"  # 已归档


class MetricType(str, Enum):
    """指标类型枚举"""
    SUCCESS = "success"  # 成功指标（二值）
    LATENCY = "latency"  # 延迟指标（连续值）
    ENGAGEMENT = "engagement"  # 参与度指标（计数）
    CONVERSION = "conversion"  # 转化率指标（比例）
    CUSTOM = "custom"  # 自定义指标


class ABExperiment(BaseModel):
    """
    A/B测试实验主表
    管理实验的基本信息和生命周期
    """
    __tablename__ = "ab_experiments"

    # 基本信息
    name = Column(String(200), nullable=False, doc="实验名称")
    description = Column(Text, nullable=True, doc="实验描述")
    hypothesis = Column(Text, nullable=False, doc="实验假设")

    # 状态管理
    status = Column(
        String(20),
        nullable=False,
        default="created",
        index=True,
        doc="实验状态: created, running, paused, completed, archived"
    )

    # 创建者
    created_by = Column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="创建者ID"
    )

    # 统计参数
    sample_size_target = Column(Integer, nullable=True, doc="目标样本量")
    significance_level = Column(Float, nullable=False, default=0.05, doc="显著性水平 (alpha)")
    power = Column(Float, nullable=False, default=0.8, doc="统计功效 (1-beta)")
    minimum_detectable_effect = Column(Float, nullable=True, doc="最小可检测效应 (相对提升)")

    # 时间管理
    start_date = Column(DateTime, nullable=True, index=True, doc="实验开始时间")
    end_date = Column(DateTime, nullable=True, doc="实验结束时间")

    # 实验结论
    conclusion = Column(Text, nullable=True, doc="实验结论")
    winning_variant_id = Column(
        GUID(),
        ForeignKey("ab_experiment_variants.id", ondelete="SET NULL"),
        nullable=True,
        doc="获胜变体ID"
    )

    # 元数据
    extra_metadata = Column(JSONBCompat, nullable=True, doc="额外的元数据信息")

    # 关系
    variants = relationship(
        "ABExperimentVariant",
        back_populates="experiment",
        foreign_keys="[ABExperimentVariant.experiment_id]",
        cascade="all, delete-orphan",
        order_by="ABExperimentVariant.created_at"
    )
    metrics = relationship(
        "ABExperimentMetric",
        back_populates="experiment",
        cascade="all, delete-orphan"
    )
    assignments = relationship(
        "ABExperimentAssignment",
        back_populates="experiment",
        cascade="all, delete-orphan"
    )
    winning_variant = relationship(
        "ABExperimentVariant",
        foreign_keys=[winning_variant_id],
        post_update=True
    )

    def __repr__(self):
        return f"<ABExperiment(id={self.id}, name={self.name}, status={self.status})>"


class ABExperimentVariant(BaseModel):
    """
    A/B测试实验变体表
    定义实验的不同变体（对照组和实验组）
    """
    __tablename__ = "ab_experiment_variants"

    # 基本信息
    experiment_id = Column(
        GUID(),
        ForeignKey("ab_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="所属实验ID"
    )
    variant_name = Column(String(100), nullable=False, doc="变体名称")
    description = Column(Text, nullable=True, doc="变体描述")

    # 变体类型
    is_control = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="是否为对照组"
    )

    # 配置信息
    prompt_version = Column(String(50), nullable=True, doc="Prompt版本标识")
    configuration = Column(JSONBCompat, nullable=True, doc="变体配置（JSON格式）")

    # 流量分配
    allocation_weight = Column(Float, nullable=False, default=0.5, doc="分配权重")
    traffic_allocation_percentage = Column(
        Float,
        nullable=False,
        default=50.0,
        doc="流量分配百分比"
    )

    # 元数据
    extra_metadata = Column(JSONBCompat, nullable=True, doc="额外的元数据信息")

    # 关系
    experiment = relationship("ABExperiment", back_populates="variants", foreign_keys=[experiment_id])
    metrics = relationship(
        "ABExperimentMetric",
        back_populates="variant",
        cascade="all, delete-orphan"
    )
    assignments = relationship(
        "ABExperimentAssignment",
        back_populates="variant",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ABExperimentVariant(id={self.id}, name={self.variant_name}, is_control={self.is_control})>"


class ABExperimentMetric(BaseModel):
    """
    A/B测试实验指标表
    记录各变体的指标数据
    """
    __tablename__ = "ab_experiment_metrics"

    # 关联信息
    experiment_id = Column(
        GUID(),
        ForeignKey("ab_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="实验ID"
    )
    variant_id = Column(
        GUID(),
        ForeignKey("ab_experiment_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="变体ID"
    )
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="用户ID（可选，用于用户级别指标）"
    )

    # 指标信息
    metric_name = Column(
        String(100),
        nullable=False,
        index=True,
        doc="指标名称: success, latency, engagement, etc."
    )
    metric_value = Column(Float, nullable=False, doc="指标值")
    metric_type = Column(
        String(50),
        nullable=False,
        doc="指标类型: success, latency, engagement, conversion, custom"
    )

    # 上下文数据
    context_data = Column(JSONBCompat, nullable=True, doc="上下文信息（JSON格式）")

    # 时间戳
    timestamp = Column(DateTime, nullable=False, index=True, doc="指标记录时间")

    # 关系
    experiment = relationship("ABExperiment", back_populates="metrics")
    variant = relationship("ABExperimentVariant", back_populates="metrics")

    def __repr__(self):
        return f"<ABExperimentMetric(id={self.id}, name={self.metric_name}, value={self.metric_value})>"


class ABExperimentAssignment(BaseModel):
    """
    A/B测试实验分配表
    记录用户到实验变体的分配关系
    """
    __tablename__ = "ab_experiment_assignments"

    # 关联信息
    experiment_id = Column(
        GUID(),
        ForeignKey("ab_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="实验ID"
    )
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="用户ID"
    )
    variant_id = Column(
        GUID(),
        ForeignKey("ab_experiment_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="分配到的变体ID"
    )

    # 分配信息
    assignment_date = Column(DateTime, nullable=False, doc="分配时间")

    # 排除标记
    is_excluded = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="是否被排除在实验外"
    )
    exclusion_reason = Column(String(200), nullable=True, doc="排除原因")

    # 关系
    experiment = relationship("ABExperiment", back_populates="assignments")
    variant = relationship("ABExperimentVariant", back_populates="assignments")

    def __repr__(self):
        return f"<ABExperimentAssignment(id={self.id}, user_id={self.user_id}, variant_id={self.variant_id})>"
