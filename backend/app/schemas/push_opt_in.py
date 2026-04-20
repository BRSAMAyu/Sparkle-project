from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


def _parse_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


class PushOptInUpdate(BaseModel):
    enabled: bool | None = None
    allow_commitment_follow_up: bool | None = None
    allow_engagement_recovery: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_quiet_hours(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("quiet hour must use HH:MM format")
        hours = _parse_minutes(value)
        allowed = {
            22 * 60,
            22 * 60 + 30,
            23 * 60,
            7 * 60,
            7 * 60 + 30,
            8 * 60,
        }
        if hours not in allowed:
            raise ValueError("quiet hours may only narrow the default 22:00-08:00 window")
        return value


class PushOptInResponse(BaseModel):
    enabled: bool
    allow_commitment_follow_up: bool
    allow_engagement_recovery: bool
    quiet_hours_start: str
    quiet_hours_end: str
    timezone: str
    created_at: datetime | None
    updated_at: datetime | None

