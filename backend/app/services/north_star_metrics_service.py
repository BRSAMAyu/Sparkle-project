"""North Star product metrics for exam pass and 7-day goal completion."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.north_star_metrics import NorthStarMetricEvent
from app.schemas.north_star_metrics import (
    NorthStarMetricDefinition,
    NorthStarTrendPoint,
    NorthStarTrendResponse,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp_ratio(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


class NorthStarMetricType:
    EXAM_PASS_PROBABILITY_ESTIMATED = "exam_pass_probability_estimated"
    EXAM_OUTCOME_RECORDED = "exam_outcome_recorded"
    SEVEN_DAY_GOAL_STARTED = "seven_day_goal_started"
    SEVEN_DAY_GOAL_COMPLETED = "seven_day_goal_completed"
    FIRST_GOAL_PROFILE_CREATED = "first_goal_profile_created"
    FIRST_AURORA_BASELINE_FORMED = "first_aurora_baseline_formed"
    FIRST_PLAN_REQUESTED = "first_plan_requested"
    FIRST_TASK_COMPLETED = "first_task_completed"


NORTH_STAR_DEFINITIONS = [
    NorthStarMetricDefinition(
        key="exam_pass_probability",
        label="Exam pass probability",
        description="Average predicted probability that a learner can pass the target exam from sprint intake.",
        unit="ratio",
    ),
    NorthStarMetricDefinition(
        key="exam_pass_outcome_rate",
        label="Exam pass outcome rate",
        description="Share of post-exam reviews where the learner reports passing, or result rating implies pass.",
        unit="ratio",
    ),
    NorthStarMetricDefinition(
        key="seven_day_goal_completion_rate",
        label="7-day goal completion",
        description="Completed 7-day survival sprint goals divided by 7-day survival sprint goals started.",
        unit="ratio",
    ),
    NorthStarMetricDefinition(
        key="cold_start_first_value",
        label="Cold-start first value",
        description="Counts the first goal profile, Aurora baseline, first plan request, and first task completion milestones.",
        unit="count",
    ),
]


class NorthStarMetricsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_exam_pass_probability(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        pass_probability: float,
        source: str,
        occurred_at: datetime | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NorthStarMetricEvent:
        probability = _clamp_ratio(pass_probability) or 0.0
        return await self._upsert_event(
            user_id=user_id,
            plan_id=plan_id,
            event_type=NorthStarMetricType.EXAM_PASS_PROBABILITY_ESTIMATED,
            event_key=f"north_star:exam_pass_probability:{plan_id}",
            source=source,
            occurred_at=occurred_at,
            value_float=probability,
            numerator=round(probability * 100),
            denominator=100,
            payload=payload or {},
        )

    async def record_exam_outcome(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        passed: bool,
        source: str,
        occurred_at: datetime | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NorthStarMetricEvent:
        return await self._upsert_event(
            user_id=user_id,
            plan_id=plan_id,
            event_type=NorthStarMetricType.EXAM_OUTCOME_RECORDED,
            event_key=f"north_star:exam_outcome:{plan_id}",
            source=source,
            occurred_at=occurred_at,
            value_float=1.0 if passed else 0.0,
            numerator=1 if passed else 0,
            denominator=1,
            passed=passed,
            payload=payload or {},
        )

    async def record_seven_day_goal_started(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        source: str,
        occurred_at: datetime | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NorthStarMetricEvent:
        return await self._upsert_event(
            user_id=user_id,
            plan_id=plan_id,
            event_type=NorthStarMetricType.SEVEN_DAY_GOAL_STARTED,
            event_key=f"north_star:seven_day_goal_started:{plan_id}",
            source=source,
            occurred_at=occurred_at,
            value_float=0.0,
            numerator=0,
            denominator=1,
            payload=payload or {},
        )

    async def record_seven_day_goal_completed(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        source: str,
        occurred_at: datetime | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NorthStarMetricEvent:
        return await self._upsert_event(
            user_id=user_id,
            plan_id=plan_id,
            event_type=NorthStarMetricType.SEVEN_DAY_GOAL_COMPLETED,
            event_key=f"north_star:seven_day_goal_completed:{plan_id}",
            source=source,
            occurred_at=occurred_at,
            value_float=1.0,
            numerator=1,
            denominator=1,
            passed=True,
            payload=payload or {},
        )

    async def record_cold_start_milestone(
        self,
        *,
        user_id: UUID,
        milestone: str,
        source: str,
        occurred_at: datetime | None = None,
        plan_id: UUID | None = None,
        task_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NorthStarMetricEvent:
        allowed = {
            NorthStarMetricType.FIRST_GOAL_PROFILE_CREATED,
            NorthStarMetricType.FIRST_AURORA_BASELINE_FORMED,
            NorthStarMetricType.FIRST_PLAN_REQUESTED,
            NorthStarMetricType.FIRST_TASK_COMPLETED,
        }
        if milestone not in allowed:
            raise ValueError(f"Unsupported cold-start North Star milestone: {milestone}")

        event_key = f"north_star:cold_start:{milestone}:{user_id}"
        existing_result = await self.db.execute(
            select(NorthStarMetricEvent).where(NorthStarMetricEvent.event_key == event_key)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            return existing

        return await self._upsert_event(
            user_id=user_id,
            plan_id=plan_id,
            task_id=task_id,
            event_type=milestone,
            event_key=event_key,
            source=source,
            occurred_at=occurred_at,
            value_float=1.0,
            numerator=1,
            denominator=1,
            payload=payload or {},
        )

    async def get_trends(
        self,
        *,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 30,
    ) -> NorthStarTrendResponse:
        safe_days = max(1, min(days, 365))
        resolved_end = end_date or _utcnow().date()
        resolved_start = start_date or (resolved_end - timedelta(days=safe_days - 1))
        if resolved_start > resolved_end:
            resolved_start, resolved_end = resolved_end, resolved_start

        result = await self.db.execute(
            select(NorthStarMetricEvent)
            .where(
                and_(
                    NorthStarMetricEvent.user_id == user_id,
                    NorthStarMetricEvent.metric_date >= resolved_start,
                    NorthStarMetricEvent.metric_date <= resolved_end,
                    NorthStarMetricEvent.deleted_at.is_(None),
                )
            )
            .order_by(NorthStarMetricEvent.metric_date.asc(), NorthStarMetricEvent.occurred_at.asc())
        )
        events = list(result.scalars().all())

        buckets: dict[date, dict[str, list[NorthStarMetricEvent]]] = defaultdict(lambda: defaultdict(list))
        for event in events:
            buckets[event.metric_date][event.event_type].append(event)

        series: list[NorthStarTrendPoint] = []
        cursor = resolved_start
        while cursor <= resolved_end:
            daily = buckets.get(cursor, {})
            started = len(daily.get(NorthStarMetricType.SEVEN_DAY_GOAL_STARTED, []))
            completed = len(daily.get(NorthStarMetricType.SEVEN_DAY_GOAL_COMPLETED, []))
            series.append(
                NorthStarTrendPoint(
                    date=cursor,
                    exam_pass_probability=self._avg_value(
                        daily.get(NorthStarMetricType.EXAM_PASS_PROBABILITY_ESTIMATED, [])
                    ),
                    exam_pass_outcome_rate=self._ratio(daily.get(NorthStarMetricType.EXAM_OUTCOME_RECORDED, [])),
                    seven_day_goal_completion_rate=(round(completed / started, 4) if started else None),
                    seven_day_goals_started=started,
                    seven_day_goals_completed=completed,
                    first_goal_profiles_created=len(
                        daily.get(NorthStarMetricType.FIRST_GOAL_PROFILE_CREATED, [])
                    ),
                    aurora_baselines_formed=len(
                        daily.get(NorthStarMetricType.FIRST_AURORA_BASELINE_FORMED, [])
                    ),
                    first_plan_requests=len(daily.get(NorthStarMetricType.FIRST_PLAN_REQUESTED, [])),
                    first_tasks_completed=len(daily.get(NorthStarMetricType.FIRST_TASK_COMPLETED, [])),
                )
            )
            cursor += timedelta(days=1)

        summary = self._summary(events)
        summary["start_date"] = resolved_start.isoformat()
        summary["end_date"] = resolved_end.isoformat()
        return NorthStarTrendResponse(
            definitions=NORTH_STAR_DEFINITIONS,
            summary=summary,
            series=series,
        )

    async def _upsert_event(
        self,
        *,
        user_id: UUID,
        event_type: str,
        event_key: str,
        source: str,
        occurred_at: datetime | None = None,
        plan_id: UUID | None = None,
        task_id: UUID | None = None,
        value_float: float | None = None,
        numerator: int | None = None,
        denominator: int | None = None,
        passed: bool | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NorthStarMetricEvent:
        resolved_at = occurred_at or _utcnow()
        result = await self.db.execute(select(NorthStarMetricEvent).where(NorthStarMetricEvent.event_key == event_key))
        event = result.scalar_one_or_none()
        if event is None:
            event = NorthStarMetricEvent(
                user_id=user_id,
                plan_id=plan_id,
                task_id=task_id,
                event_type=event_type,
                event_key=event_key,
                source=source,
                metric_date=resolved_at.date(),
                occurred_at=resolved_at,
            )
            self.db.add(event)

        event.user_id = user_id
        event.plan_id = plan_id
        event.task_id = task_id
        event.event_type = event_type
        event.source = source
        event.metric_date = resolved_at.date()
        event.occurred_at = resolved_at
        event.value_float = _clamp_ratio(value_float)
        event.numerator = numerator
        event.denominator = denominator
        event.passed = passed
        event.payload = payload or {}
        await self.db.commit()
        await self.db.refresh(event)
        return event

    @staticmethod
    def _avg_value(events: list[NorthStarMetricEvent]) -> float | None:
        values = [float(event.value_float) for event in events if event.value_float is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    @staticmethod
    def _ratio(events: list[NorthStarMetricEvent]) -> float | None:
        numerator = sum(int(event.numerator or 0) for event in events)
        denominator = sum(int(event.denominator or 0) for event in events)
        if denominator <= 0:
            return None
        return round(numerator / denominator, 4)

    def _summary(self, events: list[NorthStarMetricEvent]) -> dict[str, Any]:
        latest_probability = None
        probability_events = [
            event for event in events if event.event_type == NorthStarMetricType.EXAM_PASS_PROBABILITY_ESTIMATED
        ]
        if probability_events:
            latest_probability = float(probability_events[-1].value_float or 0.0)

        outcome_rate = self._ratio(
            [event for event in events if event.event_type == NorthStarMetricType.EXAM_OUTCOME_RECORDED]
        )
        starts = sum(1 for event in events if event.event_type == NorthStarMetricType.SEVEN_DAY_GOAL_STARTED)
        completions = sum(1 for event in events if event.event_type == NorthStarMetricType.SEVEN_DAY_GOAL_COMPLETED)
        first_goal_profiles = sum(
            1 for event in events if event.event_type == NorthStarMetricType.FIRST_GOAL_PROFILE_CREATED
        )
        aurora_baselines = sum(
            1 for event in events if event.event_type == NorthStarMetricType.FIRST_AURORA_BASELINE_FORMED
        )
        first_plan_requests = sum(1 for event in events if event.event_type == NorthStarMetricType.FIRST_PLAN_REQUESTED)
        first_tasks_completed = sum(1 for event in events if event.event_type == NorthStarMetricType.FIRST_TASK_COMPLETED)

        return {
            "latest_exam_pass_probability": latest_probability,
            "exam_pass_outcome_rate": outcome_rate,
            "exam_outcomes_recorded": sum(
                1 for event in events if event.event_type == NorthStarMetricType.EXAM_OUTCOME_RECORDED
            ),
            "seven_day_goals_started": starts,
            "seven_day_goals_completed": completions,
            "seven_day_goal_completion_rate": round(completions / starts, 4) if starts else None,
            "first_goal_profiles_created": first_goal_profiles,
            "aurora_baselines_formed": aurora_baselines,
            "first_plan_requests": first_plan_requests,
            "first_tasks_completed": first_tasks_completed,
            "cold_start_first_value_completion_rate": (
                round(first_tasks_completed / first_goal_profiles, 4) if first_goal_profiles else None
            ),
        }
