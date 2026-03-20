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


class AiUsageSummaryResponse(BaseModel):
    current_mode: str
    items: list[AiModeUsageItem]
    generated_at: datetime
