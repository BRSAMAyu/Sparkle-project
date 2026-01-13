"""
Cognitive Prism Models
认知棱镜相关模型
"""
import uuid
import enum
from sqlalchemy import Column, String, Text, ForeignKey, Integer, Boolean, JSON, Float, Enum
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import BaseModel, GUID

VectorCompat = Vector(1536).with_variant(JSON(), "sqlite")
class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class CognitiveFragment(BaseModel):
    """
    行为/闪念碎片表 (Cognitive Fragments)
    记录用户的主动输入(闪念)和被动捕捉(行为)
    """
    __tablename__ = "cognitive_fragments"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True) # 可选关联任务
    
    # 状态追踪 (v2.3 Patch)
    analysis_status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    error_message = Column(String(500), nullable=True)

    # 来源类型: capsule (闪念), interceptor (拦截器), behavior (隐式行为)
    source_type = Column(String(20), nullable=False) 
    
    # 资源信息 (v2.3)
    resource_type = Column(String(20), default="text", nullable=False) # text, audio, image
    resource_url = Column(String(512), nullable=True) # oss url
    
    # 内容: 用户输入的内容 或 系统生成的描述
    content = Column(Text, nullable=False)
    
    # AI 预分析结果
    sentiment = Column(String(20), nullable=True)   # anxious, bored, neutral...

    # 画像版本与溯源 (V3.1)
    persona_version = Column(String(50), nullable=True)
    source_event_id = Column(String(64), nullable=True, index=True)
    
    # 敏感标签加密存储 (V3.1)
    sensitive_tags_encrypted = Column(Text, nullable=True)
    sensitive_tags_version = Column(Integer, default=1, nullable=True)
    sensitive_tags_key_id = Column(String(100), nullable=True)
    
    # 标签系统 (v2.3 Enhanced)
    tags = Column(JSON, nullable=True)     # Generic tags
    error_tags = Column(JSON, nullable=True) # Structured error tags e.g. ["planning.underestimate", "execution.procrastination"]
    context_tags = Column(JSON, nullable=True) # Context: { "location": "library", "mood": "anxious", "people": "alone" }
    
    # 严重程度 (v2.3)
    severity = Column(Integer, default=1, nullable=False) # 1-5

    # 语义向量
    embedding = Column(VectorCompat, nullable=True)

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
    evidence_ids = Column(JSON, nullable=True)
    
    # 统计指标 (v2.3)
    confidence_score = Column(Float, default=0.0) # AI Confidence
    frequency = Column(Integer, default=1)        # Occurrences count
    
    is_archived = Column(Boolean, default=False) # 用户是否已克服此定式

    # 关系
    user = relationship("User", backref="behavior_patterns")
