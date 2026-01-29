from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    transparency_level: int | None = Field(default=None, ge=0, le=3)
    system_update_level: int | None = Field(default=None, ge=0, le=2)
    task_reminders_enabled: bool | None = None
    task_reminder_times: list[int] | None = None


class UserSettingsResponse(BaseModel):
    transparency_level: int
    system_update_level: int
    task_reminders_enabled: bool
    task_reminder_times: list[int] | None = None
    created_at: datetime | None
    updated_at: datetime | None
