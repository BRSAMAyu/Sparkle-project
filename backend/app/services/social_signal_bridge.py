from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.event_bus import event_bus
from app.core.event_types import ACCOUNTABILITY_STRUGGLE_DETECTED
from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.community import Group, GroupMember, GroupMessage, GroupType, MessageType
from app.models.notification import Notification
from app.models.user import User
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService
from app.services.community_signal_bridge import CommunitySignalBridge
from app.services.personalization.preference_service import PreferenceService
from app.services.social_signal_types import SocialSignalsV1


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_encouragement_presets(locale: str = "zh") -> tuple[dict[str, str], ...]:
    if locale == "en":
        return (
            {
                "id": "spark_small_step",
                "emoji": "👏",
                "message": "Just finishing one small piece is great. I'm watching you.",
            },
            {
                "id": "spark_restart",
                "emoji": "💪",
                "message": "Starting with 5 minutes today still counts. Go for it.",
            },
            {
                "id": "spark_warm",
                "emoji": "✨",
                "message": "No need to prove anything. Just get your rhythm back.",
            },
        )
    return (
        {
            "id": "spark_small_step",
            "emoji": "👏",
            "message": "先完成一个小块就很好，我在看着你。",
        },
        {
            "id": "spark_restart",
            "emoji": "💪",
            "message": "今天从 5 分钟开始也算数，加油。",
        },
        {
            "id": "spark_warm",
            "emoji": "✨",
            "message": "别急着证明什么，先把节奏接回来。",
        },
    )


def _user_display_name(user: User | None, default: str = "好友") -> str:
    if user is None:
        return default
    return user.nickname or user.full_name or user.username or default


PRESET_ENCOURAGEMENTS: tuple[dict[str, str], ...] = (
    {
        "id": "spark_small_step",
        "emoji": "👏",
        "message": "先完成一个小块就很好，我在看着你。",
    },
    {
        "id": "spark_restart",
        "emoji": "💪",
        "message": "今天从 5 分钟开始也算数，加油。",
    },
    {
        "id": "spark_warm",
        "emoji": "✨",
        "message": "别急着证明什么，先把节奏接回来。",
    },
)


