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
from app.services.metacognition_service import MetacognitionService


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
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                bridge = CommunitySignalBridge(db, cache_service.redis)

                estimated = event.get("estimated_minutes", 0)
                actual = event.get("actual_minutes", 0)
                completion_rate = event.get("completion_rate")
                if completion_rate is None:
                    completion_rate = actual / estimated if estimated > 0 else 1.0
                await collector.handle_task_completed_event(event)
                await MetacognitionService(db, cache_service.redis, self.event_bus).refresh_snapshot(user_id)
                await bridge.handle_group_task_completed(event)

                # Signal-to-Action Spine: task.completed → signal detection
                try:
                    from app.signals.spine_orchestrator import SpineOrchestrator
                    spine = SpineOrchestrator(cache_service.redis)
                    await spine.on_task_completed(
                        user_id=str(user_id),
                        task_id=str(task_id),
                        estimated_minutes=estimated,
                        actual_minutes=actual,
                        plan_id=event.get("plan_id"),
                    )
                except Exception as spine_exc:
                    logger.warning("Spine pipeline error for task {}: {}", task_id, spine_exc)

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
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_task_abandoned_event(event)

        except Exception as e:
            logger.error(f"Failed to handle task.abandoned: {e}")

    async def _handle_task_feedback(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_task_feedback_event(event)

                user_id_raw = event.get("user_id")
                task_id_raw = event.get("task_id")
                if not user_id_raw or not task_id_raw:
                    return

                user_id = UUID(str(user_id_raw))
                task_id = UUID(str(task_id_raw))
                plan_id = event.get("plan_id")
                if not plan_id or plan_id == "None":
                    result = await db.execute(
                        select(Task.plan_id).where(
                            Task.id == task_id,
                            Task.user_id == user_id,
                        )
                    )
                    plan_id = result.scalar_one_or_none()

                if not plan_id:
                    return

                adaptive_replanner = AdaptiveReplanner(db, cache_service.redis)
                await adaptive_replanner.on_task_feedback(
                    user_id=user_id,
                    plan_id=UUID(str(plan_id)),
                    task_id=task_id,
                    category=event.get("category") or event.get("feedback_category"),
                    difficulty_delta=event.get("difficulty_delta"),
                    feedback_text=event.get("feedback_text") or event.get("feedback"),
                )
        except Exception as e:
            logger.error(f"Failed to handle task.feedback_submitted: {e}")

    async def _handle_plan_replanned(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_plan_replanned_event(event)
        except Exception as e:
            logger.error(f"Failed to handle plan.replanned: {e}")

    async def _handle_behavior_pattern(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_behavior_pattern_event(event)
        except Exception as e:
            logger.error(f"Failed to handle behavior.pattern.updated: {e}")

    def stop(self):
        """停止消费者"""
        self._running = False
