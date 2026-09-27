from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import valid_timezone_name, wall_clock_to_utc_naive
from app.models.chat import ChatMessage, MessageRole
from app.models.focus import FocusSession
from app.models.task import Task, TaskStatus
from app.models.user import PushPreference


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

    async def _user_timezone(self, user_id: UUID) -> str:
        """用户 IANA 时区名——push_preference.timezone 标量直查，缺省 Asia/Shanghai。

        state_aggregator._user_timezone 同款先例（V3-FIX-297 族）：标量直查规避
        db.get 身份映射命中未加载关系的 async lazy-load；缺省/非法回落主市场
        Asia/Shanghai（time_utils 口径）。
        """
        tz_name = await self.db.scalar(select(PushPreference.timezone).where(PushPreference.user_id == user_id))
        return valid_timezone_name(tz_name)

    async def get_last_activity_snapshot(self, user_id: UUID) -> UserActivitySnapshot:
        tz_name = await self._user_timezone(user_id)
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
        # V3-FIX-319：end_time 存客户端本地墙上时间 naive（V3-FIX-37 定界），
        # 与 UTC 存储列（ChatMessage.created_at / Task.completed_at）同入 max()
        # 会跨钟夺魁——UTC+8 墙上钟值显得比真实绝对时刻「新」8h，活跃判定
        # （消费面 aurora comeback 以 now - last_activity_at 差值取静默时长）
        # 延迟 ~8h。先按用户时区换算成绝对 UTC naive 同钟再 max；字段语义
        # 与另两列统一为绝对 UTC naive（V3-FIX-297 engagement max 同款）。
        focus_end_wall = focus_result.scalar_one_or_none()
        return UserActivitySnapshot(
            last_message_at=_as_utc_naive(message_result.scalar_one_or_none()),
            last_task_completion_at=_as_utc_naive(task_result.scalar_one_or_none()),
            last_focus_session_at=(
                wall_clock_to_utc_naive(focus_end_wall, tz_name) if focus_end_wall is not None else None
            ),
        )

    async def get_last_real_activity_at(self, user_id: UUID) -> datetime | None:
        return (await self.get_last_activity_snapshot(user_id)).last_activity_at
