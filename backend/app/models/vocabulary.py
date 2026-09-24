"""
生词本与词典模型 (Vocabulary & Dictionary Models)
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class WordBook(BaseModel):
    """
    用户生词本
    记录用户收藏的单词及其复习进度

    统一复习系统:
    - importance: 1-5 星，5 星为最需要复习的词汇
    - consecutive_correct: 当前连续正确次数
    - correct_review_count: 总正确次数
    - next_review_at: 基于 importance 和 consecutive_correct 计算得出
    """
    __tablename__ = "word_books"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    word: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phonetic: Mapped[str] = mapped_column(String(100), nullable=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)

    # 旧版艾宾浩斯复习字段 (保留向后兼容)
    mastery_level: Mapped[int] = mapped_column(Integer, default=0, nullable=True)  # DEPRECATED: 0-7 阶段

    # 统一复习系统字段
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1-5 星，5 星为关键词汇
    consecutive_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 当前连续正确
    correct_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 总正确次数

    next_review_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    last_review_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    # 扩展元数据
    context_sentence: Mapped[str] = mapped_column(Text, nullable=True)  # 来源例句
    source_task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)
    part_of_speech: Mapped[str] = mapped_column(String(50), nullable=True)  # 词性
    source_translation_id: Mapped[str] = mapped_column(String(100), nullable=True)  # 来源翻译 ID
    tags: Mapped[Any] = mapped_column(JSON, default=list, nullable=True)

    # 关系
    user = relationship("User")
    task = relationship("Task")

    __table_args__ = (
        UniqueConstraint('user_id', 'word', name='uq_user_word'),
        Index('idx_wordbook_review', 'user_id', 'next_review_at'),
    )

class DictionaryEntry(BaseModel):
    """
    系统词典库 (导入自牛津/朗文等)
    """
    __tablename__ = "dictionary_entries"

    word: Mapped[str] = mapped_column(String(100), nullable=False, index=True, unique=True)
    phonetic: Mapped[str] = mapped_column(String(100), nullable=True)
    pos: Mapped[str] = mapped_column(String(50), nullable=True) # Part of speech
    definitions: Mapped[Any] = mapped_column(JSON, nullable=False) # List of strings or structured data
    examples: Mapped[Any] = mapped_column(JSON, nullable=True) # List of strings
    source: Mapped[str] = mapped_column(String(50), nullable=True) # e.g., 'Oxford', 'Longman'

    __table_args__ = (
        Index('idx_dict_word', 'word'),
    )
