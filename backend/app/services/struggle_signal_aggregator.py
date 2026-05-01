from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.focus import FocusSession
from app.models.plan_state import PlanState
from app.models.task import Task, TaskStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _coerce_uuid(value: str | UUID) -> UUID | str:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError):
        return str(value)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class StruggleSignals:
    skip_rate: float = 0.0
    short_session_rate: float = 0.0
    error_trend: float = 0.0
    overdue_weight: float = 0.0
    streak_weight: float = 0.0
    completion_gap_weight: float = 0.0
    today_skipped: int = 0
    today_total: int = 0
    short_sessions: int = 0
    total_sessions: int = 0
    overdue_tasks: int = 0
    struggle_streak: int = 0
    no_completion_days: int = 0
    recent_completion_count: int = 0
    last_completed_at: str | None = None
    error_counts_3d: tuple[int, int, int] = (0, 0, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skip_rate": self.skip_rate,
            "short_session_rate": self.short_session_rate,
            "error_trend": self.error_trend,
            "overdue_weight": self.overdue_weight,
            "streak_weight": self.streak_weight,
            "completion_gap_weight": self.completion_gap_weight,
            "today_skipped": self.today_skipped,
            "today_total": self.today_total,
            "short_sessions": self.short_sessions,
            "total_sessions": self.total_sessions,
            "overdue_tasks": self.overdue_tasks,
            "struggle_streak": self.struggle_streak,
            "no_completion_days": self.no_completion_days,
            "recent_completion_count": self.recent_completion_count,
            "last_completed_at": self.last_completed_at,
            "error_counts_3d": list(self.error_counts_3d),
        }


