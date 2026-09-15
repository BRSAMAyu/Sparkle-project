from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, MessageRole
from app.models.focus import FocusSession
from app.models.task import Task, TaskStatus


def _as_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


@dataclass(frozen=True, slots=True)
class UserActivitySnapshot:
    last_message_at: datetime | None = None
    last_task_completion_at: datetime | None = None
    last_focus_session_at: datetime | None = None

    @property
    def last_activity_at(self) -> datetime | None:
        return max(
            (
                activity_at
                for activity_at in (
                    self.last_message_at,
                    self.last_task_completion_at,
                    self.last_focus_session_at,
                )
                if activity_at is not None
            ),
            default=None,
        )


class UserActivityService:
    """Reads user activity signals that reflect real product usage."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_last_activity_snapshot(self, user_id: UUID) -> UserActivitySnapshot:
        message_result = await self.db.execute(
            select(func.max(ChatMessage.created_at)).where(
                ChatMessage.user_id == user_id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.deleted_at.is_(None),
            )
        )
        task_result = await self.db.execute(
            select(func.max(Task.completed_at)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.isnot(None),
                Task.deleted_at.is_(None),
            )
        )
        focus_result = await self.db.execute(
            select(func.max(FocusSession.end_time)).where(
                FocusSession.user_id == user_id,
                FocusSession.end_time.isnot(None),
                FocusSession.deleted_at.is_(None),
            )
        )

        return UserActivitySnapshot(
            last_message_at=_as_utc_naive(message_result.scalar_one_or_none()),
            last_task_completion_at=_as_utc_naive(task_result.scalar_one_or_none()),
            last_focus_session_at=_as_utc_naive(focus_result.scalar_one_or_none()),
        )

    async def get_last_real_activity_at(self, user_id: UUID) -> datetime | None:
        return (await self.get_last_activity_snapshot(user_id)).last_activity_at
