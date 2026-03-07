"""
Achievement event consumer.
Closes event-bus paths for achievement progression without blocking request handlers.
"""
import asyncio
from datetime import UTC, datetime

from loguru import logger

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.services.achievement_engine import AchievementEngine, AchievementEvent


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AchievementEventConsumer:
    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "achievement_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"achievement-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error(f"AchievementEventConsumer error: {exc}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        event_type = event.get("event_type")
        if event_type == "task.completed":
            await self._handle_task_completed(event)
        elif event_type == "community.group_task_completed":
            await self._handle_group_task_completed(event)
        elif event_type == "galaxy.node.updated":
            await self._handle_node_updated(event)

    async def _handle_task_completed(self, event: dict):
        if str(event.get("source") or "personal") == "group":
            return
        async with AsyncSessionLocal() as db:
            engine = AchievementEngine(db)
            await engine.process_event(
                user_id=str(event["user_id"]),
                event_type=AchievementEvent.TASK_COMPLETED,
                task_id=str(event.get("task_id") or ""),
                actual_minutes=int(float(event.get("actual_minutes") or 0)),
                estimated_minutes=int(float(event.get("estimated_minutes") or 0)),
                difficulty=int(float(event.get("difficulty") or 1)),
            )

    async def _handle_group_task_completed(self, event: dict):
        async with AsyncSessionLocal() as db:
            engine = AchievementEngine(db)
            await engine.process_event(
                user_id=str(event["user_id"]),
                event_type=AchievementEvent.TASK_COMPLETED,
                task_id=str(event.get("personal_task_id") or ""),
                source="group",
                group_task_id=str(event.get("group_task_id") or ""),
            )

    async def _handle_node_updated(self, event: dict):
        old_mastery = float(event.get("old_mastery") or 0.0)
        new_mastery = float(event.get("new_mastery") or 0.0)
        if new_mastery <= old_mastery:
            return
        async with AsyncSessionLocal() as db:
            engine = AchievementEngine(db)
            user_id = str(event["user_id"])
            if old_mastery <= 0 < new_mastery:
                await engine.process_event(
                    user_id=user_id,
                    event_type=AchievementEvent.NODE_UNLOCKED,
                    node_id=str(event.get("node_id") or ""),
                )
            if old_mastery < 80 <= new_mastery:
                await engine.process_event(
                    user_id=user_id,
                    event_type=AchievementEvent.NODE_MASTERED,
                    node_id=str(event.get("node_id") or ""),
                )

    def stop(self):
        self._running = False
