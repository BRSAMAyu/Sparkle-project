from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    transparency_level: int | None = Field(default=None, ge=0, le=3)
    system_update_level: int | None = Field(default=None, ge=0, le=2)
    ai_reasoning_mode: str | None = Field(default=None, pattern="^(fast|balanced|deep)$")
    current_goal_id: str | None = Field(default=None, max_length=64)
    task_reminders_enabled: bool | None = None
    task_reminder_times: list[int] | None = None
    community_intelligence_enabled: bool | None = None


class UserSettingsResponse(BaseModel):
    transparency_level: int
    system_update_level: int
    ai_reasoning_mode: str
    current_goal_id: str | None = None
    task_reminders_enabled: bool
    task_reminder_times: list[int] | None = None
    community_intelligence_enabled: bool = True
    notification_preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None
    updated_at: datetime | None


class AiModeUsageItem(BaseModel):
    mode: str
    label: str
    requests_used: int
    requests_limit: int
    requests_remaining: int
    total_tokens: int
    total_cost_usd: float
    total_duration_ms: int = 0
    avg_total_duration_ms: float = 0.0
    avg_first_token_ms: float = 0.0
    avg_stream_duration_ms: float = 0.0


class AiUsageSummaryResponse(BaseModel):
    current_mode: str
    items: list[AiModeUsageItem]
    generated_at: datetime


class AiChatModeTimingItem(BaseModel):
    date: str
    mode: str
    chat_mode: str
    requests: int
    avg_total_duration_ms: float = 0.0
    avg_first_token_ms: float = 0.0
    avg_stream_duration_ms: float = 0.0


class AiUsageExportResponse(BaseModel):
    current_mode: str
    window_days: int
    items: list[AiModeUsageItem]
    chat_mode_timing: list[AiChatModeTimingItem]
    generated_at: datetime


class AiOpsReasoningBreakdownItem(BaseModel):
    mode: str
    requests_total: int = 0
    requests_success: int = 0
    fallback_count: int = 0
    total_cost_usd: float = 0.0


class AiOpsModeItem(BaseModel):
    chat_mode: str
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    success_rate_percent: float = 0.0
    fallback_rate_percent: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_total_duration_ms: float = 0.0
    avg_first_token_ms: float = 0.0
    avg_stream_duration_ms: float = 0.0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    positive_feedback_rate_percent: float = 0.0
    feedback_coverage_percent: float = 0.0
    task_count: int = 0
    plan_count: int = 0
    execution_count: int = 0
    task_conversion_rate_percent: float = 0.0
    plan_conversion_rate_percent: float = 0.0
    execution_conversion_rate_percent: float = 0.0
    avg_prompt_utilization_percent: float = 0.0
    avg_inference_utilization_percent: float = 0.0
    prompt_utilization_known_count: int = 0
    prompt_utilization_unknown_count: int = 0
    prompt_utilization_not_applicable_count: int = 0
    inference_utilization_known_count: int = 0
    inference_utilization_unknown_count: int = 0
    inference_utilization_not_applicable_count: int = 0
    reasoning_mode_breakdown: list[AiOpsReasoningBreakdownItem] = Field(default_factory=list)


class AiOpsOverviewItem(BaseModel):
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    success_rate_percent: float = 0.0
    fallback_rate_percent: float = 0.0
    total_cost_usd: float = 0.0
    avg_total_duration_ms: float = 0.0
    avg_first_token_ms: float = 0.0
    avg_stream_duration_ms: float = 0.0
    task_count: int = 0
    plan_count: int = 0
    execution_count: int = 0
    task_conversion_rate_percent: float = 0.0
    plan_conversion_rate_percent: float = 0.0
    execution_conversion_rate_percent: float = 0.0
    avg_prompt_utilization_percent: float = 0.0
    avg_inference_utilization_percent: float = 0.0
    prompt_utilization_known_count: int = 0
    prompt_utilization_unknown_count: int = 0
    prompt_utilization_not_applicable_count: int = 0
    inference_utilization_known_count: int = 0
    inference_utilization_unknown_count: int = 0
    inference_utilization_not_applicable_count: int = 0


class AiOpsTrendPoint(BaseModel):
    date: str
    requests_total: int = 0
    success_rate_percent: float = 0.0
    fallback_rate_percent: float = 0.0
    total_cost_usd: float = 0.0
    avg_total_duration_ms: float = 0.0
    avg_first_token_ms: float = 0.0
    avg_stream_duration_ms: float = 0.0
    execution_conversion_rate_percent: float = 0.0


class AiOpsTrendSeries(BaseModel):
    chat_mode: str
    points: list[AiOpsTrendPoint] = Field(default_factory=list)


class AiOpsDashboardResponse(BaseModel):
    window_days: int
    items: list[AiOpsModeItem]
    generated_at: datetime


class AiOpsExportResponse(BaseModel):
    window_days: int
    overview: AiOpsOverviewItem
    items: list[AiOpsModeItem]
    trend_series: list[AiOpsTrendSeries] = Field(default_factory=list)
    generated_at: datetime
