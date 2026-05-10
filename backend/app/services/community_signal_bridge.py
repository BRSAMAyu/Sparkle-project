"""
CommunitySignalBridge - bridge high-value community signals back into personal systems.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
import uuid

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.datetime_utils import _utcnow
from app.core.event_bus import event_bus
from app.core.metrics import (
    COMMUNITY_PRIVACY_AGGREGATE_TOTAL,
    COMMUNITY_PRIVACY_BUDGET_SPENT,
    COMMUNITY_PRIVACY_COHORT_SIZE,
)
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService
from app.models.community import Group, GroupTask, GroupTaskClaim, GroupType
from app.models.community_privacy import CommunityAggregateSignal, PrivacyBudgetLedger
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task
from app.models.user_settings import UserSettings
from app.orchestration.dual_core_router import AdaptationRecord
from app.services.community_service import GroupTaskService
from app.services.galaxy_service import GalaxyService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.signals.privacy_community_intelligence import PrivacyPreservingCommunityEngine


class CommunitySignalBridge:
    """Bridge selected group signals into personal growth systems."""

    GROUP_WEIGHT_FACTOR = 0.7
    KNOWLEDGE_SHARE_BONUS = 5.0  # user_node_status.mastery_score uses 0-100 scale
    PRIVACY_WINDOW_PREFIX = "community-intelligence"
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
        # NOTE: PrivacyPreservingCommunityEngine is used only for its
        # stateless aggregation math (Laplace noise, cohort binning).
        # Privacy budget enforcement is handled by the DB-backed
        # _check_daily_budget / PrivacyBudgetLedger path — the in-memory
        # budget tracking inside the engine is NOT authoritative.
        self.privacy_engine = PrivacyPreservingCommunityEngine()
        self.kill_switch = AuroraStage33KillSwitchService()

    async def _community_mode(self) -> str:
        return await self.kill_switch.get_feature_mode("community")

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
        mode = await self._community_mode()
        if mode != "live":
            logger.info("community_bridge mode={mode}, skipping handle_group_task_completed", mode=mode)
            return
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
        if await self._community_mode() != "live":
            logger.info("community_bridge mode=shadow_or_off, skipping handle_resource_shared")
            return
        await event_bus.publish(
            "community.resource_shared",
            {
                "event_type": "community.resource_shared",
                "user_id": str(user_id),
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "target_group_id": str(target_group_id) if target_group_id else None,
                "share_id": str(share_id),
                "timestamp": _utcnow().isoformat(),
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

    async def build_privacy_preserving_cohort_signal(
        self,
        *,
        requester_user_id: UUID | str,
        cohort_criteria: dict[str, str],
        stat_name: str,
        contributor_values: list[float | int | dict],
        query_type: str = "pattern_mining",
        signal_type: str = "community_cohort_pattern",
    ) -> dict:
        """Build and persist an anonymized community signal.

        This is the production bridge for cross-user intelligence. It enforces
        opt-out on both sides, spends a persistent privacy budget, persists only
        anonymized aggregates, and emits the result as a candidate soft-bias
        signal rather than writing personal state directly.
        """
        if await self._community_mode() != "live":
            logger.info("community_bridge mode=shadow_or_off, build_privacy_preserving_cohort_signal suppressed")
            return {"allowed": False, "reason": "community_bridge_disabled"}
        requester = str(requester_user_id)
        if not getattr(settings, "COMMUNITY_INTELLIGENCE_ENABLED", True):
            COMMUNITY_PRIVACY_AGGREGATE_TOTAL.labels(result="disabled", query_type=query_type).inc()
            return {"allowed": False, "reason": "community_intelligence_disabled"}
        if not await self._community_intelligence_enabled(requester):
            COMMUNITY_PRIVACY_AGGREGATE_TOTAL.labels(result="requester_opted_out", query_type=query_type).inc()
            return {"allowed": False, "reason": "requester_opted_out"}

        raw_values = await self._filter_opted_in_values(contributor_values)
        min_k = int(getattr(settings, "COMMUNITY_INTELLIGENCE_MIN_COHORT_SIZE", 5))
        if len(raw_values) < min_k:
            await self._write_privacy_budget_ledger(
                subject_id=requester,
                query_type=query_type,
                epsilon_spent=0.0,
                allowed=False,
                denial_reason="below_privacy_floor",
            )
            COMMUNITY_PRIVACY_AGGREGATE_TOTAL.labels(result="below_privacy_floor", query_type=query_type).inc()
            return {
                "allowed": False,
                "reason": "below_privacy_floor",
                "cohort_size": len(raw_values),
                "min_cohort_size": min_k,
            }

        query_cost = float(getattr(settings, "COMMUNITY_INTELLIGENCE_QUERY_EPSILON", 0.5))
        budget_check = await self._check_daily_budget(requester, query_type=query_type, query_cost=query_cost)
        if not budget_check["allowed"]:
            await self._write_privacy_budget_ledger(
                subject_id=requester,
                query_type=query_type,
                epsilon_spent=0.0,
                allowed=False,
                denial_reason=budget_check["reason"],
            )
            COMMUNITY_PRIVACY_AGGREGATE_TOTAL.labels(result="budget_exhausted", query_type=query_type).inc()
            return budget_check

        result = self.privacy_engine.aggregate_cohort_signal(
            requester_id=requester,
            cohort_criteria=cohort_criteria,
            raw_values=raw_values,
            stat_name=stat_name,
            query_type=query_type,
            epsilon=float(getattr(settings, "COMMUNITY_INTELLIGENCE_EPSILON", 1.0)),
            min_cohort_size=min_k,
        )
        await self._write_privacy_budget_ledger(
            subject_id=requester,
            query_type=query_type,
            epsilon_spent=query_cost,
            allowed=True,
            denial_reason="",
            metadata={"cohort_criteria": cohort_criteria, "stat_name": stat_name},
        )
        COMMUNITY_PRIVACY_BUDGET_SPENT.labels(query_type=query_type).inc(query_cost)

        if not result.get("allowed"):
            COMMUNITY_PRIVACY_AGGREGATE_TOTAL.labels(
                result=str(result.get("reason") or "suppressed"),
                query_type=query_type,
            ).inc()
            return result

        record = await self._persist_aggregate_signal(
            result=result,
            cohort_criteria=cohort_criteria,
            stat_name=stat_name,
            signal_type=signal_type,
            query_type=query_type,
        )
        payload = {
            "event_type": "community.aggregate_signal.created",
            "signal_id": record.signal_id,
            "signal_type": signal_type,
            "cohort_key": record.cohort_key,
            "pattern": record.pattern,
            "observation": record.observation,
            "soft_bias_only": True,
            "requires_user_confirmation": True,
            "privacy_boundary": "differential_privacy_k_anonymous",
            "timestamp": _utcnow().isoformat(),
        }
        await event_bus.publish("community.aggregate_signal.created", payload)
        COMMUNITY_PRIVACY_AGGREGATE_TOTAL.labels(result="persisted", query_type=query_type).inc()
        COMMUNITY_PRIVACY_COHORT_SIZE.labels(privacy_tier=record.privacy_tier).observe(record.cohort_size)
        return {**result, "record_id": str(record.id), "signal_id": record.signal_id, "directive_payload": payload}

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

    async def _community_intelligence_enabled(self, user_id: UUID | str | None) -> bool:
        if not user_id:
            return False
        try:
            result = await self.db.execute(select(UserSettings).where(UserSettings.user_id == UUID(str(user_id))))
            settings_row = result.scalar_one_or_none()
            if settings_row is None:
                return True
            return bool(settings_row.community_intelligence_enabled)
        except Exception:
            logger.warning("community_intelligence_enabled check failed for {}", user_id, exc_info=True)
            return False

    async def _filter_opted_in_values(self, contributor_values: list[float | int | dict]) -> list[float]:
        values: list[float] = []
        # Batch query: extract contributor IDs, check all at once
        contributor_ids = [
            item["user_id"] for item in contributor_values
            if isinstance(item, dict) and item.get("user_id")
        ]
        if not contributor_ids:
            # No dict items with user_id - process non-dict values only
            for item in contributor_values:
                if not isinstance(item, dict):
                    try:
                        values.append(float(item))
                    except (TypeError, ValueError):
                        continue
            return values

        # Batch query for community intelligence settings
        settings_result = await self.db.execute(
            select(UserSettings.user_id, UserSettings.community_intelligence_enabled)
            .where(UserSettings.user_id.in_(contributor_ids))
        )
        opted_in = {row[0] for row in settings_result.all() if row[1]}
        opted_out = {row[0] for row in settings_result.all() if not row[1]}
        # Default to opted-in for users without settings row
        all_ids_set = set(contributor_ids)
        unknown_ids = all_ids_set - opted_in - opted_out
        opted_in.update(unknown_ids)

        for item in contributor_values:
            if isinstance(item, dict):
                contributor_id = item.get("user_id")
                if contributor_id and contributor_id not in opted_in:
                    continue
                raw_value = item.get("value")
            else:
                raw_value = item
            try:
                values.append(float(raw_value))
            except (TypeError, ValueError):
                continue
        return values

    @classmethod
    def _cohort_key(cls, criteria: dict[str, str]) -> str:
        canonical = json.dumps(criteria, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]

    @classmethod
    def _window_key(cls) -> str:
        return f"{cls.PRIVACY_WINDOW_PREFIX}:{datetime.now(UTC).date().isoformat()}"

    async def _check_daily_budget(self, subject_id: str, *, query_type: str, query_cost: float) -> dict:
        max_epsilon = float(getattr(settings, "COMMUNITY_INTELLIGENCE_DAILY_EPSILON", 3.0))
        window_key = self._window_key()
        result = await self.db.execute(
            select(func.coalesce(func.sum(PrivacyBudgetLedger.epsilon_spent), 0.0)).where(
                PrivacyBudgetLedger.subject_id == subject_id,
                PrivacyBudgetLedger.query_type == query_type,
                PrivacyBudgetLedger.window_key == window_key,
                PrivacyBudgetLedger.allowed.is_(True),
                PrivacyBudgetLedger.deleted_at.is_(None),
            )
        )
        spent = float(result.scalar_one() or 0.0)
        if spent + query_cost > max_epsilon:
            return {
                "allowed": False,
                "reason": "privacy_budget_exhausted",
                "remaining_epsilon": max(0.0, max_epsilon - spent),
                "max_epsilon": max_epsilon,
            }
        return {"allowed": True, "remaining_epsilon": max_epsilon - spent - query_cost, "max_epsilon": max_epsilon}

    async def _write_privacy_budget_ledger(
        self,
        *,
        subject_id: str,
        query_type: str,
        epsilon_spent: float,
        allowed: bool,
        denial_reason: str,
        metadata: dict | None = None,
    ) -> PrivacyBudgetLedger:
        max_epsilon = float(getattr(settings, "COMMUNITY_INTELLIGENCE_DAILY_EPSILON", 3.0))
        check = await self._check_daily_budget(subject_id, query_type=query_type, query_cost=0.0)
        # With query_cost=0, check.remaining_epsilon = max - already_spent (not yet
        # reduced by this query's cost). Subtract here to get the true post-spend remainder.
        pre_spend_remaining = float(check.get("remaining_epsilon", max_epsilon))
        record = PrivacyBudgetLedger(
            subject_id=subject_id,
            subject_type="user",
            query_type=query_type,
            epsilon_spent=epsilon_spent,
            max_epsilon=max_epsilon,
            remaining_epsilon=max(0.0, pre_spend_remaining - epsilon_spent),
            window_key=self._window_key(),
            allowed=allowed,
            denial_reason=denial_reason,
            spent_at=_utcnow(),
            runtime_metadata=metadata or {},
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def _persist_aggregate_signal(
        self,
        *,
        result: dict,
        cohort_criteria: dict[str, str],
        stat_name: str,
        signal_type: str,
        query_type: str,
    ) -> CommunityAggregateSignal:
        cohort = result.get("cohort") or {}
        stat = result.get("stat") or {}
        record = CommunityAggregateSignal(
            signal_id=str(result.get("observation", {}).get("observation_id") or f"cas_{datetime.now(UTC).timestamp()}"),
            cohort_id=str(cohort.get("cohort_id") or ""),
            cohort_key=self._cohort_key(cohort_criteria),
            cohort_criteria=cohort_criteria,
            signal_type=signal_type,
            stat_name=stat_name,
            cohort_size=int(stat.get("cohort_size") or 0),
            min_cohort_size=int(stat.get("min_cohort_size") or 5),
            privacy_tier=str(cohort.get("privacy_tier") or "suppressed"),
            value=float(stat.get("value")) if stat.get("value") is not None else None,
            noise_std=float(stat.get("noise_std") or 0.0),
            confidence_interval=stat.get("confidence_interval") or [],
            pattern=result.get("pattern") or {},
            observation=result.get("observation") or {},
            privacy_cost=float(result.get("privacy_cost") or 0.0),
            status="candidate",
            generated_at=_utcnow(),
            runtime_metadata={
                "query_type": query_type,
                "soft_bias_only": True,
                "requires_user_confirmation": True,
            },
        )
        self.db.add(record)
        await self.db.flush()
        return record

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
        if await self._community_mode() != "live":
            logger.info("community_bridge mode=shadow_or_off, skipping broadcast_achievement_unlock")
            return
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
                    json.dumps(payload, ensure_ascii=False),
                )
            except Exception as e:
                logger.warning(f"Failed to publish achievement to Redis channel: {e}")

        # Send push notification for achievement unlock
        try:
            from app.schemas.notification import NotificationCreate
            from app.services.notification_service import NotificationService

            await NotificationService.create(
                self.db if hasattr(self, "db") and self.db else None,
                user_id,
                NotificationCreate(
                    title=f"🏆 {achievement_title}",
                    content=f"Congratulations! You unlocked: {achievement_title}",
                    type="achievement_unlock",
                    data={"achievement_id": achievement_id, "rarity": rarity},
                ),
                push_via_websocket=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send achievement push notification: {e}")

        logger.info(f"Broadcast achievement unlock: user={user_id} achievement={achievement_id} rarity={rarity}")
