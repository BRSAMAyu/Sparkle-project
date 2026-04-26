from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.core.event_types import ATTRACTOR_UPDATED
from app.db.session import AsyncSessionLocal
from app.learning.changepoint_pelt import detect_change_points
from app.learning.rolling_correlator import CorrelationResult, correlate_dimensions
from app.models.aurora_stage20 import RoutingDecisionLog
from app.models.aurora_stage31 import (
    DailyBehaviorVector,
    IdiographicAssociation,
    IdiographicChangepoint,
)
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import StudyRecord
from app.models.memory import MemoryCorrection
from app.models.srl_phase_state import SRLPhaseStateRecord
from app.models.task import Task, TaskStatus
from app.services.aurora_stage31_idiographic_kill_switch_service import (
    AuroraStage31IdiographicKillSwitchService,
)
from app.services.metacognition_service import MetacognitionService
from app.services.persdyn_attractor_service import PersDynAttractorService
from app.state_aggregator.schema import (
    AssociationPairValue,
    ChangePointItemValue,
    IdiographicSummaryValue,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min)


class IdiographicAssociationService:
    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "idiographic_association"
    WINDOW_DAYS = 45
    CHANGEPOINT_LOOKBACK_DAYS = 30
    MIN_ACTIVE_DAYS = 25
    DISPLAY_ACTIVE_DAYS = 40
    MIN_ACTIVE_DIMS = 5
    MIN_VISIBLE_ABS_R = 0.30
    BH_Q_THRESHOLD = 0.05
    CONFIDENCE_CAP = 0.80
    TOP_ASSOCIATION_LIMIT = 3
    SILENT_STREAK_CUTOFF = 5
    DENSITY_MIN_RANK_PAIRS = 150
    DENSITY_MIN_COVERAGE = 0.70
    DISCONFIRM_SUPPRESSION_DAYS = 30
    SUMMARY_CACHE_TTL_SECONDS = 300
    SUMMARY_CACHE_PREFIX = "idiographic"
    DISCLAIMER_TEXT = "这只是你数据中的模式，不代表因果关系。"
    ASSOCIATION_LANGUAGE_TEMPLATES = {
        "positive_sync": "在你最近 {n_days} 天的数据里，{dim_a} 和 {dim_b} 有同步变化的趋势（关联强度 {strength_label}）。这只是你数据中的模式，不代表因果关系。",
        "negative_sync": "在你最近 {n_days} 天的数据里，{dim_a} 偏高时 {dim_b} 倾向于偏低（关联强度 {strength_label}）。这只是你数据中的模式，不代表因果关系。",
        "change_point": "在 {date} 前后，你的 {dim} 模式出现了明显变化。这是一个观察，不是评判。",
    }
    DIMENSION_LABELS = {
        "study_pace": "学习节奏",
        "completion_rate": "完成率",
        "engagement_level": "投入程度",
        "mood_valence": "情绪效价",
        "plan_adherence": "计划贴合度",
        "focus_duration_daily": "专注时长",
        "task_accuracy_daily": "任务预估准确度",
        "session_frequency_daily": "学习记录频次",
        "srl_phase_signal": "自我调节阶段",
        "metacognition_accuracy": "元认知准确性",
    }
    PHASE_SCORES = {
        "UNKNOWN": 0.0,
        "FORETHOUGHT": 0.25,
        "PERFORMANCE": 0.55,
        "SELF_REFLECTION": 0.85,
    }

    def __init__(
        self,
        db: AsyncSession | None = None,
        *,
        event_bus: EventBus | None = None,
        redis=None,
        now_factory=_utcnow,
    ) -> None:
        self.db = db
        self.event_bus = event_bus
        self.redis = redis or cache_service.redis
        self.now_factory = now_factory
        self.kill_switch = AuroraStage31IdiographicKillSwitchService()
        self.consumer_name = f"idiographic-{os.getpid()}"
        self._running = False
        self._subscribed = False

    async def start(self) -> None:
        if self.event_bus is None:
            raise RuntimeError("event_bus is required to start IdiographicAssociationService")
        await self.event_bus.connect()
        if self._running:
            return
        self._running = True
        while self._running:
            try:
                if not self._subscribed:
                    await self.event_bus.subscribe(
                        stream=self.STREAM_NAME,
                        group_name=self.GROUP_NAME,
                        consumer_name=self.consumer_name,
                        callback=self.handle_event,
                    )
                    self._subscribed = True
                await asyncio.sleep(1)
            except Exception as exc:  # pragma: no cover - infra defensive
                self._subscribed = False
                logger.error("IdiographicAssociationService loop error: {}", exc)
                await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def handle_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type") or "").strip()
        if event_type not in {
            "task.completed",
            "focus.session.completed",
            "study_record.created",
            ATTRACTOR_UPDATED,
        }:
            return
        user_id_raw = event.get("user_id")
        if not user_id_raw:
            return
        try:
            user_id = UUID(str(user_id_raw))
        except (TypeError, ValueError):
            return
        async with self._session_scope() as (db, _):
            service = self if self.db is db else IdiographicAssociationService(
                db,
                event_bus=self.event_bus,
                redis=self.redis,
                now_factory=self.now_factory,
            )
            await service.recompute_user(user_id, publish_event=False)

    async def recompute_all_users(self, *, now: datetime | None = None) -> int:
        reference_time = now or self.now_factory()
        async with self._session_scope() as (db, _):
            user_ids: set[UUID] = set()
            for model in (Task, FocusSession, StudyRecord):
                result = await db.execute(select(model.user_id).where(model.deleted_at.is_(None)).distinct())
                user_ids.update(user_id for (user_id,) in result.all() if user_id is not None)
            updated = 0
            for user_id in sorted(user_ids, key=str):
                await IdiographicAssociationService(
                    db,
                    event_bus=self.event_bus,
                    redis=self.redis,
                    now_factory=self.now_factory,
                ).recompute_user(user_id, now=reference_time, publish_event=False)
                updated += 1
            return updated

    async def recompute_user(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        publish_event: bool = False,
    ) -> dict[str, Any]:
        reference_time = now or self.now_factory()
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            await self._write_summary_cache(user_id, None)
            return {"user_id": str(user_id), "mode": "off", "path_mode": "C"}

        daily_vectors = await self._build_daily_vectors(user_id, reference_time)
        changepoints = self._detect_recent_changepoints(daily_vectors)

        effective_days = self._effective_window_days(daily_vectors, changepoints)
        series_by_dim = self._series_by_dim(daily_vectors, effective_days)
        active_days = sum(1 for day in effective_days if int(daily_vectors[day]["active_event_count"]) > 0)
        active_dims = self._count_active_dims(series_by_dim)
        stage30_dim_count = max(
            (int(daily_vectors[day]["stage30_dim_count"]) for day in daily_vectors),
            default=0,
        )
        stage30_ready = stage30_dim_count >= 2
        path_mode = "A" if stage30_ready and active_days >= self.DISPLAY_ACTIVE_DAYS and active_dims >= self.MIN_ACTIVE_DIMS else "B"
        correlation_results = (
            correlate_dimensions(
                series_by_dim,
                density_min_rank_pairs=self.DENSITY_MIN_RANK_PAIRS,
                density_min_coverage=self.DENSITY_MIN_COVERAGE,
            )
            if active_days >= self.MIN_ACTIVE_DAYS and active_dims >= self.MIN_ACTIVE_DIMS
            else []
        )
        disconfirmed_until = await self._load_disconfirmed_pairs(user_id, reference_time)

        if mode == "live":
            await self._upsert_daily_vectors(user_id, daily_vectors)
            await self._upsert_changepoints(user_id, changepoints, reference_time)
            await self._upsert_associations(
                user_id=user_id,
                reference_time=reference_time,
                effective_days=effective_days,
                active_days=active_days,
                path_mode=path_mode,
                correlation_results=correlation_results,
                disconfirmed_until=disconfirmed_until,
            )
            summary = await self.build_aggregator_summary(user_id, now=reference_time)
            await self._write_summary_cache(user_id, summary)

            if publish_event and self.event_bus is not None:
                await self.event_bus.publish(
                    "idiographic.updated",
                    {
                        "event_type": "idiographic.updated",
                        "user_id": str(user_id),
                        "path_mode": path_mode,
                        "active_days": active_days,
                    },
                )
        return {
            "user_id": str(user_id),
            "mode": mode,
            "path_mode": path_mode,
            "active_days": active_days,
            "active_dims": active_dims,
            "effective_days": len(effective_days),
            "association_count": len(correlation_results),
        }

    async def build_aggregator_summary(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> IdiographicSummaryValue | None:
        reference_time = now or self.now_factory()
        if await self.kill_switch.get_mode() != "live":
            return None
        cached = await self._read_summary_cache(user_id)
        if cached is not None:
            return cached

        async with self._session_scope() as (db, _):
            association_rows = (
                (
                    await db.execute(
                        select(IdiographicAssociation)
                        .where(
                            IdiographicAssociation.user_id == user_id,
                            IdiographicAssociation.deleted_at.is_(None),
                        )
                        .order_by(desc(func.abs(IdiographicAssociation.correlation)))
                        .limit(12)
                    )
                )
                .scalars()
                .all()
            )
            changepoint_rows = (
                (
                    await db.execute(
                        select(IdiographicChangepoint)
                        .where(
                            IdiographicChangepoint.user_id == user_id,
                            IdiographicChangepoint.deleted_at.is_(None),
                            IdiographicChangepoint.change_date >= reference_time.date() - timedelta(days=self.CHANGEPOINT_LOOKBACK_DAYS),
                        )
                        .order_by(desc(IdiographicChangepoint.change_date))
                        .limit(6)
                    )
                )
                .scalars()
                .all()
            )

        top_associations = tuple(
            AssociationPairValue(
                dim_pair=str(row.dim_pair or ""),
                dim_a=str(row.dim_a or ""),
                dim_b=str(row.dim_b or ""),
                correlation=round(float(row.correlation or 0.0), 4),
                q_value=round(float(row.p_value_bh or 1.0), 4),
                confidence=round(float(row.confidence or 0.0), 4),
                direction=str(row.direction or "positive_sync"),
                strength_label=self._strength_label(float(row.correlation or 0.0)),
                rendered_text=str(row.rendered_text or ""),
                displayed=bool(row.visible),
                density_insufficient=bool(row.density_insufficient),
                sample_days=int(row.sample_days or 0),
            )
            for row in association_rows[: self.TOP_ASSOCIATION_LIMIT]
        )
        change_points_30d = tuple(
            ChangePointItemValue(
                dim=str(row.dim or ""),
                change_date=row.change_date,
                confidence=round(float(row.confidence or 0.0), 4),
                rendered_text=str(row.rendered_text or ""),
            )
            for row in changepoint_rows
        )
        summary = IdiographicSummaryValue(
            top_associations=top_associations,
            change_points_30d=change_points_30d,
            sample_days=max((item.sample_days for item in top_associations), default=0),
            confidence=max((item.confidence for item in top_associations), default=0.0),
            disclaimer_text=self.DISCLAIMER_TEXT,
        )
        await self._write_summary_cache(user_id, summary)
        return summary

    async def register_user_disconfirmation(
        self,
        user_id: UUID,
        *,
        dim_pair: str,
        reason: str | None = None,
        decision_id: UUID | None = None,
    ) -> None:
        async with self._session_scope() as (db, owns_session):
            correction = MemoryCorrection(
                user_id=user_id,
                memory_type="idiographic_association",
                memory_id=decision_id or user_id,
                action="wrong",
                reason=json.dumps(
                    {
                        "dim_pair": str(dim_pair or "").strip(),
                        "user_disconfirmed": True,
                        "reason": reason,
                    },
                    ensure_ascii=True,
                ),
            )
            db.add(correction)
            row = (
                (
                    await db.execute(
                        select(IdiographicAssociation).where(
                            IdiographicAssociation.user_id == user_id,
                            IdiographicAssociation.dim_pair == str(dim_pair or "").strip(),
                            IdiographicAssociation.deleted_at.is_(None),
                        )
                    )
                )
                .scalars()
                .first()
            )
            if row is not None:
                row.user_disconfirmed = True
                row.user_disconfirmed_until = self.now_factory() + timedelta(days=self.DISCONFIRM_SUPPRESSION_DAYS)
                row.visible = False
                row.updated_at = self.now_factory()
            if owns_session:
                await db.commit()
            ratio = await self._recent_disconfirm_ratio(db, user_id=user_id, now=self.now_factory())
            await self.kill_switch.auto_downgrade_on_disconfirm_rate(ratio)

    async def _build_daily_vectors(
        self,
        user_id: UUID,
        reference_time: datetime,
    ) -> dict[date, dict[str, Any]]:
        start_day = reference_time.date() - timedelta(days=self.WINDOW_DAYS - 1)
        observations = await PersDynAttractorService(self._require_db()).build_daily_observations(
            user_id=user_id,
            now=reference_time,
            days=self.WINDOW_DAYS,
        )
        focus_by_day, task_accuracy_by_day, task_count_by_day, study_by_day = await self._load_behavior_daily_aggregates(
            user_id,
            start_day,
            reference_time.date(),
        )
        metacognition_by_day = await MetacognitionService(self._require_db()).build_daily_accuracy_series(
            user_id,
            now=reference_time,
            days=self.WINDOW_DAYS,
        )
        srl_phase_by_day = await self._build_srl_phase_series(user_id, start_day, reference_time.date())

        vectors: dict[date, dict[str, Any]] = {}
        for offset in range(self.WINDOW_DAYS):
            current_day = start_day + timedelta(days=offset)
            persdyn = dict(observations.get(current_day) or {})
            focus_duration = round(float(focus_by_day.get(current_day) or 0.0), 4)
            session_frequency = round(float(study_by_day.get(current_day) or 0.0), 4)
            dims = {
                "study_pace": persdyn.get("study_pace"),
                "completion_rate": persdyn.get("completion_rate"),
                "engagement_level": persdyn.get("engagement_level"),
                "mood_valence": persdyn.get("mood_valence"),
                "plan_adherence": persdyn.get("plan_adherence"),
                "focus_duration_daily": focus_duration,
                "task_accuracy_daily": task_accuracy_by_day.get(current_day),
                "session_frequency_daily": session_frequency,
                "srl_phase_signal": srl_phase_by_day.get(current_day),
                "metacognition_accuracy": metacognition_by_day.get(current_day),
            }
            active_event_count = int(task_count_by_day.get(current_day) or 0) + int(round(focus_duration * 60)) // 1
            active_event_count = int(active_event_count + int(study_by_day.get(current_day) or 0))
            stage30_dim_count = sum(
                1
                for key in ("srl_phase_signal", "metacognition_accuracy")
                if dims.get(key) is not None
            )
            vectors[current_day] = {
                "dims": dims,
                "active_event_count": active_event_count,
                "stage30_dim_count": stage30_dim_count,
                "silent_window_cut": False,
            }
        self._mark_silent_window_cuts(vectors)
        return vectors

    async def _load_behavior_daily_aggregates(
        self,
        user_id: UUID,
        start_day: date,
        end_day: date,
    ) -> tuple[dict[date, float], dict[date, float | None], dict[date, int], dict[date, int]]:
        db = self._require_db()
        start_at = _day_start(start_day)
        end_at = _day_start(end_day + timedelta(days=1))

        focus_rows = (
            (
                await db.execute(
                    select(FocusSession.end_time, FocusSession.duration_minutes).where(
                        FocusSession.user_id == user_id,
                        FocusSession.deleted_at.is_(None),
                        FocusSession.status == FocusStatus.COMPLETED,
                        FocusSession.end_time >= start_at,
                        FocusSession.end_time < end_at,
                    )
                )
            )
            .all()
        )
        focus_by_day: dict[date, float] = defaultdict(float)
        for end_time, duration_minutes in focus_rows:
            if end_time is None:
                continue
            focus_by_day[end_time.date()] += round(float(duration_minutes or 0) / 60.0, 4)

        task_rows = (
            (
                await db.execute(
                    select(Task.completed_at, Task.estimated_minutes, Task.actual_minutes).where(
                        Task.user_id == user_id,
                        Task.deleted_at.is_(None),
                        Task.status == TaskStatus.COMPLETED,
                        Task.completed_at.is_not(None),
                        Task.completed_at >= start_at,
                        Task.completed_at < end_at,
                    )
                )
            )
            .all()
        )
        task_count_by_day: dict[date, int] = defaultdict(int)
        task_accuracy_values: dict[date, list[float]] = defaultdict(list)
        for completed_at, estimated_minutes, actual_minutes in task_rows:
            if completed_at is None:
                continue
            day = completed_at.date()
            task_count_by_day[day] += 1
            estimated = float(estimated_minutes or 0.0)
            actual = float(actual_minutes or 0.0)
            if estimated > 0 and actual > 0:
                accuracy = 1.0 - min(1.0, abs(actual - estimated) / estimated)
                task_accuracy_values[day].append(round(accuracy, 4))
        task_accuracy_by_day = {
            day: round(sum(values) / len(values), 4)
            for day, values in task_accuracy_values.items()
            if values
        }

        study_rows = (
            (
                await db.execute(
                    select(StudyRecord.created_at).where(
                        StudyRecord.user_id == user_id,
                        StudyRecord.deleted_at.is_(None),
                        StudyRecord.created_at >= start_at,
                        StudyRecord.created_at < end_at,
                    )
                )
            )
            .all()
        )
        study_by_day: dict[date, int] = defaultdict(int)
        for (created_at,) in study_rows:
            if created_at is not None:
                study_by_day[created_at.date()] += 1

        return dict(focus_by_day), task_accuracy_by_day, dict(task_count_by_day), dict(study_by_day)

    async def _build_srl_phase_series(
        self,
        user_id: UUID,
        start_day: date,
        end_day: date,
    ) -> dict[date, float]:
        row = (
            (
                await self._require_db().execute(
                    select(SRLPhaseStateRecord).where(
                        SRLPhaseStateRecord.user_id == user_id,
                        SRLPhaseStateRecord.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .first()
        )
        if row is None:
            return {}
        current_score = self.PHASE_SCORES.get(str(row.current_phase or "UNKNOWN").upper(), 0.0)
        previous_score = self.PHASE_SCORES.get(str(row.previous_phase or row.current_phase or "UNKNOWN").upper(), current_score)
        phase_started_at = row.phase_started_at.date() if row.phase_started_at else start_day
        series: dict[date, float] = {}
        total_days = (end_day - start_day).days + 1
        for offset in range(total_days):
            current_day = start_day + timedelta(days=offset)
            series[current_day] = current_score if current_day >= phase_started_at else previous_score
        return series

    def _detect_recent_changepoints(
        self,
        daily_vectors: dict[date, dict[str, Any]],
    ) -> list[tuple[str, date, float]]:
        recent_days = sorted(daily_vectors)[-self.CHANGEPOINT_LOOKBACK_DAYS :]
        detected: list[tuple[str, date, float]] = []
        for dim in self.DIMENSION_LABELS:
            compact_dates: list[date] = []
            compact_values: list[float] = []
            for day in recent_days:
                value = daily_vectors[day]["dims"].get(dim)
                if value is None:
                    continue
                compact_dates.append(day)
                compact_values.append(float(value))
            for result in detect_change_points(compact_values):
                if 0 <= result.index < len(compact_dates):
                    detected.append((dim, compact_dates[result.index], result.confidence))
        deduped: dict[tuple[str, date], float] = {}
        for dim, change_day, confidence in detected:
            deduped[(dim, change_day)] = max(confidence, deduped.get((dim, change_day), 0.0))
        return [(dim, change_day, confidence) for (dim, change_day), confidence in sorted(deduped.items())]

    def _effective_window_days(
        self,
        daily_vectors: dict[date, dict[str, Any]],
        changepoints: list[tuple[str, date, float]],
    ) -> list[date]:
        days = sorted(daily_vectors)
        if not days:
            return []
        latest_change = max((change_day for _, change_day, _ in changepoints), default=None)
        if latest_change is not None:
            days = [day for day in days if day >= latest_change]
        cutoff_index = 0
        silent_streak = 0
        for index, day in enumerate(days):
            if int(daily_vectors[day]["active_event_count"]) <= 0:
                silent_streak += 1
                if silent_streak >= self.SILENT_STREAK_CUTOFF:
                    cutoff_index = index + 1
            else:
                silent_streak = 0
        return days[cutoff_index:]

    def _series_by_dim(
        self,
        daily_vectors: dict[date, dict[str, Any]],
        effective_days: list[date],
    ) -> dict[str, list[float | None]]:
        if not effective_days:
            return {}
        dims = {
            dim: [daily_vectors[day]["dims"].get(dim) for day in effective_days]
            for dim in self.DIMENSION_LABELS
        }
        active_dims = {
            dim: values
            for dim, values in dims.items()
            if self._non_missing_count(values) >= math.ceil(len(effective_days) * self.DENSITY_MIN_COVERAGE)
        }
        stage30_dims = {"srl_phase_signal", "metacognition_accuracy"}
        if stage30_dims.issubset(active_dims):
            return active_dims
        return {dim: values for dim, values in active_dims.items() if dim not in stage30_dims}

    def _count_active_dims(self, series_by_dim: dict[str, list[float | None]]) -> int:
        return sum(1 for values in series_by_dim.values() if self._non_missing_count(values) > 0)

    async def _upsert_daily_vectors(
        self,
        user_id: UUID,
        daily_vectors: dict[date, dict[str, Any]],
    ) -> None:
        db = self._require_db()
        existing = {
            row.vector_date: row
            for row in (
                (
                    await db.execute(
                        select(DailyBehaviorVector).where(
                            DailyBehaviorVector.user_id == user_id,
                            DailyBehaviorVector.vector_date.in_(tuple(daily_vectors)),
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        for vector_date, payload in daily_vectors.items():
            row = existing.get(vector_date)
            if row is None:
                row = DailyBehaviorVector(
                    user_id=user_id,
                    vector_date=vector_date,
                )
                db.add(row)
            row.dims_payload = payload["dims"]
            row.active_event_count = int(payload["active_event_count"])
            row.stage30_dim_count = int(payload["stage30_dim_count"])
            row.silent_window_cut = bool(payload["silent_window_cut"])
            row.updated_at = self.now_factory()
        await db.commit()

    async def _upsert_associations(
        self,
        *,
        user_id: UUID,
        reference_time: datetime,
        effective_days: list[date],
        active_days: int,
        path_mode: str,
        correlation_results: list[CorrelationResult],
        disconfirmed_until: dict[str, datetime],
    ) -> None:
        db = self._require_db()
        existing = {
            row.dim_pair: row
            for row in (
                (
                    await db.execute(
                        select(IdiographicAssociation).where(
                            IdiographicAssociation.user_id == user_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        selected_top_pairs = {
            item.dim_pair
            for item in self._select_top_associations(
                correlation_results,
                active_days=active_days,
                path_mode=path_mode,
                disconfirmed_until=disconfirmed_until,
            )
        }
        seen_pairs: set[str] = set()
        window_start = effective_days[0] if effective_days else None
        window_end = effective_days[-1] if effective_days else None

        for result in correlation_results:
            dim_pair = self._dim_pair(result.dim_a, result.dim_b)
            row = existing.get(dim_pair)
            if row is None:
                row = IdiographicAssociation(
                    user_id=user_id,
                    dim_a=result.dim_a,
                    dim_b=result.dim_b,
                    dim_pair=dim_pair,
                )
                db.add(row)
            row.dim_a = result.dim_a
            row.dim_b = result.dim_b
            row.direction = "positive_sync" if result.r_value >= 0 else "negative_sync"
            row.correlation = round(float(result.r_value), 4)
            row.p_value_raw = round(float(result.p_value_raw), 6)
            row.p_value_bh = round(float(result.p_value_bh), 6)
            row.sample_days = int(result.sample_days)
            row.active_days = int(active_days)
            row.rank_pair_count = int(result.rank_pair_count)
            row.confidence = self._confidence(
                active_days=active_days,
                r_value=result.r_value,
                path_mode=path_mode,
            )
            row.density_insufficient = bool(result.density_insufficient)
            row.visible = dim_pair in selected_top_pairs
            row.path_mode = path_mode
            row.window_start = window_start
            row.window_end = window_end
            row.disclaimer_text = self.DISCLAIMER_TEXT
            row.rendered_text = self._render_association_text(result)
            row.user_disconfirmed_until = disconfirmed_until.get(dim_pair)
            row.user_disconfirmed = row.user_disconfirmed_until is not None and row.user_disconfirmed_until > reference_time
            row.deleted_at = None
            row.updated_at = reference_time
            seen_pairs.add(dim_pair)

        for dim_pair, row in existing.items():
            if dim_pair in seen_pairs:
                continue
            row.deleted_at = reference_time
            row.visible = False
            row.updated_at = reference_time
        await db.commit()

    async def _upsert_changepoints(
        self,
        user_id: UUID,
        changepoints: list[tuple[str, date, float]],
        reference_time: datetime,
    ) -> None:
        db = self._require_db()
        existing = {
            (row.dim, row.change_date): row
            for row in (
                (
                    await db.execute(
                        select(IdiographicChangepoint).where(
                            IdiographicChangepoint.user_id == user_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        seen: set[tuple[str, date]] = set()
        for dim, change_day, confidence in changepoints:
            key = (dim, change_day)
            row = existing.get(key)
            if row is None:
                row = IdiographicChangepoint(
                    user_id=user_id,
                    dim=dim,
                    change_date=change_day,
                )
                db.add(row)
            row.confidence = round(float(confidence), 4)
            row.path_mode = "B"
            row.rendered_text = self.ASSOCIATION_LANGUAGE_TEMPLATES["change_point"].format(
                date=change_day.isoformat(),
                dim=self.DIMENSION_LABELS.get(dim, dim),
            )
            row.deleted_at = None
            row.updated_at = reference_time
            seen.add(key)
        for key, row in existing.items():
            if key in seen:
                continue
            row.deleted_at = reference_time
            row.updated_at = reference_time
        await db.commit()

    async def _load_disconfirmed_pairs(
        self,
        user_id: UUID,
        reference_time: datetime,
    ) -> dict[str, datetime]:
        rows = (
            (
                await self._require_db().execute(
                    select(MemoryCorrection).where(
                        MemoryCorrection.user_id == user_id,
                        MemoryCorrection.deleted_at.is_(None),
                        MemoryCorrection.memory_type == "idiographic_association",
                        MemoryCorrection.created_at >= reference_time - timedelta(days=self.DISCONFIRM_SUPPRESSION_DAYS),
                    )
                )
            )
            .scalars()
            .all()
        )
        suppressed: dict[str, datetime] = {}
        for row in rows:
            try:
                payload = json.loads(str(row.reason or "{}"))
            except json.JSONDecodeError:
                continue
            dim_pair = str(
                payload.get("dim_pair")
                or payload.get("target_id")
                or payload.get("field_name")
                or ""
            ).strip()
            if not dim_pair:
                continue
            suppressed[dim_pair] = max(
                suppressed.get(dim_pair, row.created_at or reference_time),
                (row.created_at or reference_time) + timedelta(days=self.DISCONFIRM_SUPPRESSION_DAYS),
            )
        return suppressed

    async def _recent_disconfirm_ratio(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        now: datetime,
    ) -> float:
        since = now - timedelta(days=3)
        correction_count = int(
            (
                await db.execute(
                    select(func.count(MemoryCorrection.id)).where(
                        MemoryCorrection.user_id == user_id,
                        MemoryCorrection.deleted_at.is_(None),
                        MemoryCorrection.memory_type == "idiographic_association",
                        MemoryCorrection.created_at >= since,
                    )
                )
            ).scalar()
            or 0
        )
        display_count = int(
            (
                await db.execute(
                    select(func.count(RoutingDecisionLog.decision_id)).where(
                        RoutingDecisionLog.user_id == user_id,
                        RoutingDecisionLog.created_at >= since,
                        RoutingDecisionLog.idiographic_associations_injected.is_not(None),
                    )
                )
            ).scalar()
            or 0
        )
        if display_count <= 0:
            return 0.0
        return round(correction_count / display_count, 4)

    def _select_top_associations(
        self,
        correlation_results: list[CorrelationResult],
        *,
        active_days: int,
        path_mode: str,
        disconfirmed_until: dict[str, datetime],
    ) -> list[CorrelationResult]:
        eligible = [
            item
            for item in correlation_results
            if not item.density_insufficient
            and item.p_value_bh <= self.BH_Q_THRESHOLD
            and abs(item.r_value) >= self.MIN_VISIBLE_ABS_R
            and active_days >= self.DISPLAY_ACTIVE_DAYS
            and disconfirmed_until.get(self._dim_pair(item.dim_a, item.dim_b), datetime.min) <= self.now_factory()
        ]
        eligible.sort(key=lambda item: abs(item.r_value), reverse=True)
        non_mood = [item for item in eligible if "mood_valence" not in {item.dim_a, item.dim_b}]
        mood = [item for item in eligible if "mood_valence" in {item.dim_a, item.dim_b}]
        selected = non_mood[: self.TOP_ASSOCIATION_LIMIT]
        if len(selected) < self.TOP_ASSOCIATION_LIMIT and mood:
            selected.extend(mood[:1])
        return selected[: self.TOP_ASSOCIATION_LIMIT]

    def _confidence(self, *, active_days: int, r_value: float, path_mode: str) -> float:
        base = min(
            self.CONFIDENCE_CAP,
            (active_days / self.WINDOW_DAYS) * min(1.0, abs(float(r_value or 0.0)) / 0.4),
        )
        if path_mode == "B":
            base *= 0.7
        return round(min(self.CONFIDENCE_CAP, base), 4)

    def _render_association_text(self, result: CorrelationResult) -> str:
        template_key = "positive_sync" if result.r_value >= 0 else "negative_sync"
        return self.ASSOCIATION_LANGUAGE_TEMPLATES[template_key].format(
            n_days=result.sample_days,
            dim_a=self.DIMENSION_LABELS.get(result.dim_a, result.dim_a),
            dim_b=self.DIMENSION_LABELS.get(result.dim_b, result.dim_b),
            strength_label=self._strength_label(result.r_value),
        )

    def _strength_label(self, r_value: float) -> str:
        absolute = abs(float(r_value or 0.0))
        if absolute < 0.40:
            return "初步"
        if absolute < 0.55:
            return "中等"
        return "较强"

    def _mark_silent_window_cuts(self, daily_vectors: dict[date, dict[str, Any]]) -> None:
        consecutive = 0
        ordered_days = sorted(daily_vectors)
        for index, day in enumerate(ordered_days):
            if int(daily_vectors[day]["active_event_count"]) <= 0:
                consecutive += 1
                continue
            if consecutive >= self.SILENT_STREAK_CUTOFF and index < len(ordered_days):
                daily_vectors[day]["silent_window_cut"] = True
            consecutive = 0

    def _non_missing_count(self, values: list[float | None]) -> int:
        return sum(1 for value in values if value is not None)

    @staticmethod
    def _dim_pair(dim_a: str, dim_b: str) -> str:
        left, right = sorted((str(dim_a or "").strip(), str(dim_b or "").strip()))
        return f"{left}__{right}"

    async def _read_summary_cache(self, user_id: UUID) -> IdiographicSummaryValue | None:
        if self.redis is None:
            return None
        raw = await self.redis.get(self._summary_cache_key(user_id))
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if payload is None:
            return None
        return IdiographicSummaryValue(
            top_associations=tuple(
                AssociationPairValue(
                    dim_pair=str(item.get("dim_pair") or ""),
                    dim_a=str(item.get("dim_a") or ""),
                    dim_b=str(item.get("dim_b") or ""),
                    correlation=float(item.get("correlation") or 0.0),
                    q_value=float(item.get("q_value") or 1.0),
                    confidence=float(item.get("confidence") or 0.0),
                    direction=str(item.get("direction") or "positive_sync"),
                    strength_label=str(item.get("strength_label") or ""),
                    rendered_text=str(item.get("rendered_text") or ""),
                    displayed=bool(item.get("displayed")),
                    density_insufficient=bool(item.get("density_insufficient")),
                    sample_days=int(item.get("sample_days") or 0),
                )
                for item in payload.get("top_associations") or []
            ),
            change_points_30d=tuple(
                ChangePointItemValue(
                    dim=str(item.get("dim") or ""),
                    change_date=date.fromisoformat(str(item.get("change_date"))),
                    confidence=float(item.get("confidence") or 0.0),
                    rendered_text=str(item.get("rendered_text") or ""),
                )
                for item in payload.get("change_points_30d") or []
                if item.get("change_date")
            ),
            sample_days=int(payload.get("sample_days") or 0),
            confidence=float(payload.get("confidence") or 0.0),
            disclaimer_text=str(payload.get("disclaimer_text") or self.DISCLAIMER_TEXT),
        )

    async def _write_summary_cache(
        self,
        user_id: UUID,
        summary: IdiographicSummaryValue | None,
    ) -> None:
        if self.redis is None:
            return
        if summary is None:
            await self.redis.setex(self._summary_cache_key(user_id), self.SUMMARY_CACHE_TTL_SECONDS, "null")
            return
        payload = {
            "top_associations": [
                {
                    "dim_pair": item.dim_pair,
                    "dim_a": item.dim_a,
                    "dim_b": item.dim_b,
                    "correlation": item.correlation,
                    "q_value": item.q_value,
                    "confidence": item.confidence,
                    "direction": item.direction,
                    "strength_label": item.strength_label,
                    "rendered_text": item.rendered_text,
                    "displayed": item.displayed,
                    "density_insufficient": item.density_insufficient,
                    "sample_days": item.sample_days,
                }
                for item in summary.top_associations
            ],
            "change_points_30d": [
                {
                    "dim": item.dim,
                    "change_date": item.change_date.isoformat(),
                    "confidence": item.confidence,
                    "rendered_text": item.rendered_text,
                }
                for item in summary.change_points_30d
            ],
            "sample_days": summary.sample_days,
            "confidence": summary.confidence,
            "disclaimer_text": summary.disclaimer_text,
        }
        await self.redis.setex(
            self._summary_cache_key(user_id),
            self.SUMMARY_CACHE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=True),
        )

    def _summary_cache_key(self, user_id: UUID) -> str:
        user_hash = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:16]
        return f"{self.SUMMARY_CACHE_PREFIX}:{user_hash}:summary"

    def _require_db(self) -> AsyncSession:
        if self.db is None:
            raise RuntimeError("AsyncSession is required for idiographic operations")
        return self.db

    def _session_scope(self):
        if self.db is not None:
            class _Context:
                async def __aenter__(self_nonlocal):
                    return self.db, False

                async def __aexit__(self_nonlocal, exc_type, exc, tb):
                    return False

            return _Context()
        class _OwnedContext:
            async def __aenter__(self_nonlocal):
                self_nonlocal.session = AsyncSessionLocal()
                return await self_nonlocal.session.__aenter__(), True

            async def __aexit__(self_nonlocal, exc_type, exc, tb):
                return await self_nonlocal.session.__aexit__(exc_type, exc, tb)

        return _OwnedContext()
