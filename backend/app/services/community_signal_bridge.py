"""
CommunitySignalBridge - bridge high-value community signals back into personal systems.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.models.community import Group, GroupTask, GroupTaskClaim, GroupType
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task
from app.orchestration.dual_core_router import AdaptationRecord
from app.services.community_service import GroupTaskService
from app.services.galaxy_service import GalaxyService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CommunitySignalBridge:
    """Bridge selected group signals into personal growth systems."""

    GROUP_WEIGHT_FACTOR = 0.7
    KNOWLEDGE_SHARE_BONUS = 5.0  # user_node_status.mastery_score uses 0-100 scale

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def handle_group_task_completed(self, event: dict) -> None:
        if str(event.get("source") or "") != "group":
            return

        task_id = event.get("task_id")
        user_id = event.get("user_id")
        if not task_id or not user_id:
            return

        claim_result = await self.db.execute(
            select(GroupTaskClaim).where(GroupTaskClaim.personal_task_id == UUID(str(task_id)))
        )
        claim = claim_result.scalar_one_or_none()
        if not claim:
            return

        if not claim.is_completed:
            await GroupTaskService.complete_task(self.db, claim.id)
            await self.db.commit()

        await event_bus.publish(
            "community.group_task_completed",
            {
                "event_type": "community.group_task_completed",
                "user_id": str(user_id),
                "task_id": str(task_id),
                "claim_id": str(claim.id),
                "group_task_id": str(claim.group_task_id),
                "group_weight_factor": self.GROUP_WEIGHT_FACTOR,
                "timestamp": _utcnow().isoformat(),
            },
        )

        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="community_group_contribution_counted",
                category="evolution",
                title="群组贡献已同步",
                description="你在群组中的贡献已计入个人成就进度。",
                priority="low",
                metadata={
                    "evolution_kind": "highlight",
                    "highlight": "你在群组中的贡献已计入个人成就。",
                    "group_weight_factor": self.GROUP_WEIGHT_FACTOR,
                    "source": "community_signal_bridge",
                },
            ),
        )

        await self._sync_sprint_progress_hint(claim=claim)

    async def handle_resource_shared(
        self,
        *,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        target_group_id: UUID | None,
        share_id: UUID,
    ) -> None:
        if resource_type != "knowledge_node" or target_group_id is None:
            return

        node = await self.db.get(KnowledgeNode, resource_id)
        if not node:
            return

        status_result = await self.db.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == resource_id,
            )
        )
        status = status_result.scalar_one_or_none()
        old_mastery = float(status.mastery_score or 0.0) if status else 0.0
        new_mastery = min(100.0, old_mastery + self.KNOWLEDGE_SHARE_BONUS)

        galaxy_service = GalaxyService(self.db)
        await galaxy_service.update_node_mastery(
            user_id=user_id,
            node_id=resource_id,
            new_mastery=int(round(new_mastery)),
            reason="community_knowledge_share_bonus",
        )
        await self.db.commit()

        await event_bus.publish(
            "galaxy.node.updated",
            {
                "event_type": "galaxy.node.updated",
                "user_id": str(user_id),
                "node_id": str(resource_id),
                "old_mastery": old_mastery,
                "new_mastery": new_mastery,
                "delta": new_mastery - old_mastery,
                "reason": "community_knowledge_share_bonus",
                "share_id": str(share_id),
                "group_id": str(target_group_id),
                "timestamp": _utcnow().isoformat(),
            },
        )

        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="knowledge_share_bonus_applied",
                category="evolution",
                title="知识分享已回流",
                description=f"你分享了「{node.name}」，这个知识点的掌握度已获得小幅提升。",
                priority="low",
                metadata={
                    "evolution_kind": "highlight",
                    "highlight": f"你分享了「{node.name}」，这个知识点的掌握度提升了一些。",
                    "source": "community_signal_bridge",
                    "node_id": str(resource_id),
                    "old_mastery": old_mastery,
                    "new_mastery": new_mastery,
                },
            ),
        )

    async def _sync_sprint_progress_hint(self, *, claim: GroupTaskClaim) -> None:
        task = await self.db.get(Task, claim.personal_task_id) if claim.personal_task_id else None
        if not task or not task.plan_id:
            return

        group_task = await self.db.get(GroupTask, claim.group_task_id)
        if not group_task:
            return
        group = await self.db.get(Group, group_task.group_id)
        if not group or group.type != GroupType.SPRINT:
            return

        record = AdaptationRecord(
            what_changed="同步了冲刺群完成进度到个人计划",
            why=f"你在冲刺群「{group.name}」中完成了群任务「{group_task.title}」。",
            expected_effect="你的个人计划进度会保持和群组冲刺节奏一致。",
            user_facing_message=f"你在冲刺群「{group.name}」中完成了目标，个人计划进度已同步更新。",
            source="community_signal_bridge",
        )
        await SystemUpdateService(self.redis).enqueue(
            claim.user_id,
            build_system_update(
                update_type="community_sprint_progress_synced",
                category="evolution",
                title="冲刺进度已同步",
                description=record.user_facing_message,
                priority="low",
                metadata={
                    "evolution_kind": "adaptation_record",
                    "adaptation_record": record.to_dict(),
                },
            ),
        )

    async def broadcast_achievement_unlock(
        self,
        *,
        user_id: UUID,
        achievement_id: str,
        achievement_title: str,
        rarity: str = "common",
    ) -> None:
        """
        Broadcast an achievement unlock to community feeds.
        Publishes to Redis channel for real-time notification and stores in user's activity feed.
        """
        payload = {
            "event_type": "community.achievement_unlocked",
            "user_id": str(user_id),
            "achievement_id": achievement_id,
            "achievement_title": achievement_title,
            "rarity": rarity,
            "timestamp": _utcnow().isoformat(),
        }

        await event_bus.publish(
            "community.achievement_unlocked",
            payload,
            stream="community_events",
        )

        if self.redis:
            try:
                await self.redis.publish(
                    "community:achievements",
                    __import__("json").dumps(payload, ensure_ascii=False),
                )
            except Exception as e:
                logger.warning(f"Failed to publish achievement to Redis channel: {e}")

        logger.info(f"Broadcast achievement unlock: user={user_id} achievement={achievement_id} rarity={rarity}")
