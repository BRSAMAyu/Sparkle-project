"""
Cognitive Prism Models
认知棱镜相关模型
"""
import enum
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, CheckConstraint, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.models.base import GUID, BaseModel

VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")
class AnalysisStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PatternType(enum.StrEnum):
    COGNITIVE = "cognitive"
    EMOTIONAL = "emotional"
    EXECUTION = "execution"

class CognitiveFragment(BaseModel):
    """
    行为/闪念碎片表 (Cognitive Fragments)
    记录用户的主动输入(闪念)和被动捕捉(行为)
    """
    __tablename__ = "cognitive_fragments"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True) # 可选关联任务

    # 状态追踪 (v2.3 Patch)
    analysis_status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    error_message: Mapped[str] = mapped_column(String(500), nullable=True)

    # 来源类型: capsule (闪念), interceptor (拦截器), behavior (隐式行为)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # 资源信息 (v2.3)
    resource_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False) # text, audio, image
    resource_url: Mapped[str] = mapped_column(String(512), nullable=True) # oss url

    # 内容: 用户输入的内容 或 系统生成的描述
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI 预分析结果
    sentiment: Mapped[str] = mapped_column(String(20), nullable=True)   # anxious, bored, neutral...

    # 画像版本与溯源 (V3.1)
    persona_version: Mapped[str] = mapped_column(String(50), nullable=True)
    source_event_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # 敏感标签加密存储 (V3.1)
    sensitive_tags_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    sensitive_tags_version: Mapped[int] = mapped_column(Integer, default=1, nullable=True)
    sensitive_tags_key_id: Mapped[str] = mapped_column(String(100), nullable=True)

    # 标签系统 (v2.3 Enhanced)
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)     # Generic tags
    error_tags: Mapped[Any] = mapped_column(JSON, nullable=True) # Structured error tags e.g. ["planning.underestimate", "execution.procrastination"]
    context_tags: Mapped[Any] = mapped_column(JSON, nullable=True) # Context: { "location": "library", "mood": "anxious", "people": "alone" }

    # 严重程度 (v2.3)
    severity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5
    __table_args__ = (
        CheckConstraint("severity >= 1 AND severity <= 5", name="ck_cognitive_fragment_severity"),
    )

    # 语义向量
    embedding = deferred(Column(VectorCompat, nullable=True))

    # 关系
    user = relationship("User", backref="cognitive_fragments")
    task = relationship("Task")


class BehaviorPattern(BaseModel):
    """
    归因定式表 (Behavior Patterns)
    基于碎片分析出的行为定式
    """
    __tablename__ = "behavior_patterns"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g., "Planning Fallacy"
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)   # cognitive, emotional, execution

    description: Mapped[str] = mapped_column(Text, nullable=True)           # AI 生成的具体描述
    solution_text: Mapped[str] = mapped_column(Text, nullable=True)         # 建议文案

    # 关联的 cognitive_fragments ID 数组
    evidence_ids: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 统计指标 (v2.3)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=True) # AI Confidence
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=True)        # Occurrences count

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True) # 用户是否已克服此定式
    last_observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_decay_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    user = relationship("User", backref="behavior_patterns")
