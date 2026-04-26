"""
Document feedback event consumer.
"""
from __future__ import annotations

import asyncio
import os

from loguru import logger

from app.core.event_bus import EventBus, reliable_consumer
from app.db.session import AsyncSessionLocal
from app.services.document_service import document_service


class DocumentFeedbackEventConsumer:
    """Persist document citation feedback events and refresh retrieval quality scores."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "document_feedback_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._subscribed = False
        self.consumer_name = f"document-feedback-{os.getpid()}"

    async def start(self):
        await self.event_bus.connect()
        if self._running:
            return
        self._running = True

        logger.info(f"DocumentFeedbackEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                if not self._subscribed:
                    await self.event_bus.subscribe(
                        stream=self.STREAM_NAME,
                        group_name=self.GROUP_NAME,
                        consumer_name=self.consumer_name,
                        callback=self.handle_event,
                    )
                    self._subscribed = True
                await asyncio.sleep(1)
            except Exception as exc:
                self._subscribed = False
                logger.error(f"DocumentFeedbackEventConsumer error: {exc}")
                await asyncio.sleep(1)

    @reliable_consumer("DocumentFeedbackEventConsumer")
    async def handle_event(self, event: dict):
        if event.get("event_type") != "document.citation.feedback":
            return

        async with AsyncSessionLocal() as db:
            await document_service.persist_feedback_event(db, event)
            await db.commit()

    def stop(self):
        self._running = False
