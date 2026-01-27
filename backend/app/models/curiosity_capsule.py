"""
Curiosity Capsule Model
"""
import enum
from sqlalchemy import (
    Column, String, Text, Enum,
    ForeignKey, DateTime, Boolean, Float, Integer, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel, GUID

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
from app.models.task import Task


class DepthLevel(enum.Enum):
    """胶囊深度级别"""
    SHALLOW = "shallow"   # 浅度 - 快速响应，轻量级内容
    MEDIUM = "medium"     # 中度 - 标准深度，平衡内容
    DEEP = "deep"         # 深度 - 深度推理，详细内容


class CuriosityCapsule(BaseModel):
    """
    好奇心胶囊模型

    字段:
        user_id: 所属用户ID
        title: 标题
        content: 内容（Markdown）
        related_subject: 相关科目 (Optional, String for now)
        related_task_id: 相关任务ID (Optional)
        is_read: 是否已读

    增强字段:
        depth_level: 深度级别 (shallow/medium/deep)
        generation_method: 生成使用的模型名称
        source_context: 来源上下文 (JSON)
        quality_score: 质量评分 (0.0-1.0)
        feedback_count: 反馈数量
        share_count: 分享次数
    """

    __tablename__ = "curiosity_capsules"

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    related_subject = Column(String(255), nullable=True) # e.g., "Math", "History"
    related_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True, index=True)
    is_read = Column(Boolean, default=False, nullable=False)

    # 增强字段
    depth_level = Column(Enum(DepthLevel), nullable=True, index=True)
    generation_method = Column(String(100), nullable=True)  # e.g. "xiaomi_chat", "zhipu_chat", "deepseek_reason"
    source_context = Column(JSONBCompat, nullable=True)  # 来源上下文数据
    quality_score = Column(Float, nullable=True, index=True)  # 0.0-1.0 质量评分
    feedback_count = Column(Integer, nullable=False, default=0)  # 反馈数量
    share_count = Column(Integer, nullable=False, default=0)  # 分享次数

    user = relationship("User", back_populates="curiosity_capsules")
    task = relationship("Task", back_populates="curiosity_capsules")
    feedbacks = relationship("CapsuleFeedback", back_populates="capsule", cascade="all, delete-orphan")
    favorites = relationship("CapsuleFavorite", back_populates="capsule", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CuriosityCapsule(title={self.title}, user_id={self.user_id}, depth_level={self.depth_level})>"

    @property
    def depth_level_value(self) -> str:
        """获取深度级别的字符串值"""
        return self.depth_level.value if self.depth_level else None

# Add relationship to User and Task models if needed
# In User model: curiosity_capsules = relationship("CuriosityCapsule", back_populates="user")
# In Task model: curiosity_capsule = relationship("CuriosityCapsule", back_populates="task", uselist=False) # if one-to-one
