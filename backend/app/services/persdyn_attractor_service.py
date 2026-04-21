from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import fmean, pstdev
from typing import Iterable
from uuid import UUID

from loguru import logger
from prometheus_client import Counter as PrometheusCounter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.event_bus import event_bus
from app.core.event_types import ATTRACTOR_UPDATED
from app.core.metrics import get_or_create_metric
from app.models.aurora_stage27 import PersDynAttractor
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import StudyRecord
from app.models.memory import EpisodicMemory, Scene
from app.models.task import Task, TaskStatus
from app.schemas.foresight import AttractorState


PERSDYN_ATTRACTOR_UPDATED_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_persdyn_attractor_updated_total",
    "Total PersDyn attractor updates",
    ["dim"],
)


@dataclass(frozen=True)
class _SignalRows:
    study_records: tuple[StudyRecord, ...]
    tasks: tuple[Task, ...]
    focus_sessions: tuple[FocusSession, ...]
    scenes: tuple[Scene, ...]
    reflections: tuple[EpisodicMemory, ...]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time())


def _end_exclusive(day: date) -> datetime:
    return _start_of_day(day) + timedelta(days=1)


def _linear_regression_slope(values: Iterable[float]) -> float:
    materialized = [float(item) for item in values]
    count = len(materialized)
    if count < 2:
        return 0.0
    xs = list(range(count))
    mean_x = fmean(xs)
    mean_y = fmean(materialized)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, materialized, strict=False))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


