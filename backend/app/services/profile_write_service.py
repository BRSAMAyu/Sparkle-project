from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PushPreference, User
from app.core.event_bus import ProfilePreferenceDeleted, ProfilePreferenceUpdated, event_bus
from app.services.memory_service import MemoryService
from app.services.personalization.preference_service import PreferenceService


@dataclass
class ProfileWriteResult:
    preference_version: int
    history_version: int | None = None
    history_record_id: str | None = None


class ProfileWriteService:
    """
    Unified write entry for profile preference updates.

    UserPreferencesCenter is the canonical write model.
    MemoryPreference remains the append-only history/audit log.
    """

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.pref_service = PreferenceService(db, redis)
        self.memory_service = MemoryService(db)

    async def set_explicit_preference(
        self,
        *,
        user_id: UUID,
        pref_key: str,
        pref_value: Any,
        evidence_refs: list[dict[str, Any]],
        confidence: float | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> ProfileWriteResult:
        return await self.set_explicit_preferences(
            user_id=user_id,
            updates={pref_key: pref_value},
            evidence_refs_by_key={pref_key: evidence_refs},
            confidence_by_key={pref_key: confidence},
            source_type=source_type,
            source=source,
        )

    async def set_explicit_preferences(
        self,
        *,
        user_id: UUID,
        updates: dict[str, Any],
        evidence_refs_by_key: dict[str, list[dict[str, Any]]],
        confidence_by_key: dict[str, float | None] | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> ProfileWriteResult:
        if not updates:
            prefs = await self.pref_service.get_preferences(user_id)
            return ProfileWriteResult(preference_version=prefs.version or 0)

        explicit_updates = {
            pref_key: self._to_explicit_value(pref_key, pref_value)
            for pref_key, pref_value in updates.items()
        }
        prefs = await self.pref_service.update_explicit(user_id, explicit_updates)
        await self._sync_legacy_fields(user_id, explicit_updates)

        latest_history_version: int | None = None
        latest_record_id: str | None = None
        confidence_by_key = confidence_by_key or {}

        for pref_key, pref_value in updates.items():
            refs = evidence_refs_by_key.get(pref_key) or []
            try:
                record = await self.memory_service.upsert_preference(
                    user_id=user_id,
                    pref_key=pref_key,
                    pref_value=self._to_history_payload(pref_value),
                    evidence_refs=refs,
                    confidence=confidence_by_key.get(pref_key),
                    source_type=source_type,
                )
                if record is not None:
                    latest_history_version = record.version
                    latest_record_id = str(record.id)
            except Exception as exc:
                logger.warning(
                    "Preference history write failed user_id=%s pref_key=%s error=%s",
                    user_id,
                    pref_key,
                    exc,
                )

        result = ProfileWriteResult(
            preference_version=prefs.version or 0,
            history_version=latest_history_version,
            history_record_id=latest_record_id,
        )
        await self._publish_preference_updated_event(
            user_id=user_id,
            pref_keys=list(updates.keys()),
            preference_version=result.preference_version,
            source=source or "manual_edit",
        )
        return result

    async def remove_explicit_preference(
        self,
        *,
        user_id: UUID,
        pref_key: str,
        reason: str = "manual_delete",
    ) -> ProfileWriteResult:
        prefs = await self.pref_service.delete_explicit_key(user_id, pref_key)
        await self._sync_legacy_fields(user_id, {pref_key: None}, removal=True)

        try:
            record = await self.memory_service.find_preference(user_id=user_id, pref_key=pref_key)
            if record is not None:
                await self.memory_service.delete_preference(
                    user_id=user_id,
                    preference_id=record.id,
                    reason=reason,
                )
        except Exception as exc:
            logger.warning(
                "Preference history delete failed user_id=%s pref_key=%s error=%s",
                user_id,
                pref_key,
                exc,
            )

        result = ProfileWriteResult(preference_version=prefs.version or 0)
        await self._publish_preference_deleted_event(
            user_id=user_id,
            pref_key=pref_key,
            preference_version=result.preference_version,
        )
        return result

    async def _sync_legacy_fields(
        self,
        user_id: UUID,
        updates: dict[str, Any],
        *,
        removal: bool = False,
    ) -> None:
        user = await self.db.get(User, user_id)
        if user is None:
            return

        push_pref = await self._get_or_create_push_preference(user_id)

        for key, value in updates.items():
            if key == "depth_preference" and value is not None:
                user.depth_preference = float(value)
            elif key == "curiosity_preference" and value is not None:
                user.curiosity_preference = float(value)
            elif key == "schedule_preferences":
                user.schedule_preferences = None if removal else value
            elif key == "weather_preferences":
                user.weather_preferences = {} if removal else (value or {})

            if push_pref is None:
                continue
            if key == "persona_type":
                push_pref.persona_type = "coach" if removal else str(value or "coach")
            elif key == "daily_cap":
                push_pref.daily_cap = 5 if removal else int(value or 5)
            elif key in {"active_slots", "schedule_preferences"} and value is not None and isinstance(value, list):
                push_pref.active_slots = value
            elif key == "timezone":
                push_pref.timezone = "Asia/Shanghai" if removal else str(value or "Asia/Shanghai")
            elif key == "enable_curiosity_push":
                push_pref.enable_curiosity = True if removal else bool(value)

        await self.db.commit()
        if user is not None:
            await self.db.refresh(user)
        if push_pref is not None:
            await self.db.refresh(push_pref)

    async def _get_or_create_push_preference(self, user_id: UUID) -> PushPreference | None:
        result = await self.db.execute(
            select(PushPreference).where(PushPreference.user_id == user_id)
        )
        push_pref = result.scalar_one_or_none()
        if push_pref is not None:
            return push_pref

        push_pref = PushPreference(user_id=user_id)
        self.db.add(push_pref)
        await self.db.commit()
        await self.db.refresh(push_pref)
        return push_pref

    async def _publish_preference_updated_event(
        self,
        *,
        user_id: UUID,
        pref_keys: list[str],
        preference_version: int,
        source: str,
    ) -> None:
        try:
            event = ProfilePreferenceUpdated(
                user_id=str(user_id),
                pref_keys=pref_keys,
                preference_version=preference_version,
                source=source,
            )
            await event_bus.publish(event.to_dict()["event_type"], event.to_dict())
        except Exception as exc:
            logger.warning("ProfilePreferenceUpdated publish failed: %s", exc)

    async def _publish_preference_deleted_event(
        self,
        *,
        user_id: UUID,
        pref_key: str,
        preference_version: int,
    ) -> None:
        try:
            event = ProfilePreferenceDeleted(
                user_id=str(user_id),
                pref_key=pref_key,
                preference_version=preference_version,
            )
            await event_bus.publish(event.to_dict()["event_type"], event.to_dict())
        except Exception as exc:
            logger.warning("ProfilePreferenceDeleted publish failed: %s", exc)

    @staticmethod
    def _to_history_payload(pref_value: Any) -> dict[str, Any]:
        if isinstance(pref_value, dict):
            return pref_value
        return {"value": pref_value}

    @staticmethod
    def _to_explicit_value(pref_key: str, pref_value: Any) -> Any:
        if not isinstance(pref_value, dict):
            return pref_value
        if pref_key == "study_time_preference" and "minutes" in pref_value:
            return pref_value.get("minutes")
        if set(pref_value.keys()) == {"value"}:
            return pref_value.get("value")
        return pref_value
