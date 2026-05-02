from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from app.core.time_utils import utcnow
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.user_insight_state import BigFiveTraits
from app.models.achievement import (
    Achievement,
    AchievementRarity,
    UserAchievement,
    UserStreakStats,
)
from app.models.calendar_event import CalendarEvent
from app.models.chat import ChatSession
from app.models.cognitive import CognitiveFragment
from app.models.focus import FocusSession, FocusStatus
from app.models.memory import EpisodicMemory
from app.models.srl_phase_state import SRLPhaseStateRecord
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService
from app.services.idiographic_association_service import IdiographicAssociationService
from app.services.memory_service import MemoryService
from app.services.metacognition_service import MetacognitionService
from app.services.policy_scheduler_service import PolicySchedulerService
from app.services.predictive_service import PredictiveService
from app.services.scene_consolidation_service import SceneConsolidationService
from app.services.skill_schema import SkillSelectionContext
from app.services.skill_selection_service import SkillSelectionService
from app.services.social_signal_bridge import SocialSignalBridge
from app.services.sufficiency_judge_schema import CurrentTurnParseResult
from app.services.sufficiency_judge_service import SufficiencyJudgeService
from app.state_aggregator.schema import (
    AchievementProgressSummaryItemValue,
    AchievementSummaryValue,
    AchievementUnlockSummaryItemValue,
    ActiveSkillsSummaryValue,
    ActiveSkillSummaryItemValue,
    CalendarContextValue,
    CalendarDeadlineItemValue,
    CalendarTimeBlockItemValue,
    CommitmentSummaryValue,
    EmotionHintValue,
    EngagementStateValue,
    ForesightConfidenceItemValue,
    ForesightHintSummaryValue,
    IdiographicSummaryValue,
    LearningStateValue,
    MetacognitionProfileSummaryValue,
    PendingPoliciesSummaryValue,
    RecentPersonMentionsValue,
    RecentReflectionsSummaryValue,
    RecentSceneItemValue,
    RecentScenesSummaryValue,
    SocialMentionValue,
    SocialSignalsSummaryValue,
    SRLPhaseSummaryValue,
    StateFieldEnvelope,
    SufficiencySummaryValue,
    TraitPriorDimensionValue,
    TraitsPriorSummaryValue,
    UserStateFieldName,
    UserStateV1,
    WorkingMemorySnapshotValue,
    WorkingMemorySnapshotValueItem,
)
from app.working_memory.service import WorkingMemoryService

