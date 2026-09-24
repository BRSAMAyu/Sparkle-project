"""
Capsule Feedback Model
"""
from __future__ import annotations

import enum
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, BaseModel


class FeedbackCategory(enum.Enum):
    """反馈分类"""

    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    JUST_RIGHT = "just_right"
    TOO_COMPLEX = "too_complex"
    TOO_SIMPLE = "too_simple"
    IRRELEVANT = "irrelevant"
    OTHER = "other"


class CapsuleFeedback(BaseModel):
    """
    胶囊反馈模型

    用于收集用户对胶囊的反馈，并据此更新用户推断偏好
    """

    __tablename__ = "capsule_feedbacks"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    capsule_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("curiosity_capsules.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=True, index=True)  # 1-5 星评分
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=True)  # 点赞/点踩
    category: Mapped[str] = mapped_column(String(50), nullable=True)  # 反馈分类
    comment: Mapped[str] = mapped_column(Text, nullable=True)  # 用户评论
    inferred_depth_delta: Mapped[float] = mapped_column(Float, nullable=True)  # 基于反馈推断的深度偏好变化
    inferred_curiosity_delta: Mapped[float] = mapped_column(Float, nullable=True)  # 基于反馈推断的好奇心偏好变化

    # Relationships
    user = relationship("User", back_populates="capsule_feedbacks")
    capsule = relationship("CuriosityCapsule", back_populates="feedbacks")

    def __repr__(self):
        return f"<CapsuleFeedback(capsule_id={self.capsule_id}, rating={self.rating})>"

    def calculate_preference_deltas(self) -> tuple[float | None, float | None]:
        """
        根据反馈计算偏好变化

        Returns:
            (depth_delta, curiosity_delta)
        """
        depth_delta = None
        curiosity_delta = None

        if self.category:
            if self.category == FeedbackCategory.TOO_SHORT.value or self.category == FeedbackCategory.TOO_SIMPLE.value:
                depth_delta = 0.1  # 希望更深入
            elif (
                self.category == FeedbackCategory.TOO_LONG.value or self.category == FeedbackCategory.TOO_COMPLEX.value
            ):
                depth_delta = -0.1  # 希望更浅显

        if self.rating is not None:
            # 高评分增加好奇心偏好
            if self.rating >= 4:
                curiosity_delta = 0.05
            elif self.rating <= 2:
                curiosity_delta = -0.05

        return depth_delta, curiosity_delta
