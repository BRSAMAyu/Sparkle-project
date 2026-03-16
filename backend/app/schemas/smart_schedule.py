"""Smart Schedule Schemas - 智能排程请求/响应模型"""
from datetime import date as DateType
from enum import Enum

from pydantic import BaseModel, Field


class TimeSlotQuality(str, Enum):
    """时间槽质量等级"""
    PEAK = "peak"      # 高效时段
    NORMAL = "normal"  # 常规时段
    LOW = "low"        # 低效时段
    BLOCKED = "blocked"  # 被占用时段


class SmartScheduleRequest(BaseModel):
    """智能排程请求"""
    estimated_minutes: int = Field(..., ge=5, le=480, description="预估时长(分钟)")
    energy_cost: int = Field(1, ge=1, le=5, description="精力消耗(1-5)")
    difficulty: int = Field(1, ge=1, le=5, description="难度(1-5)")
    preferred_date: DateType | None = Field(None, description="偏好日期")
    task_type: str | None = Field(None, description="任务类型")
    exclude_event_ids: list[str] | None = Field(None, description="排除的事件ID")


class TimeSlotSuggestion(BaseModel):
    """时间槽建议"""
    start_time: str = Field(description="开始时间 (HH:MM)")
    end_time: str = Field(description="结束时间 (HH:MM)")
    date: DateType = Field(description="日期")
    quality: TimeSlotQuality = Field(description="质量等级")
    score: float = Field(description="综合评分 (0-1)")
    confidence: float = Field(description="置信度 (0-1)")
    reason: str = Field(description="推荐理由")


class SmartScheduleResponse(BaseModel):
    """智能排程响应"""
    suggestions: list[TimeSlotSuggestion] = Field(description="建议列表")
    cognitive_insights: dict | None = Field(None, description="认知洞察")
    fallback_used: bool = Field(False, description="是否使用兜底逻辑")
