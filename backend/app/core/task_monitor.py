from __future__ import annotations

import json
from datetime import timezone, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select

from app.core.cache import cache_service
from app.db.session import AsyncSessionLocal
from app.models.background_task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TaskMonitorService:
    STREAM_NAME = "task_monitor_events"
    COMMAND_STREAM = "task_monitor_commands"
    RESPONSE_STREAM = "task_monitor_responses"

    @staticmethod
    def user_channel(user_id: str | UUID) -> str:
        return f"task_monitor:{user_id}"

    async def publish_progress(
        self,
        *,
        user_id: str | UUID,
        task_type: BackgroundTaskType,
        name: str,
        status: BackgroundTaskStatus,
        progress: float,
        progress_message: str,
        external_task_id: str | None = None,
        related_entity_id: str | UUID | None = None,
        related_entity_type: str | None = None,
        result_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        command_type: str = "task.progress",
    ) -> dict[str, Any]:
        task_payload = await self._upsert_background_task(
            user_id=user_id,
            task_type=task_type,
            name=name,
            status=status,
            progress=progress,
            progress_message=progress_message,
            external_task_id=external_task_id,
            related_entity_id=related_entity_id,
            related_entity_type=related_entity_type,
            result_data=result_data,
            error_message=error_message,
        )

        payload = {
            "command_type": command_type,
            "tracked_at": _utcnow().isoformat(),
            "task": task_payload,
        }
        await self._publish_realtime(str(user_id), payload)
        await self._append_stream(self.STREAM_NAME, payload)
        return task_payload

    async def publish_command(
        self,
        *,
        user_id: str | UUID,
        command_type: str,
        payload: dict[str, Any],
        correlation_id: str,
    ) -> None:
        event = {
            "user_id": str(user_id),
            "command_type": command_type,
            "correlation_id": correlation_id,
            "payload": payload,
            "created_at": _utcnow().isoformat(),
        }
        await self._append_stream(self.COMMAND_STREAM, event)

    async def publish_response(
        self,
        *,
        user_id: str | UUID,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        event = {
            "user_id": str(user_id),
            "correlation_id": correlation_id,
            "payload": payload,
            "created_at": _utcnow().isoformat(),
        }
        await self._append_stream(self.RESPONSE_STREAM, event)
        await self._publish_realtime(str(user_id), {"command_type": "task.response", **event})

    async def _upsert_background_task(
        self,
        *,
        user_id: str | UUID,
        task_type: BackgroundTaskType,
        name: str,
        status: BackgroundTaskStatus,
        progress: float,
        progress_message: str,
        external_task_id: str | None,
        related_entity_id: str | UUID | None,
        related_entity_type: str | None,
        result_data: dict[str, Any] | None,
        error_message: str | None,
    ) -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            task = None
            if external_task_id:
                result = await session.execute(
                    select(BackgroundTask).where(
                        and_(
                            BackgroundTask.user_id == UUID(str(user_id)),
                            BackgroundTask.external_task_id == external_task_id,
                        )
                    )
                )
                task = result.scalar_one_or_none()

            if task is None:
                task = BackgroundTask(
                    user_id=UUID(str(user_id)),
                    task_type=task_type,
                    name=name,
                    external_task_id=external_task_id,
                    related_entity_id=UUID(str(related_entity_id)) if related_entity_id else None,
                    related_entity_type=related_entity_type,
                )
                session.add(task)

            task.task_type = task_type
            task.name = name
            task.status = status
            task.progress = max(0.0, min(progress, 1.0))
            task.progress_message = progress_message[:2000] if progress_message else None
            task.related_entity_type = related_entity_type
            task.result_data = result_data
            task.error_message = error_message
            if related_entity_id:
                task.related_entity_id = UUID(str(related_entity_id))
            if status in {BackgroundTaskStatus.COMPLETED, BackgroundTaskStatus.FAILED, BackgroundTaskStatus.CANCELLED}:
                task.completed_at = _utcnow()

            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task.to_dict()

    async def _publish_realtime(self, user_id: str, payload: dict[str, Any]) -> None:
        if not cache_service.redis:
            await cache_service.init_redis()
        if not cache_service.redis:
            return
        try:
            await cache_service.redis.publish(
                self.user_channel(user_id),
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception as exc:
            logger.warning("Failed to publish task monitor realtime event: {}", exc)

    async def _append_stream(self, stream: str, payload: dict[str, Any]) -> None:
        if not cache_service.redis:
            await cache_service.init_redis()
        if not cache_service.redis:
            return
        try:
            await cache_service.redis.xadd(
                stream,
                {
                    "payload": json.dumps(payload, ensure_ascii=False),
                    "user_id": str(payload.get("user_id") or payload.get("task", {}).get("user_id") or ""),
                    "command_type": str(payload.get("command_type") or ""),
                    "timestamp": _utcnow().isoformat(),
                },
                maxlen=5000,
                approximate=True,
            )
        except Exception as exc:
            logger.warning("Failed to append task monitor stream event: {}", exc)


task_monitor_service = TaskMonitorService()
