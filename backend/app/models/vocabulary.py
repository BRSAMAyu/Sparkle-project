"""
生词本与词典模型 (Vocabulary & Dictionary Models)
"""
import enum
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    ForeignKey, DateTime, Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID

class WordBook(BaseModel):
    """
    用户生词本
    记录用户收藏的单词及其复习进度
    """
    __tablename__ = "word_books"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    word = Column(String(100), nullable=False, index=True)
    phonetic = Column(String(100), nullable=True)
    definition = Column(Text, nullable=False)
    
    # 艾宾浩斯复习字段
    mastery_level = Column(Integer, default=0) # 0-7 阶段
    next_review_at = Column(DateTime, default=datetime.utcnow)
    last_review_at = Column(DateTime, nullable=True)
    review_count = Column(Integer, default=0)
    
    # 元数据
    context_sentence = Column(Text, nullable=True) # 来源例句
    source_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)
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
