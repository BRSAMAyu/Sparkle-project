"""
Preference Consumption Service

Bridges user preferences to all downstream systems:
- Learning mode → capsule generation depth/curiosity
- Weekly schedule → push timing, do-not-disturb, proactive AI
- Notification preferences → push suppression, quiet hours
- AI reasoning mode → LLM temperature, model selection
- Theme/transparency → profile visibility
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PushPreference
from app.models.user_push_opt_in import UserPushOptIn
from app.models.user_settings import UserSettings
from app.services.personalization.preference_service import PreferenceService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PreferenceConsumptionService:
    """Reads user preferences and exposes them for consumption by downstream systems."""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self._pref_service = PreferenceService(db, redis)

    # ==================== Learning Mode → Capsules & AI ====================

    async def get_learning_config(self, user_id: UUID) -> dict[str, Any]:
        """Get depth/curiosity preferences for capsule generation and AI profiling."""
        prefs = await self._pref_service.get_preferences(user_id)
        explicit = prefs.explicit or {}
        inferred = prefs.inferred or {}

        depth = explicit.get("depth_preference")
        if depth is None:
            depth = inferred.get("depth_preference", 0.5)

        curiosity = explicit.get("curiosity_preference")
        if curiosity is None:
            curiosity = inferred.get("curiosity_preference", 0.5)

        return {
            "depth_preference": float(depth),
            "curiosity_preference": float(curiosity),
            "learning_style": explicit.get("learning_style", "balanced"),
            "feedback_style": explicit.get("feedback_style", "balanced"),
            "ai_verbosity": explicit.get("ai_verbosity", "balanced"),
        }

    async def get_capsule_config(self, user_id: UUID) -> dict[str, Any]:
        """Get capsule generation configuration derived from preferences."""
        learning = await self.get_learning_config(user_id)
        depth = learning["depth_preference"]
        curiosity = learning["curiosity_preference"]

        if depth < 0.3:
            depth_level = "shallow"
            capsule_content_style = "concise"
        elif depth > 0.7:
            depth_level = "deep"
            capsule_content_style = "detailed"
        else:
            depth_level = "medium"
            capsule_content_style = "balanced"

        if curiosity < 0.3:
            capsule_count = 1
            exploration_scope = "focused"
        elif curiosity <= 0.7:
            capsule_count = 2
            exploration_scope = "moderate"
        else:
            capsule_count = 4
            exploration_scope = "exploratory"

        return {
            "depth_level": depth_level,
            "capsule_count": capsule_count,
            "exploration_scope": exploration_scope,
            "content_style": capsule_content_style,
            "raw_depth": depth,
            "raw_curiosity": curiosity,
        }

    # ==================== Weekly Schedule → Do Not Disturb ====================

    async def get_schedule_context(self, user_id: UUID) -> dict[str, Any]:
        """Get current time slot context from weekly schedule preferences."""
        prefs = await self._pref_service.get_preferences(user_id)
        explicit = prefs.explicit or {}
        schedule = explicit.get("schedule_preferences", {})
        grid = schedule.get("grid") if isinstance(schedule, dict) else None
        user_timezone = await self._resolve_timezone(user_id, explicit)

        if not grid or not isinstance(grid, list) or len(grid) != 168:
            return {
                "current_slot_type": "unknown",
                "is_busy": False,
                "is_relax": False,
                "is_fragmented": False,
                "schedule_available": False,
                "timezone": user_timezone,
            }

        now = self._local_now(user_timezone)
        day_of_week = now.weekday()
        hour = now.hour
        slot_index = hour * 7 + day_of_week

        slot_type = str(grid[slot_index]) if 0 <= slot_index < len(grid) else "relax"

        return {
            "current_slot_type": slot_type,
            "is_busy": slot_type == "busy",
            "is_relax": slot_type == "relax",
            "is_fragmented": slot_type == "fragmented",
            "schedule_available": True,
            "slot_index": slot_index,
            "timezone": user_timezone,
            "local_time": now.isoformat(),
        }

    async def should_suppress_push(self, user_id: UUID) -> bool:
        """Check if push notifications should be suppressed based on schedule + notification prefs."""
        prefs = await self._pref_service.get_preferences(user_id)
        explicit = prefs.explicit or {}
        user_timezone = await self._resolve_timezone(user_id, explicit)
        now = self._local_now(user_timezone)

        notification_prefs = await self.get_notification_config(user_id)

        if notification_prefs.get("push_enabled") is False:
            return True

        push_opt_in = notification_prefs.get("push_opt_in")
        if isinstance(push_opt_in, dict) and push_opt_in.get("enabled") is False:
            return True

        quiet_hours_enabled = notification_prefs.get("quiet_hours_enabled", False)
        if quiet_hours_enabled:
            quiet_start = str(notification_prefs.get("quiet_hours_start", "22:00"))
            quiet_end = str(notification_prefs.get("quiet_hours_end", "08:00"))
            current_minutes = now.hour * 60 + now.minute

            try:
                start_parts = quiet_start.split(":")
                end_parts = quiet_end.split(":")
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

                if start_minutes <= end_minutes:
                    in_quiet = start_minutes <= current_minutes <= end_minutes
                else:
                    in_quiet = current_minutes >= start_minutes or current_minutes <= end_minutes

                if in_quiet:
                    return True
            except (ValueError, IndexError):
                pass

        schedule = await self.get_schedule_context(user_id)
        if schedule.get("is_busy"):
            return True

        return False

    async def get_schedule_for_date(self, user_id: UUID, date: datetime | None = None) -> list[dict[str, Any]]:
        """Get schedule grid for a specific date as structured slots."""
        prefs = await self._pref_service.get_preferences(user_id)
        schedule = (prefs.explicit or {}).get("schedule_preferences", {})
        grid = schedule.get("grid") if isinstance(schedule, dict) else None

        if not grid or not isinstance(grid, list) or len(grid) != 168:
            return []

        if date is None:
            date = _utcnow()
        user_timezone = await self._resolve_timezone(user_id, prefs.explicit or {})
        local_date = self._as_local_datetime(date, user_timezone)

        day_of_week = local_date.weekday()
        slots = []
        for hour in range(24):
            slot_index = hour * 7 + day_of_week
            slot_type = str(grid[slot_index]) if 0 <= slot_index < len(grid) else "relax"
            slots.append({
                "hour": hour,
                "type": slot_type,
                "is_busy": slot_type == "busy",
                "is_relax": slot_type == "relax",
                "is_fragmented": slot_type == "fragmented",
            })

        return slots

    # ==================== Notification Preferences ====================

    async def get_notification_config(self, user_id: UUID) -> dict[str, Any]:
        """Get consolidated notification configuration from all preference sources."""
        prefs = await self._pref_service.get_preferences(user_id)
        explicit = prefs.explicit or {}

        notification_prefs_raw = explicit.get("notification_preferences", {})
        notification_prefs: dict[str, Any] = {}
        if isinstance(notification_prefs_raw, dict):
            notification_prefs = notification_prefs_raw
        elif isinstance(notification_prefs_raw, str):
            try:
                notification_prefs = json.loads(notification_prefs_raw)
            except (json.JSONDecodeError, TypeError):
                pass

        notif_prefs_model: dict[str, Any] = {}
        try:
            from app.models.notification_interaction import NotificationPreferences as NotifPrefModel
            result = await self.db.execute(
                select(NotifPrefModel).where(NotifPrefModel.user_id == user_id)
            )
            np = result.scalar_one_or_none()
            if np:
                notif_prefs_model = {
                    "enable_system": np.enable_system,
                    "enable_interventions": np.enable_interventions,
                    "disabled_types": list(np.disabled_types or []),
                    "notification_level": np.notification_level or "standard",
                    "quiet_hours_enabled": np.quiet_hours_enabled or False,
                    "quiet_hours_start": np.quiet_hours_start or "22:00",
                    "quiet_hours_end": np.quiet_hours_end or "08:00",
                }
        except Exception as exc:
            logger.warning("Failed to load notification preferences model for user {}: {}", user_id, exc)

        merged = {**notification_prefs, **notif_prefs_model}

        try:
            result = await self.db.execute(
                select(UserPushOptIn).where(UserPushOptIn.user_id == user_id)
            )
            push_opt_in = result.scalar_one_or_none()
        except Exception as exc:
            logger.warning("Failed to load push opt-in for user {}: {}", user_id, exc)
            push_opt_in = None

        return {
            "notification_level": merged.get("notification_level", "standard"),
            "enable_system": merged.get("enable_system", True),
            "enable_interventions": merged.get("enable_interventions", True),
            "disabled_types": merged.get("disabled_types", []),
            "quiet_hours_enabled": merged.get("quiet_hours_enabled", False),
            "quiet_hours_start": merged.get("quiet_hours_start", "22:00"),
            "quiet_hours_end": merged.get("quiet_hours_end", "08:00"),
            "push_enabled": explicit.get("enable_push", True),
            "curiosity_push_enabled": explicit.get("enable_curiosity_push", True),
            "persona_type": explicit.get("persona_type", "coach"),
            "daily_cap": explicit.get("daily_cap", 5),
            "timezone": explicit.get("timezone", "Asia/Shanghai"),
            "push_opt_in": {
                "enabled": push_opt_in.enabled if push_opt_in else True,
                "allow_commitment_follow_up": push_opt_in.allow_commitment_follow_up if push_opt_in else True,
                "allow_engagement_recovery": push_opt_in.allow_engagement_recovery if push_opt_in else True,
                "quiet_hours_start": str(push_opt_in.quiet_hours_start) if push_opt_in and push_opt_in.quiet_hours_start else "22:00",
                "quiet_hours_end": str(push_opt_in.quiet_hours_end) if push_opt_in and push_opt_in.quiet_hours_end else "08:00",
            } if push_opt_in else {
                "enabled": True,
                "allow_commitment_follow_up": True,
                "allow_engagement_recovery": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
            },
        }

    # ==================== AI Reasoning Mode ====================

    async def get_ai_reasoning_config(self, user_id: UUID) -> dict[str, Any]:
        """Get AI reasoning mode and its derived LLM parameters."""
        ai_reasoning_mode = "balanced"
        try:
            result = await self.db.execute(
                select(UserSettings.ai_reasoning_mode).where(
                    UserSettings.user_id == user_id,
                    UserSettings.deleted_at.is_(None),
                )
            )
            mode = result.scalar_one_or_none()
            if mode:
                ai_reasoning_mode = str(mode)
        except Exception as exc:
            logger.warning("Failed to load AI reasoning mode for user {}: {}", user_id, exc)

        if ai_reasoning_mode not in ("fast", "balanced", "deep"):
            ai_reasoning_mode = "balanced"

        mode_configs = {
            "fast": {
                "temperature": 0.3,
                "max_tokens": 1024,
                "top_p": 0.9,
                "model_preference": "fast",
                "reasoning_effort": "low",
            },
            "balanced": {
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.95,
                "model_preference": "balanced",
                "reasoning_effort": "medium",
            },
            "deep": {
                "temperature": 0.9,
                "max_tokens": 4096,
                "top_p": 0.98,
                "model_preference": "deep",
                "reasoning_effort": "high",
            },
        }

        return {
            "mode": ai_reasoning_mode,
            **mode_configs[ai_reasoning_mode],
        }

    async def get_user_settings_snapshot(self, user_id: UUID) -> dict[str, Any]:
        """Get complete user settings snapshot."""
        try:
            result = await self.db.execute(
                select(UserSettings).where(
                    UserSettings.user_id == user_id,
                    UserSettings.deleted_at.is_(None),
                )
            )
            settings = result.scalar_one_or_none()
        except Exception as exc:
            logger.warning("Failed to load user settings snapshot for user {}: {}", user_id, exc)
            settings = None

        if settings:
            return {
                "transparency_level": settings.transparency_level,
                "system_update_level": settings.system_update_level,
                "ai_reasoning_mode": settings.ai_reasoning_mode,
                "task_reminders_enabled": settings.task_reminders_enabled,
                "task_reminder_times": settings.task_reminder_times,
            }

        return {
            "transparency_level": 0,
            "system_update_level": 1,
            "ai_reasoning_mode": "balanced",
            "task_reminders_enabled": True,
            "task_reminder_times": [1440, 60, 15],
        }

    async def _resolve_timezone(self, user_id: UUID, explicit: dict[str, Any]) -> str:
        raw_timezone = explicit.get("timezone")
        if isinstance(raw_timezone, str) and raw_timezone.strip():
            return raw_timezone.strip()

        try:
            result = await self.db.execute(
                select(PushPreference.timezone).where(PushPreference.user_id == user_id)
            )
            push_timezone = result.scalar_one_or_none()
            if isinstance(push_timezone, str) and push_timezone.strip():
                return push_timezone.strip()
        except Exception as exc:
            logger.warning("Failed to load push preference timezone for user {}: {}", user_id, exc)

        try:
            result = await self.db.execute(
                select(UserPushOptIn.timezone).where(UserPushOptIn.user_id == user_id)
            )
            opt_in_timezone = result.scalar_one_or_none()
            if isinstance(opt_in_timezone, str) and opt_in_timezone.strip():
                return opt_in_timezone.strip()
        except Exception as exc:
            logger.warning("Failed to load push opt-in timezone for user {}: {}", user_id, exc)

        return "Asia/Shanghai"

    @staticmethod
    def _local_now(timezone_name: str) -> datetime:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(timezone_name))
        except Exception as exc:
            logger.warning("Invalid timezone {}, falling back to Asia/Shanghai: {}", timezone_name, exc)
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo("Asia/Shanghai"))

    @staticmethod
    def _as_local_datetime(value: datetime, timezone_name: str) -> datetime:
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(timezone_name)
        except Exception as exc:
            logger.warning("Invalid timezone {}, falling back to Asia/Shanghai: {}", timezone_name, exc)
            from zoneinfo import ZoneInfo

            tz = ZoneInfo("Asia/Shanghai")

        if value.tzinfo is None:
            return value.replace(tzinfo=tz)
        return value.astimezone(tz)

    async def get_complete_preference_profile(self, user_id: UUID) -> dict[str, Any]:
        """Get complete preference profile for AI profiling and personalization."""
        learning = await self.get_learning_config(user_id)
        capsule = await self.get_capsule_config(user_id)
        notification = await self.get_notification_config(user_id)
        reasoning = await self.get_ai_reasoning_config(user_id)
        schedule_ctx = await self.get_schedule_context(user_id)
        settings = await self.get_user_settings_snapshot(user_id)

        return {
            "learning": learning,
            "capsule": capsule,
            "notification": notification,
            "reasoning": reasoning,
            "schedule": schedule_ctx,
            "settings": settings,
            "preference_version": await self._pref_service.get_preference_version(user_id),
        }


class PreferenceEventConsumer:
    """Consumes preference update events and propagates changes to downstream systems."""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.consumption = PreferenceConsumptionService(db, redis)

    async def on_preferences_updated(self, user_id: UUID) -> None:
        """Handle preference update event - propagate to downstream systems."""
        logger.info(f"Preference update propagated for user {user_id}")
        self._invalidate_downstream_caches(user_id)
        await self._notify_downstream_systems(user_id)

    def _invalidate_downstream_caches(self, user_id: UUID) -> None:
        if not self.redis:
            return
        keys = [
            f"pref:consumption:{user_id}",
            f"pref:learning:{user_id}",
            f"pref:capsule:{user_id}",
            f"pref:notification:{user_id}",
            f"pref:reasoning:{user_id}",
            f"pref:complete:{user_id}",
            f"schedule:context:{user_id}",
            f"personalization:{user_id}",
        ]
        try:
            import asyncio
            asyncio.ensure_future(self.redis.delete(*keys))
        except Exception as e:
            logger.warning(f"Failed to invalidate downstream caches: {e}")

    async def _notify_downstream_systems(self, user_id: UUID) -> None:
        """Notify downstream systems about preference changes."""
        try:
            if self.redis:
                event = {
                    "type": "preferences_updated",
                    "user_id": str(user_id),
                    "timestamp": _utcnow().isoformat(),
                }
                await self.redis.publish("preference:events", json.dumps(event, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Failed to notify downstream systems: {e}")