class SocialSignalBridge:
    ACCOUNTABILITY_STRUGGLE_THRESHOLD = 0.6
    ACCOUNTABILITY_STRUGGLE_DEDUP_TTL = 20 * 3600
    HIGH_RELEVANCE_EVENT_LIMIT = 3
    PARTNER_ACTIVITY_LOOKBACK_HOURS = 36
    COMMUNITY_ACTIVITY_LOOKBACK_HOURS = 24

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)
        from app.routing.aggregator_backed_social_context_provider import (
            AggregatorBackedSocialContextProvider,
        )

        self.provider = AggregatorBackedSocialContextProvider(db)
        self.kill_switch = AuroraStage33KillSwitchService()

    async def _social_mode(self) -> str:
        return await self.kill_switch.get_feature_mode("social")

    async def _fetch_for_user(self, user_id: UUID) -> dict[str, Any]:
        snapshot = await self.provider.fetch_social_snapshot(user_id)
        prefs_center = await self.preference_service.get_preferences(user_id)
        inferred = dict(getattr(prefs_center, "inferred", {}) or {})
        explicit = dict(getattr(prefs_center, "explicit", {}) or {})
        return {
            "snapshot": snapshot,
            "inferred": inferred,
            "explicit": explicit,
        }

    async def build_social_signals_v1(self, user_id: UUID) -> SocialSignalsV1 | None:
        mode = await self._social_mode()
        if mode == "off":
            return None

        payload = await self._fetch_for_user(user_id)
        snapshot = payload.get("snapshot")
        if snapshot is None:
            return None

        inferred = payload.get("inferred")
        inferred = inferred if isinstance(inferred, dict) else {}
        explicit = payload.get("explicit")
        explicit = explicit if isinstance(explicit, dict) else {}
        if self._social_signals_disabled(explicit):
            return None

        partnerships = await self._active_partnerships_for_user(user_id)
        high_relevance_events = await self._rank_high_relevance_events(
            user_id=user_id,
            partnerships=partnerships,
        )
        mention_count = len(getattr(snapshot, "recent_person_mentions", []) or [])
        relationship_count = int(getattr(snapshot, "relationship_count", 0) or 0)
        pending_commitments_count = int(getattr(snapshot, "pending_commitments_count", 0) or 0)
        engagement_level = str(inferred.get("community_engagement_level") or "").strip() or None
        social_learning_preference = inferred.get("social_learning_preference")
        if social_learning_preference is not None:
            social_learning_preference = float(social_learning_preference)
        content_contribution_rate = inferred.get("content_contribution_rate")
        if content_contribution_rate is not None:
            content_contribution_rate = float(content_contribution_rate)

        summary_lines: list[str] = []
        if mention_count > 0:
            summary_lines.append(f"最近 7 天提到过 {mention_count} 位学习相关人物。")
        if relationship_count > 0:
            summary_lines.append(f"当前有 {relationship_count} 条关系型背景需要在建议里保持边界感。")
        if pending_commitments_count > 0:
            summary_lines.append(f"目前有 {pending_commitments_count} 条到期承诺待跟进。")
        if partnerships:
            summary_lines.append(f"当前有 {len(partnerships)} 个进行中的责任伙伴约定，卡点时优先用共同推进感而不是比较压力。")
        if engagement_level:
            summary_lines.append(f"社区参与度推断为 {engagement_level}。")
        if social_learning_preference is not None:
            summary_lines.append(f"社交学习倾向约为 {social_learning_preference:.2f}。")
        if content_contribution_rate is not None:
            summary_lines.append(f"内容贡献倾向约为 {content_contribution_rate:.2f}。")
        for event in high_relevance_events:
            summary_line = str(event.get("summary_line") or "").strip()
            if summary_line:
                summary_lines.append(summary_line)

        tone_guidance = self._build_tone_guidance(
            active_contract_count=len(partnerships),
            high_relevance_events=high_relevance_events,
        )
        social_context_receipt = self._build_social_context_receipt(high_relevance_events)

        signals = SocialSignalsV1(
            mention_count=mention_count,
            relationship_count=relationship_count,
            pending_commitments_count=pending_commitments_count,
            active_accountability_contract_count=len(partnerships),
            community_engagement_level=engagement_level,
            social_learning_preference=social_learning_preference,
            content_contribution_rate=content_contribution_rate,
            summary_lines=tuple(summary_lines[:6]),
            high_relevance_events=tuple(high_relevance_events),
            tone_guidance=tuple(tone_guidance),
            social_context_receipt=social_context_receipt,
        )
        if (
            not signals.summary_lines
            and mention_count <= 0
            and relationship_count <= 0
            and pending_commitments_count <= 0
            and not high_relevance_events
            and not partnerships
        ):
            return None
        if mode != "live":
            return None
        return signals

    @staticmethod
    def _social_signals_disabled(explicit: dict[str, Any]) -> bool:
        for key in (
            "use_social_signals",
            "enable_social_signals",
            "allow_social_context_in_aurora",
        ):
            if key in explicit and explicit.get(key) is False:
                return True
        return False

    async def _rank_high_relevance_events(
        self,
        *,
        user_id: UUID,
        partnerships: list[AccountabilityPartnership],
    ) -> list[dict[str, Any]]:
        raw_events: list[dict[str, Any]] = []
        raw_events.extend(await self._partner_activity_events(user_id=user_id, partnerships=partnerships))
        raw_events.extend(await self._community_activity_events(user_id=user_id))

        sanitized_events = [
            event
            for event in (
                CommunitySignalBridge.sanitize_for_aurora_context(event, viewer_user_id=user_id)
                for event in raw_events
            )
            if event is not None
        ]
        sanitized_events.sort(
            key=lambda item: (
                float(item.get("relevance") or 0.0),
                str(item.get("created_at") or ""),
            ),
            reverse=True,
        )

        selected: list[dict[str, Any]] = []
        seen_kinds: set[str] = set()
        for event in sanitized_events:
            kind = str(event.get("kind") or "")
            if kind in seen_kinds and kind != "direct_mention":
                continue
            selected.append(event)
            seen_kinds.add(kind)
            if len(selected) >= self.HIGH_RELEVANCE_EVENT_LIMIT:
                break
        return selected

    async def _partner_activity_events(
        self,
        *,
        user_id: UUID,
        partnerships: list[AccountabilityPartnership],
    ) -> list[dict[str, Any]]:
        if not partnerships:
            return []

        partnership_ids = [partnership.id for partnership in partnerships]
        partner_ids = {
            partnership.partner_id if str(partnership.initiator_id) == str(user_id) else partnership.initiator_id
            for partnership in partnerships
        }
        cutoff = _utcnow() - timedelta(hours=self.PARTNER_ACTIVITY_LOOKBACK_HOURS)
        result = await self.db.execute(
            select(AccountabilityCheckin)
            .where(
                AccountabilityCheckin.partnership_id.in_(partnership_ids),
                AccountabilityCheckin.user_id.in_(partner_ids),
                AccountabilityCheckin.created_at >= cutoff,
                AccountabilityCheckin.deleted_at.is_(None),
            )
            .order_by(desc(AccountabilityCheckin.created_at))
            .limit(5)
        )
        events: list[dict[str, Any]] = []
        for checkin in result.scalars().all():
            events.append(
                {
                    "kind": "partner_checkin",
                    "source": "accountability_checkin",
                    "actor_id": str(checkin.user_id),
                    "label": "你的学习伙伴",
                    "summary_line": "你的学习伙伴刚完成了一次 check-in；如果当前用户卡住，可把它作为温和启动信号，不做进度比较。",
                    "relevance": 0.95,
                    "created_at": checkin.created_at.isoformat() if checkin.created_at else "",
                }
            )
        if not events and partnerships:
            events.append(
                {
                    "kind": "accountability_contract",
                    "source": "accountability_partnership",
                    "label": "你的学习伙伴",
                    "summary_line": "用户有进行中的责任伙伴约定；任务卡点时可提醒“这不是你一个人的目标”，但不要施压。",
                    "relevance": 0.72,
                    "created_at": max(
                        (p.started_at or p.created_at for p in partnerships if p.started_at or p.created_at),
                        default=_utcnow(),
                    ).isoformat(),
                }
            )
        return events

    async def _community_activity_events(self, *, user_id: UUID) -> list[dict[str, Any]]:
        cutoff = _utcnow() - timedelta(hours=self.COMMUNITY_ACTIVITY_LOOKBACK_HOURS)
        membership_result = await self.db.execute(
            select(GroupMember.group_id)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.deleted_at.is_(None),
            )
            .limit(30)
        )
        group_ids = [row[0] for row in membership_result.all()]
        if not group_ids:
            return []

        group_result = await self.db.execute(select(Group).where(Group.id.in_(group_ids)))
        group_by_id = {group.id: group for group in group_result.scalars().all()}
        message_result = await self.db.execute(
            select(GroupMessage)
            .where(
                GroupMessage.group_id.in_(group_ids),
                GroupMessage.created_at >= cutoff,
                GroupMessage.deleted_at.is_(None),
                GroupMessage.is_revoked.is_(False),
                or_(GroupMessage.sender_id.is_(None), GroupMessage.sender_id != user_id),
            )
            .order_by(desc(GroupMessage.created_at))
            .limit(60)
        )

        events: list[dict[str, Any]] = []
        for message in message_result.scalars().all():
            mention_user_ids = [str(item) for item in (message.mention_user_ids or [])]
            if str(user_id) in mention_user_ids:
                events.append(
                    {
                        "kind": "direct_mention",
                        "source": "group_message",
                        "actor_id": str(message.sender_id or ""),
                        "label": "学习群成员",
                        "summary_line": "学习群里有人直接提到了用户；只有当前回复与协作或回看群内进展有关时才轻轻提及。",
                        "relevance": 0.9,
                        "created_at": message.created_at.isoformat() if message.created_at else "",
                    }
                )
                continue

            group = group_by_id.get(message.group_id)
            group_type = getattr(group, "type", None)
            group_type_value = str(getattr(group_type, "value", group_type) or "").lower()
            message_type = getattr(message.message_type, "value", message.message_type)
            if group_type_value == GroupType.SPRINT.value and message_type in {
                MessageType.TASK_SHARE.value,
                MessageType.PLAN_SHARE.value,
                MessageType.PROGRESS.value,
                MessageType.CHECKIN.value,
            }:
                events.append(
                    {
                        "kind": "shared_goal_progress",
                        "source": "group_message",
                        "actor_id": str(message.sender_id or ""),
                        "label": "冲刺群伙伴",
                        "summary_line": "冲刺群里有一条共同目标相关进展；可用作共同体感背景，不要展开具体成员内容。",
                        "relevance": 0.76,
                        "created_at": message.created_at.isoformat() if message.created_at else "",
                    }
                )
        return events

    @staticmethod
    def _build_tone_guidance(
        *,
        active_contract_count: int,
        high_relevance_events: list[dict[str, Any]],
    ) -> list[str]:
        guidance: list[str] = []
        if active_contract_count > 0:
            guidance.append("任务卡点时可以用“这不是你一个人的目标”来降低孤立感，但禁止责备、比较或替伙伴发话。")
        if any(str(event.get("kind")) == "partner_checkin" for event in high_relevance_events):
            guidance.append("伙伴刚活跃时，只把它当成温和启动线索；不要说“别人已经完成了”。")
        if any(str(event.get("kind")) == "direct_mention" for event in high_relevance_events):
            guidance.append("群内 @ 提及时，先确认当前问题确实相关；不相关就不要主动提起。")
        if high_relevance_events:
            guidance.append("提及社群信号时只使用“学习伙伴/责任伙伴/学习群”这类角色标签，除非用户显式允许实名。")
        return guidance

    @staticmethod
    def _build_social_context_receipt(high_relevance_events: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not high_relevance_events:
            return None
        labels = []
        for event in high_relevance_events:
            label = str(event.get("label") or "学习伙伴动态").strip()
            kind = str(event.get("kind") or "").strip()
            labels.append("学习伙伴动态" if kind == "partner_checkin" else label)
        deduped_labels = list(dict.fromkeys(labels))
        return {
            "type": "social_context_receipt",
            "used_count": len(high_relevance_events),
            "used_names": deduped_labels,
            "excluded_count": 0,
            "excluded_names": [],
            "decision_reason": "参考了学习伙伴的动态",
            "privacy_boundary": "只使用匿名角色标签，不展示伙伴姓名、原文或联系方式。",
            "retrieval_mode": "social_context",
            "events": [
                {
                    "kind": str(event.get("kind") or ""),
                    "label": str(event.get("label") or ""),
                    "source": str(event.get("source") or ""),
                    "relevance": round(float(event.get("relevance") or 0.0), 2),
                }
                for event in high_relevance_events
            ],
            "user_actions": ["dismiss", "disable_social_signals"],
        }

    async def maybe_publish_accountability_struggle_signal(
        self,
        *,
        user_id: UUID | str,
        plan_id: UUID | str,
        struggle_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Publish a social accountability event when a plan stall becomes visible."""
        mode = await self._social_mode()
        if mode == "off":
            return {"published": False, "reason": "kill_switch_off"}

        try:
            score = float(struggle_context.get("struggle_score", 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        try:
            no_completion_days = int(struggle_context.get("no_completion_days", 0) or 0)
        except (TypeError, ValueError):
            no_completion_days = 0

        if score < self.ACCOUNTABILITY_STRUGGLE_THRESHOLD:
            return {"published": False, "reason": "below_threshold", "struggle_score": score}
        if no_completion_days < 2:
            return {"published": False, "reason": "completion_gap_too_short", "struggle_score": score}

        user_uuid = UUID(str(user_id))
        plan_uuid = UUID(str(plan_id))
        partnerships = await self._active_partnerships_for_user(user_uuid)
        if not partnerships:
            return {"published": False, "reason": "no_active_accountability_partner", "struggle_score": score}
        if mode != "live":
            return {
                "published": False,
                "reason": "kill_switch_shadow",
                "struggle_score": score,
                "partner_count": len(partnerships),
            }

        dedupe_key = f"accountability:struggle:{user_uuid}:{plan_uuid}:{no_completion_days // 2}"
        if not await self._claim_dedupe_key(dedupe_key):
            return {"published": False, "reason": "deduped", "struggle_score": score}

        target = await self.db.get(User, user_uuid)
        target_name = _user_display_name(target, "你的伙伴")
        partner_payloads = []
        for partnership in partnerships:
            partner_id = (
                partnership.partner_id
                if str(partnership.initiator_id) == str(user_uuid)
                else partnership.initiator_id
            )
            partner_payloads.append(
                {
                    "partnership_id": str(partnership.id),
                    "partner_id": str(partner_id),
                }
            )

        payload = {
            "event_type": ACCOUNTABILITY_STRUGGLE_DETECTED,
            "user_id": str(user_uuid),
            "plan_id": str(plan_uuid),
            "struggle_score": score,
            "primary_signal": struggle_context.get("primary_signal"),
            "no_completion_days": no_completion_days,
            "recent_completion_count": struggle_context.get("recent_completion_count", 0),
            "last_completed_at": struggle_context.get("last_completed_at"),
            "partnerships": partner_payloads,
            "dedupe_key": dedupe_key,
            "timestamp": _utcnow().isoformat(),
        }
        await event_bus.publish(ACCOUNTABILITY_STRUGGLE_DETECTED, payload)
        logger.info(
            "Published accountability struggle signal for user={} plan={} partners={} score={}",
            user_uuid,
            plan_uuid,
            len(partner_payloads),
            score,
        )
        return {
            "published": True,
            "event_type": ACCOUNTABILITY_STRUGGLE_DETECTED,
            "partner_count": len(partner_payloads),
            "struggle_score": score,
        }

    async def handle_accountability_struggle_detected(self, event: dict[str, Any]) -> dict[str, Any]:
        """Consume a struggle event and create actionable partner notifications."""
        if await self._social_mode() != "live":
            return {"handled": False, "reason": "kill_switch_not_live"}

        if event.get("event_type") != ACCOUNTABILITY_STRUGGLE_DETECTED:
            return {"handled": False, "reason": "ignored_event_type"}

        user_id = event.get("user_id")
        plan_id = event.get("plan_id")
        if not user_id or not plan_id:
            return {"handled": False, "reason": "missing_identifiers"}

        target_user_id = UUID(str(user_id))
        partnerships = await self._active_partnerships_for_user(target_user_id)
        if not partnerships:
            return {"handled": False, "reason": "no_active_accountability_partner"}

        sent_count = 0
        from app.services.accountability_notification_service import accountability_notification_service

        for partnership in partnerships:
            partner_id = (
                partnership.partner_id
                if str(partnership.initiator_id) == str(target_user_id)
                else partnership.initiator_id
            )
            if await self._has_recent_partner_alert(
                partner_id=partner_id,
                target_user_id=target_user_id,
                plan_id=UUID(str(plan_id)),
                dedupe_key=str(event.get("dedupe_key") or ""),
            ):
                continue

            # Resolve target_name from DB instead of event payload (PII hygiene)
            target_user = await self.db.get(User, target_user_id)
            resolved_name = _user_display_name(target_user, "你的伙伴")

            await accountability_notification_service.send_struggle_alert(
                self.db,
                partner_id=partner_id,
                target_user_id=target_user_id,
                partnership_id=partnership.id,
                plan_id=UUID(str(plan_id)),
                target_name=resolved_name,
                no_completion_days=int(event.get("no_completion_days") or 2),
                struggle_score=float(event.get("struggle_score") or 0.0),
                dedupe_key=str(event.get("dedupe_key") or ""),
                preset_encouragements=list(get_encouragement_presets()),
            )
            sent_count += 1

        return {"handled": True, "sent_count": sent_count}

    async def _active_partnerships_for_user(self, user_id: UUID) -> list[AccountabilityPartnership]:
        result = await self.db.execute(
            select(AccountabilityPartnership)
            .options(
                selectinload(AccountabilityPartnership.initiator),
                selectinload(AccountabilityPartnership.partner),
            )
            .where(
                AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
                AccountabilityPartnership.deleted_at.is_(None),
                or_(
                    AccountabilityPartnership.initiator_id == user_id,
                    AccountabilityPartnership.partner_id == user_id,
                ),
            )
            .limit(50)
        )
        return list(result.scalars().all())

    async def _has_recent_partner_alert(
        self,
        *,
        partner_id: UUID,
        target_user_id: UUID,
        plan_id: UUID,
        dedupe_key: str,
    ) -> bool:
        from app.services.accountability_notification_service import AccountabilityNotificationType

        cutoff = _utcnow() - timedelta(hours=20)
        result = await self.db.execute(
            select(Notification)
            .where(
                and_(
                    Notification.user_id == partner_id,
                    Notification.type == AccountabilityNotificationType.STRUGGLE_ALERT.value,
                    Notification.created_at >= cutoff,
                    Notification.deleted_at.is_(None),
                )
            )
            .order_by(Notification.created_at.desc())
        )
        for notification in result.scalars().all():
            data = notification.data or {}
            if dedupe_key and data.get("dedupe_key") == dedupe_key:
                return True
            if data.get("target_user_id") == str(target_user_id) and data.get("plan_id") == str(plan_id):
                return True
        return False

    async def _claim_dedupe_key(self, key: str) -> bool:
        if self.redis is None:
            return True
        try:
            result = await self._redis_call(
                self.redis,
                "set",
                key,
                "1",
                ex=self.ACCOUNTABILITY_STRUGGLE_DEDUP_TTL,
                nx=True,
            )
            return bool(result)
        except Exception as exc:
            logger.debug("Accountability struggle dedupe unavailable: {}", exc)
            return True

    @staticmethod
    async def _redis_call(redis, method_name: str, *args, **kwargs):
        method = getattr(redis, method_name, None)
        if method is None:
            return None
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result
