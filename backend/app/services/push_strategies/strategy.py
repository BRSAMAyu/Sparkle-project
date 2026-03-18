from abc import ABC, abstractmethod
from datetime import timezone, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.personalization import PushPolicyProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

        query = (
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.status == TaskStatus.PENDING,
                Task.due_date.isnot(None),
                Task.due_date <= deadline_threshold.date(),
                Task.due_date >= now.date(),
            )
        )

        result = await self.db.execute(query)
        return result.first() is not None

    async def get_context_data(self, user: User) -> dict[str, Any]:
        now = _utcnow()
        query = (
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.status == TaskStatus.PENDING,
                Task.due_date.isnot(None),
                Task.due_date >= now.date(),
            )
            .order_by(Task.due_date.asc())
            .limit(1)
        )

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()

        if task and task.due_date:
            deadline_dt = datetime.combine(task.due_date, time(23, 59, 59))
            hours_left = int(max(0, (deadline_dt - now).total_seconds() / 3600))
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
