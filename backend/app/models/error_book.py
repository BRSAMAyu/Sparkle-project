"""
Error Book Models (SQLAlchemy) - Phase 4 Optimized
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, func, Index, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.db.session import Base

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
ArrayStringCompat = ARRAY(String).with_variant(JSON(), "sqlite")
ArrayUUIDCompat = ARRAY(UUID(as_uuid=True)).with_variant(JSON(), "sqlite")
ArrayTextCompat = ARRAY(Text).with_variant(JSON(), "sqlite")

class ErrorRecord(Base):
    """
    ErrorRecord - 错题本核心模型
    采用 "Flat Table" 设计，利用 PostgreSQL 的 JSONB 和 ARRAY 特性减少 JOIN 查询。
    """
    __tablename__ = "error_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # --- 核心内容区 ---
    subject_code = Column(String(50), nullable=False) # e.g., 'math', 'physics'
    chapter = Column(String(100), nullable=True)      # 章节/标签
    
    # 题目内容 (OCR 兜底策略: question_text 可以为空，如果 question_image_url 存在)
    question_text = Column(Text, nullable=True)
    question_image_url = Column(String(500), nullable=True)
    user_answer = Column(Text, nullable=True)
    correct_answer = Column(Text, nullable=True)
    
    # --- 间隔复习状态 (SM-2 变体) ---
    mastery_level = Column(Float, default=0.0)      # 0.0 ~ 1.0
    easiness_factor = Column(Float, default=2.5)    # 难度系数 (SM-2 E-Factor)
    review_count = Column(Integer, default=0)
    interval_days = Column(Float, default=0.0)      # 当前间隔天数 (支持小数, 配合 Fuzzing)
    
    next_review_at = Column(DateTime(timezone=True), server_default=func.now())
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # --- AI 智能分析 (JSONB) ---
    # 结构: { "error_type": "...", "root_cause": "...", "study_suggestions": "...", "ocr_text": "..." }
    latest_analysis = Column(JSONBCompat, nullable=True)
    
    # 认知维度标签 (e.g., ['logic', 'memory'])
    cognitive_tags = Column(ArrayStringCompat, default=list)
    # AI 深度分析摘要 (Text)
    ai_analysis_summary = Column(Text, nullable=True)
    
    # --- 知识图谱关联 ---
    # 强关联: 已存在的知识点 ID
    linked_knowledge_node_ids = Column(ArrayUUIDCompat, default=list)
    # 弱关联: AI 建议创建的新概念/标签 (解决冷启动问题)
    suggested_concepts = Column(ArrayTextCompat, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="error_records")

    # Indexes
    __table_args__ = (
        Index('idx_errors_user_review', 'user_id', 'next_review_at', postgresql_where=(mastery_level < 1.0)),
        Index('idx_errors_subject', 'subject_code'),
        Index('idx_error_records_cognitive_tags', 'cognitive_tags', postgresql_using='gin'),
    )
