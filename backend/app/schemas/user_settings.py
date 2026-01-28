from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    transparency_level: Optional[int] = Field(default=None, ge=0, le=3)
    system_update_level: Optional[int] = Field(default=None, ge=0, le=2)
    task_reminders_enabled: Optional[bool] = None
    task_reminder_times: Optional[List[int]] = None


class UserSettingsResponse(BaseModel):
    transparency_level: int
    system_update_level: int
    task_reminders_enabled: bool
    task_reminder_times: Optional[List[int]] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
