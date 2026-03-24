"""
任务推荐服务 - 基于用户偏好和知识图谱
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import timezone, datetime
from uuid import UUID

from sqlalchemy import nullsfirst, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.personalization import PersonalizationEngine, TaskPlanProfile


@dataclass
class TaskRecommendation:
    knowledge_node_id: UUID
    title: str
    estimated_minutes: int
    task_type: str  # "review" | "micro_review" | "exploration"
    difficulty: int
    priority: float
    reason: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TaskRecommendationService:
    """任务推荐服务"""

    def __init__(self, db: AsyncSession, engine: PersonalizationEngine):
        self.db = db
        self.engine = engine

    async def get_recommendations(
        self,
        user_id: UUID,
        limit: int = 5,
        context: str | None = None,
    ) -> list[TaskRecommendation]:
        """获取个性化任务推荐"""
        profile = await self.engine.get_task_plan_profile(user_id)
        review_nodes = await self._get_review_candidates(user_id, profile)

        review_count = int(limit * (1 - profile.exploration_ratio))
        recommendations: list[TaskRecommendation] = []

        for row in review_nodes[:review_count]:
            status, node = row
            task = self._create_review_task(status, node, profile, context)
            recommendations.append(task)

        return recommendations

    async def _get_review_candidates(
        self,
        user_id: UUID,
        profile: TaskPlanProfile
    ):
        """获取待复习知识点"""
        priority_threshold = {
            "high": 40.0,
            "medium": 30.0,
            "low": 20.0,
        }.get(profile.review_priority, 30.0)

        query = (
            select(UserNodeStatus, KnowledgeNode)
            .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.mastery_score < priority_threshold,
                UserNodeStatus.mastery_score > 5,
            )
            .order_by(nullsfirst(UserNodeStatus.next_review_at.asc()))
            .limit(10)
        )

        result = await self.db.execute(query)
        return result.all()

    def _create_review_task(
        self,
        status: UserNodeStatus,
        node: KnowledgeNode,
        profile: TaskPlanProfile,
        context: str | None,
    ) -> TaskRecommendation:
        """创建复习任务"""
        if context in ("commute", "lunch") and profile.micro_task_friendly:
            duration = min(15, profile.preferred_task_duration)
            task_type = "micro_review"
        else:
            duration = profile.preferred_task_duration
            task_type = "review"

        mastery_ratio = (status.mastery_score or 0) / 100.0
        priority = (1 - mastery_ratio) * (node.importance_level or 1) / 10

        days_since = 0
        if status.last_study_at:
            days_since = (_utcnow() - status.last_study_at).days

        difficulty = max(1, min(5, node.importance_level or 1))

        return TaskRecommendation(
            knowledge_node_id=node.id,
            title=f"复习: {node.name}",
            estimated_minutes=duration,
            task_type=task_type,
            difficulty=difficulty,
            priority=priority,
            reason=f"掌握度 {mastery_ratio:.0%}，距上次学习 {days_since} 天",
        )
