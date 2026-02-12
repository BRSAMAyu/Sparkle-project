"""
运行时上下文服务 - 收集影响个性化的实时状态
"""
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import PushHistory
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user_state import UserStateSnapshot


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RuntimeContextService:
    """运行时上下文服务"""

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def get_runtime_context(self, user_id: UUID, timezone: str = "Asia/Shanghai") -> dict[str, Any]:
        """获取运行时上下文"""
        return {
            "focus_session_active": await self._is_focus_active(user_id),
            "active_plan_count": await self._get_active_plan_count(user_id),
            "pending_task_count": await self._get_pending_task_count(user_id),
            "today_push_count": await self._get_today_push_count(user_id),
            "last_activity_minutes_ago": await self._get_last_activity_minutes(user_id),
            "current_local_hour": self._get_user_local_hour(timezone),
            "current_local_minute": self._get_user_local_minute(timezone),
            "current_local_dow": self._get_user_local_dow(timezone),
        }

    async def _is_focus_active(self, user_id: UUID) -> bool:
        """检查是否处于专注模式"""
        result = await self.db.execute(
            select(UserStateSnapshot.focus_mode, UserStateSnapshot.snapshot_at)
            .where(UserStateSnapshot.user_id == user_id)
            .order_by(UserStateSnapshot.snapshot_at.desc())
            .limit(1)
        )
        row = result.first()
        if not row:
            return False
        focus_mode, snapshot_at = row
        if not focus_mode:
            return False
        return not (snapshot_at and _utcnow() - snapshot_at > timedelta(hours=2))

    async def _get_active_plan_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Plan.id)).where(
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
        )
        return result.scalar() or 0

    async def _get_pending_task_count(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING,
            )
        )
        return result.scalar() or 0

    async def _get_today_push_count(self, user_id: UUID) -> int:
        today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count(PushHistory.id)).where(
                PushHistory.user_id == user_id,
                PushHistory.created_at >= today_start,
            )
        )
        return result.scalar() or 0

    async def _get_last_activity_minutes(self, user_id: UUID) -> int:
        """获取距离上次活动的分钟数"""
        result = await self.db.execute(
            select(Task.updated_at)
            .where(Task.user_id == user_id)
            .order_by(Task.updated_at.desc())
            .limit(1)
        )
        last_update = result.scalar_one_or_none()
        if not last_update:
            return 9999

        delta = _utcnow() - last_update
        return int(delta.total_seconds() / 60)

    def _get_user_local_hour(self, timezone: str) -> int:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
        return datetime.now(tz).hour

    def _get_user_local_minute(self, timezone: str) -> int:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        return now.hour * 60 + now.minute

    def _get_user_local_dow(self, timezone: str) -> int:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Shanghai")
        return datetime.now(tz).weekday()
