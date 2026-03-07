from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import UserAchievement, UserStreakStats
from app.models.cognitive import BehaviorPattern
from app.models.community import GroupTaskClaim, SharedResource, SharedResourceType
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class ProgressSnapshot:
    period: str
    highlights: list[str]
    comparisons: dict[str, dict[str, float | int]]
    streak_info: dict[str, int]
    growth_areas: list[str]
    attention_areas: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "highlights": self.highlights,
            "comparisons": self.comparisons,
            "streak_info": self.streak_info,
            "growth_areas": self.growth_areas,
            "attention_areas": self.attention_areas,
            "generated_at": self.generated_at,
        }


class ProgressNarrativeService:
    """Build cross-period growth snapshots from existing product signals."""

    LAST_SNAPSHOT_KEY = "progress_snapshot:last_generated:"
    AUTO_INJECT_INTERVAL = timedelta(days=3)

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def build_snapshot(
        self,
        user_id: str,
        *,
        period_label: str = "本周",
        period_days: int = 7,
    ) -> ProgressSnapshot:
        now = _utcnow()
        current_start = now - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)

        task_current = await self._count_completed_tasks(user_id, current_start, now)
        task_previous = await self._count_completed_tasks(user_id, previous_start, current_start)

        mastery_current = await self._study_mastery_delta(user_id, current_start, now)
        mastery_previous = await self._study_mastery_delta(user_id, previous_start, current_start)

        achievements = await self._weekly_achievements(user_id, current_start, now)
        plan_progress = await self._plan_progress(user_id)
        group_stats = await self._group_contribution(user_id, current_start, now)
        streak = await self._streak_info(user_id)
        patterns = await self._pattern_shift(user_id, current_start, now)

        highlights: list[str] = []
        growth_areas: list[str] = []
        attention_areas: list[str] = []

        task_delta = task_current - task_previous
        if task_current > 0:
            if task_previous > 0:
                highlights.append(f"你这周完成了 {task_current} 个任务，比上周多 {task_delta} 个。")
            else:
                highlights.append(f"你这周完成了 {task_current} 个任务，重新把执行节奏拉起来了。")
            growth_areas.append("任务执行")

        mastery_nodes = mastery_current["nodes"]
        mastery_delta = mastery_current["delta"]
        if mastery_nodes > 0 or mastery_delta > 0:
            highlights.append(
                f"最近 7 天你在 {mastery_nodes} 个知识点上有推进，累计掌握度提升约 {mastery_delta:.1f}。"
            )
            growth_areas.append("知识掌握")

        if streak["current_streak"] > 0:
            highlights.append(f"你已经连续学习 {streak['current_streak']} 天，目前最长记录是 {streak['max_streak']} 天。")
            growth_areas.append("连续性")

        if achievements:
            highlights.append(f"你本周新解锁了 {len(achievements)} 个成就：{achievements[0]}。")
            growth_areas.append("成就里程碑")

        if group_stats["completed_claims"] > 0 or group_stats["shared_nodes"] > 0:
            highlights.append(
                f"你在群组里完成了 {group_stats['completed_claims']} 个协作任务，分享了 {group_stats['shared_nodes']} 次知识节点。"
            )
            growth_areas.append("群组贡献")

        if task_current == 0 and plan_progress["active_plan_count"] > 0:
            attention_areas.append("本周活跃计划仍在推进中，但任务完成数偏低。")
        if mastery_previous["delta"] > mastery_delta and mastery_previous["delta"] > 0:
            attention_areas.append("知识掌握推进速度比上一周期慢了一些。")
        if patterns["new_patterns"]:
            attention_areas.append(f"最近出现了新的阻力模式：{patterns['new_patterns'][0]}。")
        if patterns["archived_patterns"]:
            growth_areas.append(f"已弱化的模式：{patterns['archived_patterns'][0]}")

        if not highlights:
            highlights.append("最近几天你的节奏还比较平，先把下一次完成动作稳住最重要。")
        return ProgressSnapshot(
            period=period_label,
            highlights=highlights[:3],
            comparisons={
                "tasks_completed": {"current": task_current, "previous": task_previous},
                "mastery_delta": {"current": round(mastery_delta, 2), "previous": round(mastery_previous["delta"], 2)},
                "group_contributions": {
                    "current": group_stats["completed_claims"] + group_stats["shared_nodes"],
                    "previous": group_stats["previous_contributions"],
                },
                "active_plan_progress": {
                    "current": round(plan_progress["average_progress"], 2),
                    "previous": round(plan_progress["previous_average_progress"], 2),
                },
            },
            streak_info=streak,
            growth_areas=growth_areas[:3],
            attention_areas=attention_areas[:3],
            generated_at=now.isoformat(),
        )

    async def maybe_get_lightweight_snapshot(self, user_id: str) -> dict[str, Any] | None:
        if not await self._should_refresh(user_id):
            return None
        snapshot = await self.build_snapshot(user_id, period_label="最近7天", period_days=7)
        await self._mark_generated(user_id)
        return snapshot.to_dict()

    async def _should_refresh(self, user_id: str) -> bool:
        if not self.redis:
            return True
        key = f"{self.LAST_SNAPSHOT_KEY}{user_id}"
        try:
            raw = await self.redis.get(key)
            if not raw:
                return True
            return (float(raw) + self.AUTO_INJECT_INTERVAL.total_seconds()) <= _utcnow().timestamp()
        except Exception as exc:
            logger.warning(f"Failed to read progress snapshot freshness: {exc}")
            return True

    async def _mark_generated(self, user_id: str) -> None:
        if not self.redis:
            return
        key = f"{self.LAST_SNAPSHOT_KEY}{user_id}"
        try:
            await self.redis.setex(key, int(self.AUTO_INJECT_INTERVAL.total_seconds()), str(_utcnow().timestamp()))
        except Exception as exc:
            logger.warning(f"Failed to persist progress snapshot freshness: {exc}")

    async def _count_completed_tasks(self, user_id: str, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= start,
                Task.completed_at < end,
            )
        )
        return int(result.scalar() or 0)

    async def _study_mastery_delta(self, user_id: str, start: datetime, end: datetime) -> dict[str, float | int]:
        result = await self.db.execute(
            select(
                func.count(func.distinct(StudyRecord.node_id)),
                func.coalesce(func.sum(StudyRecord.mastery_delta), 0.0),
            ).where(
                StudyRecord.user_id == user_id,
                StudyRecord.created_at >= start,
                StudyRecord.created_at < end,
                StudyRecord.mastery_delta > 0,
            )
        )
        nodes, delta = result.one()
        return {"nodes": int(nodes or 0), "delta": float(delta or 0.0)}

    async def _weekly_achievements(self, user_id: str, start: datetime, end: datetime) -> list[str]:
        result = await self.db.execute(
            select(UserAchievement.achievement_id)
            .where(
                UserAchievement.user_id == user_id,
                UserAchievement.unlocked_at.is_not(None),
                UserAchievement.unlocked_at >= start,
                UserAchievement.unlocked_at < end,
            )
            .limit(3)
        )
        return [str(item) for item in result.scalars().all()]

    async def _plan_progress(self, user_id: str) -> dict[str, float | int]:
        current = await self.db.execute(
            select(
                func.count(Plan.id),
                func.coalesce(func.avg(Plan.progress), 0.0),
            ).where(
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
            )
        )
        count, average = current.one()
        previous = await self.db.execute(
            select(func.coalesce(func.avg(Plan.progress), 0.0)).where(
                Plan.user_id == user_id,
                Plan.updated_at < (_utcnow() - timedelta(days=7)),
            )
        )
        return {
            "active_plan_count": int(count or 0),
            "average_progress": float(average or 0.0),
            "previous_average_progress": float(previous.scalar() or 0.0),
        }

    async def _group_contribution(self, user_id: str, start: datetime, end: datetime) -> dict[str, int]:
        current_claims = await self.db.execute(
            select(func.count(GroupTaskClaim.id)).where(
                GroupTaskClaim.user_id == user_id,
                GroupTaskClaim.is_completed.is_(True),
                GroupTaskClaim.completed_at >= start,
                GroupTaskClaim.completed_at < end,
            )
        )
        current_shares = await self.db.execute(
            select(func.count(SharedResource.id)).where(
                SharedResource.shared_by == user_id,
                SharedResource.knowledge_node_id.is_not(None),
                SharedResource.created_at >= start,
                SharedResource.created_at < end,
            )
        )
        previous_start = start - (end - start)
        prev_claims = await self.db.execute(
            select(func.count(GroupTaskClaim.id)).where(
                GroupTaskClaim.user_id == user_id,
                GroupTaskClaim.is_completed.is_(True),
                GroupTaskClaim.completed_at >= previous_start,
                GroupTaskClaim.completed_at < start,
            )
        )
        prev_shares = await self.db.execute(
            select(func.count(SharedResource.id)).where(
                SharedResource.shared_by == user_id,
                SharedResource.knowledge_node_id.is_not(None),
                SharedResource.created_at >= previous_start,
                SharedResource.created_at < start,
            )
        )
        return {
            "completed_claims": int(current_claims.scalar() or 0),
            "shared_nodes": int(current_shares.scalar() or 0),
            "previous_contributions": int(prev_claims.scalar() or 0) + int(prev_shares.scalar() or 0),
        }

    async def _streak_info(self, user_id: str) -> dict[str, int]:
        result = await self.db.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()
        if not stats:
            return {"current_streak": 0, "max_streak": 0, "total_checkin_days": 0}
        return {
            "current_streak": int(stats.current_streak or 0),
            "max_streak": int(stats.max_streak or stats.longest_streak or 0),
            "total_checkin_days": int(stats.total_checkin_days or 0),
        }

    async def _pattern_shift(self, user_id: str, start: datetime, end: datetime) -> dict[str, list[str]]:
        new_patterns_result = await self.db.execute(
            select(BehaviorPattern.pattern_name)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.created_at >= start,
                BehaviorPattern.created_at < end,
                BehaviorPattern.is_archived.is_(False),
                BehaviorPattern.confidence_score >= 0.7,
            )
            .limit(3)
        )
        archived_patterns_result = await self.db.execute(
            select(BehaviorPattern.pattern_name)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.updated_at >= start,
                BehaviorPattern.updated_at < end,
                BehaviorPattern.is_archived.is_(True),
            )
            .limit(3)
        )
        return {
            "new_patterns": [str(item) for item in new_patterns_result.scalars().all()],
            "archived_patterns": [str(item) for item in archived_patterns_result.scalars().all()],
        }
