"""
CommunitySignalBridge - bridge high-value community signals back into personal systems.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID
import uuid

from loguru import logger
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.event_bus import event_bus
from app.core.metrics import (
    COMMUNITY_PRIVACY_AGGREGATES_TOTAL,
    COMMUNITY_PRIVACY_BUDGET_REMAINING,
    COMMUNITY_PRIVACY_BUDGET_SPENT_TOTAL,
    COMMUNITY_PRIVACY_COHORT_SIZE,
)
from app.models.community import Group, GroupTask, GroupTaskClaim, GroupType
from app.models.community_privacy import CommunityAggregateSignal, PrivacyBudgetLedger
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task
from app.models.user_settings import UserSettings
from app.orchestration.dual_core_router import AdaptationRecord
from app.services.community_service import GroupTaskService
from app.services.galaxy_service import GalaxyService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.signals.policy_engine import PolicyEngine
from app.signals.privacy_community_intelligence import PrivacyPreservingCommunityEngine
from app.signals.types import ActionableSignal


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CommunitySignalBridge:
    """Bridge selected group signals into personal growth systems."""

    GROUP_WEIGHT_FACTOR = 0.7
    KNOWLEDGE_SHARE_BONUS = 5.0  # user_node_status.mastery_score uses 0-100 scale
    AURORA_ALLOWED_SOCIAL_EVENT_KINDS = frozenset(
        {
            "partner_checkin",
            "accountability_contract",
            "shared_goal_progress",
            "direct_mention",
        }
    )
    AURORA_FORBIDDEN_SOCIAL_KEYS = frozenset(
        {
            "actor_name",
            "display_name",
            "email",
            "full_name",
            "nickname",
            "phone",
            "raw_content",
            "username",
        }
    )

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.privacy_engine = PrivacyPreservingCommunityEngine()

    async def user_community_intelligence_enabled(self, user_id: UUID | str) -> bool:
        result = await self.db.execute(
            select(UserSettings.community_intelligence_enabled).where(
                UserSettings.user_id == UUID(str(user_id)),
                UserSettings.not_deleted_filter(),
            )
        )
        enabled = result.scalar_one_or_none()
        return True if enabled is None else bool(enabled)

    async def build_group_task_completion_aggregate(
        self,
        *,
        group_id: UUID,
        requester_user_id: UUID,
    ) -> dict[str, Any]:
        """Build and persist a DP aggregate for group task completion.

        Raw per-user completion values are read only inside this method. The
        persisted output is anonymous, noised, and marked as soft-bias-only for
        downstream PolicyEngine consumption.
        """
        if not await self.user_community_intelligence_enabled(requester_user_id):
            return {
                "computed": False,
                "reason": "community_intelligence_disabled",
                "privacy_note": "This user opted out; no aggregate was consumed.",
            }

        group = await self.db.get(Group, group_id)
        if not group or group.deleted_at is not None:
            return {"computed": False, "reason": "group_not_found"}

        raw_values = await self._load_group_task_completion_values(group_id)
        min_cohort_size = max(5, int(getattr(settings, "COMMUNITY_PRIVACY_MIN_COHORT_SIZE", 5)))
        if len(raw_values) < min_cohort_size:
            COMMUNITY_PRIVACY_AGGREGATES_TOTAL.labels(
                "task_completion_rate",
                "suppressed",
                "k_anonymity_rejected",
            ).inc()
            return {
                "computed": False,
                "reason": "k_anonymity_floor",
                "cohort_size": len(raw_values),
                "min_cohort_size": min_cohort_size,
            }

        budget = await self._spend_persistent_budget(
            requester_user_id=requester_user_id,
            budget_subject=f"group:{group_id}:task_completion_rate",
            query_type="cohort_lookup",
            metadata={"group_id": str(group_id), "stat_name": "task_completion_rate"},
        )
        if not budget["allowed"]:
            return {
                "computed": False,
                "reason": budget["reason"],
                "budget_remaining": budget["epsilon_remaining"],
            }

        cohort = self.privacy_engine.create_cohort(
            {
                "group_id": str(group_id),
                "group_type": getattr(group.type, "value", str(group.type)),
                "goal_type": getattr(group.type, "value", str(group.type)),
            },
            member_count=len(raw_values),
        )
        stat = self.privacy_engine.compute_anonymized_stat(
            "task_completion_rate",
            raw_values,
            epsilon=float(getattr(settings, "COMMUNITY_PRIVACY_DP_EPSILON", 0.5)),
            sensitivity=1.0,
            min_cohort_size=min_cohort_size,
            dp_enabled=bool(getattr(settings, "COMMUNITY_PRIVACY_DP_ENABLED", True)),
        )
        cohort.stats.append(stat)
        pattern = self.privacy_engine.detect_cohort_pattern(cohort, stat)
        signal = self._build_policy_signal(cohort=cohort, stat=stat, pattern=pattern)
        policy_engine = PolicyEngine()
        policy_result = await policy_engine.evaluate(signal)
        policy_decision = policy_result[0] if policy_result else None
        community_directive = (
            policy_engine.build_community_directive(policy_decision, signal)
            if policy_decision is not None
            else None
        )
        directive_payload = {
            "actionable_signal": signal.to_dict(),
            "policy_decision": policy_decision.to_dict() if policy_decision else None,
            "community_directive": community_directive.to_dict() if community_directive else None,
            "policy_path": "aggregate_signal_to_CommunityDirective",
            "allowed_effect": "soft_bias_only",
            "hard_override_allowed": False,
        }

        record = CommunityAggregateSignal(
            cohort_key=f"group:{group_id}",
            cohort_type="group_task_completion",
            cohort_criteria=cohort.cohort_criteria,
            stat_name=stat.stat_name,
            privacy_tier=cohort.privacy_tier,
            cohort_size=stat.cohort_size,
            min_cohort_size=stat.min_cohort_size,
            noised_value=stat.value if stat.is_reliable else None,
            noise_std=stat.noise_std,
            confidence_interval=list(stat.confidence_interval),
            pattern=pattern,
            directive_payload=directive_payload,
            epsilon_spent=budget["epsilon_spent"],
            generated_by="community_signal_bridge",
            policy_bias_only=True,
            generated_at=_utcnow(),
        )
        self.db.add(record)
        await self.db.flush()

        COMMUNITY_PRIVACY_AGGREGATES_TOTAL.labels(stat.stat_name, cohort.privacy_tier, "generated").inc()
        COMMUNITY_PRIVACY_COHORT_SIZE.labels(stat.stat_name, cohort.privacy_tier).observe(stat.cohort_size)
        await self._publish_aggregate_signal(record)
        return self._aggregate_to_dict(record, admin=True)

    async def list_aggregate_signals(
        self,
        *,
        viewer_user_id: UUID,
        admin: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not admin and not await self.user_community_intelligence_enabled(viewer_user_id):
            return []
        result = await self.db.execute(
            select(CommunityAggregateSignal)
            .where(CommunityAggregateSignal.not_deleted_filter())
            .order_by(desc(CommunityAggregateSignal.generated_at))
            .limit(max(1, min(limit, 100)))
        )
        return [self._aggregate_to_dict(row, admin=admin) for row in result.scalars().all()]

    async def _load_group_task_completion_values(self, group_id: UUID) -> list[float]:
        result = await self.db.execute(
            select(GroupTaskClaim.user_id, GroupTaskClaim.is_completed)
            .join(GroupTask, GroupTask.id == GroupTaskClaim.group_task_id)
            .outerjoin(UserSettings, UserSettings.user_id == GroupTaskClaim.user_id)
            .where(
                GroupTask.group_id == group_id,
                GroupTask.not_deleted_filter(),
                GroupTaskClaim.not_deleted_filter(),
                or_(
                    UserSettings.id.is_(None),
                    UserSettings.community_intelligence_enabled.is_(True),
                ),
            )
        )
        by_user: dict[str, list[float]] = {}
        for user_id, is_completed in result.all():
            by_user.setdefault(str(user_id), []).append(1.0 if is_completed else 0.0)
        return [sum(values) / len(values) for values in by_user.values() if values]

    async def _spend_persistent_budget(
        self,
        *,
        requester_user_id: UUID,
        budget_subject: str,
        query_type: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        query_cost = float(getattr(settings, "COMMUNITY_PRIVACY_QUERY_COST", 0.1))
        max_epsilon = float(getattr(settings, "COMMUNITY_PRIVACY_MAX_EPSILON", 10.0))
        spent_result = await self.db.execute(
            select(func.coalesce(func.sum(PrivacyBudgetLedger.epsilon_spent), 0.0)).where(
                PrivacyBudgetLedger.budget_subject == budget_subject,
                PrivacyBudgetLedger.status == "accepted",
                PrivacyBudgetLedger.not_deleted_filter(),
            )
        )
        spent = float(spent_result.scalar_one() or 0.0)
        remaining_before = max(0.0, max_epsilon - spent)
        if remaining_before < query_cost:
            ledger = PrivacyBudgetLedger(
                requester_user_id=str(requester_user_id),
                budget_subject=budget_subject,
                query_type=query_type,
                epsilon_spent=0.0,
                epsilon_remaining=remaining_before,
                max_epsilon=max_epsilon,
                status="denied",
                denial_reason="privacy_budget_exhausted",
                metadata_json=metadata,
            )
            self.db.add(ledger)
            await self.db.flush()
            COMMUNITY_PRIVACY_BUDGET_SPENT_TOTAL.labels(query_type, "denied").inc(0)
            COMMUNITY_PRIVACY_BUDGET_REMAINING.labels(budget_subject, query_type).set(remaining_before)
            return {
                "allowed": False,
                "reason": "privacy_budget_exhausted",
                "epsilon_spent": 0.0,
                "epsilon_remaining": remaining_before,
            }

        remaining_after = max(0.0, remaining_before - query_cost)
        ledger = PrivacyBudgetLedger(
            requester_user_id=str(requester_user_id),
            budget_subject=budget_subject,
            query_type=query_type,
            epsilon_spent=query_cost,
            epsilon_remaining=remaining_after,
            max_epsilon=max_epsilon,
            status="accepted",
            metadata_json=metadata,
        )
        self.db.add(ledger)
        await self.db.flush()
        COMMUNITY_PRIVACY_BUDGET_SPENT_TOTAL.labels(query_type, "accepted").inc(query_cost)
        COMMUNITY_PRIVACY_BUDGET_REMAINING.labels(budget_subject, query_type).set(remaining_after)
        return {
            "allowed": True,
            "reason": "ok",
            "epsilon_spent": query_cost,
            "epsilon_remaining": remaining_after,
        }

    @staticmethod
    def _build_policy_signal(
        *,
        cohort,
        stat,
        pattern: dict[str, Any],
    ) -> ActionableSignal:
        return ActionableSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:12]}",
            source_event_ids=[stat.stat_id],
            source_system="privacy_community_intelligence",
            state_key="community_cohort_pattern",
            claim="cohort_mistake_detected",
            confidence=0.75 if stat.is_reliable else 0.0,
            scope="current_sprint",
            ttl_hours=72,
            evidence_summary=f"Differentially private cohort aggregate ({pattern.get('pattern', 'unknown')}); soft-bias-only.",
            possible_effects=["community_directive_soft_bias"],
            priority="low",
        )

    async def _publish_aggregate_signal(self, record: CommunityAggregateSignal) -> None:
        try:
            await event_bus.publish(
                "community.aggregate_signal.generated",
                {
                    "event_type": "community.aggregate_signal.generated",
                    "aggregate_id": str(record.id),
                    "cohort_key": record.cohort_key,
                    "stat_name": record.stat_name,
                    "privacy_tier": record.privacy_tier,
                    "policy_bias_only": True,
                    "directive_payload": record.directive_payload,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        except Exception as exc:
            logger.warning("Failed to publish community aggregate signal: {}", exc)

    @staticmethod
    def _aggregate_to_dict(record: CommunityAggregateSignal, *, admin: bool = False) -> dict[str, Any]:
        base = {
            "id": str(record.id),
            "cohort_type": record.cohort_type,
            "stat_name": record.stat_name,
            "privacy_tier": record.privacy_tier,
            "pattern": record.pattern,
            "value": record.noised_value,
            "confidence_interval": record.confidence_interval,
            "generated_at": record.generated_at.isoformat() if record.generated_at else None,
            "policy_bias_only": record.policy_bias_only,
            "privacy_note": "Anonymous aggregate only; no individual user data is exposed.",
        }
        if admin:
            base.update(
                {
                    "cohort_key": record.cohort_key,
                    "cohort_criteria": record.cohort_criteria,
                    "cohort_size": record.cohort_size,
                    "min_cohort_size": record.min_cohort_size,
                    "noise_std": record.noise_std,
                    "epsilon_spent": record.epsilon_spent,
                    "directive_payload": record.directive_payload,
                }
            )
        return base

    @classmethod
    def sanitize_for_aurora_context(
        cls,
        event: dict,
        *,
        viewer_user_id: UUID | str | None = None,
    ) -> dict | None:
        """Return a privacy-safe social event for Aurora prompt/receipt use.

        The bridge only exposes role-level labels and high-level event kinds.
        It intentionally strips names, raw message bodies, and contact fields so
        Aurora can adjust tone without turning community data into surveillance.
        """
        if not isinstance(event, dict):
            return None

        kind = str(event.get("kind") or event.get("event_type") or "").strip()
        if kind not in cls.AURORA_ALLOWED_SOCIAL_EVENT_KINDS:
            return None

        actor_id = str(event.get("actor_id") or event.get("sender_id") or "").strip()
        viewer = str(viewer_user_id or "").strip()
        if actor_id and viewer and actor_id == viewer:
            return None

        sanitized: dict = {
            "kind": kind,
            "source": str(event.get("source") or "community_signal_bridge"),
            "label": str(event.get("label") or "你的学习伙伴").strip() or "你的学习伙伴",
            "summary_line": str(event.get("summary_line") or "").strip(),
            "relevance": float(event.get("relevance") or 0.0),
            "privacy_boundary": "仅使用匿名角色标签，不暴露伙伴姓名、原文或联系方式。",
        }
        created_at = event.get("created_at") or event.get("timestamp")
        if created_at:
            sanitized["created_at"] = str(created_at)

        for key in cls.AURORA_FORBIDDEN_SOCIAL_KEYS:
            sanitized.pop(key, None)
        if not sanitized["summary_line"]:
            return None
        return sanitized

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
        await event_bus.publish(
            "community.resource_shared",
            {
                "event_type": "community.resource_shared",
                "user_id": str(user_id),
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "target_group_id": str(target_group_id) if target_group_id else None,
                "share_id": str(share_id),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

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
