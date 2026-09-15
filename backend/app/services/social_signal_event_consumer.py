from __future__ import annotations

import asyncio

from loguru import logger

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.core.event_types import ACCOUNTABILITY_STRUGGLE_DETECTED
from app.db.session import AsyncSessionLocal
from app.services.social_signal_bridge import SocialSignalBridge


class SocialSignalEventConsumer:
    """Consumes social accountability signals and turns them into user-visible support."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "social_signal_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self) -> None:
        await self.event_bus.connect()
        self._running = True
        logger.info("SocialSignalEventConsumer started")

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"social-signal-{id(self)}",
                    callback=self._handle_event,
                )
                break
            except Exception as exc:
                logger.error("SocialSignalEventConsumer error: {}", exc)
                await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def _handle_event(self, event: dict) -> None:
        if event.get("event_type") != ACCOUNTABILITY_STRUGGLE_DETECTED:
            return

        async with AsyncSessionLocal() as db:
            result = await SocialSignalBridge(db, cache_service.redis).handle_accountability_struggle_detected(event)
            logger.debug("Social signal handled: {}", result)
