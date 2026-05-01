from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, UTC
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


@dataclass(frozen=True)
class ReviewUrgencySignal:
    """Predictive review signal exposed to Galaxy clients."""

    score: float
    is_recommended: bool
    reason: str | None
    mastery_last_updated_at: datetime | None
    days_since_mastery_update: float


class ReviewUrgencyService:
    """Scores how useful it is to review a node right now.

    The score is monotonic in the two core inputs:
    lower mastery and older mastery updates both increase urgency.
    """

    DEFAULT_THRESHOLD = 0.55
    DEFAULT_MAX_RECOMMENDATIONS = 3

    @classmethod
    def score_status(
        cls,
        status: object | None,
        *,
        now: datetime | None = None,
        recent_error_count: int = 0,
    ) -> ReviewUrgencySignal:
        now = _as_utc_naive(now) or _utcnow()
        if status is None:
            return cls._empty_signal()

        if not bool(getattr(status, "is_unlocked", False)):
            return cls._empty_signal()
        if bool(getattr(status, "is_collapsed", False)) or bool(getattr(status, "decay_paused", False)):
            return cls._empty_signal()

        mastery = cls._clamp(float(getattr(status, "mastery_score", 0.0) or 0.0), 0.0, 100.0)
        last_updated = cls._mastery_last_updated_at(status)
        days_since = cls._days_since(last_updated, now)

        study_count = max(int(getattr(status, "study_count", 0) or 0), 0)
        total_minutes = max(float(getattr(status, "total_study_minutes", 0.0) or 0.0), 0.0)
        avg_minutes = total_minutes / study_count if study_count > 0 else 0.0

        mastery_pressure = math.pow((100.0 - mastery) / 100.0, 0.82)
        stability_days = 1.0 + 13.0 * math.pow(mastery / 100.0, 1.35)
        learning_frequency = cls._clamp(
            1.0 + math.log1p(study_count) / 12.0 + min(avg_minutes, 60.0) / 300.0, 1.0, 1.38
        )
        due_days = max(0.75, stability_days / learning_frequency)
        time_pressure = days_since / (days_since + due_days) if days_since > 0 else 0.0
        error_pressure = min(max(recent_error_count, 0) * 0.06, 0.18)

        score = cls._clamp(
            0.55 * mastery_pressure + 0.35 * time_pressure + error_pressure,
            0.0,
            1.0,
        )

        next_review_at = _as_utc_naive(getattr(status, "next_review_at", None))
        if next_review_at is not None and now >= next_review_at:
            score = cls._clamp(score + 0.08, 0.0, 1.0)

        return ReviewUrgencySignal(
            score=round(score, 3),
            is_recommended=False,
            reason=cls._reason_for(
                mastery=mastery,
                days_since=days_since,
                due_days=due_days,
                recent_error_count=recent_error_count,
            ),
            mastery_last_updated_at=last_updated,
            days_since_mastery_update=round(days_since, 2),
        )

    @classmethod
    def score_graph_nodes(
        cls,
        nodes_with_status: list[tuple[object, object | None]],
        *,
        now: datetime | None = None,
        recent_error_counts: dict[UUID, int] | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        max_recommendations: int = DEFAULT_MAX_RECOMMENDATIONS,
    ) -> dict[UUID, ReviewUrgencySignal]:
        now = _as_utc_naive(now) or _utcnow()
        recent_error_counts = recent_error_counts or {}
        signals: dict[UUID, ReviewUrgencySignal] = {}

        for node, status in nodes_with_status:
            node_id = getattr(node, "id", None)
            if not isinstance(node_id, UUID):
                continue
            signal = cls.score_status(
                status,
                now=now,
                recent_error_count=recent_error_counts.get(node_id, 0),
            )
            signals[node_id] = signal

        ranked_ids = sorted(
            (node_id for node_id, signal in signals.items() if signal.score >= threshold),
            key=lambda node_id: signals[node_id].score,
            reverse=True,
        )[: max(0, max_recommendations)]

        for node_id in ranked_ids:
            signals[node_id] = replace(signals[node_id], is_recommended=True)

        return signals

    @staticmethod
    def _mastery_last_updated_at(status: object) -> datetime | None:
        for attr in (
            "bkt_last_updated_at",
            "last_study_at",
            "updated_at",
            "last_interacted_at",
            "first_unlock_at",
        ):
            value = _as_utc_naive(getattr(status, attr, None))
            if value is not None:
                return value
        return None

    @staticmethod
    def _days_since(last_updated: datetime | None, now: datetime) -> float:
        if last_updated is None:
            return 30.0
        elapsed = now - last_updated
        return max(0.0, elapsed.total_seconds() / 86400.0)

    @staticmethod
    def _reason_for(
        *,
        mastery: float,
        days_since: float,
        due_days: float,
        recent_error_count: int,
    ) -> str:
        if recent_error_count > 0:
            return "recent_errors"
        if days_since >= due_days:
            return "review_window"
        if mastery < 60:
            return "low_mastery"
        return "memory_refresh"

    @staticmethod
    def _empty_signal() -> ReviewUrgencySignal:
        return ReviewUrgencySignal(
            score=0.0,
            is_recommended=False,
            reason=None,
            mastery_last_updated_at=None,
            days_since_mastery_update=0.0,
        )

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))
