from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

CAPTURE_LEVELS = {"low", "medium", "high"}


class MemorySettingsUpdate(BaseModel):
    enabled: bool | None = None
    allow_preferences: bool | None = None
    allow_goals: bool | None = None
    allow_episodic: bool | None = None
    allow_inferred_episodic: bool | None = None
    capture_level: str | None = None
    blocked_pref_keys: list[str] | None = None
    blocked_sources: list[str] | None = None

    @field_validator("capture_level")
    @classmethod
    def validate_capture_level(cls, value: str | None) -> str | None:
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
    allow_inferred_episodic: bool
    capture_level: str
    blocked_pref_keys: list[str]
    blocked_sources: list[str]
    created_at: datetime | None
    updated_at: datetime | None
