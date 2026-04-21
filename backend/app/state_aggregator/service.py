from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import UserStreakStats
from app.models.chat import ChatSession
from app.models.focus import FocusSession, FocusStatus
from app.services.memory_service import MemoryService
from app.services.predictive_service import PredictiveService
from app.services.sufficiency_judge_schema import CurrentTurnParseResult
from app.services.sufficiency_judge_service import SufficiencyJudgeService
from app.state_aggregator.schema import (
    CommitmentSummaryValue,
    EngagementStateValue,
    LearningStateValue,
    RecentPersonMentionsValue,
    SocialMentionValue,
    SufficiencySummaryValue,
    StateFieldEnvelope,
    UserStateFieldName,
    UserStateV1,
    WorkingMemorySnapshotValue,
    WorkingMemorySnapshotValueItem,
)
from app.working_memory.service import WorkingMemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class StateAggregatorService:
    """Read-only Stage 18 user-state aggregator."""

    FIELD_TTLS_SECONDS: dict[UserStateFieldName, int] = {
        "commitment_summary": 30,
        "engagement_state": 60,
        "recent_person_mentions": 300,
        "learning_state": 60 * 60 * 24,
        "working_memory_snapshot": 30,
        "task_sufficiency_summary": 30,
        "context_sufficiency_summary": 30,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.predictive_service = PredictiveService(db)
        self.working_memory_service = WorkingMemoryService()
        self.sufficiency_judge = SufficiencyJudgeService()
        self._cache: dict[tuple[UUID, UserStateFieldName, str], tuple[StateFieldEnvelope[Any], datetime]] = {}

    async def get_user_state(
        self,
        user_id: UUID,
        required_fields: tuple[UserStateFieldName, ...] | list[UserStateFieldName],
        *,
        now: datetime | None = None,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> UserStateV1:
        reference_time = now or _utcnow()
        state = UserStateV1(user_id=user_id)
        for field_name in tuple(dict.fromkeys(required_fields)):
            envelope = await self._get_field(
                user_id=user_id,
                field_name=field_name,
                now=reference_time,
                current_turn_parse=current_turn_parse,
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
    ) -> StateFieldEnvelope[Any]:
        cache_key = (user_id, field_name, self._turn_parse_fingerprint(field_name, current_turn_parse))
        cached = self._cache.get(cache_key)
        if cached is not None:
            envelope, expires_at = cached
            if expires_at > now:
                return replace(
                    envelope,
                    freshness_seconds=max(0, int((now - envelope.computed_at).total_seconds())),
                )

        fetcher: dict[
            UserStateFieldName,
            Callable[[UUID, datetime, CurrentTurnParseResult | None], Awaitable[StateFieldEnvelope[Any]]],
        ] = {
            "commitment_summary": self._build_commitment_summary,
            "recent_person_mentions": self._build_recent_person_mentions,
            "engagement_state": self._build_engagement_state,
            "learning_state": self._build_learning_state,
            "working_memory_snapshot": self._build_working_memory_snapshot,
            "task_sufficiency_summary": self._build_task_sufficiency_summary,
            "context_sufficiency_summary": self._build_context_sufficiency_summary,
        }
        envelope = await fetcher[field_name](user_id, now, current_turn_parse)
        ttl_seconds = self.FIELD_TTLS_SECONDS[field_name]
        self._cache[cache_key] = (envelope, envelope.computed_at + timedelta(seconds=ttl_seconds))
        return envelope

    async def _build_commitment_summary(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[CommitmentSummaryValue]:
        rows = await self.memory_service.list_pending_commitments(user_id=user_id, now=now)
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
        relationship_count = sum(1 for row in rows if row.subject_type == "relationship")
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
            .where(FocusSession.user_id == user_id, FocusSession.status == FocusStatus.COMPLETED)
            .order_by(FocusSession.end_time.desc())
            .limit(1)
        )
        latest_focus_at = (await self.db.execute(latest_focus_stmt)).scalar_one_or_none()

        streak_stmt = select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        streak_row = (await self.db.execute(streak_stmt)).scalar_one_or_none()
        streak = int(streak_row.current_streak or 0) if streak_row is not None else 0
        last_active_candidates = [value for value in [latest_focus_at, getattr(streak_row, "last_activity_date", None)] if value]
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

    async def _build_learning_state(
        self,
        user_id: UUID,
        now: datetime,
        current_turn_parse: CurrentTurnParseResult | None = None,
    ) -> StateFieldEnvelope[LearningStateValue]:
        forecast = await self.predictive_service.get_next_intent_forecast(user_id)
        within_category = forecast.get("within_category_preference")
        value = LearningStateValue(
            within_category_preference=within_category if isinstance(within_category, dict) else None,
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
            .order_by(ChatSession.last_message_at.desc().nullslast(), ChatSession.created_at.desc())
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
            value=WorkingMemorySnapshotValue(active_session_id=str(session.id), items=items),
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
        judgment = await self._evaluate_sufficiency(user_id=user_id, now=now, current_turn_parse=current_turn_parse)
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
        judgment = await self._evaluate_sufficiency(user_id=user_id, now=now, current_turn_parse=current_turn_parse)
        return StateFieldEnvelope(
            value=SufficiencySummaryValue(
                score=judgment.context_sufficiency.score,
                top_missing_dimensions=judgment.context_sufficiency.missing_dimensions[:3],
            ),
            computed_at=now,
            source_snapshot_ids=("sufficiency:context",),
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
            recent_person_mentions=await self._build_recent_person_mentions(user_id, now),
            engagement_state=await self._build_engagement_state(user_id, now),
            working_memory_snapshot=await self._build_working_memory_snapshot(user_id, now),
        )
        return self.sufficiency_judge.evaluate(user_state=base_state, current_turn=parse_result)

    @staticmethod
    def _turn_parse_fingerprint(
        field_name: UserStateFieldName,
        current_turn_parse: CurrentTurnParseResult | None,
    ) -> str:
        if field_name not in {"task_sufficiency_summary", "context_sufficiency_summary"}:
            return ""
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
