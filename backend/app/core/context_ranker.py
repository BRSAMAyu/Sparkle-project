from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import exp
from typing import TypeVar

from app.config import settings

T = TypeVar("T")

def _default_weights() -> dict[str, float]:
    return {
        "evidence": settings.MEMORY_RANK_DEFAULT_EVIDENCE,
        "freshness": settings.MEMORY_RANK_DEFAULT_FRESHNESS,
        "correction": settings.MEMORY_RANK_DEFAULT_CORRECTION,
    }
PREFERENCE_STALE_DAYS = 180


@dataclass(frozen=True)
class RankedItem:
    item: T
    score: float


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _freshness_episodic(occurred_at: datetime | None, now: datetime) -> float:
    if occurred_at is None:
        return 0.0
    days = max(0.0, (now - occurred_at).total_seconds() / 86400.0)
    return _clamp(exp(-days / 30.0))


def _freshness_preference(updated_at: datetime | None, now: datetime) -> float:
    if updated_at is None:
        return 1.0
    if updated_at < now - timedelta(days=PREFERENCE_STALE_DAYS):
        return 0.5
    return 1.0


def _freshness_goal(status: str | None, expires_at: datetime | None, now: datetime) -> float:
    if expires_at is not None and expires_at <= now:
        return 0.5
    if status and status.lower() not in {"active", "in_progress"}:
        return 0.5
    return 1.0


def _correction_penalty(correction_count: int | None) -> float:
    if not correction_count:
        return 0.0
    return min(correction_count * 0.1, 0.5)


def _normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    defaults = _default_weights()
    values = {}
    for key in ("evidence", "freshness", "correction"):
        value = defaults[key] if weights is None else weights.get(key, defaults[key])
        value = max(0.0, min(1.0, float(value)))
        values[key] = value
    total = sum(values.values())
    if total <= 0:
        return defaults
    return {key: values[key] / total for key in values}


def _score_item(
    item: T,
    kind: str,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    now = now or datetime.utcnow()
    weights = _normalize_weights(weights)
    evidence_score = float(getattr(item, "evidence_score", 0.0) or 0.0)
    correction_count = getattr(item, "correction_count", 0) or 0

    if kind == "episodic":
        freshness = _freshness_episodic(getattr(item, "occurred_at", None), now)
    elif kind == "goals":
        freshness = _freshness_goal(
            getattr(item, "status", None),
            getattr(item, "expires_at", None),
            now,
        )
    else:
        freshness = _freshness_preference(getattr(item, "updated_at", None), now)

    penalty = _correction_penalty(correction_count)
    score = (weights["evidence"] * evidence_score) + (weights["freshness"] * freshness) - (
        weights["correction"] * penalty
    )
    return _clamp(score)


def rank_items(
    items: Iterable[T],
    kind: str,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
) -> list[RankedItem[T]]:
    now = now or datetime.utcnow()
    ranked = [
        RankedItem(item=item, score=_score_item(item, kind=kind, now=now, weights=weights))
        for item in items
    ]
    ranked.sort(
        key=lambda entry: (
            entry.score,
            getattr(entry.item, "updated_at", None) or getattr(entry.item, "occurred_at", None),
        ),
        reverse=True,
    )
    return ranked
