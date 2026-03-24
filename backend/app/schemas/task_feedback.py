"""
Task Feedback Schemas
"""
from __future__ import annotations
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskFeedbackCategory:
    """任务反馈分类常量"""
    TOO_DIFFICULT = "too_difficult"
    TOO_EASY = "too_easy"
    JUST_RIGHT = "just_right"
    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"
    UNCLEAR = "unclear"
    IRRELEVANT = "irrelevant"
    OTHER = "other"


class TaskFeedbackCreate(BaseModel):
    """提交任务反馈请求"""
    completion_quality: int | None = Field(None, ge=1, le=5, description="完成质量评分 (1-5)")
    feedback_text: str | None = Field(None, max_length=2000, description="用户文字反馈")
    category: str | None = Field(None, description="反馈分类")

    class Config:
        json_schema_extra = {
            "example": {
                "completion_quality": 5,
                "feedback_text": "这个任务很有帮助！",
                "category": "just_right"
            }
        }


class TaskFeedbackResponse(BaseModel):
    """任务反馈响应"""
    id: UUID
    user_id: UUID
    task_id: UUID
    completion_quality: int | None = None
    feedback_text: str | None = None
    category: str | None = None
    inferred_depth_delta: float | None = None
    inferred_difficulty_delta: float | None = None
    task_difficulty_snapshot: int | None = None
    task_type_snapshot: str | None = None
    actual_minutes_snapshot: int | None = None
    reflection_payload: dict[str, Any] | None = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskFeedbackStats(BaseModel):
    """用户任务反馈统计"""
    total_feedbacks: int
    avg_completion_quality: float | None = None
    category_distribution: dict
    recent_feedbacks: list[TaskFeedbackResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "total_feedbacks": 42,
                "avg_completion_quality": 4.2,
                "category_distribution": {
                    "just_right": 30,
                    "too_difficult": 8,
                    "too_easy": 4
                },
                "recent_feedbacks": []
            }
        }


class NextActionSelectionCreate(BaseModel):
    """下一步操作选择记录请求"""
    task_id: UUID
    action_type: str
    action_title: str
    selected: bool
    skipped: bool = False
    display_position: int | None = None
    displayed_actions_count: int | None = None
    context: dict[str, Any] | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "action_type": "quick_review",
                "action_title": "快速回顾",
                "selected": True,
                "skipped": False,
                "display_position": 0,
                "displayed_actions_count": 3
            }
        }


class PreferenceUpdateDetail(BaseModel):
    """偏好更新详情"""
    depth_preference: float | None = Field(None, description="深度偏好变化")
    difficulty_preference: float | None = Field(None, description="难度偏好变化")

    class Config:
        json_schema_extra = {
            "example": {
                "depth_preference": 0.03,
                "difficulty_preference": -0.05
            }
        }


class TaskFeedbackSubmitResponse(BaseModel):
    """任务反馈提交响应（增强版）"""
    success: bool
    message: str | None = Field(None, description="响应消息")
    data: TaskFeedbackResponse | None = Field(None, description="反馈数据")
    preference_updates: PreferenceUpdateDetail | None = Field(None, description="偏好更新详情")
    reflection_prompt: dict[str, Any] | None = Field(None, description="可选的反思引导卡片")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "偏好已更新",
                "data": None,
                "preference_updates": {
                    "depth_preference": 0.03,
                    "difficulty_preference": -0.05
                }
            }
        }


class ReflectionAnswerCreate(BaseModel):
    """提交反思答案"""
    selected_option: str | None = Field(None, max_length=200, description="选择的原因标签")
    free_text: str | None = Field(None, max_length=1000, description="补充说明")


class ReflectionAnswerResponse(BaseModel):
    """反思答案提交响应"""
    success: bool
    message: str
    reflection_payload: dict[str, Any] | None = None
