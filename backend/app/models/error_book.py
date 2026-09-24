"""
Error Book Models (SQLAlchemy) - Phase 4 Optimized
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.session import Base

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
ArrayStringCompat = ARRAY(String).with_variant(JSON(), "sqlite")


class _UUIDListJSON(TypeDecorator):
    """sqlite 下 ARRAY(UUID) 的 JSON 兼容变体（prod 走原生 ARRAY(UUID)，不经此类型）。

    JSON 序列化不认 UUID 对象——CP-03 E2E 首次以 ORM 直接写入该列时暴露；
    绑定前统一转字符串，读侧由服务层 _coerce_uuid/str() 容错（与既有
    mastery 同步读法一致）。
    """

    impl = JSON
    cache_ok = True

    def bind_processor(self, dialect):
        super_process = super().bind_processor(dialect)

        def process(value):
            if isinstance(value, (list, tuple)):
                value = [str(item) if isinstance(item, uuid.UUID) else item for item in value]
            return super_process(value) if super_process is not None else value

        return process


ArrayUUIDCompat = ARRAY(UUID(as_uuid=True)).with_variant(_UUIDListJSON(), "sqlite")
ArrayTextCompat = ARRAY(Text).with_variant(JSON(), "sqlite")


class ErrorRecord(Base):
    """
    ErrorRecord - 错题本核心模型
    采用 "Flat Table" 设计，利用 PostgreSQL 的 JSONB 和 ARRAY 特性减少 JOIN 查询。
    """

    __tablename__ = "error_records"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # --- 核心内容区 ---
    subject_code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'math', 'physics'
    chapter: Mapped[str] = mapped_column(String(100), nullable=True)  # 章节/标签

    # 题目内容 (OCR 兜底策略: question_text 可以为空，如果 question_image_url 存在)
    question_text: Mapped[str] = mapped_column(Text, nullable=True)
    question_image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    user_answer: Mapped[str] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=True)

    # --- 间隔复习状态 (SM-2 变体) ---
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=True)  # 0.0 ~ 1.0
    easiness_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=True)  # 难度系数 (SM-2 E-Factor)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=True)  # 当前间隔天数 (支持小数, 配合 Fuzzing)

    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- AI 智能分析 (JSONB) ---
    # 结构: { "error_type": "...", "root_cause": "...", "study_suggestions": "...", "ocr_text": "..." }
    latest_analysis: Mapped[Any] = mapped_column(JSONBCompat, nullable=True)

    # 认知维度标签 (e.g., ['logic', 'memory'])
    cognitive_tags: Mapped[Any] = mapped_column(ArrayStringCompat, default=list, nullable=True)
    # AI 深度分析摘要 (Text)
    ai_analysis_summary: Mapped[str] = mapped_column(Text, nullable=True)

    # --- 知识图谱关联 ---
    # 主受影响节点：用于错题本列表直连星图聚焦
    affected_node_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=True)
    # 本题造成的掌握度变化，负数表示错题诊断扣分
    mastery_delta: Mapped[float] = mapped_column(Float, nullable=True)
    # 强关联: 已存在的知识点 ID
    linked_knowledge_node_ids: Mapped[Any] = mapped_column(ArrayUUIDCompat, default=list, nullable=True)
    # 弱关联: AI 建议创建的新概念/标签 (解决冷启动问题)
    suggested_concepts: Mapped[Any] = mapped_column(ArrayTextCompat, default=list, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    # Relationships
    user = relationship("User", back_populates="error_records")

    # Indexes
    __table_args__ = (
        Index("idx_errors_user_review", "user_id", "next_review_at", postgresql_where=(mastery_level < 1.0)),
        Index("idx_errors_subject", "subject_code"),
        Index("idx_error_records_cognitive_tags", "cognitive_tags", postgresql_using="gin"),
    )
