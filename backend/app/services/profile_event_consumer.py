"""
Profile preference event consumer.
Keeps downstream caches and user-visible updates in sync with preference changes.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.core.event_types import (
    ACCOUNTABILITY_CHECKIN_CREATED,
    ACCOUNTABILITY_PARTNERSHIP_UPDATED,
    CAPSULE_CONTENT_UPDATED,
    CAPSULE_FAVORITE_UPDATED,
    CAPSULE_FEEDBACK_SUBMITTED,
    CAPSULE_REGENERATE_REQUESTED,
    TOOL_HISTORY_RECORDED,
    TOOL_USAGE_EVENT,
)
from app.db.session import AsyncSessionLocal
from app.models.seed_content import SeedLibrary
from app.services.behavior_signal_collector import BehaviorSignalCollector
from app.services.capsule_favorite_service import CapsuleFavoriteService
from app.services.cognitive.auto_fragment_collector import AutoFragmentCollector
from app.services.error_book_signal_processor import ErrorBookSignalProcessor
from app.services.focus_signal_processor import FocusSignalProcessor
from app.services.personalization.engine import invalidate_personalization_cache
from app.services.profile_write_service import ProfileWriteService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ProfileEventConsumer:
    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "profile_event_consumer"
    INSIGHT_SIGNAL_EVENTS = {
        "achievement.unlocked",
        "calendar.event.created",
        "calendar.event.updated",
        "calendar.event.deleted",
        CAPSULE_FEEDBACK_SUBMITTED,
        CAPSULE_REGENERATE_REQUESTED,
        CAPSULE_FAVORITE_UPDATED,
        CAPSULE_CONTENT_UPDATED,
        TOOL_HISTORY_RECORDED,
        TOOL_USAGE_EVENT,
        ACCOUNTABILITY_PARTNERSHIP_UPDATED,
        ACCOUNTABILITY_CHECKIN_CREATED,
    }

    def __init__(self, event_bus: EventBus, redis_client=None):
        self.event_bus = event_bus
        self.redis = redis_client or cache_service.redis
        self._running = False

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name="profile-consumer-1",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error(f"ProfileEventConsumer error: {exc}")
                await asyncio.sleep(1)

    def stop(self):
        self._running = False

    async def handle_event(self, event: dict):
        event_type = event.get("event_type")
        if event_type == "profile.preference.updated":
            await self._handle_preference_updated(event)
        elif event_type == "profile.preference.deleted":
            await self._handle_preference_deleted(event)
        elif event_type in {"knowledge_node_updated", "node_mastery_updated"}:
            await self._handle_knowledge_updated(event)
        elif event_type == "behavior.pattern.updated":
            await self._handle_behavior_pattern_updated(event)
        elif event_type == "focus.session.completed":
            await self._handle_focus_session_completed(event)
        elif event_type == "error_created":
            await self._handle_error_created(event)
        elif event_type in {"seed.created", "seed.consumed"}:
            await self._handle_seed_library_event(event)
        elif event_type == CAPSULE_FAVORITE_UPDATED:
            await self._handle_capsule_favorite_updated(event)
        elif event_type == TOOL_USAGE_EVENT:
            await self._handle_tool_history_recorded(event)
        elif event_type in self.INSIGHT_SIGNAL_EVENTS:
            await self._handle_insight_signal_family_updated(event)

    async def _handle_preference_updated(self, event: dict):
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return

            await self._invalidate_context_cache(user_id)
            await self._invalidate_profile_context_cache(user_id)
            invalidate_personalization_cache(user_id)

            source = str(event.get("source") or "")
            if source == "ai_inferred":
                pref_keys = self._normalize_pref_keys(event.get("pref_keys"))
                description = "系统根据你的行为更新了偏好"
                if pref_keys:
                    description = f"系统根据你的行为更新了偏好：{', '.join(pref_keys)}"
                await SystemUpdateService(self.redis).enqueue(
                    user_id,
                    build_system_update(
                        update_type="profile_preference_inferred",
                        category="preference",
                        title="你的画像偏好已更新",
                        description=description,
                        priority="medium",
                        metadata={
                            "pref_keys": pref_keys,
                            "source": source,
                            "preference_version": event.get("preference_version"),
                        },
                    ),
                )
        except Exception as exc:
            logger.error(f"Failed to handle profile.preference.updated: {exc}")
            raise

    async def _handle_preference_deleted(self, event: dict):
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_context_cache(user_id)
            await self._invalidate_profile_context_cache(user_id)
            invalidate_personalization_cache(user_id)
        except Exception as exc:
            logger.error(f"Failed to handle profile.preference.deleted: {exc}")
            raise

    async def _handle_knowledge_updated(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_profile_context_cache(user_id)
        except Exception as exc:
            logger.error(f"Failed to handle knowledge update event: {exc}")
            raise

    async def _handle_behavior_pattern_updated(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_profile_context_cache(user_id)
        except Exception as exc:
            logger.error(f"Failed to handle behavior pattern update event: {exc}")
            raise

    async def _handle_focus_session_completed(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_profile_context_cache(user_id)
            async with AsyncSessionLocal() as db:
                processor = FocusSignalProcessor(db, self.redis)
                await processor.process_focus_event(UUID(user_id))
        except Exception as exc:
            logger.error(f"Failed to handle focus session event: {exc}")
            raise

    async def _handle_error_created(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_profile_context_cache(user_id)
            async with AsyncSessionLocal() as db:
                processor = ErrorBookSignalProcessor(db, self.redis)
                await processor.process_error_created(UUID(user_id))
                auto_collector = AutoFragmentCollector(db)
                error_id_value = event.get("error_id")
                error_id = None
                if error_id_value:
                    try:
                        error_id = UUID(str(error_id_value))
                    except ValueError:
                        error_id = None
                await auto_collector.collect_from_error_pattern(
                    user_id=UUID(user_id),
                    error_id=error_id,
                    linked_node_ids=event.get("linked_node_ids") or [],
                )
        except Exception as exc:
            logger.error(f"Failed to handle error created event: {exc}")
            raise

    async def _handle_insight_signal_family_updated(self, event: dict) -> None:
        try:
            user_ids = self._normalize_user_ids(event)
            if not user_ids:
                return
            for user_id in user_ids:
                await self._invalidate_profile_context_cache(user_id)
        except Exception as exc:
            logger.error(f"Failed to handle insight signal family update event: {exc}")
            raise

    async def _handle_capsule_favorite_updated(self, event: dict) -> None:
        try:
            user_ids = self._normalize_user_ids(event)
            if not user_ids:
                return

            for user_id in user_ids:
                await self._invalidate_context_cache(user_id)
                await self._invalidate_profile_context_cache(user_id)
                invalidate_personalization_cache(user_id)

                user_uuid = UUID(user_id)
                async with AsyncSessionLocal() as db:
                    await BehaviorSignalCollector(db, self.redis, self.event_bus).handle_capsule_favorite_event(event)
                    capsule_preferences = await CapsuleFavoriteService().get_preferences(user_uuid, db)
                    await ProfileWriteService(db, self.redis).update_inferred_preference(
                        user_id=user_uuid,
                        updates=self._capsule_preference_updates(capsule_preferences),
                        source="capsule_favorite",
                    )
        except Exception as exc:
            logger.error(f"Failed to handle capsule favorite update event: {exc}")
            raise

    async def _handle_seed_library_event(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return

            await self._invalidate_context_cache(user_id)
            await self._invalidate_profile_context_cache(user_id)
            invalidate_personalization_cache(user_id)

            user_uuid = UUID(user_id)
            async with AsyncSessionLocal() as db:
                library = await self._load_seed_library(db, event.get("library_id"))
                updates = self._seed_library_preference_updates(event, library)
                if updates:
                    await ProfileWriteService(db, self.redis).update_inferred_preference(
                        user_id=user_uuid,
                        updates=updates,
                        source=str(event.get("event_type") or "seed_library"),
                    )
        except Exception as exc:
            logger.error(f"Failed to handle seed library event: {exc}")
            raise

    async def _handle_tool_history_recorded(self, event: dict) -> None:
        try:
            user_ids = self._normalize_user_ids(event)
            if not user_ids:
                return

            for user_id in user_ids:
                await self._invalidate_profile_context_cache(user_id)
                async with AsyncSessionLocal() as db:
                    await BehaviorSignalCollector(db, self.redis, self.event_bus).handle_tool_history_event(event)
        except Exception as exc:
            logger.error(f"Failed to handle tool history event: {exc}")
            raise

    @staticmethod
    async def _load_seed_library(db: Any, library_id: Any) -> SeedLibrary | None:
        if not library_id:
            return None
        try:
            return await db.get(SeedLibrary, UUID(str(library_id)))
        except Exception as db_exc:
            logger.warning("Failed to load SeedLibrary %s: %s", library_id, db_exc)
            return None

    async def _invalidate_context_cache(self, user_id: str) -> None:
        if not self.redis:
            return
        keys = [
            f"user:context:{user_id}",
            f"user:context:snapshot:{user_id}",
        ]
        try:
            await self.redis.delete(*keys)
        except Exception as exc:
            logger.warning(f"Failed to invalidate context cache for user {user_id}: {exc}")

    async def _invalidate_profile_context_cache(self, user_id: str) -> None:
        if not self.redis:
            return
        try:
            await self.redis.delete(f"user:profile_context:{user_id}")
        except Exception as exc:
            logger.warning(f"Failed to invalidate profile context cache for user {user_id}: {exc}")

    @staticmethod
    def _normalize_user_id(value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @classmethod
    def _normalize_user_ids(cls, event: dict[str, Any]) -> list[str]:
        normalized: list[str] = []
        explicit_user_ids = event.get("user_ids")
        if isinstance(explicit_user_ids, list):
            for item in explicit_user_ids:
                user_id = cls._normalize_user_id(item)
                if user_id and user_id not in normalized:
                    normalized.append(user_id)

        user_id = cls._normalize_user_id(event.get("user_id"))
        if user_id and user_id not in normalized:
            normalized.append(user_id)
        return normalized

    @staticmethod
    def _normalize_pref_keys(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except Exception:
                pass
            return [value]
        return [str(value)]

    @staticmethod
    def _capsule_preference_updates(preferences: dict[str, Any]) -> dict[str, Any]:
        updates: dict[str, Any] = {"capsule_preferences": preferences or {}}
        depth = str((preferences or {}).get("content_depth_preference") or "").strip()
        if depth:
            updates["content_depth_preference"] = depth
        subjects = [
            str(subject).strip()
            for subject in list((preferences or {}).get("subject_affinity") or [])
            if str(subject).strip()
        ]
        if subjects:
            updates["content_subject_affinities"] = subjects[:3]
        methods = [
            method
            for method in list((preferences or {}).get("method_preferences") or [])
            if isinstance(method, dict) and str(method.get("label") or "").strip()
        ]
        if methods:
            updates["capsule_method_preferences"] = methods[:5]
            updates["learning_method_preferences"] = [
                str(method.get("label") or "").strip()
                for method in methods[:5]
                if str(method.get("label") or "").strip()
            ]
        favorite_count = int((preferences or {}).get("favorite_count") or 0)
        updates["capsule_favorite_count"] = favorite_count
        return updates

    @staticmethod
    def _seed_library_preference_updates(event: dict[str, Any], library: SeedLibrary | None) -> dict[str, Any]:
        event_type = str(event.get("event_type") or "").strip()
        category = str(getattr(library, "category", None) or event.get("category") or "").strip()
        visibility = str(getattr(library, "visibility", None) or event.get("visibility") or "").strip()
        language = str(getattr(library, "language", None) or event.get("language") or "").strip()
        tags = [
            str(tag).strip()
            for tag in list(getattr(library, "tags", None) or event.get("tags") or [])
            if str(tag).strip()
        ]
        signal = {
            "last_event": event_type,
            "last_library_id": str(event.get("library_id") or ""),
            "last_library_name": str(getattr(library, "name", None) or event.get("library_name") or "").strip(),
            "category": category,
            "visibility": visibility,
            "language": language,
            "tags": tags[:12],
            "priority": event.get("priority"),
            "timestamp": event.get("timestamp"),
        }
        updates: dict[str, Any] = {"seed_library_signal": signal}
        if tags:
            updates["seed_library_affinities"] = tags[:8]
        if category:
            updates["seed_library_category_preference"] = category
        if event_type == "seed.consumed":
            updates["uses_seed_libraries"] = True
        elif event_type == "seed.created":
            updates["creates_seed_libraries"] = True
        return updates
