"""
Cognitive Prism Models
认知棱镜相关模型
"""
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import BaseModel, GUID


class CognitiveFragment(BaseModel):
    """
    行为/闪念碎片表 (Cognitive Fragments)
    记录用户的主动输入(闪念)和被动捕捉(行为)
    """
    __tablename__ = "cognitive_fragments"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True) # 可选关联任务
    
    # 来源类型: capsule (闪念), interceptor (拦截器), behavior (隐式行为)
    source_type = Column(String(20), nullable=False) 
    
    # 内容: 用户输入的内容 或 系统生成的描述
    content = Column(Text, nullable=False)
    
    # AI 预分析结果
    sentiment = Column(String(20), nullable=True)   # anxious, bored, neutral...
    tags = Column(JSON, nullable=True)     # ['procrastination', 'distraction']
    
    # 语义向量
    embedding = Column(Vector(1536), nullable=True)

    # 关系
    user = relationship("User", backref="cognitive_fragments")
    task = relationship("Task")


class BehaviorPattern(BaseModel):
    """
    归因定式表 (Behavior Patterns)
    基于碎片分析出的行为定式
    """
    __tablename__ = "behavior_patterns"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    
    pattern_name = Column(String(100), nullable=False)   # e.g., "Planning Fallacy"
    pattern_type = Column(String(50), nullable=False)   # cognitive, emotional, execution
    
    description = Column(Text, nullable=True)           # AI 生成的具体描述
    solution_text = Column(Text, nullable=True)         # 建议文案
    
    # 关联的 cognitive_fragments ID 数组
    # 注意: 这里存储 ID 数组，应用层处理关联，或者使用多对多关系表。
    # 为了简化，设计文档建议使用 ID 数组。在 SQLAlchemy 中可以使用 ARRAY(GUID)
    evidence_ids = Column(JSON, nullable=True)
    
    is_archived = Column(Boolean, default=False) # 用户是否已克服此定式

    # 关系
    user = relationship("User", backref="behavior_patterns")
