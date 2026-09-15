"""
Group file event consumer.
"""
from __future__ import annotations

import asyncio
import os

from loguru import logger

from app.core.celery_tasks import delete_group_file_index, process_group_shared_file
from app.core.event_bus import EventBus


class GroupFileEventConsumer:
    """Consume group file lifecycle events and enqueue indexing work."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "group_file_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._subscribed = False
        self.consumer_name = f"group-file-{os.getpid()}"

    async def start(self) -> None:
        await self.event_bus.connect()
        if self._running:
            return
        self._running = True

        logger.info(f"GroupFileEventConsumer started, listening on {self.STREAM_NAME}")

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
                logger.error(f"GroupFileEventConsumer error: {exc}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict) -> None:
        event_type = str(event.get("event_type") or "").strip()
        if event_type == "group.file.shared":
            self._enqueue_group_processing(event)
        elif event_type == "group.file.deleted":
            self._enqueue_group_cleanup(event)

    def _enqueue_group_processing(self, event: dict) -> None:
        group_id = str(event.get("group_id") or "").strip()
        file_id = str(event.get("file_id") or "").strip()
        shared_by_user_id = str(event.get("shared_by_user_id") or "").strip()
        if not group_id or not file_id or not shared_by_user_id:
            logger.warning(f"Discarding invalid group.file.shared event: {event}")
            return
        process_group_shared_file.delay(
            group_id=group_id,
            file_id=file_id,
            shared_by_user_id=shared_by_user_id,
        )

    def _enqueue_group_cleanup(self, event: dict) -> None:
        group_id = str(event.get("group_id") or "").strip()
        file_id = str(event.get("file_id") or "").strip()
        if not group_id or not file_id:
            logger.warning(f"Discarding invalid group.file.deleted event: {event}")
            return
        delete_group_file_index.delay(
            group_id=group_id,
            file_id=file_id,
        )

    def stop(self) -> None:
        self._running = False
