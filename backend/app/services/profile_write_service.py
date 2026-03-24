from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PushPreference, User
from app.core.event_bus import ProfilePreferenceDeleted, ProfilePreferenceUpdated, event_bus
from app.services.memory_policy_evaluator import MemoryPolicyEvaluator
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
        self._override_backup_key_prefix = "user:profile:override_backup"

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
                await self.db.rollback()
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

    async def update_inferred_preference(
        self,
        *,
        user_id: UUID,
        updates: dict[str, Any],
        source: str = "ai_inferred",
    ) -> int:
        """写入推断偏好并发布事件。返回新版本号。"""
        if not updates:
            prefs = await self.pref_service.get_preferences(user_id)
            return prefs.version or 0

        evaluator = MemoryPolicyEvaluator(self.db)
        filtered_updates: dict[str, Any] = {}
        for key, value in updates.items():
            decision = await evaluator.evaluate(
                user_id=user_id,
                kind="preference",
                pref_key=key,
                source_type="ai_inferred",
            )
            if decision.allowed:
                filtered_updates[key] = value
            else:
                logger.debug("Inferred pref %s blocked by memory policy: %s", key, decision.reason)

        if not filtered_updates:
            prefs = await self.pref_service.get_preferences(user_id)
            return prefs.version or 0

        prefs = await self.pref_service.update_inferred(user_id, filtered_updates)

        for key, value in filtered_updates.items():
            try:
                await self.memory_service.upsert_preference(
                    user_id=user_id,
                    pref_key=key,
                    pref_value={"value": value, "source": source},
                    evidence_refs=[{"type": "ai_inferred", "id": source}],
                    confidence=0.6,
                    source_type="ai_inferred",
                )
            except Exception as exc:
                await self.db.rollback()
                logger.warning(
                    "Inferred preference history write failed user_id=%s pref_key=%s error=%s",
                    user_id,
                    key,
                    exc,
                )

        await self._publish_preference_updated_event(
            user_id=user_id,
            pref_keys=list(filtered_updates.keys()),
            preference_version=prefs.version or 0,
            source=source,
        )
        return prefs.version or 0

    async def remove_inferred_preference(
        self,
        *,
        user_id: UUID,
        pref_key: str,
    ) -> ProfileWriteResult:
        prefs = await self.pref_service.delete_inferred_key(user_id, pref_key)
        result = ProfileWriteResult(preference_version=prefs.version or 0)
        await self._publish_preference_deleted_event(
            user_id=user_id,
            pref_key=pref_key,
            preference_version=result.preference_version,
        )
        return result

    async def remove_inferred_keys(
        self,
        *,
        user_id: UUID,
        keys: list[str],
        source: str = "memory_settings_sync",
    ) -> ProfileWriteResult:
        if not keys:
            prefs = await self.pref_service.get_preferences(user_id)
            return ProfileWriteResult(preference_version=prefs.version or 0)

        prefs = await self.pref_service.get_preferences(user_id)
        current_inferred = dict(prefs.inferred or {})
        removed_keys = [key for key in keys if key in current_inferred]
        if not removed_keys:
            return ProfileWriteResult(preference_version=prefs.version or 0)

        for key in removed_keys:
            current_inferred.pop(key, None)

        updated = await self.pref_service.update_inferred_raw(user_id, current_inferred)
        result = ProfileWriteResult(preference_version=updated.version or 0)
        await self._publish_preference_updated_event(
            user_id=user_id,
            pref_keys=removed_keys,
            preference_version=result.preference_version,
            source=source,
        )
        return result

    async def override_inferred_preference(
        self,
        *,
        user_id: UUID,
        pref_key: str,
        pref_value: Any,
        evidence_refs: list[dict[str, Any]],
        source: str = "user_override",
    ) -> ProfileWriteResult:
        prefs = await self.pref_service.get_preferences(user_id)
        if prefs.inferred and pref_key in prefs.inferred:
            await self._backup_inferred_value(user_id, pref_key, prefs.inferred[pref_key], prefs.last_inferred_update)

        result = await self.set_explicit_preference(
            user_id=user_id,
            pref_key=pref_key,
            pref_value=pref_value,
            evidence_refs=evidence_refs,
            source_type="user_state",
            source=source,
        )
        if prefs.inferred and pref_key in prefs.inferred:
            await self.remove_inferred_preference(user_id=user_id, pref_key=pref_key)
        return result

    async def reset_override_preference(
        self,
        *,
        user_id: UUID,
        pref_key: str,
        restore_source: str = "reset_override",
    ) -> ProfileWriteResult:
        result = await self.remove_explicit_preference(
            user_id=user_id,
            pref_key=pref_key,
            reason="reset_override",
        )
        backup = await self._load_inferred_backup(user_id, pref_key)
        if backup is not None:
            await self.update_inferred_preference(
                user_id=user_id,
                updates={pref_key: backup},
                source=restore_source,
            )
            await self._delete_inferred_backup(user_id, pref_key)
        return result

    async def list_inferred_backups(self, user_id: UUID) -> dict[str, dict[str, Any]]:
        if not self.redis:
            return {}
        try:
            raw_map = await self.redis.hgetall(self._override_backup_key(user_id))
        except Exception as exc:
            logger.warning("Failed to list inferred backups for %s: %s", user_id, exc)
            return {}
        backups: dict[str, dict[str, Any]] = {}
        for key, raw in (raw_map or {}).items():
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if isinstance(payload, dict):
                backups[str(key)] = payload
        return backups

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

    def _override_backup_key(self, user_id: UUID) -> str:
        return f"{self._override_backup_key_prefix}:{user_id}"

    async def _backup_inferred_value(
        self,
        user_id: UUID,
        pref_key: str,
        value: Any,
        updated_at: Any,
    ) -> None:
        if not self.redis:
            return
        payload = {
            "value": value,
            "updated_at": updated_at.isoformat() if updated_at is not None else None,
        }
        try:
            await self.redis.hset(
                self._override_backup_key(user_id),
                pref_key,
                json.dumps(payload, ensure_ascii=True),
            )
        except Exception as exc:
            logger.warning("Failed to backup inferred preference %s: %s", pref_key, exc)

    async def _load_inferred_backup(self, user_id: UUID, pref_key: str) -> Any | None:
        if not self.redis:
            return None
        try:
            raw = await self.redis.hget(self._override_backup_key(user_id), pref_key)
        except Exception as exc:
            logger.warning("Failed to load inferred backup %s: %s", pref_key, exc)
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except Exception:
            return None
        if isinstance(payload, dict):
            return payload.get("value")
        return None

    async def _delete_inferred_backup(self, user_id: UUID, pref_key: str) -> None:
        if not self.redis:
            return
        try:
            await self.redis.hdel(self._override_backup_key(user_id), pref_key)
        except Exception as exc:
            logger.warning("Failed to delete inferred backup %s: %s", pref_key, exc)
