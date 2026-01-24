from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


CAPTURE_LEVELS = {"low", "medium", "high"}


class MemorySettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    allow_preferences: Optional[bool] = None
    allow_goals: Optional[bool] = None
    allow_episodic: Optional[bool] = None
    capture_level: Optional[str] = None
    blocked_pref_keys: Optional[List[str]] = None
    blocked_sources: Optional[List[str]] = None

    @field_validator("capture_level")
    @classmethod
    def validate_capture_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in CAPTURE_LEVELS:
            raise ValueError("capture_level must be low, medium, or high")
        return value


class MemorySettingsResponse(BaseModel):
    enabled: bool
    allow_preferences: bool
    allow_goals: bool
    allow_episodic: bool
    capture_level: str
    blocked_pref_keys: List[str]
    blocked_sources: List[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
