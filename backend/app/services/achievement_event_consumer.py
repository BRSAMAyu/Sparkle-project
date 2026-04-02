"""
Achievement event consumer.
Closes event-bus paths for achievement progression without blocking request handlers.
"""

import asyncio
from datetime import timezone, datetime

from loguru import logger

from app.core.event_bus import EventBus
from app.core.event_types import EXECUTION_RESULT_INGESTED
from app.db.session import AsyncSessionLocal
from app.models.execution_intent import ExecutionIntent
from app.models.execution_record import ExecutionRecord
from app.models.task import Task
from app.services.achievement_engine import AchievementEngine, AchievementEvent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        elif event_type == "focus.session.completed":
            await self._handle_focus_session_completed(event)
        elif event_type == EXECUTION_RESULT_INGESTED:
            await self._handle_execution_result(event)
        elif event_type == "achievement.unlocked":
            await self._handle_achievement_unlocked(event)

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

    async def _handle_focus_session_completed(self, event: dict):
        user_id = event.get("user_id")
        if not user_id:
            return
        duration_minutes = int(float(event.get("duration_minutes") or 0))
        if duration_minutes <= 0:
            return
        async with AsyncSessionLocal() as db:
            engine = AchievementEngine(db)
            await engine.process_event(
                user_id=str(user_id),
                event_type=AchievementEvent.STUDY_MINUTES_ACCUMULATED,
                actual_minutes=duration_minutes,
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

    async def _handle_execution_result(self, event: dict):
        if not bool(event.get("success")):
            return

        intent_id = event.get("execution_intent_id")
        record_id = event.get("execution_record_id")
        user_id = event.get("user_id")
        if not intent_id or not record_id or not user_id:
            return

        try:
            async with AsyncSessionLocal() as db:
                intent = await db.get(ExecutionIntent, intent_id)
                record = await db.get(ExecutionRecord, record_id)
                if intent is None or record is None:
                    return
                if not bool((intent.policy or {}).get("chat_control")):
                    return

                task = await db.get(Task, intent.task_id) if intent.task_id else None
                actual_minutes = max(1, int((record.duration_ms or 0) / 60000))
                estimated_minutes = int(getattr(task, "estimated_minutes", 0) or actual_minutes)
                difficulty = int(getattr(task, "difficulty", 1) or 1)

                engine = AchievementEngine(db)
                await engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.TASK_COMPLETED,
                    task_id=str(intent.task_id or ""),
                    actual_minutes=actual_minutes,
                    estimated_minutes=estimated_minutes,
                    difficulty=difficulty,
                    source="execution_chat_control",
                )
        except Exception as exc:
            logger.warning(f"Failed to process execution achievement event: {exc}")

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

    async def _handle_achievement_unlocked(self, event: dict):
        """处理成就解锁事件，触发认知系统碎片记录及可能的广播"""
        user_id = event.get("user_id")
        achievement_id = event.get("achievement_id")
        if not user_id or not achievement_id:
            return

        try:
            from uuid import UUID

            from app.core.cache import cache_service
            from app.services.cognitive_service import CognitiveService
            from app.services.community_signal_bridge import CommunitySignalBridge
            from app.services.personalization.preference_service import PreferenceService

            async with AsyncSessionLocal() as db:
                cognitive_service = CognitiveService(db)
                achievement_title = event.get("achievement_name") or event.get("title") or str(achievement_id)
                await cognitive_service.create_fragment(
                    user_id=UUID(str(user_id)),
                    content=f"用户达成了 {achievement_title} 成就。这是用户持续努力和进步的证明。",
                    source_type="achievement",
                    severity=1,
                    context_tags={"achievement_id": str(achievement_id), "type": "positive_milestone"},
                )
                logger.info(f"Recorded cognitive fragment for achievement {achievement_id} unlock by user {user_id}")

                pref_service = PreferenceService(db, cache_service.redis)
                prefs = await pref_service.get_preferences(UUID(str(user_id)))
                share_enabled = (prefs.explicit or {}).get("share_achievements_to_community", True)

                if share_enabled:
                    try:
                        bridge = CommunitySignalBridge(db, cache_service.redis)
                        await bridge.broadcast_achievement_unlock(
                            user_id=UUID(str(user_id)),
                            achievement_id=str(achievement_id),
                            achievement_title=achievement_title,
                            rarity=event.get("rarity", "common"),
                        )
                        logger.info(f"Broadcast achievement {achievement_id} unlock to community for user {user_id}")
                    except Exception as broadcast_err:
                        logger.warning(f"Failed to broadcast achievement to community: {broadcast_err}")
        except Exception as e:
            logger.warning(f"Failed to record cognitive fragment for achievement: {e}")

    def stop(self):
        self._running = False