class StruggleSignalAggregator:
    """
    聚合多维度挣扎信号，计算 struggle_score（0.0-1.0）。

    信号全部来自现有数据：任务状态、专注会话、错题记录，以及 PlanState.adaptive_meta。
    """

    REDIS_KEY_TEMPLATE = "struggle:score:{user_id}"
    REDIS_TTL = 6 * 3600

    WEIGHTS = {
        "skip_rate": 0.30,
        "short_session_rate": 0.20,
        "error_trend": 0.25,
        "overdue_weight": 0.15,
        "streak_weight": 0.10,
        "completion_gap_weight": 0.35,
    }

    async def compute_struggle_score(
        self,
        db: AsyncSession,
        redis,
        *,
        user_id: str,
        plan_id: str,
    ) -> float:
        """计算并缓存 struggle score。"""
        signals = await self._collect_signals(db, user_id=user_id, plan_id=plan_id)
        score = self._score_from_signals(signals)
        await self._cache_score(redis, user_id=user_id, score=score)
        await self._maybe_emit_accountability_signal(
            db,
            redis=redis,
            user_id=user_id,
            plan_id=plan_id,
            context={
                "struggle_score": score,
                "primary_signal": self._primary_signal(signals),
                **signals.to_dict(),
            },
        )
        return score

    async def get_cached_score(self, redis, *, user_id: str) -> float | None:
        """读取缓存的 score，用于快速判断。"""
        if redis is None:
            return None
        raw = await self._redis_call(redis, "get", self._redis_key(user_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return _clamp(float(raw))
        except (TypeError, ValueError):
            return None

    async def get_struggle_context(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        plan_id: str,
    ) -> dict:
        """
        返回详细的挣扎上下文，用于生成主动关怀消息。
        """
        signals = await self._collect_signals(db, user_id=user_id, plan_id=plan_id)
        score = self._score_from_signals(signals)

        context = {
            "struggle_score": score,
            "primary_signal": self._primary_signal(signals),
            **signals.to_dict(),
            "stuck_concepts": await self._recent_stuck_concepts(db, user_id=user_id),
            "days_behind": await self._days_behind(db, user_id=user_id, plan_id=plan_id),
            "last_active": await self._last_active_text(db, user_id=user_id),
        }
        await self._maybe_emit_accountability_signal(
            db,
            redis=None,
            user_id=user_id,
            plan_id=plan_id,
            context=context,
        )
        return context

    async def _collect_signals(self, db: AsyncSession, *, user_id: str, plan_id: str) -> StruggleSignals:
        user_uuid = _coerce_uuid(user_id)
        plan_uuid = _coerce_uuid(plan_id)
        now = _utcnow()
        today_start = datetime.combine(now.date(), time.min)
        tomorrow_start = today_start + timedelta(days=1)

        today_skipped, today_total = await self._task_skip_counts(
            db,
            user_id=user_uuid,
            plan_id=plan_uuid,
            start=today_start,
            end=tomorrow_start,
        )
        short_sessions, total_sessions = await self._short_session_counts(
            db,
            user_id=user_uuid,
            plan_id=plan_uuid,
            start=today_start,
            end=tomorrow_start,
        )
        error_counts = await self._error_counts_3d(db, user_id=user_uuid, now=now)
        overdue_tasks = await self._overdue_task_count(db, user_id=user_uuid, plan_id=plan_uuid, today=now.date())
        struggle_streak = await self._struggle_streak(db, user_id=user_uuid, plan_id=plan_uuid)
        completion_gap = await self._completion_gap(db, user_id=user_uuid, plan_id=plan_uuid, now=now)

        skip_rate = today_skipped / today_total if today_total else 0.0
        short_session_rate = short_sessions / total_sessions if total_sessions else 0.0
        return StruggleSignals(
            skip_rate=_clamp(skip_rate),
            short_session_rate=_clamp(short_session_rate),
            error_trend=self._error_trend(error_counts),
            overdue_weight=_clamp(overdue_tasks / 3.0),
            streak_weight=_clamp(struggle_streak / 3.0),
            completion_gap_weight=completion_gap["completion_gap_weight"],
            today_skipped=today_skipped,
            today_total=today_total,
            short_sessions=short_sessions,
            total_sessions=total_sessions,
            overdue_tasks=overdue_tasks,
            struggle_streak=struggle_streak,
            no_completion_days=completion_gap["no_completion_days"],
            recent_completion_count=completion_gap["recent_completion_count"],
            last_completed_at=completion_gap["last_completed_at"],
            error_counts_3d=error_counts,
        )

    async def _task_skip_counts(
        self,
        db: AsyncSession,
        *,
        user_id: UUID | str,
        plan_id: UUID | str,
        start: datetime,
        end: datetime,
    ) -> tuple[int, int]:
        touched_today = or_(
            and_(Task.created_at >= start, Task.created_at < end),
            and_(Task.updated_at >= start, Task.updated_at < end),
        )
        base = [
            Task.user_id == user_id,
            Task.plan_id == plan_id,
            Task.deleted_at.is_(None),
            touched_today,
        ]

        total_result = await db.execute(select(func.count(Task.id)).where(*base))
        skipped_result = await db.execute(select(func.count(Task.id)).where(*base, Task.status == TaskStatus.ABANDONED))
        return int(skipped_result.scalar() or 0), int(total_result.scalar() or 0)

    async def _short_session_counts(
        self,
        db: AsyncSession,
        *,
        user_id: UUID | str,
        plan_id: UUID | str,
        start: datetime,
        end: datetime,
    ) -> tuple[int, int]:
        base = [
            FocusSession.user_id == user_id,
            FocusSession.deleted_at.is_(None),
            FocusSession.start_time >= start,
            FocusSession.start_time < end,
        ]
        stmt = select(func.count(FocusSession.id)).where(*base)
        short_stmt = select(func.count(FocusSession.id)).where(*base, FocusSession.duration_minutes < 5)

        if isinstance(plan_id, UUID):
            stmt = stmt.join(Task, FocusSession.task_id == Task.id).where(Task.plan_id == plan_id)
            short_stmt = short_stmt.join(Task, FocusSession.task_id == Task.id).where(Task.plan_id == plan_id)

        total_result = await db.execute(stmt)
        short_result = await db.execute(short_stmt)
        return int(short_result.scalar() or 0), int(total_result.scalar() or 0)

    async def _error_counts_3d(self, db: AsyncSession, *, user_id: UUID | str, now: datetime) -> tuple[int, int, int]:
        counts: list[int] = []
        for days_ago in (2, 1, 0):
            day = now.date() - timedelta(days=days_ago)
            start = datetime.combine(day, time.min)
            end = start + timedelta(days=1)
            result = await db.execute(
                select(func.count(ErrorRecord.id)).where(
                    ErrorRecord.user_id == user_id,
                    ErrorRecord.is_deleted.is_(False),
                    ErrorRecord.created_at >= start,
                    ErrorRecord.created_at < end,
                )
            )
            counts.append(int(result.scalar() or 0))
        return tuple(counts)  # type: ignore[return-value]

    @staticmethod
    def _error_trend(counts: tuple[int, int, int]) -> float:
        oldest, middle, latest = counts
        baseline = (oldest + middle) / 2.0
        if latest <= baseline:
            return 0.0
        return _clamp((latest - baseline) / max(float(latest), 1.0))

    async def _overdue_task_count(
        self,
        db: AsyncSession,
        *,
        user_id: UUID | str,
        plan_id: UUID | str,
        today: date,
    ) -> int:
        result = await db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.deleted_at.is_(None),
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                Task.due_date.isnot(None),
                Task.due_date < today,
            )
        )
        return int(result.scalar() or 0)

    async def _struggle_streak(self, db: AsyncSession, *, user_id: UUID | str, plan_id: UUID | str) -> int:
        result = await db.execute(
            select(PlanState.facts).where(
                PlanState.user_id == user_id,
                PlanState.plan_id == plan_id,
                PlanState.deleted_at.is_(None),
            )
        )
        facts = result.scalar_one_or_none() or {}
        adaptive_meta = dict((facts or {}).get("adaptive_meta") or {})
        try:
            return max(0, int(adaptive_meta.get("struggle_streak_since_last_replan") or 0))
        except (TypeError, ValueError):
            return 0

    async def _completion_gap(
        self,
        db: AsyncSession,
        *,
        user_id: UUID | str,
        plan_id: UUID | str,
        now: datetime,
    ) -> dict[str, Any]:
        cutoff = now - timedelta(days=2)
        completed_at_expr = func.coalesce(Task.completed_at, Task.updated_at, Task.created_at)
        recent_result = await db.execute(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.COMPLETED,
                completed_at_expr >= cutoff,
            )
        )
        recent_completion_count = int(recent_result.scalar() or 0)

        last_result = await db.execute(
            select(func.max(completed_at_expr)).where(
                Task.user_id == user_id,
                Task.plan_id == plan_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.COMPLETED,
            )
        )
        last_completed_at = last_result.scalar_one_or_none()

        reference_at = last_completed_at
        if reference_at is None:
            reference_result = await db.execute(
                select(func.min(Task.created_at)).where(
                    Task.user_id == user_id,
                    Task.plan_id == plan_id,
                    Task.deleted_at.is_(None),
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.ABANDONED]),
                )
            )
            reference_at = reference_result.scalar_one_or_none()

        if reference_at is None:
            return {
                "completion_gap_weight": 0.0,
                "no_completion_days": 0,
                "recent_completion_count": recent_completion_count,
                "last_completed_at": None,
            }

        if reference_at.tzinfo is not None:
            reference_at = reference_at.astimezone(UTC).replace(tzinfo=None)
        no_completion_days = max(0, int((now - reference_at).total_seconds() // 86400))
        completion_gap_weight = 1.0 if recent_completion_count == 0 and no_completion_days >= 2 else 0.0

        return {
            "completion_gap_weight": completion_gap_weight,
            "no_completion_days": no_completion_days,
            "recent_completion_count": recent_completion_count,
            "last_completed_at": last_completed_at.isoformat() if isinstance(last_completed_at, datetime) else None,
        }

    def _score_from_signals(self, signals: StruggleSignals) -> float:
        weighted = (
            signals.skip_rate * self.WEIGHTS["skip_rate"]
            + signals.short_session_rate * self.WEIGHTS["short_session_rate"]
            + signals.error_trend * self.WEIGHTS["error_trend"]
            + signals.overdue_weight * self.WEIGHTS["overdue_weight"]
            + signals.streak_weight * self.WEIGHTS["streak_weight"]
            + signals.completion_gap_weight * self.WEIGHTS["completion_gap_weight"]
        )
        # A high-volume skip spike is actionable even before the softer signals accumulate.
        if signals.today_total >= 5 and signals.skip_rate >= 0.7:
            weighted = max(weighted, 0.61)
        # Two full days with no completed plan task is socially actionable for
        # an accountability loop even if the user has not actively skipped tasks.
        if signals.completion_gap_weight >= 1.0 and signals.no_completion_days >= 2:
            weighted = max(weighted, 0.62)
        return round(_clamp(weighted), 4)

    def _primary_signal(self, signals: StruggleSignals) -> str:
        if signals.today_total >= 5 and signals.skip_rate >= 0.7:
            return "task_skip"
        candidates = {
            "task_skip": signals.skip_rate * self.WEIGHTS["skip_rate"],
            "short_session": signals.short_session_rate * self.WEIGHTS["short_session_rate"],
            "error_trend": signals.error_trend * self.WEIGHTS["error_trend"],
            "overdue_task": signals.overdue_weight * self.WEIGHTS["overdue_weight"],
            "struggle_streak": signals.streak_weight * self.WEIGHTS["streak_weight"],
            "completion_gap": signals.completion_gap_weight * self.WEIGHTS["completion_gap_weight"],
        }
        primary, value = max(candidates.items(), key=lambda item: item[1])
        return primary if value > 0 else "none"

    async def _maybe_emit_accountability_signal(
        self,
        db: AsyncSession,
        *,
        redis,
        user_id: str,
        plan_id: str,
        context: dict[str, Any],
    ) -> None:
        try:
            if redis is None:
                from app.core.cache import cache_service

                redis = cache_service.redis
            from app.services.social_signal_bridge import SocialSignalBridge

            await SocialSignalBridge(db, redis).maybe_publish_accountability_struggle_signal(
                user_id=_coerce_uuid(user_id),
                plan_id=_coerce_uuid(plan_id),
                struggle_context=context,
            )
        except Exception as exc:
            logger.debug("Accountability struggle signal publish skipped for user {}: {}", user_id, exc)

    async def _recent_stuck_concepts(self, db: AsyncSession, *, user_id: str) -> list[str]:
        user_uuid = _coerce_uuid(user_id)
        result = await db.execute(
            select(ErrorRecord)
            .where(
                ErrorRecord.user_id == user_uuid,
                ErrorRecord.is_deleted.is_(False),
            )
            .order_by(desc(ErrorRecord.updated_at), desc(ErrorRecord.created_at))
            .limit(5)
        )
        concepts: list[str] = []
        for error in result.scalars().all():
            for concept in self._concepts_from_error(error):
                if concept not in concepts:
                    concepts.append(concept)
                if len(concepts) >= 5:
                    return concepts
        return concepts

    @staticmethod
    def _concepts_from_error(error: ErrorRecord) -> list[str]:
        concepts: list[str] = []

        for item in list(error.suggested_concepts or []):
            text = str(item or "").strip()
            if text:
                concepts.append(text)

        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        for key in ("knowledge_point", "concept", "root_cause", "error_type"):
            value = analysis.get(key)
            if isinstance(value, list):
                concepts.extend(str(item).strip() for item in value if str(item).strip())
            elif str(value or "").strip():
                concepts.append(str(value).strip())

        chapter = str(error.chapter or "").strip()
        if chapter:
            concepts.append(chapter)

        return concepts[:5]

    async def _days_behind(self, db: AsyncSession, *, user_id: str, plan_id: str) -> float:
        user_uuid = _coerce_uuid(user_id)
        plan_uuid = _coerce_uuid(plan_id)
        today = _utcnow().date()
        result = await db.execute(
            select(Task.due_date).where(
                Task.user_id == user_uuid,
                Task.plan_id == plan_uuid,
                Task.deleted_at.is_(None),
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                Task.due_date.isnot(None),
                Task.due_date < today,
            )
        )
        overdue_dates = [item for item in result.scalars().all() if item is not None]
        if not overdue_dates:
            return 0.0
        days = [(today - due_date).days for due_date in overdue_dates]
        return round(sum(days) / len(days), 1)

    async def _last_active_text(self, db: AsyncSession, *, user_id: str) -> str:
        user_uuid = _coerce_uuid(user_id)
        candidates: list[datetime] = []
        for stmt in (
            select(func.max(FocusSession.end_time)).where(FocusSession.user_id == user_uuid),
            select(func.max(Task.updated_at)).where(Task.user_id == user_uuid),
            select(func.max(ErrorRecord.updated_at)).where(ErrorRecord.user_id == user_uuid),
        ):
            result = await db.execute(stmt)
            value = result.scalar_one_or_none()
            if isinstance(value, datetime):
                candidates.append(value.replace(tzinfo=None))

        if not candidates:
            return "暂无记录"
        delta = max(timedelta(0), _utcnow() - max(candidates))
        minutes = int(delta.total_seconds() // 60)
        if minutes < 60:
            return f"{max(minutes, 1)}分钟前"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}小时前"
        return f"{hours // 24}天前"

    async def _cache_score(self, redis, *, user_id: str, score: float) -> None:
        if redis is None:
            return
        try:
            await self._redis_call(redis, "setex", self._redis_key(user_id), self.REDIS_TTL, str(score))
        except Exception as exc:
            logger.debug("Failed to cache struggle score for user {}: {}", user_id, exc)

    def _redis_key(self, user_id: str) -> str:
        return self.REDIS_KEY_TEMPLATE.format(user_id=user_id)

    @staticmethod
    async def _redis_call(redis, method_name: str, *args, **kwargs):
        method = getattr(redis, method_name, None)
        if method is None:
            return None
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


struggle_signal_aggregator = StruggleSignalAggregator()
