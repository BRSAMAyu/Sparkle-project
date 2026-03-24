"""
Task 事件消费者 - 处理任务与计划相关事件，驱动认知闭环。
"""
import asyncio
import os
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.task import Task
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.behavior_signal_collector import BehaviorSignalCollector
from app.services.cognitive.auto_fragment_collector import AutoFragmentCollector
from app.services.community_signal_bridge import CommunitySignalBridge


class TaskEventConsumer:
    """消费任务 / 计划相关事件"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "task_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._subscribed = False
        self.consumer_name = f"task-{os.getpid()}"

    async def start(self):
        """启动事件消费循环"""
        await self.event_bus.connect()
        if self._running:
            return
        self._running = True

        logger.info(f"TaskEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                if not self._subscribed:
                    await self.event_bus.subscribe(
                        stream=self.STREAM_NAME,
                        group_name=self.GROUP_NAME,
                        consumer_name=self.consumer_name,
                        callback=self.handle_event
                    )
                    self._subscribed = True
                await asyncio.sleep(1)
            except Exception as e:
                self._subscribed = False
                logger.error(f"TaskEventConsumer error: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        """处理单个事件"""
        event_type = event.get("event_type")

        if event_type == "task.completed":
            await self._handle_task_completed(event)
        elif event_type == "task.abandoned":
            await self._handle_task_abandoned(event)
        elif event_type == "task.feedback_submitted":
            await self._handle_task_feedback(event)
        elif event_type == "plan.replanned":
            await self._handle_plan_replanned(event)
        elif event_type == "behavior.pattern.updated":
            await self._handle_behavior_pattern(event)

    async def _handle_task_completed(self, event: dict):
        """处理任务完成。"""
        try:
            user_id = UUID(event["user_id"])
            task_id = UUID(event["task_id"])

            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis)
                bridge = CommunitySignalBridge(db, cache_service.redis)

                estimated = event.get("estimated_minutes", 0)
                actual = event.get("actual_minutes", 0)
                completion_rate = event.get("completion_rate")
                if completion_rate is None:
                    completion_rate = actual / estimated if estimated > 0 else 1.0
                await collector.handle_task_completed_event(event)
                await bridge.handle_group_task_completed(event)

                try:
                    auto_collector = AutoFragmentCollector(db)
                    await auto_collector.collect_from_task_completion(
                        user_id=user_id,
                        task_id=task_id,
                        estimated_minutes=estimated if estimated else None,
                        actual_minutes=actual if actual else None,
                        completion_rate=completion_rate,
                        difficulty=event.get("difficulty"),
                    )
                except Exception as exc:
                    logger.warning(f"Auto fragment collection failed for task {task_id}: {exc}")

                plan_id = event.get("plan_id")
                if not plan_id or plan_id == "None":
                    result = await db.execute(
                        select(Task.plan_id).where(
                            Task.id == task_id,
                            Task.user_id == user_id,
                        )
                    )
                    plan_id = result.scalar_one_or_none()

                if plan_id:
                    adaptive_replanner = AdaptiveReplanner(db, cache_service.redis)
                    await adaptive_replanner.on_task_completed(
                        user_id=user_id,
                        plan_id=UUID(str(plan_id)),
                        task_id=task_id,
                        completion_rate=completion_rate,
                    )

        except Exception as e:
            logger.error(f"Failed to handle task.completed: {e}")

    async def _handle_task_abandoned(self, event: dict):
        """处理任务放弃。"""
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis)
                await collector.handle_task_abandoned_event(event)

        except Exception as e:
            logger.error(f"Failed to handle task.abandoned: {e}")

    async def _handle_task_feedback(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis)
                await collector.handle_task_feedback_event(event)
        except Exception as e:
            logger.error(f"Failed to handle task.feedback_submitted: {e}")

    async def _handle_plan_replanned(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis)
                await collector.handle_plan_replanned_event(event)
        except Exception as e:
            logger.error(f"Failed to handle plan.replanned: {e}")

    async def _handle_behavior_pattern(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis)
                await collector.handle_behavior_pattern_event(event)
        except Exception as e:
            logger.error(f"Failed to handle behavior.pattern.updated: {e}")

    def stop(self):
        """停止消费者"""
        self._running = False
