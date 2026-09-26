from abc import ABC, abstractmethod
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import local_date, valid_timezone_name
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.models.user import PushPreference, User
from app.services.personalization import PushPolicyProfile


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _local_wall_now(now_utc_naive: datetime, timezone_name: str) -> datetime:
    """Naive wall-clock "now" in the user's timezone (for wall-semantics date math)."""
    return now_utc_naive.replace(tzinfo=UTC).astimezone(ZoneInfo(timezone_name)).replace(tzinfo=None)


class PushStrategy(ABC):
    """推送策略基类 - 集成个性化引擎"""

    trigger_type: str = "unknown"

    def __init__(self, db: AsyncSession):
        self.db = db

    @abstractmethod
    async def should_trigger(self, user: User, policy: PushPolicyProfile) -> bool:
        """判断是否应该触发推送（使用个性化策略）"""
        raise NotImplementedError

    @abstractmethod
    async def get_context_data(self, user: User) -> dict[str, Any]:
        """获取推送上下文数据"""
        raise NotImplementedError


class MemoryStrategy(PushStrategy):
    """记忆临界点策略 - 个性化版本"""

    trigger_type = "memory"

    async def should_trigger(self, user: User, policy: PushPolicyProfile) -> bool:
        urgency_threshold = policy.memory_urgency_threshold
        importance_threshold = 5 if policy.pressure_tolerance > 0.6 else 3

        query = (
            select(UserNodeStatus, KnowledgeNode)
            .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(
                UserNodeStatus.user_id == user.id,
                UserNodeStatus.mastery_score > 0.1,
                UserNodeStatus.mastery_score < urgency_threshold,
                KnowledgeNode.importance_level >= importance_threshold,
            )
            .order_by(UserNodeStatus.mastery_score.asc())
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.first() is not None

    async def get_context_data(self, user: User) -> dict[str, Any]:
        query = (
            select(UserNodeStatus, KnowledgeNode)
            .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(
                UserNodeStatus.user_id == user.id,
                UserNodeStatus.mastery_score > 0.1,
                UserNodeStatus.mastery_score < 0.4,
            )
            .order_by(UserNodeStatus.mastery_score.asc())
            .limit(1)
        )

        result = await self.db.execute(query)
        row = result.first()

        if row:
            status, node = row
            return {
                "node_label": node.name,
                "current_mastery": status.mastery_score,
                "importance": node.importance_level,
            }
        return {}


class SprintStrategy(PushStrategy):
    """冲刺提醒策略 - 个性化版本"""

    trigger_type = "sprint"

    async def should_trigger(self, user: User, policy: PushPolicyProfile) -> bool:
        base_hours = 72
        adjusted_hours = base_hours * (1 + policy.pressure_tolerance)

        now = _utcnow()
        deadline_threshold = now + timedelta(hours=adjusted_hours)

        # V3-FIX-221：Task.due_date 是客户端给到的到期日（无时刻成分，墙上
        # 钟日界语义），提醒窗两端须用用户本地日——修前
        # ``deadline_threshold.date()`` / ``now.date()`` 双双 UTC date：上海
        # 凌晨（UTC 尚在前日）下界早开一日把本地昨日到期（已过期）任务拉
        # 回提醒窗，72h 截止端落在 UTC 16:00-24:00 时上界早收一日漏掉最后
        # 一日本地到期任务。tz 通道沿 policy.timezone（engine.py 由
        # push_preference 装配，缺省 Asia/Shanghai），valid_timezone_name
        # 兜底。
        tz_name = valid_timezone_name(policy.timezone)
        query = select(Task).where(
            Task.user_id == user.id,
            Task.status == TaskStatus.PENDING,
            Task.due_date.isnot(None),
            Task.due_date <= local_date(deadline_threshold, tz_name),
            Task.due_date >= local_date(now, tz_name),
        )

        result = await self.db.execute(query)
        return result.first() is not None

    async def get_context_data(self, user: User) -> dict[str, Any]:
        now = _utcnow()
        # 本方法无 policy 通道（签名只收 user）：tz 沿 207/211 先例——
        # PushPreference.timezone 标量直查（规避 ORM 关系 async lazy-load），
        # 缺省 Asia/Shanghai。
        tz_name = valid_timezone_name(
            await self.db.scalar(select(PushPreference.timezone).where(PushPreference.user_id == user.id))
        )
        query = (
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.status == TaskStatus.PENDING,
                Task.due_date.isnot(None),
                Task.due_date >= local_date(now, tz_name),
            )
            .order_by(Task.due_date.asc())
            .limit(1)
        )

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if task and task.due_date:
            # hours_left 同钟修：墙上 due_date 23:59:59 直减 UTC now 会把
            # 剩余时间多算一个时区偏移；改用同一墙钟的本地 now。
            deadline_dt = datetime.combine(task.due_date, time(23, 59, 59))
            hours_left = int(max(0, (deadline_dt - _local_wall_now(now, tz_name)).total_seconds() / 3600))
            return {
                "task_title": task.title,
                "hours_left": hours_left,
                "deadline": deadline_dt.isoformat(),
            }
        return {}


class InactivityStrategy(PushStrategy):
    """唤醒策略 - 个性化版本"""

    trigger_type = "inactivity"

    async def should_trigger(self, user: User, policy: PushPolicyProfile) -> bool:
        if not user.last_login_at:
            return True

        hours_inactive = (_utcnow() - user.last_login_at).total_seconds() / 3600
        return hours_inactive >= 24

    async def get_context_data(self, user: User) -> dict[str, Any]:
        return {"reason": "长时间未学习"}