class StateAggregatorService:
    """Read-only Stage 18 user-state aggregator."""

    FIELD_TTLS_SECONDS: dict[UserStateFieldName, int] = {
        "commitment_summary": 30,
        "pending_policies": 30,
        "recent_reflections": 30,
        "recent_scenes": 30,
        "foresight_hint": 30,
        "engagement_state": 60,
        "recent_person_mentions": 300,
        "social_signals_summary": 300,
        "learning_state": 60 * 60 * 24,
        "working_memory_snapshot": 30,
        "task_sufficiency_summary": 30,
        "context_sufficiency_summary": 30,
        "active_skills_summary": 30,
        "achievement_summary": 300,
        "calendar_context": 300,
        "traits_prior": 30,
        "srl_phase": settings.AURORA_SRL_AGGREGATOR_TTL_SECONDS,
        "metacognition_profile": settings.AURORA_METACOG_CACHE_TTL_SECONDS,
        "idiographic_summary": settings.AURORA_IDIOGRAPHIC_TTL_SECONDS,
        "emotion_hint": 60,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.predictive_service = PredictiveService(db)
        self.working_memory_service = WorkingMemoryService()
        self.sufficiency_judge = SufficiencyJudgeService()
        self.kill_switches = AuroraStage18KillSwitchService()
        self._cache: dict[
            tuple[UUID, UserStateFieldName, str],
            tuple[StateFieldEnvelope[Any] | None, datetime],
        ] = {}

    async def get_user_state(
        self,
        user_id: UUID,
        required_fields: tuple[UserStateFieldName, ...] | list[UserStateFieldName],
        *,
        now: datetime | None = None,
        current_turn_parse: CurrentTurnParseResult | None = None,
        skill_selection_context: SkillSelectionContext | None = None,
        expose_shadow: bool = False,
    ) -> UserStateV1:
        reference_time = now or utcnow()
        state = UserStateV1(user_id=user_id)
        for field_name in tuple(dict.fromkeys(required_fields)):
            envelope = await self._get_field(
                user_id=user_id,
                field_name=field_name,
                now=reference_time,
                current_turn_parse=current_turn_parse,
                skill_selection_context=skill_selection_context,
                expose_shadow=expose_shadow,
            )
            state = replace(state, **{field_name: envelope})
        return state

    async def _get_field(
        self,
        *,
        user_id: UUID,
        field_name: UserStateFieldName,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None,
        skill_selection_context: SkillSelectionContext | None,
        expose_shadow: bool,
    ) -> StateFieldEnvelope[Any] | None:
        cache_key = (
            user_id,
            field_name,
            self._turn_parse_fingerprint(
                field_name, current_turn_parse, skill_selection_context
            ),
        )
        aggregator_mode = await self.kill_switches.get_feature_mode("aggregator_enabled")
        if aggregator_mode == "off":
            return None
        stage33_social_mode: str | None = None
        if field_name in {"recent_person_mentions", "social_signals_summary"}:
            stage33_social_mode = await AuroraStage33KillSwitchService().get_feature_mode("social")
            if stage33_social_mode == "off":
                return None

        cached = self._cache.get(cache_key)
        if aggregator_mode == "live" and stage33_social_mode != "shadow" and cached is not None:
            envelope, expires_at = cached
            if expires_at > now:
                if envelope is None:
                    return None
                return replace(
                    envelope,
                    freshness_seconds=max(
                        0, int((now - envelope.computed_at).total_seconds())
                    ),
                )

        fetcher: dict[
            UserStateFieldName,
            Callable[
                [UUID, datetime, CurrentTurnParseResult | None],
                Awaitable[StateFieldEnvelope[Any] | None],
            ],
        ] = {
            "commitment_summary": self._build_commitment_summary,
            "pending_policies": self._build_pending_policies_summary,
            "recent_reflections": self._build_recent_reflections_summary,
            "recent_scenes": self._build_recent_scenes_summary,
            "foresight_hint": self._build_foresight_hint_summary,
            "recent_person_mentions": self._build_recent_person_mentions,
            "social_signals_summary": self._build_social_signals_summary,
            "engagement_state": self._build_engagement_state,
            "learning_state": self._build_learning_state,
            "working_memory_snapshot": self._build_working_memory_snapshot,
            "task_sufficiency_summary": self._build_task_sufficiency_summary,
            "context_sufficiency_summary": self._build_context_sufficiency_summary,
            "active_skills_summary": self._build_active_skills_summary,
            "achievement_summary": self._build_achievement_summary,
            "calendar_context": self._build_calendar_context,
            "traits_prior": self._build_traits_prior_summary,
            "srl_phase": self._build_srl_phase_summary,
            "metacognition_profile": self._build_metacognition_profile_summary,
            "idiographic_summary": self._build_idiographic_summary,
            "emotion_hint": self._build_emotion_hint_summary,
        }
        envelope = await fetcher[field_name](
            user_id,
            now,
            (
                current_turn_parse
                if field_name != "active_skills_summary"
                else skill_selection_context
            ),
        )
        if aggregator_mode == "shadow":
            return None
        if stage33_social_mode == "shadow" and not expose_shadow:
            return None
        if stage33_social_mode == "shadow":
            return envelope

        ttl_seconds = self.FIELD_TTLS_SECONDS[field_name]
        expires_at = now + timedelta(seconds=ttl_seconds)
        if envelope is not None:
            expires_at = envelope.computed_at + timedelta(seconds=ttl_seconds)
        self._cache[cache_key] = (envelope, expires_at)
        # Evict expired entries periodically to bound memory
        if len(self._cache) > 500:
            expired_keys = [k for k, (_, exp) in self._cache.items() if exp <= now]
            for k in expired_keys:
                del self._cache[k]
        return envelope

    async def _build_commitment_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[CommitmentSummaryValue]:
        rows = await self.memory_service.list_pending_commitments(
            user_id=user_id, now=now
        )
        value = CommitmentSummaryValue(
            overdue_count=len(rows),
            next_due_at=rows[0].due_at if rows else None,
            pending_commitment_ids=tuple(str(row.id) for row in rows[:10]),
        )
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=tuple(f"episodic:{row.id}" for row in rows[:10]),
            freshness_seconds=0,
        )

    async def _build_pending_policies_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[PendingPoliciesSummaryValue]:
        policies = await PolicySchedulerService(self.db).ensure_policies_for_user(
            user_id=user_id, now=now
        )
        active = [row for row in policies if row.is_enabled and row.revoked_at is None]
        value = PendingPoliciesSummaryValue(
            count=len(active),
            next_trigger_at=min(
                (
                    row.next_trigger_at
                    for row in active
                    if row.next_trigger_at is not None
                ),
                default=None,
            ),
            policy_ids=tuple(row.policy_id for row in active[:10]),
        )
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=tuple(f"policy:{row.policy_id}" for row in active[:10]),
            freshness_seconds=0,
        )

    async def _build_recent_person_mentions(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[RecentPersonMentionsValue]:
        rows = await self.memory_service.list_recent_episodic(
            user_id=user_id,
            limit=12,
            start=now - timedelta(days=7),
            subject_types=["person_mention", "relationship"],
        )
        mentions = tuple(
            SocialMentionValue(summary=row.summary, occurred_at=row.occurred_at)
            for row in rows
            if row.subject_type == "person_mention"
        )[:3]
        relationship_count = sum(
            1 for row in rows if row.subject_type == "relationship"
        )
        value = RecentPersonMentionsValue(
            mentions=mentions,
            relationship_count=relationship_count,
        )
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=tuple(f"episodic:{row.id}" for row in rows[:12]),
            freshness_seconds=0,
        )

    async def _build_recent_reflections_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[RecentReflectionsSummaryValue]:
        window_start = now - timedelta(days=7)
        stmt = (
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.deleted_at.is_(None),
                EpisodicMemory.archived_at.is_(None),
                EpisodicMemory.retracted_at.is_(None),
                EpisodicMemory.revoked_at.is_(None),
                EpisodicMemory.source_type == "reflection",
                EpisodicMemory.source_lane == "inferred_extraction",
                EpisodicMemory.occurred_at >= window_start,
            )
            .order_by(EpisodicMemory.occurred_at.desc())
            .limit(20)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        last_category = None
        if rows:
            tags = rows[0].tags or []
            last_category = next(
                (
                    str(tag).split(":", 1)[1]
                    for tag in tags
                    if str(tag).startswith("reflection_category:")
                ),
                None,
            )
        return StateFieldEnvelope(
            value=RecentReflectionsSummaryValue(
                count=len(rows),
                last_category=last_category,
                last_at=rows[0].occurred_at if rows else None,
            ),
            computed_at=now,
            source_snapshot_ids=tuple(f"episodic:{row.id}" for row in rows[:10]),
            freshness_seconds=0,
        )

    async def _build_social_signals_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[SocialSignalsSummaryValue] | None:
        del current_turn_parse
        signals = await SocialSignalBridge(self.db).build_social_signals_v1(user_id)
        if signals is None:
            return None

        source_ids = [f"social_signals:{user_id}"]
        if signals.community_engagement_level is not None:
            source_ids.append(f"user_prefs:{user_id}")
        return StateFieldEnvelope(
            value=SocialSignalsSummaryValue(
                summary_text=signals.to_summary_text(max_chars=400),
                mention_count=signals.mention_count,
                relationship_count=signals.relationship_count,
                pending_commitments_count=signals.pending_commitments_count,
                community_engagement_level=signals.community_engagement_level,
                social_learning_preference=signals.social_learning_preference,
                content_contribution_rate=signals.content_contribution_rate,
            ),
            computed_at=now,
            source_snapshot_ids=tuple(source_ids),
            freshness_seconds=0,
        )

    async def _build_recent_scenes_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[RecentScenesSummaryValue]:
        items = await SceneConsolidationService(
            self.db
        ).list_recent_scenes_for_aggregator(
            user_id=user_id,
            now=now,
        )
        return StateFieldEnvelope(
            value=RecentScenesSummaryValue(
                items=tuple(
                    RecentSceneItemValue(
                        scene_id=item.scene_id,
                        title=item.title,
                        time_start=item.time_start,
                        time_end=item.time_end,
                        member_count=item.member_count,
                        quality_score=item.quality_score,
                    )
                    for item in items
                )
            ),
            computed_at=now,
            source_snapshot_ids=tuple(f"scene:{item.scene_id}" for item in items),
            freshness_seconds=0,
        )

    async def _build_foresight_hint_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[ForesightHintSummaryValue]:
        snapshot = await self.predictive_service.build_foresight_snapshot(user_id)
        latest_hint = snapshot.hints[0] if snapshot.hints else None
        confidence_items = tuple(
            ForesightConfidenceItemValue(dim=dim, confidence=state.confidence)
            for dim, state in sorted(
                snapshot.attractors.items(),
                key=lambda item: (-float(item[1].confidence), item[0]),
            )[:5]
        )
        source_ids = []
        if latest_hint is not None:
            source_ids.append(f"foresight_hint:{latest_hint.hint_id}")
        source_ids.extend(f"persdyn:{item.dim}" for item in confidence_items)
        return StateFieldEnvelope(
            value=ForesightHintSummaryValue(
                hint_text=latest_hint.message if latest_hint is not None else None,
                generated_at=(
                    latest_hint.generated_at if latest_hint is not None else None
                ),
                deviation_count=len(snapshot.deviations),
                attractor_confidences=confidence_items,
            ),
            computed_at=now,
            source_snapshot_ids=tuple(source_ids),
            freshness_seconds=0,
        )

    async def _build_engagement_state(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[EngagementStateValue]:
        last_7d = now - timedelta(days=7)
        focus_count_stmt = select(func.count(FocusSession.id)).where(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.end_time >= last_7d,
        )
        focus_count = int((await self.db.execute(focus_count_stmt)).scalar() or 0)

        latest_focus_stmt = (
            select(FocusSession.end_time)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.status == FocusStatus.COMPLETED,
            )
            .order_by(FocusSession.end_time.desc())
            .limit(1)
        )
        latest_focus_at = (
            await self.db.execute(latest_focus_stmt)
        ).scalar_one_or_none()

        streak_stmt = select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        streak_row = (await self.db.execute(streak_stmt)).scalar_one_or_none()
        streak = int(streak_row.current_streak or 0) if streak_row is not None else 0
        last_active_candidates = [
            value
            for value in [
                latest_focus_at,
                getattr(streak_row, "last_activity_date", None),
            ]
            if value
        ]
        last_active_at = max(last_active_candidates) if last_active_candidates else None
        source_ids = []
        if streak_row is not None:
            source_ids.append(f"streak:{user_id}")
        if latest_focus_at is not None:
            source_ids.append(f"focus:{user_id}")

        return StateFieldEnvelope(
            value=EngagementStateValue(
                last_active_at=last_active_at,
                session_count_7d=focus_count,
                streak=streak,
            ),
            computed_at=now,
            source_snapshot_ids=tuple(source_ids),
            freshness_seconds=0,
        )

    async def _build_emotion_hint_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[EmotionHintValue]:
        last_24h = now - timedelta(days=1)
        stmt = (
            select(CognitiveFragment.sentiment)
            .where(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.sentiment.isnot(None),
                CognitiveFragment.sentiment != "",
                CognitiveFragment.created_at >= last_24h,
            )
            .order_by(CognitiveFragment.created_at.desc())
            .limit(20)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        distribution: dict[str, int] = {}
        for s in rows:
            distribution[s] = distribution.get(s, 0) + 1
        dominant = max(distribution, key=distribution.get) if distribution else None
        emotional_block = dominant in {"anxious", "frustrated", "overwhelmed"} if dominant else False
        return StateFieldEnvelope(
            value=EmotionHintValue(
                dominant_sentiment=dominant,
                sentiment_distribution=distribution,
                emotional_block_detected=emotional_block,
            ),
            computed_at=now,
            source_snapshot_ids=(f"fragments:{user_id}",),
            freshness_seconds=0,
        )

    async def _build_learning_state(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[LearningStateValue]:
        forecast = await self.predictive_service.get_next_intent_forecast(user_id)
        within_category = forecast.get("within_category_preference")
        value = LearningStateValue(
            within_category_preference=(
                within_category if isinstance(within_category, dict) else None
            ),
        )
        source_ids = ["predictive:next_intent"]
        if value.within_category_preference:
            source_ids.append("predictive:within_category_preference")
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=tuple(source_ids),
            freshness_seconds=0,
        )

    async def _build_working_memory_snapshot(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[WorkingMemorySnapshotValue]:
        session_stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.is_active.is_(True))
            .order_by(
                ChatSession.last_message_at.desc().nullslast(),
                ChatSession.created_at.desc(),
            )
            .limit(1)
        )
        session = (await self.db.execute(session_stmt)).scalar_one_or_none()
        if session is None:
            return StateFieldEnvelope(
                value=WorkingMemorySnapshotValue(active_session_id=None, items=()),
                computed_at=now,
                source_snapshot_ids=(),
                freshness_seconds=0,
            )

        snapshot = await self.working_memory_service.build_snapshot(
            user_id=str(user_id),
            session_id=str(session.id),
            limit=5,
        )
        items = tuple(
            WorkingMemorySnapshotValueItem(
                summary=item.summary,
                subject_type=item.subject_type,
                mention_count=item.mention_count,
                consolidated=item.consolidated,
                last_seen_at=item.last_seen_at,
            )
            for item in snapshot
        )
        return StateFieldEnvelope(
            value=WorkingMemorySnapshotValue(
                active_session_id=str(session.id), items=items
            ),
            computed_at=now,
            source_snapshot_ids=tuple(
                f"working_memory:{user_id}:{session.id}:{index}"
                for index, _item in enumerate(items, start=1)
            ),
            freshness_seconds=0,
        )

    async def _build_task_sufficiency_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[SufficiencySummaryValue]:
        judgment = await self._evaluate_sufficiency(
            user_id=user_id, now=now, current_turn_parse=current_turn_parse
        )
        return StateFieldEnvelope(
            value=SufficiencySummaryValue(
                score=judgment.task_sufficiency.score,
                top_missing_dimensions=judgment.task_sufficiency.missing_dimensions[:3],
            ),
            computed_at=now,
            source_snapshot_ids=("sufficiency:task",),
            freshness_seconds=0,
        )

    async def _build_context_sufficiency_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[SufficiencySummaryValue]:
        judgment = await self._evaluate_sufficiency(
            user_id=user_id, now=now, current_turn_parse=current_turn_parse
        )
        return StateFieldEnvelope(
            value=SufficiencySummaryValue(
                score=judgment.context_sufficiency.score,
                top_missing_dimensions=judgment.context_sufficiency.missing_dimensions[
                    :3
                ],
            ),
            computed_at=now,
            source_snapshot_ids=("sufficiency:context",),
            freshness_seconds=0,
        )

    async def _build_active_skills_summary(
        self,
        user_id: UUID,
        now: datetime,
        skill_selection_context: SkillSelectionContext | None = None,
    ) -> StateFieldEnvelope[ActiveSkillsSummaryValue]:
        if skill_selection_context is None:
            return StateFieldEnvelope(
                value=ActiveSkillsSummaryValue(items=()),
                computed_at=now,
                source_snapshot_ids=(),
                freshness_seconds=0,
            )

        matches, _blocked = await SkillSelectionService(self.db).resolve_prompt_payload(
            user_id=user_id,
            selection_context=skill_selection_context,
        )
        items = tuple(
            ActiveSkillSummaryItemValue(
                skill_id=item.skill_id,
                name=item.name,
                activation_match_score=item.activation_match_score,
            )
            for item in matches
        )
        return StateFieldEnvelope(
            value=ActiveSkillsSummaryValue(items=items),
            computed_at=now,
            source_snapshot_ids=tuple(f"user_skill:{item.skill_id}" for item in items),
            freshness_seconds=0,
        )

    async def _build_achievement_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[AchievementSummaryValue]:
        recent_cutoff = now - timedelta(days=14)
        recent_rows = (
            await self.db.execute(
                select(UserAchievement, Achievement)
                .join(Achievement, Achievement.id == UserAchievement.achievement_id)
                .where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.unlocked_at.is_not(None),
                    UserAchievement.unlocked_at >= recent_cutoff,
                )
                .order_by(UserAchievement.unlocked_at.desc())
                .limit(5)
            )
        ).all()
        progress_rows = (
            await self.db.execute(
                select(UserAchievement, Achievement)
                .join(Achievement, Achievement.id == UserAchievement.achievement_id)
                .where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.unlocked_at.is_(None),
                    UserAchievement.progress > 0.5,
                )
                .order_by(
                    UserAchievement.progress.desc(),
                    UserAchievement.last_progress_update.desc().nullslast(),
                )
                .limit(5)
            )
        ).all()
        score_rows = (
            await self.db.execute(
                select(UserAchievement, Achievement)
                .join(Achievement, Achievement.id == UserAchievement.achievement_id)
                .where(UserAchievement.user_id == user_id)
            )
        ).all()

        rarity_weights = {
            AchievementRarity.COMMON.value: 1.0,
            AchievementRarity.RARE.value: 2.0,
            AchievementRarity.EPIC.value: 3.0,
            AchievementRarity.LEGENDARY.value: 4.0,
        }
        total_score = 0.0
        source_ids: list[str] = []
        for user_achievement, achievement in score_rows:
            rarity = (
                achievement.rarity.value
                if hasattr(achievement.rarity, "value")
                else str(achievement.rarity or "common")
            )
            weight = rarity_weights.get(rarity, 1.0)
            progress = float(user_achievement.progress or 0.0)
            total_score += (
                weight if user_achievement.unlocked_at else (progress * weight)
            )
            source_ids.append(f"achievement:{achievement.id}")

        # DF-10: Also read recent events from Redis cache
        recent_events: list[dict] = []
        try:
            import json as _json

            from app.core.cache import cache_service
            events_key = f"spine:achievement_events:{user_id}"
            raw_events = await cache_service.redis.lrange(events_key, 0, 4) if hasattr(cache_service, 'redis') else []
            for raw in raw_events:
                try:
                    recent_events.append(_json.loads(raw))
                except Exception:
                    pass
        except Exception:
            pass

        value = AchievementSummaryValue(
            recent_unlocks=tuple(
                AchievementUnlockSummaryItemValue(
                    achievement_id=achievement.id,
                    name=achievement.name,
                    rarity=(
                        achievement.rarity.value
                        if hasattr(achievement.rarity, "value")
                        else str(achievement.rarity)
                    ),
                    unlocked_at=user_achievement.unlocked_at,
                )
                for user_achievement, achievement in recent_rows
                if user_achievement.unlocked_at is not None
            ),
            in_progress_achievements=tuple(
                AchievementProgressSummaryItemValue(
                    achievement_id=achievement.id,
                    name=achievement.name,
                    progress=round(float(user_achievement.progress or 0.0), 3),
                )
                for user_achievement, achievement in progress_rows
            ),
            total_achievement_score=round(total_score, 2),
        )
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=tuple(dict.fromkeys(source_ids)),
            freshness_seconds=0,
        )

    async def _build_calendar_context(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[CalendarContextValue]:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = now + timedelta(days=7)
        today_events = list(
            (
                await self.db.execute(
                    select(CalendarEvent)
                    .where(
                        CalendarEvent.user_id == user_id,
                        CalendarEvent.deleted_at.is_(None),
                        CalendarEvent.start_time < today_end,
                        CalendarEvent.end_time > today_start,
                    )
                    .order_by(CalendarEvent.start_time)
                )
            )
            .scalars()
            .all()
        )
        week_events = list(
            (
                await self.db.execute(
                    select(CalendarEvent)
                    .where(
                        CalendarEvent.user_id == user_id,
                        CalendarEvent.deleted_at.is_(None),
                        CalendarEvent.start_time >= now,
                        CalendarEvent.start_time <= week_end,
                    )
                    .order_by(CalendarEvent.start_time)
                )
            )
            .scalars()
            .all()
        )
        forecast = await self.predictive_service.get_next_intent_forecast(user_id)
        exam_urgency = (
            forecast.get("exam_urgency")
            if isinstance(forecast, dict)
            and isinstance(forecast.get("exam_urgency"), dict)
            else None
        )

        value = CalendarContextValue(
            upcoming_deadlines=tuple(
                CalendarDeadlineItemValue(
                    title=event.title,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    source=(
                        "task"
                        if event.task_id
                        else ("plan" if event.plan_id else "calendar")
                    ),
                )
                for event in week_events[:6]
                if event.task_id is not None or event.plan_id is not None
            ),
            time_blocks_today=tuple(
                CalendarTimeBlockItemValue(start=item["start"], end=item["end"])
                for item in self._derive_available_time_blocks(
                    today_events, reference_day=today_start.date()
                )
            ),
            workload_density=self._derive_workload_density(week_events),
            exam_urgency=exam_urgency,
        )
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=tuple(
                f"calendar_event:{event.id}" for event in week_events[:10]
            ),
            freshness_seconds=0,
        )

    async def _build_traits_prior_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[TraitsPriorSummaryValue]:
        del current_turn_parse
        row = (
            await self.db.execute(
                select(UserPreferencesCenter).where(
                    UserPreferencesCenter.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        traits = BigFiveTraits.model_validate(
            dict(getattr(row, "traits_prior", {}) or {})
        )
        observation_state = dict(getattr(row, "trait_observation_state", {}) or {})
        latest_evidence_ids = dict(observation_state.get("latest_evidence_ids") or {})
        items = tuple(
            TraitPriorDimensionValue(
                dim=dim,
                value=value.value,
                confidence=value.confidence,
                source=value.source,
            )
            for dim, value in traits.active_dimensions().items()
            if float(value.confidence) >= 0.1
        )
        return StateFieldEnvelope(
            value=TraitsPriorSummaryValue(items=items),
            computed_at=now,
            source_snapshot_ids=tuple(
                str(latest_evidence_ids.get(item.dim) or f"trait:{item.dim}")
                for item in items
            ),
            freshness_seconds=0,
        )

    async def _build_srl_phase_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[SRLPhaseSummaryValue]:
        del current_turn_parse
        row = (
            await self.db.execute(
                select(SRLPhaseStateRecord).where(
                    SRLPhaseStateRecord.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        value = SRLPhaseSummaryValue(
            current_phase=str(getattr(row, "current_phase", "UNKNOWN") or "UNKNOWN"),
            phase_started_at=getattr(row, "phase_started_at", None),
            confidence=float(getattr(row, "confidence", 0.0) or 0.0),
            source=str(getattr(row, "source", "default") or "default"),
        )
        snapshot_ids = ()
        if row is not None:
            snapshot_ids = (f"srl_phase:{row.user_id}",)
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=snapshot_ids,
            freshness_seconds=0,
        )

    async def _build_metacognition_profile_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[MetacognitionProfileSummaryValue]:
        value = await MetacognitionService(self.db).build_aggregator_summary(user_id)
        source_ids = tuple(f"metacognition:{item.dim}" for item in value.items)
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=source_ids,
            freshness_seconds=0,
        )

    async def _build_idiographic_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[IdiographicSummaryValue] | None:
        del current_turn_parse
        value = await IdiographicAssociationService(self.db).build_aggregator_summary(
            user_id,
            now=now,
        )
        if value is None:
            return None
        source_ids = tuple(
            f"idiographic:{item.dim_pair}" for item in value.top_associations
        ) or tuple(
            f"idiographic:changepoint:{item.dim}:{item.change_date.isoformat()}"
            for item in value.change_points_30d
        )
        return StateFieldEnvelope(
            value=value,
            computed_at=now,
            source_snapshot_ids=source_ids,
            freshness_seconds=0,
        )

    async def _evaluate_sufficiency(
        self,
        *,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None,
    ):
        parse_result = current_turn_parse or CurrentTurnParseResult(
            intent="chat",
            intent_confidence=0.0,
            information_sufficient=False,
            target_object_resolved=False,
            constraint_explicit=False,
        )
        base_state = UserStateV1(
            user_id=user_id,
            commitment_summary=await self._build_commitment_summary(user_id, now),
            recent_person_mentions=await self._build_recent_person_mentions(
                user_id, now
            ),
            engagement_state=await self._build_engagement_state(user_id, now),
            working_memory_snapshot=await self._build_working_memory_snapshot(
                user_id, now
            ),
        )
        return self.sufficiency_judge.evaluate(
            user_state=base_state, current_turn=parse_result
        )

    @staticmethod
    def _turn_parse_fingerprint(
        field_name: UserStateFieldName,
        current_turn_parse: CurrentTurnParseResult | None,
        skill_selection_context: SkillSelectionContext | None = None,
    ) -> str:
        if field_name not in {
            "task_sufficiency_summary",
            "context_sufficiency_summary",
        }:
            if field_name != "active_skills_summary":
                return ""
            if skill_selection_context is None:
                return "missing"
            return ":".join(
                [
                    skill_selection_context.intent,
                    skill_selection_context.tool_category,
                    str(skill_selection_context.current_time.hour),
                    str(skill_selection_context.current_time.weekday()),
                ]
            )
        if current_turn_parse is None:
            return "missing"
        return ":".join(
            [
                current_turn_parse.intent,
                f"{current_turn_parse.intent_confidence:.2f}",
                "1" if current_turn_parse.information_sufficient else "0",
                "1" if current_turn_parse.target_object_resolved else "0",
                "1" if current_turn_parse.constraint_explicit else "0",
            ]
        )

    @staticmethod
    def _derive_available_time_blocks(
        events: list[CalendarEvent], *, reference_day: date
    ) -> list[dict[str, str]]:
        day_start = datetime.combine(reference_day, datetime.min.time()).replace(hour=7)
        day_end = datetime.combine(reference_day, datetime.min.time()).replace(hour=22)
        busy: list[tuple[datetime, datetime]] = []
        for event in events:
            start = (
                event.start_time.replace(tzinfo=None)
                if event.start_time.tzinfo
                else event.start_time
            )
            end = (
                event.end_time.replace(tzinfo=None)
                if event.end_time.tzinfo
                else event.end_time
            )
            start = max(start, day_start)
            end = min(end, day_end)
            if start < end:
                busy.append((start, end))

        blocks: list[dict[str, str]] = []
        cursor = day_start
        for start, end in sorted(busy, key=lambda item: item[0]):
            if start > cursor:
                blocks.append(
                    {"start": cursor.strftime("%H:%M"), "end": start.strftime("%H:%M")}
                )
            cursor = max(cursor, end)
        if cursor < day_end:
            blocks.append(
                {"start": cursor.strftime("%H:%M"), "end": day_end.strftime("%H:%M")}
            )
        return blocks[:4]

    @staticmethod
    def _derive_workload_density(events: list[CalendarEvent]) -> str:
        if not events:
            return "low"
        by_day: dict[date, int] = {}
        total_minutes = 0
        for event in events:
            key = event.start_time.date()
            by_day[key] = by_day.get(key, 0) + 1
            total_minutes += max(
                0, int((event.end_time - event.start_time).total_seconds() / 60)
            )
        active_days = max(len(by_day), 1)
        avg_events = sum(by_day.values()) / active_days
        avg_minutes = total_minutes / active_days
        if avg_events >= 4 or avg_minutes >= 240:
            return "high"
        if avg_events >= 2 or avg_minutes >= 120:
            return "medium"
        return "low"
