from __future__ import annotations

import inspect
import json
from datetime import datetime, UTC
from typing import Any
from collections.abc import Mapping
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator

from app.aurora.common import AuroraSchemaBase
from app.aurora.runtime_v1.state import (
    ActivityProfile,
    AuroraTeachingStrategy,
    build_aurora_runtime_metadata,
    merge_activity_profile_payload,
    merge_expression_settings,
    normalize_expression_update,
)
from app.config import settings


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _coerce_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    raw = _normalize_text(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _validate_clock(clock: str) -> str:
    text = _normalize_text(clock)
    hour, minute = text.split(":")
    if len(hour) > 2 or len(minute) != 2:
        raise ValueError("clock value must use HH:MM format")
    hour_value = int(hour)
    minute_value = int(minute)
    if not (0 <= hour_value <= 23 and 0 <= minute_value <= 59):
        raise ValueError("clock value must use HH:MM format")
    return f"{hour_value:02d}:{minute_value:02d}"


class DndWindow(AuroraSchemaBase):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _validate_clock_value(cls, value: str) -> str:
        return _validate_clock(value)

    def contains(self, when_local: datetime) -> bool:
        start_hour, start_minute = (int(part) for part in self.start.split(":"))
        end_hour, end_minute = (int(part) for part in self.end.split(":"))
        current_minutes = when_local.hour * 60 + when_local.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        if start_minutes == end_minutes:
            return True
        if start_minutes < end_minutes:
            return start_minutes <= current_minutes < end_minutes
        return current_minutes >= start_minutes or current_minutes < end_minutes


class AuroraHardBounds(AuroraSchemaBase):
    dnd_windows: list[DndWindow] = Field(default_factory=list)
    privacy_boundaries: list[str] = Field(default_factory=list)
    disabled_actions: list[str] = Field(default_factory=list)
    timezone_name: str = "UTC"

    @field_validator("privacy_boundaries", "disabled_actions", mode="before")
    @classmethod
    def _normalize_tokens(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [_normalize_text(item).lower() for item in value if _normalize_text(item)]

    @field_validator("timezone_name")
    @classmethod
    def _normalize_timezone_name(cls, value: str) -> str:
        text = _normalize_text(value) or "UTC"
        try:
            ZoneInfo(text)
        except Exception:
            return "UTC"
        return text

    def is_privacy_blocked(self, domain: str | None) -> bool:
        token = _normalize_text(domain).lower()
        return bool(token) and token in set(self.privacy_boundaries)

    def is_action_disabled(self, action: str | None) -> bool:
        token = _normalize_text(action).lower()
        return bool(token) and token in set(self.disabled_actions)

    def is_within_dnd(self, when: datetime | None) -> bool:
        if when is None or not self.dnd_windows:
            return False
        localized = self._to_local_time(when)
        return any(window.contains(localized) for window in self.dnd_windows)

    def _to_local_time(self, when: datetime) -> datetime:
        if when.tzinfo is None:
            aware = when.replace(tzinfo=UTC)
        else:
            aware = when.astimezone(UTC)
        return aware.astimezone(ZoneInfo(self.timezone_name))


class ControlSurfaceReading(AuroraSchemaBase):
    adjustable: ActivityProfile = Field(default_factory=ActivityProfile)
    hard_bounds: AuroraHardBounds = Field(default_factory=AuroraHardBounds)
    runtime_enabled: bool = False


class HarnessUpdateRejectedError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class ControlSurfaceService:
    CONTROL_KEY_PREFIX = "aurora:control:"
    CONTROL_TTL_SECONDS = 24 * 60 * 60
    ALLOWED_FIELDS = {
        "proactive_intensity",
        "next_wake_at",
        "conversation_style",
        "expression",
        "agenda_priority",
        "task_density_hint",
        "strategy",
    }

    def __init__(
        self,
        db,
        redis=None,
        *,
        preference_service: Any | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.preference_service = preference_service
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_AURORA_RUNTIME_V1 if self._enabled is None else bool(self._enabled)

    def control_key(self, user_id: UUID | str) -> str:
        return f"{self.CONTROL_KEY_PREFIX}{user_id}"

    async def read_control_surface(self, user_id: UUID | str) -> ControlSurfaceReading:
        adjustable_payload = await self._read_adjustable_payload(user_id)
        if self.preference_service is None:
            return ControlSurfaceReading(
                adjustable=ActivityProfile.model_validate(adjustable_payload),
                hard_bounds=AuroraHardBounds(),
                runtime_enabled=self.enabled,
            )
        prefs = await self.preference_service.get_preferences(UUID(str(user_id)))
        explicit = dict(getattr(prefs, "explicit", {}) or {})
        hard_bounds = self._hard_bounds_from_explicit(explicit)
        return ControlSurfaceReading(
            adjustable=ActivityProfile.model_validate(adjustable_payload),
            hard_bounds=hard_bounds,
            runtime_enabled=self.enabled,
        )

    def validate_harness_update(
        self,
        updates: Mapping[str, Any],
        *,
        hard_bounds: AuroraHardBounds | None = None,
    ) -> dict[str, Any]:
        if not isinstance(updates, Mapping):
            raise HarnessUpdateRejectedError(["harness update must be a mapping"])

        unknown = sorted(set(updates.keys()) - self.ALLOWED_FIELDS)
        if unknown:
            raise HarnessUpdateRejectedError([f"unsupported harness field: {field}" for field in unknown])

        bounds = hard_bounds or AuroraHardBounds()
        normalized: dict[str, Any] = {}
        errors: list[str] = []
        expression_update: dict[str, float] | None = None
        strategy_update: dict[str, bool] | None = None

        try:
            if "proactive_intensity" in updates:
                normalized["proactive_intensity"] = float(updates["proactive_intensity"])
            if "task_density_hint" in updates:
                normalized["task_density_hint"] = float(updates["task_density_hint"])
            if "conversation_style" in updates:
                normalized["conversation_style"] = _normalize_text(updates["conversation_style"])
            if "expression" in updates:
                expression_update = normalize_expression_update(updates["expression"])
                normalized["expression"] = merge_expression_settings(updates=expression_update)
            if "agenda_priority" in updates:
                agenda_priority = _normalize_text(updates["agenda_priority"])
                normalized["agenda_priority"] = agenda_priority or None
            if "next_wake_at" in updates:
                normalized["next_wake_at"] = _coerce_datetime(updates["next_wake_at"])
            if "strategy" in updates:
                strategy_update = AuroraTeachingStrategy.model_validate(updates["strategy"]).model_dump(
                    mode="python",
                    exclude_unset=True,
                )
            normalized = ActivityProfile.model_validate(normalized).model_dump(mode="python", exclude_unset=True)
            if expression_update is not None:
                normalized["expression"] = expression_update
            if strategy_update is not None:
                normalized["strategy"] = strategy_update
        except Exception as exc:
            raise HarnessUpdateRejectedError([str(exc)]) from exc

        agenda_priority = normalized.get("agenda_priority")
        if bounds.is_privacy_blocked(agenda_priority):
            errors.append(f"agenda_priority '{agenda_priority}' crosses a privacy boundary")

        next_wake_at = normalized.get("next_wake_at")
        if next_wake_at is not None and bounds.is_action_disabled("proactive_follow_up"):
            errors.append("next_wake_at is blocked because proactive_follow_up is disabled")
        if next_wake_at is not None and bounds.is_within_dnd(next_wake_at):
            errors.append("next_wake_at falls inside a DND window")

        if errors:
            raise HarnessUpdateRejectedError(errors)
        return normalized

    async def apply_harness_update(
        self,
        user_id: UUID | str,
        updates: Mapping[str, Any],
    ) -> ControlSurfaceReading:
        reading = await self.read_control_surface(user_id)
        normalized = self.validate_harness_update(updates, hard_bounds=reading.hard_bounds)

        if self.enabled and self.redis is not None and normalized:
            persisted = ActivityProfile.model_validate(
                merge_activity_profile_payload(reading.adjustable.model_dump(mode="python"), normalized)
            ).model_dump(mode="python")
            payload = {
                key: (
                    value.isoformat()
                    if isinstance(value, datetime)
                    else (json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else ("" if value is None else str(value)))
                )
                for key, value in persisted.items()
            }
            await self._redis_call("hset", self.control_key(user_id), mapping=payload)
            await self._redis_call("expire", self.control_key(user_id), self.CONTROL_TTL_SECONDS)

        return await self.read_control_surface(user_id)

    def build_surface_metadata(
        self,
        *,
        surface: str,
        surface_complete: bool = False,
        modeling_complete: bool = False,
    ) -> dict[str, Any]:
        return build_aurora_runtime_metadata(
            surface=surface,
            surface_complete=surface_complete,
            modeling_complete=modeling_complete,
            runtime_enabled=self.enabled,
        ).model_dump(mode="python")

    async def _read_adjustable_payload(self, user_id: UUID | str) -> dict[str, Any]:
        if self.redis is None:
            return {}
        raw = await self._redis_call("hgetall", self.control_key(user_id))
        if not isinstance(raw, dict):
            return {}

        normalized: dict[str, Any] = {}
        for key, value in raw.items():
            normalized_key = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            if isinstance(value, bytes):
                normalized_value = value.decode("utf-8")
            else:
                normalized_value = value
            if normalized_key == "next_wake_at":
                normalized[normalized_key] = _coerce_datetime(normalized_value)
            elif normalized_key == "expression":
                try:
                    parsed = json.loads(str(normalized_value))
                except Exception:
                    parsed = {}
                normalized[normalized_key] = merge_expression_settings(updates=parsed if isinstance(parsed, Mapping) else {})
            elif normalized_key == "strategy":
                try:
                    parsed = json.loads(str(normalized_value))
                except Exception:
                    continue
                if isinstance(parsed, Mapping):
                    normalized[normalized_key] = dict(parsed)
            else:
                normalized[normalized_key] = normalized_value
        return normalized

    def _hard_bounds_from_explicit(self, explicit: dict[str, Any]) -> AuroraHardBounds:
        aurora_preferences = explicit.get("aurora_preferences")
        if not isinstance(aurora_preferences, dict):
            aurora_preferences = {}

        return AuroraHardBounds(
            dnd_windows=aurora_preferences.get("dnd_windows") or [],
            privacy_boundaries=aurora_preferences.get("privacy_boundaries") or [],
            disabled_actions=aurora_preferences.get("disabled_actions") or [],
            timezone_name=aurora_preferences.get("timezone") or explicit.get("timezone") or "UTC",
        )

    async def _redis_call(self, method_name: str, *args, **kwargs):
        method = getattr(self.redis, method_name, None)
        if method is None:
            return None
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result
