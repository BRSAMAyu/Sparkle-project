"""Execution event consumer for scheduled/batch completion notifications."""

from __future__ import annotations

import asyncio
from datetime import timezone, datetime
from uuid import UUID

from loguru import logger

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.task import Task
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExecutionEventConsumer:
    """Consume execution lifecycle events and fan them into user-visible notifications."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "execution_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        await self.event_bus.connect()
        self._running = True
        logger.info("ExecutionEventConsumer started, listening on {}", self.STREAM_NAME)

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"execution-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error("ExecutionEventConsumer error: {}", exc)
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        event_type = str(event.get("event_type") or "").strip()
        if event_type == "EXECUTION_SCHEDULED_COMPLETED":
            await self._handle_scheduled_completed(event)
        elif event_type == "EXECUTION_BATCH_COMPLETED":
            await self._handle_batch_completed(event)

    async def _handle_scheduled_completed(self, event: dict) -> None:
        user_id = str(event.get("user_id") or "").strip()
        if not user_id:
            return
        task_title = await self._resolve_task_title(event.get("task_id"))
        status = str(event.get("status") or "completed").strip() or "completed"
        schedule_id = str(event.get("schedule_id") or "").strip()
        async with AsyncSessionLocal() as db:
            await NotificationService.create(
                db,
                UUID(user_id),
                NotificationCreate(
                    title="定时执行已完成",
                    content=f"{task_title or '你的定时任务'} 已自动触发，本次状态：{status}。",
                    type="system",
                    data={
                        "execution_schedule_id": schedule_id,
                        "execution_intent_id": event.get("execution_intent_id"),
                        "task_id": event.get("task_id"),
                        "status": status,
                        "trigger_type": event.get("trigger_type"),
                    },
                ),
            )

    async def _handle_batch_completed(self, event: dict) -> None:
        user_id = str(event.get("user_id") or "").strip()
        if not user_id:
            return
        completed = int(event.get("completed_count") or 0)
        failed = int(event.get("failed_count") or 0)
        queued = int(event.get("queued_count") or 0)
        batch_id = str(event.get("batch_id") or "").strip()
        async with AsyncSessionLocal() as db:
            await NotificationService.create(
                db,
                UUID(user_id),
                NotificationCreate(
                    title="批量委派已完成",
                    content=f"本批次已完成 {completed} 项，失败 {failed} 项，排队 {queued} 项。",
                    type="system",
                    data={
                        "execution_batch_id": batch_id,
                        "intent_ids": list(event.get("intent_ids") or []),
                        "task_ids": list(event.get("task_ids") or []),
                        "completed_count": completed,
                        "failed_count": failed,
                        "queued_count": queued,
                        "status": event.get("status"),
                    },
                ),
            )

    @staticmethod
    async def _resolve_task_title(task_id: str | None) -> str | None:
        text = str(task_id or "").strip()
        if not text:
            return None
        try:
            task_uuid = UUID(text)
        except ValueError:
            return None
        async with AsyncSessionLocal() as db:
            task = await db.get(Task, task_uuid)
            return str(task.title).strip() if task and task.title else None
