"""
Task Feedback Model
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


class TaskFeedbackCategory(enum.Enum):
    """任务反馈分类"""
    TOO_DIFFICULT = "too_difficult"
    TOO_EASY = "too_easy"
    JUST_RIGHT = "just_right"
    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    UNCLEAR = "unclear"
    IRRELEVANT = "irrelevant"
    OTHER = "other"


class TaskFeedback(BaseModel):
    """
    任务反馈模型

    用于收集用户对任务的反馈，并据此更新用户推断偏好
    """
    __tablename__ = "task_feedbacks"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    # 反馈内容
    completion_quality = Column(Integer, nullable=True, index=True)  # 1-5 星评分
    feedback_text = Column(Text, nullable=True)  # 用户文字反馈
    category = Column(String(50), nullable=True)  # 反馈分类

    # 推断的偏好变化
    inferred_depth_delta = Column(Float, nullable=True)  # 基于反馈推断的深度偏好变化
    inferred_difficulty_delta = Column(Float, nullable=True)  # 基于反馈推断的难度偏好变化

    # 任务状态快照（防止任务变更导致反馈失真）
    task_difficulty_snapshot = Column(Integer, nullable=True)  # 任务难度快照
    task_type_snapshot = Column(String(50), nullable=True)  # 任务类型快照
    actual_minutes_snapshot = Column(Integer, nullable=True)  # 实际用时快照

    # Relationships
    user = relationship("User", back_populates="task_feedbacks")
    task = relationship("Task", back_populates="feedbacks")

    def __repr__(self):
        return f"<TaskFeedback(task_id={self.task_id}, completion_quality={self.completion_quality})>"

    def calculate_preference_deltas(self) -> tuple[Optional[float], Optional[float]]:
        """
        根据反馈计算偏好变化

        Returns:
            (depth_delta, difficulty_delta)
        """
        depth_delta = None
        difficulty_delta = None

        # 1. 基于评分的推断
        if self.completion_quality is not None:
            if self.completion_quality >= 4:
                # 高评分 -> 轻微增加深度偏好
                depth_delta = (depth_delta or 0) + 0.03
            elif self.completion_quality <= 2:
                # 低评分 -> 降低深度偏好
                depth_delta = (depth_delta or 0) - 0.05

        # 2. 基于分类的推断
        if self.category:
            if self.category == TaskFeedbackCategory.TOO_DIFFICULT.value:
                # 太难 -> 降低深度和难度
                depth_delta = (depth_delta or 0) - 0.1
                difficulty_delta = (difficulty_delta or 0) - 0.15
            elif self.category == TaskFeedbackCategory.TOO_EASY.value:
                # 太简单 -> 增加深度和难度
                depth_delta = (depth_delta or 0) + 0.1
                difficulty_delta = (difficulty_delta or 0) + 0.15
            elif self.category == TaskFeedbackCategory.TOO_LONG.value:
                # 太长 -> 降低深度（减少详细程度）
                depth_delta = (depth_delta or 0) - 0.05
            elif self.category == TaskFeedbackCategory.TOO_SHORT.value:
                # 太短 -> 增加深度
                depth_delta = (depth_delta or 0) + 0.05
            elif self.category == TaskFeedbackCategory.JUST_RIGHT.value:
                # 刚刚好 -> 轻微增加当前偏好（强化）
                depth_delta = (depth_delta or 0) + 0.02

        # 3. 基于用时比率的推断（实际用时 / 预估用时）
        if (self.actual_minutes_snapshot and self.task_difficulty_snapshot):
            # 这里使用 difficulty 作为预估的参考指标
            # 如果实际用时远超预期，说明任务偏难
            # 我们可以通过 difficulty_snapshot 来获取预估难度
            estimated_difficulty = self.task_difficulty_snapshot
            if estimated_difficulty and estimated_difficulty > 0:
                # 简单判断：如果任务困难度高但用时异常
                # 实际上我们需要任务的 estimated_minutes 来计算比率
                # 这里简化处理，直接基于难度快照
                pass

        return depth_delta, difficulty_delta
