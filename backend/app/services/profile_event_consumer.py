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
from app.db.session import AsyncSessionLocal
from app.services.error_book_signal_processor import ErrorBookSignalProcessor
from app.services.focus_signal_processor import FocusSignalProcessor
from app.services.personalization.engine import invalidate_personalization_cache
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ProfileEventConsumer:
    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "profile_event_consumer"

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
                    consumer_name=f"profile-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error(f"ProfileEventConsumer error: {exc}")
                await asyncio.sleep(1)

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
        elif event_type in {"error_created", "error.created"}:
            await self._handle_error_created(event)

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

    async def _handle_knowledge_updated(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_profile_context_cache(user_id)
        except Exception as exc:
            logger.error(f"Failed to handle knowledge update event: {exc}")

    async def _handle_behavior_pattern_updated(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            await self._invalidate_profile_context_cache(user_id)
        except Exception as exc:
            logger.error(f"Failed to handle behavior pattern update event: {exc}")

    async def _handle_focus_session_completed(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            async with AsyncSessionLocal() as db:
                processor = FocusSignalProcessor(db, self.redis)
                await processor.process_focus_event(UUID(user_id))
        except Exception as exc:
            logger.error(f"Failed to handle focus session event: {exc}")

    async def _handle_error_created(self, event: dict) -> None:
        try:
            user_id = self._normalize_user_id(event.get("user_id"))
            if not user_id:
                return
            async with AsyncSessionLocal() as db:
                processor = ErrorBookSignalProcessor(db, self.redis)
                await processor.process_error_created(UUID(user_id))
        except Exception as exc:
            logger.error(f"Failed to handle error created event: {exc}")

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