class PersDynAttractorService:
    DIMENSIONS = (
        "study_pace",
        "completion_rate",
        "engagement_level",
        "mood_valence",
        "plan_adherence",
    )
    HISTORY_DAYS = 14
    CONFIDENCE_LOOKBACK_DAYS = 28
    REFLECTION_VALENCE_MAP = {
        "too_difficult": 0.25,
        "unclear": 0.35,
        "abandoned": 0.2,
        "intervention_ineffective": 0.3,
        "plan_stall": 0.4,
        "overload": 0.1,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.alpha = float(settings.AURORA_FORESIGHT_ATTRACTOR_ALPHA)

    async def get_snapshot_attractors(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
        include_low_confidence: bool = False,
    ) -> dict[str, AttractorState]:
        normalized_user_id = self._require_user_id(user_id)
        reference_time = now or _utcnow()
        rows = await self._load_rows(normalized_user_id)
        if len(rows) < len(self.DIMENSIONS) or any(self._is_stale(row, reference_time) for row in rows):
            states = await self.recompute_user_attractors(user_id=normalized_user_id, now=reference_time)
        else:
            states = {row.dim: self._to_state(row) for row in rows if row.dim in self.DIMENSIONS}

        if include_low_confidence:
            return states
        threshold = float(settings.AURORA_FORESIGHT_ATTRACTOR_MIN_CONFIDENCE)
        return {
            dim: state
            for dim, state in states.items()
            if state.confidence >= threshold
        }

    async def build_current_observation(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> dict[str, float]:
        normalized_user_id = self._require_user_id(user_id)
        reference_time = now or _utcnow()
        rows = await self._load_signal_rows(normalized_user_id, reference_time)
        return self._build_observation_for_day(rows=rows, reference_day=reference_time.date())

    async def recompute_user_attractors(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> dict[str, AttractorState]:
        normalized_user_id = self._require_user_id(user_id)
        reference_time = now or _utcnow()
        rows = await self._load_signal_rows(normalized_user_id, reference_time)
        active_days = self._count_active_days(rows=rows, reference_time=reference_time)
        series = self._build_series(rows=rows, reference_time=reference_time)
        states = {
            dim: self._estimate_state(
                dim=dim,
                values=series[dim],
                active_days=active_days,
                reference_time=reference_time,
            )
            for dim in self.DIMENSIONS
        }
        await self._upsert_rows(user_id=normalized_user_id, states=states, now=reference_time)
        return states

    async def recompute_all_users(self, *, now: datetime | None = None) -> int:
        reference_time = now or _utcnow()
        user_ids = {
            item[0]
            for item in (await self.db.execute(select(StudyRecord.user_id).distinct())).all()
            if item and item[0] is not None
        }
        user_ids.update(
            {
                item[0]
                for item in (await self.db.execute(select(Task.user_id).distinct())).all()
                if item and item[0] is not None
            }
        )
        user_ids.update(
            {
                item[0]
                for item in (await self.db.execute(select(Scene.user_id).distinct())).all()
                if item and item[0] is not None
            }
        )
        updated = 0
        for user_id in sorted(user_ids, key=str):
            await self.recompute_user_attractors(user_id=user_id, now=reference_time)
            updated += 1
        return updated

    @staticmethod
    def _require_user_id(user_id: UUID | str) -> UUID:
        if isinstance(user_id, UUID):
            return user_id
        normalized = str(user_id or "").strip()
        if not normalized:
            raise ValueError("PersDynAttractorService requires a non-empty user_id")
        return UUID(normalized)

    @staticmethod
    def _is_stale(row: PersDynAttractor, reference_time: datetime) -> bool:
        return (reference_time - (row.updated_at or reference_time)).total_seconds() > 24 * 60 * 60

    async def _load_rows(self, user_id: UUID) -> list[PersDynAttractor]:
        stmt = select(PersDynAttractor).where(
            PersDynAttractor.user_id == user_id,
            PersDynAttractor.deleted_at.is_(None),
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _load_signal_rows(self, user_id: UUID, reference_time: datetime) -> _SignalRows:
        earliest_start = _start_of_day(reference_time.date() - timedelta(days=self.CONFIDENCE_LOOKBACK_DAYS - 1))

        study_records = tuple(
            (
                await self.db.execute(
                    select(StudyRecord).where(
                        StudyRecord.user_id == user_id,
                        StudyRecord.deleted_at.is_(None),
                        StudyRecord.created_at >= earliest_start,
                        StudyRecord.created_at < reference_time + timedelta(days=1),
                    )
                )
            ).scalars().all()
        )
        tasks = tuple(
            (
                await self.db.execute(
                    select(Task).where(
                        Task.user_id == user_id,
                        Task.deleted_at.is_(None),
                        Task.created_at < reference_time + timedelta(days=1),
                    )
                )
            ).scalars().all()
        )
        focus_sessions = tuple(
            (
                await self.db.execute(
                    select(FocusSession).where(
                        FocusSession.user_id == user_id,
                        FocusSession.deleted_at.is_(None),
                        FocusSession.status == FocusStatus.COMPLETED,
                        FocusSession.end_time.is_not(None),
                        FocusSession.end_time >= earliest_start,
                        FocusSession.end_time < reference_time + timedelta(days=1),
                    )
                )
            ).scalars().all()
        )
        scenes = tuple(
            (
                await self.db.execute(
                    select(Scene).where(
                        Scene.user_id == user_id,
                        Scene.deleted_at.is_(None),
                        Scene.time_end >= earliest_start,
                        Scene.time_end < reference_time + timedelta(days=1),
                    )
                )
            ).scalars().all()
        )
        reflections = tuple(
            (
                await self.db.execute(
                    select(EpisodicMemory).where(
                        EpisodicMemory.user_id == user_id,
                        EpisodicMemory.deleted_at.is_(None),
                        EpisodicMemory.archived_at.is_(None),
                        EpisodicMemory.retracted_at.is_(None),
                        EpisodicMemory.revoked_at.is_(None),
                        EpisodicMemory.source_type == "reflection",
                        EpisodicMemory.source_lane == "inferred_extraction",
                        EpisodicMemory.occurred_at >= earliest_start,
                        EpisodicMemory.occurred_at < reference_time + timedelta(days=1),
                    )
                )
            ).scalars().all()
        )
        return _SignalRows(
            study_records=study_records,
            tasks=tasks,
            focus_sessions=focus_sessions,
            scenes=scenes,
            reflections=reflections,
        )

    def _build_series(self, *, rows: _SignalRows, reference_time: datetime) -> dict[str, list[float]]:
        series = {dim: [] for dim in self.DIMENSIONS}
        for offset in range(self.HISTORY_DAYS - 1, -1, -1):
            reference_day = reference_time.date() - timedelta(days=offset)
            observation = self._build_observation_for_day(rows=rows, reference_day=reference_day)
            for dim in self.DIMENSIONS:
                series[dim].append(float(observation[dim]))
        return series

    def _build_observation_for_day(self, *, rows: _SignalRows, reference_day: date) -> dict[str, float]:
        day_end = _end_exclusive(reference_day)
        start_3d = _start_of_day(reference_day - timedelta(days=2))
        start_7d = _start_of_day(reference_day - timedelta(days=6))

        study_minutes = sum(
            int(record.study_minutes or 0)
            for record in rows.study_records
            if start_3d <= record.created_at < day_end
        )
        study_records_3d = [
            record for record in rows.study_records if start_3d <= record.created_at < day_end
        ]
        tasks_7d = [
            task for task in rows.tasks if start_7d <= task.created_at < day_end
        ]
        completed_tasks_7d = [
            task for task in tasks_7d if task.completed_at is not None and task.completed_at < day_end
        ]
        focus_3d = [
            session for session in rows.focus_sessions if session.end_time is not None and start_3d <= session.end_time < day_end
        ]
        scenes_7d = [
            scene for scene in rows.scenes if start_7d <= scene.time_end < day_end
        ]
        reflections_7d = [
            reflection for reflection in rows.reflections if start_7d <= reflection.occurred_at < day_end
        ]
        plan_tasks = [
            task for task in rows.tasks if task.plan_id is not None and task.created_at < day_end
        ]
        overdue_plan_tasks = [
            task
            for task in plan_tasks
            if task.due_date is not None
            and task.due_date < reference_day
            and (task.completed_at is None or task.completed_at >= day_end)
        ]

        valence_values = [
            self.REFLECTION_VALENCE_MAP.get(self._extract_reflection_category(reflection), 0.4)
            for reflection in reflections_7d
        ]

        return {
            "study_pace": round((study_minutes / 60.0) / 3.0, 4),
            "completion_rate": round((len(completed_tasks_7d) / len(tasks_7d)) if tasks_7d else 0.5, 4),
            "engagement_level": round(
                len(study_records_3d)
                + (len(focus_3d) * 1.5)
                + sum(max(0.0, min(1.0, float(scene.quality_score))) for scene in scenes_7d)
                + (len(reflections_7d) * 0.5),
                4,
            ),
            "mood_valence": round(fmean(valence_values) if valence_values else 0.5, 4),
            "plan_adherence": round(1.0 - (len(overdue_plan_tasks) / len(plan_tasks)) if plan_tasks else 0.5, 4),
        }

    def _count_active_days(self, *, rows: _SignalRows, reference_time: datetime) -> int:
        window_start = reference_time.date() - timedelta(days=self.CONFIDENCE_LOOKBACK_DAYS - 1)
        active_days: set[date] = set()
        for record in rows.study_records:
            active_days.add(record.created_at.date())
        for task in rows.tasks:
            active_days.add(task.created_at.date())
            if task.completed_at is not None:
                active_days.add(task.completed_at.date())
        for session in rows.focus_sessions:
            if session.end_time is not None:
                active_days.add(session.end_time.date())
        for scene in rows.scenes:
            active_days.add(scene.time_end.date())
        for reflection in rows.reflections:
            active_days.add(reflection.occurred_at.date())
        return sum(1 for day in active_days if window_start <= day <= reference_time.date())

    def _estimate_state(
        self,
        *,
        dim: str,
        values: list[float],
        active_days: int,
        reference_time: datetime,
    ) -> AttractorState:
        baseline = self._ema(values)
        variability = float(pstdev(values)) if len(values) > 1 else 0.0
        residuals = [abs(value - baseline) for value in values]
        recovery_rate = max(0.0, -_linear_regression_slope(residuals))
        confidence = self._confidence(active_days)
        return AttractorState(
            dim=dim,
            baseline=round(baseline, 4),
            variability=round(variability, 4),
            recovery_rate=round(recovery_rate, 4),
            confidence=round(confidence, 4),
            updated_at=reference_time,
        )

    def _confidence(self, active_days: int) -> float:
        if active_days < self.HISTORY_DAYS:
            return min(0.29, (active_days / max(1, self.HISTORY_DAYS)) * 0.29)
        capped = min(active_days, self.CONFIDENCE_LOOKBACK_DAYS)
        return min(
            0.95,
            0.3 + ((capped - self.HISTORY_DAYS) / max(1, self.CONFIDENCE_LOOKBACK_DAYS - self.HISTORY_DAYS)) * 0.65,
        )

    def _ema(self, values: list[float]) -> float:
        if not values:
            return 0.0
        ema = float(values[0])
        for value in values[1:]:
            ema = (self.alpha * float(value)) + ((1.0 - self.alpha) * ema)
        return ema

    async def _upsert_rows(
        self,
        *,
        user_id: UUID,
        states: dict[str, AttractorState],
        now: datetime,
    ) -> None:
        existing = {
            row.dim: row
            for row in await self._load_rows(user_id)
        }
        updated_dims: list[str] = []
        for dim, state in states.items():
            row = existing.get(dim)
            if row is None:
                row = PersDynAttractor(
                    user_id=user_id,
                    dim=dim,
                    baseline=state.baseline,
                    variability=state.variability,
                    recovery_rate=state.recovery_rate,
                    confidence=state.confidence,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(row)
            else:
                row.baseline = state.baseline
                row.variability = state.variability
                row.recovery_rate = state.recovery_rate
                row.confidence = state.confidence
                row.updated_at = now
            updated_dims.append(dim)
            PERSDYN_ATTRACTOR_UPDATED_TOTAL.labels(dim=dim).inc()
        await self.db.commit()
        try:
            await event_bus.publish(
                ATTRACTOR_UPDATED,
                {
                    "event_type": ATTRACTOR_UPDATED,
                    "user_id": str(user_id),
                    "dimensions": updated_dims,
                    "updated_at": now.isoformat(),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive around infra
            logger.warning("Failed to publish attractor_updated event: {}", exc)

    @staticmethod
    def _extract_reflection_category(reflection: EpisodicMemory) -> str | None:
        for tag in list(reflection.tags or []):
            if str(tag).startswith("reflection_category:"):
                return str(tag).split(":", 1)[1]
        return None

    @staticmethod
    def _to_state(row: PersDynAttractor) -> AttractorState:
        return AttractorState(
            dim=row.dim,
            baseline=round(float(row.baseline or 0.0), 4),
            variability=round(float(row.variability or 0.0), 4),
            recovery_rate=round(float(row.recovery_rate or 0.0), 4),
            confidence=round(float(row.confidence or 0.0), 4),
            updated_at=row.updated_at,
        )
