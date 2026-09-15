"""
生词本与词典模型 (Vocabulary & Dictionary Models)
"""
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

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

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    word = Column(String(100), nullable=False, index=True)
    phonetic = Column(String(100), nullable=True)
    definition = Column(Text, nullable=False)

    # 旧版艾宾浩斯复习字段 (保留向后兼容)
    mastery_level = Column(Integer, default=0, nullable=True)  # DEPRECATED: 0-7 阶段

    # 统一复习系统字段
    importance = Column(Integer, default=3, nullable=False)  # 1-5 星，5 星为关键词汇
    consecutive_correct = Column(Integer, default=0, nullable=False)  # 当前连续正确
    correct_review_count = Column(Integer, default=0, nullable=False)  # 总正确次数

    next_review_at = Column(DateTime, default=datetime.utcnow)
    last_review_at = Column(DateTime, nullable=True)
    review_count = Column(Integer, default=0)

    # 扩展元数据
    context_sentence = Column(Text, nullable=True)  # 来源例句
    source_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)
    part_of_speech = Column(String(50), nullable=True)  # 词性
    source_translation_id = Column(String(100), nullable=True)  # 来源翻译 ID
    tags = Column(JSON, default=list)

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

    word = Column(String(100), nullable=False, index=True, unique=True)
    phonetic = Column(String(100), nullable=True)
    pos = Column(String(50), nullable=True) # Part of speech
    definitions = Column(JSON, nullable=False) # List of strings or structured data
    examples = Column(JSON, nullable=True) # List of strings
    source = Column(String(50), nullable=True) # e.g., 'Oxford', 'Longman'

    __table_args__ = (
        Index('idx_dict_word', 'word'),
    )
