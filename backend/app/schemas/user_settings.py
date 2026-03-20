from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    transparency_level: int | None = Field(default=None, ge=0, le=3)
    system_update_level: int | None = Field(default=None, ge=0, le=2)
    ai_reasoning_mode: str | None = Field(default=None, pattern="^(fast|balanced|deep)$")
    task_reminders_enabled: bool | None = None
    task_reminder_times: list[int] | None = None


class UserSettingsResponse(BaseModel):
    transparency_level: int
    system_update_level: int
    ai_reasoning_mode: str
    task_reminders_enabled: bool
    task_reminder_times: list[int] | None = None
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
