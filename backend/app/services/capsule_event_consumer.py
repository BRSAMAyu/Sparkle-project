"""
Capsule event consumer - listens to cognitive profile updates and feedback triggers.
"""
import asyncio
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.core.event_types import CAPSULE_REGENERATE_REQUESTED, PROFILE_COGNITIVE_UPDATED
from app.db.session import AsyncSessionLocal
from app.services.capsule_generation_service import CapsuleGenerationService
from app.services.personalization.preference_service import PreferenceService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CapsuleEventConsumer:
    """监听画像变化，触发胶囊重新生成或提示。"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "capsule_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self.capsule_generation_service = CapsuleGenerationService()

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"capsule-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error(f"CapsuleEventConsumer error: {exc}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        event_type = event.get("event_type")
        if event_type == PROFILE_COGNITIVE_UPDATED:
            await self._handle_profile_update(event)
        elif event_type == CAPSULE_REGENERATE_REQUESTED:
            await self._handle_regenerate_request(event)

    async def _handle_profile_update(self, event: dict):
        user_id = event.get("user_id")
        if not user_id:
            return
        try:
            confidence_change = float(event.get("confidence_change") or 0)
        except (TypeError, ValueError):
            confidence_change = 0.0
        if confidence_change <= 0.15:
            return

        pattern_name = str(event.get("pattern_name") or "")
        reason = f"检测到新的行为模式：{pattern_name}" if pattern_name else "检测到新的行为模式"
        await self._suggest_capsule_generation(user_id, reason, pattern_name)

    async def _handle_regenerate_request(self, event: dict):
        user_id = event.get("user_id")
        if not user_id:
            return
        try:
            user_uuid = UUID(str(user_id))
        except ValueError:
            return

        async with AsyncSessionLocal() as db:
            pref_service = PreferenceService(db, cache_service.redis)
            prefs = await pref_service.get_preferences(user_uuid)
            inferred = prefs.inferred or {}
            explicit = prefs.explicit or {}
            depth_preference = inferred.get("depth_preference") or explicit.get("depth_preference") or 0.5
            curiosity_preference = inferred.get("curiosity_preference") or explicit.get("curiosity_preference") or 0.5

            try:
                await self.capsule_generation_service.generate_capsules_batch(
                    user_id=user_uuid,
                    db=db,
                    depth_preference=depth_preference,
                    curiosity_preference=curiosity_preference,
                    generation_type="feedback_triggered",
                )
            except Exception as exc:
                logger.error(f"Failed to regenerate capsules for user {user_uuid}: {exc}")

    async def _suggest_capsule_generation(self, user_id: str, reason: str, pattern_name: str | None = None):
        await SystemUpdateService(cache_service.redis).enqueue(
            user_id,
            build_system_update(
                update_type="capsule_regen_suggested",
                category="capsule",
                title="基于你的行为模式推荐新胶囊",
                description=reason,
                priority="low",
                metadata={
                    "pattern_name": pattern_name,
                    "reason": reason,
                },
            ),
        )
