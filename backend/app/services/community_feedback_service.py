"""SharedResourceFeedbackService — S-04 · Community Artifact Feedback → Outcome/Evidence.

产品目标（v3/07_tasks/cards/S-04.md）：把同伴反馈变成可选择的 Goal evidence，
而不是社交孤岛。

三条铁律（与卡面 Forbidden / COMMUNITY.md Privacy 对齐）：
1. **feedback/ack 永不自动成为 mastery**：给出反馈只落本表 + 事件；
   GALAXY mastery、Goal.mastery/progress 一概不动。唯一的成长系统入口是
   资源主人**显式采纳**（adopt）。
2. **不重建证据权威真源**：采纳走 ``app.services.evidence`` 既有链
   （``build_peer_feedback_evidence`` → ``FusionEngine.update_user_state``，
   Redis 信念面）+ ``Goal.metadata_payload["community_evidence"]`` 轨迹回执
   （既有 Goal 字段，不建新真源表；本表只是社群表面记录）。
3. **撤回传播到 read model**（COMMUNITY.md Privacy）：共享撤回 →
   活跃反馈行打 ``retracted_at`` + 已采纳的 Goal 轨迹回执标 ``retracted``
   （派生引用更新，不静默消失，保留审计）。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import _utcnow
from app.core.event_bus import event_bus
from app.models.community import GroupMember, SharedResource, SharedResourceFeedback
from app.models.goal import Goal
from app.models.plan import Plan
from app.models.task import Task
from app.models.user import User
from app.schemas.community import FeedbackVerdict
from app.services.community_service import UserBlockService


class SharedResourceFeedbackService:
    """同伴反馈 → 可选采纳为 outcome evidence 的服务层（handler 只走本服务）。"""

    COMMUNITY_EVIDENCE_KEY = "community_evidence"

    # ---------- 可见性（与 adopt_shared_resource 同口径） ----------

    @staticmethod
    async def get_visible_resource(
        db: AsyncSession, *, resource_id: UUID, user: User
    ) -> SharedResource:
        """按社群可见性取共享资源：群成员 / 直接目标人 / 主人；拉黑关系拒绝。"""
        result = await db.execute(
            select(SharedResource).where(
                SharedResource.id == resource_id,
                SharedResource.not_deleted_filter(),
            )
        )
        shared = result.scalar_one_or_none()
        if not shared:
            raise ValueError("共享资源不存在")

        if shared.target_user_id is not None and str(shared.target_user_id) != str(user.id):
            raise PermissionError("无权访问该共享资源")

        if shared.group_id is not None:
            membership_result = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == shared.group_id,
                    GroupMember.user_id == user.id,
                    GroupMember.not_deleted_filter(),
                )
            )
            if not membership_result.scalar_one_or_none():
                raise PermissionError("无权访问该共享资源")

        if shared.target_user_id is None and shared.group_id is None and str(shared.shared_by) != str(user.id):
            raise PermissionError("无权访问该共享资源")

        if str(shared.shared_by) != str(user.id):
            if await UserBlockService.has_block_relationship(db, user.id, shared.shared_by):
                raise PermissionError("无权访问该共享资源")
        return shared

    # ---------- 反馈（不自动成为 mastery） ----------

    @staticmethod
    async def give_feedback(
        db: AsyncSession,
        *,
        resource_id: UUID,
        user: User,
        verdict: FeedbackVerdict,
        comment: str | None,
    ) -> SharedResourceFeedback:
        """给出/更新反馈（一人一资源一条 upsert）。绝不触碰任何 mastery/证据面。"""
        shared = await SharedResourceFeedbackService.get_visible_resource(
            db, resource_id=resource_id, user=user
        )
        if str(shared.shared_by) == str(user.id):
            # 主人给自己反馈无社群语义，且会成为自我证据通道——直接拒绝。
            raise ValueError("不能给自己的共享成果反馈")

        existing_result = await db.execute(
            select(SharedResourceFeedback).where(
                SharedResourceFeedback.shared_resource_id == resource_id,
                SharedResourceFeedback.feedback_by == user.id,
                SharedResourceFeedback.not_deleted_filter(),
            )
        )
        feedback = existing_result.scalar_one_or_none()
        if feedback is not None:
            if feedback.retracted_at is not None:
                raise ValueError("该共享已撤回，反馈不可更新")
            feedback.verdict = verdict.value
            feedback.comment = comment
            feedback.updated_at = _utcnow()
            db.add(feedback)
            await db.flush()
            await event_bus.publish(
                "community.feedback_updated",
                SharedResourceFeedbackService._event(
                    "community.feedback_updated",
                    user_id=str(user.id),
                    shared_resource_id=str(resource_id),
                    feedback_id=str(feedback.id),
                    verdict=verdict.value,
                ),
            )
            return feedback

        feedback = SharedResourceFeedback(
            shared_resource_id=resource_id,
            feedback_by=user.id,
            verdict=verdict.value,
            comment=comment,
        )
        db.add(feedback)
        await db.flush()
        await event_bus.publish(
            "community.feedback_given",
            SharedResourceFeedbackService._event(
                "community.feedback_given",
                user_id=str(user.id),
                shared_resource_id=str(resource_id),
                feedback_id=str(feedback.id),
                verdict=verdict.value,
                target_group_id=str(shared.group_id) if shared.group_id else None,
            ),
        )
        return feedback

    @staticmethod
    async def list_feedback(
        db: AsyncSession, *, resource_id: UUID, user: User
    ) -> list[SharedResourceFeedback]:
        shared = await SharedResourceFeedbackService.get_visible_resource(
            db, resource_id=resource_id, user=user
        )
        result = await db.execute(
            select(SharedResourceFeedback)
            .where(
                SharedResourceFeedback.shared_resource_id == shared.id,
                SharedResourceFeedback.not_deleted_filter(),
            )
            .order_by(SharedResourceFeedback.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def feedback_count_map(db: AsyncSession, resource_ids: list[UUID]) -> dict[UUID, dict[str, int]]:
        """批量活跃反馈计数：total / unadopted（供列表端点注入卡片，单查询）。"""
        if not resource_ids:
            return {}
        result = await db.execute(
            select(
                SharedResourceFeedback.shared_resource_id,
                func.count(SharedResourceFeedback.id),
                func.count(SharedResourceFeedback.adopted_at),
            )
            .where(
                SharedResourceFeedback.shared_resource_id.in_(resource_ids),
                SharedResourceFeedback.not_deleted_filter(),
                SharedResourceFeedback.retracted_at.is_(None),
            )
            .group_by(SharedResourceFeedback.shared_resource_id)
        )
        counts: dict[UUID, dict[str, int]] = {}
        for resource_id, total, adopted in result.all():
            counts[resource_id] = {"total": int(total), "unadopted": int(total) - int(adopted)}
        return counts

    # ---------- 采纳为 outcome evidence（唯一成长系统入口） ----------

    @staticmethod
    async def adopt_feedback(
        db: AsyncSession,
        *,
        resource_id: UUID,
        feedback_id: UUID,
        owner: User,
        explicit_goal_id: UUID | None = None,
    ) -> dict:
        """资源主人把一条活跃反馈采纳为 Goal 的 outcome evidence。

        - 只改：反馈行 adopted_at/adopted_into_goal_id + Goal.metadata 回执
          + services/evidence 信念面（best-effort）。
        - 永不改：GALAXY mastery / Goal.mastery / Goal.progress。
        """
        shared_result = await db.execute(
            select(SharedResource).where(
                SharedResource.id == resource_id,
                SharedResource.not_deleted_filter(),
            )
        )
        shared = shared_result.scalar_one_or_none()
        if not shared:
            raise ValueError("共享资源不存在")
        if str(shared.shared_by) != str(owner.id):
            raise PermissionError("只有共享主人可采纳反馈为成果证据")

        feedback_result = await db.execute(
            select(SharedResourceFeedback).where(
                SharedResourceFeedback.id == feedback_id,
                SharedResourceFeedback.shared_resource_id == resource_id,
                SharedResourceFeedback.not_deleted_filter(),
            )
        )
        feedback = feedback_result.scalar_one_or_none()
        if not feedback:
            raise ValueError("反馈不存在")
        if feedback.retracted_at is not None:
            raise ValueError("该反馈已随共享撤回，不可采纳")
        if feedback.adopted_at is not None:
            # 幂等：重复采纳返回既有回执，不重复注入证据。
            goal = await db.get(Goal, feedback.adopted_into_goal_id) if feedback.adopted_into_goal_id else None
            return {
                "feedback": feedback,
                "goal": goal,
                "evidence_count": 0,
                "already_adopted": True,
            }

        giver_result = await db.execute(select(User).where(User.id == feedback.feedback_by))
        giver = giver_result.scalar_one_or_none()
        giver_alias = (giver.nickname or giver.username) if giver else ""

        goal = await SharedResourceFeedbackService._resolve_goal(
            db, shared=shared, owner=owner, explicit_goal_id=explicit_goal_id
        )
        if goal is None:
            raise ValueError("未找到可关联的目标：请先在目标下建立计划/任务，或显式指定 goal_id")

        feedback.adopted_at = _utcnow()
        feedback.adopted_into_goal_id = goal.id
        db.add(feedback)

        receipt = SharedResourceFeedbackService._receipt_entry(
            feedback=feedback,
            giver_alias=giver_alias,
            verdict=feedback.verdict,
            resource_id=shared.id,
            status="adopted",
        )
        SharedResourceFeedbackService._append_goal_receipt(goal, receipt)
        db.add(goal)

        evidence_count = await SharedResourceFeedbackService._fuse_belief_evidence(
            owner_id=owner.id,
            feedback_id=feedback.id,
            shared_resource_id=shared.id,
            goal_id=goal.id,
            verdict=feedback.verdict,
            comment=feedback.comment,
            giver_alias=giver_alias,
        )
        await db.flush()

        await event_bus.publish(
            "community.feedback_adopted",
            SharedResourceFeedbackService._event(
                "community.feedback_adopted",
                user_id=str(owner.id),
                shared_resource_id=str(shared.id),
                feedback_id=str(feedback.id),
                goal_id=str(goal.id),
                verdict=feedback.verdict,
                evidence_count=evidence_count,
            ),
        )
        await SharedResourceFeedbackService._enqueue_system_update(
            owner.id,
            title="同伴反馈已采纳",
            description=f"你把同伴对共享成果的反馈采纳为「{goal.title}」的成果证据。",
            metadata={
                "feedback_id": str(feedback.id),
                "goal_id": str(goal.id),
                "shared_resource_id": str(shared.id),
            },
        )
        return {
            "feedback": feedback,
            "goal": goal,
            "evidence_count": evidence_count,
            "already_adopted": False,
        }

    # ---------- 撤回传播（对齐既有 revoke 链语义：主人 + 软删 + 派生引用更新） ----------

    @staticmethod
    async def retract_share(db: AsyncSession, *, resource_id: UUID, owner: User) -> dict:
        """撤回共享资源：软删本体 + 派生引用更新（反馈行 + Goal 轨迹回执）。

        行不物理删除：撤回是传播事件，不是抹除（审计可查，UI 读面过滤）。
        """
        shared_result = await db.execute(
            select(SharedResource).where(
                SharedResource.id == resource_id,
                SharedResource.not_deleted_filter(),
            )
        )
        shared = shared_result.scalar_one_or_none()
        if not shared:
            raise ValueError("共享资源不存在")
        if str(shared.shared_by) != str(owner.id):
            raise PermissionError("只有共享主人可撤回")

        now = _utcnow()
        shared.deleted_at = now
        db.add(shared)

        active_feedback_result = await db.execute(
            select(SharedResourceFeedback).where(
                SharedResourceFeedback.shared_resource_id == resource_id,
                SharedResourceFeedback.not_deleted_filter(),
                SharedResourceFeedback.retracted_at.is_(None),
            )
        )
        feedbacks = list(active_feedback_result.scalars().all())
        for feedback in feedbacks:
            feedback.retracted_at = now
            db.add(feedback)

        goal_receipt_count = await SharedResourceFeedbackService._retract_goal_receipts(
            db, owner_id=owner.id, resource_id=resource_id, retracted_at=now
        )

        await event_bus.publish(
            "community.resource_retracted",
            SharedResourceFeedbackService._event(
                "community.resource_retracted",
                user_id=str(owner.id),
                shared_resource_id=str(resource_id),
                target_group_id=str(shared.group_id) if shared.group_id else None,
                target_user_id=str(shared.target_user_id) if shared.target_user_id else None,
                retracted_feedback_count=len(feedbacks),
                updated_goal_receipt_count=goal_receipt_count,
            ),
        )
        return {
            "shared": shared,
            "retracted_feedback_count": len(feedbacks),
            "updated_goal_receipt_count": goal_receipt_count,
        }

    # ---------- Goal 轨迹回执（派生引用，撤回时更新） ----------

    @staticmethod
    async def _resolve_goal(
        db: AsyncSession, *, shared: SharedResource, owner: User, explicit_goal_id: UUID | None
    ) -> Goal | None:
        if explicit_goal_id is not None:
            result = await db.execute(
                select(Goal).where(
                    Goal.id == explicit_goal_id,
                    Goal.user_id == owner.id,
                    Goal.not_deleted_filter(),
                )
            )
            goal = result.scalar_one_or_none()
            if goal is None:
                raise ValueError("指定的目标不存在或不属于当前用户")
            return goal

        # 共享资源 → 计划 → 目标（双向既有外链：Goal.plan_id 与 Plan.goal_id）
        if shared.plan_id is not None:
            result = await db.execute(
                select(Goal).where(
                    Goal.plan_id == shared.plan_id,
                    Goal.user_id == owner.id,
                    Goal.not_deleted_filter(),
                )
            )
            goal = result.scalars().first()
            if goal is not None:
                return goal
            plan = await db.get(Plan, shared.plan_id)
            if plan is not None and plan.goal_id is not None:
                result = await db.execute(
                    select(Goal).where(
                        Goal.id == plan.goal_id,
                        Goal.user_id == owner.id,
                        Goal.not_deleted_filter(),
                    )
                )
                goal = result.scalars().first()
                if goal is not None:
                    return goal

        # 共享资源 → 任务 → 计划 → 目标（Plan.goal_id 直链优先，Goal.plan_id 兜底）
        if shared.task_id is not None:
            task = await db.get(Task, shared.task_id)
            if task is not None and task.plan_id is not None:
                plan = await db.get(Plan, task.plan_id)
                if plan is not None and plan.goal_id is not None:
                    result = await db.execute(
                        select(Goal).where(
                            Goal.id == plan.goal_id,
                            Goal.user_id == owner.id,
                            Goal.not_deleted_filter(),
                        )
                    )
                    goal = result.scalars().first()
                    if goal is not None:
                        return goal
                result = await db.execute(
                    select(Goal).where(
                        Goal.plan_id == task.plan_id,
                        Goal.user_id == owner.id,
                        Goal.not_deleted_filter(),
                    )
                )
                goal = result.scalars().first()
                if goal is not None:
                    return goal
        return None

    @classmethod
    def _receipt_entry(
        cls,
        *,
        feedback: SharedResourceFeedback,
        giver_alias: str,
        verdict: str,
        resource_id: UUID,
        status: str,
    ) -> dict:
        return {
            "kind": "peer_feedback",
            "feedback_id": str(feedback.id),
            "shared_resource_id": str(resource_id),
            "verdict": verdict,
            "peer_alias": giver_alias,
            "adopted_at": (feedback.adopted_at or _utcnow()).isoformat(),
            "status": status,
        }

    @classmethod
    def _append_goal_receipt(cls, goal: Goal, entry: dict) -> None:
        metadata = goal.metadata_payload if isinstance(goal.metadata_payload, dict) else {}
        receipts = list(metadata.get(cls.COMMUNITY_EVIDENCE_KEY) or [])
        receipts = [r for r in receipts if isinstance(r, dict) and r.get("feedback_id") != entry["feedback_id"]]
        receipts.append(entry)
        metadata[cls.COMMUNITY_EVIDENCE_KEY] = receipts
        goal.metadata_payload = metadata

    @staticmethod
    async def _retract_goal_receipts(
        db: AsyncSession, *, owner_id: UUID, resource_id: UUID, retracted_at: datetime
    ) -> int:
        """撤回传播的另一半：主人所有 Goal 轨迹里引用该共享的回执标 retracted。"""
        result = await db.execute(
            select(Goal).where(Goal.user_id == owner_id, Goal.not_deleted_filter())
        )
        updated = 0
        for goal in result.scalars().all():
            metadata = goal.metadata_payload if isinstance(goal.metadata_payload, dict) else {}
            receipts = metadata.get(SharedResourceFeedbackService.COMMUNITY_EVIDENCE_KEY)
            if not isinstance(receipts, list):
                continue
            changed = False
            for receipt in receipts:
                if (
                    isinstance(receipt, dict)
                    and receipt.get("shared_resource_id") == str(resource_id)
                    and receipt.get("status") == "adopted"
                ):
                    receipt["status"] = "retracted"
                    receipt["retracted_at"] = retracted_at.isoformat()
                    changed = True
            if changed:
                metadata[SharedResourceFeedbackService.COMMUNITY_EVIDENCE_KEY] = receipts
                goal.metadata_payload = metadata
                db.add(goal)
                updated += 1
        return updated

    # ---------- 信念面（services/evidence 既有链，best-effort） ----------

    @staticmethod
    async def _fuse_belief_evidence(
        *,
        owner_id: UUID,
        feedback_id: UUID,
        shared_resource_id: UUID,
        goal_id: UUID,
        verdict: str,
        comment: str | None,
        giver_alias: str,
    ) -> int:
        """经 services/evidence 既有链注入信念证据；无 Redis 时诚实降级为 0。"""
        try:
            from app.core.cache import cache_service

            # 直接引子模块而非包 re-export（Rule AT：子模块需要真实运行时引用方）。
            from app.services.evidence.fusion_engine import FusionEngine
            from app.services.evidence.outcome_evidence_adapter import (
                build_peer_feedback_evidence,
            )

            if not cache_service.redis:
                return 0
            evidence_items = build_peer_feedback_evidence(
                {
                    "feedback_id": str(feedback_id),
                    "shared_resource_id": str(shared_resource_id),
                    "goal_id": str(goal_id),
                    "verdict": verdict,
                    "comment": comment,
                    "feedback_giver_alias": giver_alias,
                    "timestamp": _utcnow().isoformat(),
                }
            )
            if not evidence_items:
                return 0
            engine = FusionEngine(str(owner_id))
            await engine.update_user_state(cache_service.redis, user_id=str(owner_id), evidence_items=evidence_items)
            return len(evidence_items)
        except Exception as exc:
            # 信念面是副作用通道：失败不阻塞 DB 回执（回执是真源记录），但要留痕。
            logger.warning("peer feedback belief fusion degraded for {}: {}", feedback_id, exc)
            return 0

    @staticmethod
    async def _enqueue_system_update(user_id: UUID, *, title: str, description: str, metadata: dict) -> None:
        try:
            from app.core.cache import cache_service
            from app.services.system_update_service import SystemUpdateService, build_system_update

            await SystemUpdateService(cache_service.redis).enqueue(
                user_id,
                build_system_update(
                    update_type="community_feedback_adopted",
                    category="evolution",
                    title=title,
                    description=description,
                    priority="low",
                    metadata={"source": "community_feedback_service", **metadata},
                ),
            )
        except Exception as exc:
            logger.warning("peer feedback system update degraded for {}: {}", user_id, exc)

    @staticmethod
    def _event(event_type: str, **payload: object) -> dict:
        from app.core.datetime_utils import _utcnow as _now

        return {"event_type": event_type, "timestamp": _now().isoformat(), **payload}
