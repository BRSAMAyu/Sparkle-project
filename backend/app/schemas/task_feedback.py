"""
Task Feedback Schemas
"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


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
    completion_quality: Optional[int] = Field(None, ge=1, le=5, description="完成质量评分 (1-5)")
    feedback_text: Optional[str] = Field(None, max_length=2000, description="用户文字反馈")
    category: Optional[str] = Field(None, description="反馈分类")

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
    completion_quality: Optional[int] = None
    feedback_text: Optional[str] = None
    category: Optional[str] = None
    inferred_depth_delta: Optional[float] = None
    inferred_difficulty_delta: Optional[float] = None
    task_difficulty_snapshot: Optional[int] = None
    task_type_snapshot: Optional[str] = None
    actual_minutes_snapshot: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskFeedbackStats(BaseModel):
    """用户任务反馈统计"""
    total_feedbacks: int
    avg_completion_quality: Optional[float] = None
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
