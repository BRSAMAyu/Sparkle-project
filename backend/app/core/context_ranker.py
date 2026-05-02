from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import exp
from typing import Any, TypeVar

from app.config import settings

T = TypeVar("T")

def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _default_weights() -> dict[str, float]:
    return {
        "evidence": float(getattr(settings, "MEMORY_RANK_DEFAULT_EVIDENCE", 0.40) or 0.40),
        "freshness": float(getattr(settings, "MEMORY_RANK_DEFAULT_FRESHNESS", 0.20) or 0.20),
        "correction": float(getattr(settings, "MEMORY_RANK_DEFAULT_CORRECTION", 0.12) or 0.12),
        "confidence": float(getattr(settings, "MEMORY_RANK_DEFAULT_CONFIDENCE", 0.12) or 0.12),
        "goal_linkage": float(getattr(settings, "MEMORY_RANK_DEFAULT_GOAL_LINKAGE", 0.10) or 0.10),
        "importance": float(getattr(settings, "MEMORY_RANK_DEFAULT_IMPORTANCE", 0.06) or 0.06),
        "relevance": float(getattr(settings, "MEMORY_RANK_DEFAULT_RELEVANCE", 0.20) or 0.20),
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

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return _clamp(float(value))
    except (TypeError, ValueError):
        return default

def _confidence_score(item: Any, evidence_score: float) -> float:
    confidence = getattr(item, "confidence", None)
    if confidence is None:
        return _clamp((evidence_score + 0.5) / 2.0)
    return _safe_float(confidence, default=0.5)

def _importance_score(item: Any) -> float:
    for attr in ("importance_score", "priority_score", "salience_score"):
        value = getattr(item, attr, None)
        if value is not None:
            return _safe_float(value)
    return 0.0

def _iter_evidence_refs(item: Any) -> Iterable[dict[str, Any]]:
    refs = getattr(item, "evidence_refs", None) or []
    if not isinstance(refs, Iterable) or isinstance(refs, (str, bytes, dict)):
        return []
    return [ref for ref in refs if isinstance(ref, dict)]

def _goal_linkage_score(item: Any) -> float:
    if (
        getattr(item, "linked_goal_id", None)
        or getattr(item, "linked_plan_id", None)
        or getattr(item, "linked_task_id", None)
    ):
        return 1.0
    if getattr(item, "semantic_key", None) or getattr(item, "due_at", None) or getattr(item, "resolved_at", None):
        return 0.7

    metadata = getattr(item, "metadata_payload", None) or getattr(item, "metadata", None) or {}
    if isinstance(metadata, dict):
        for key in ("goal_id", "plan_id", "task_id", "linked_goal_id", "linked_plan_id", "linked_task_id"):
            if metadata.get(key):
                return 1.0

    evidence_types = {str(ref.get("type") or "").strip().lower() for ref in _iter_evidence_refs(item)}
    if evidence_types.intersection({"goal", "plan", "task", "practice_outcome", "error"}):
        return 1.0
    source_type = str(getattr(item, "source_type", "") or "").strip().lower()
    if source_type in {"task", "practice_outcome", "error", "plan"}:
        return 0.8
    return 0.0

_TOKEN_RE = re.compile(r"[\w\u3400-\u9fff]+", re.UNICODE)

def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(value or "") if token.strip()}

def _item_text(item: Any) -> str:
    parts: list[str] = []
    for attr in ("summary", "title", "status", "source_type", "source_lane", "subject_type", "pref_key", "semantic_key"):
        value = getattr(item, attr, None)
        if value:
            parts.append(str(value))
    pref_value = getattr(item, "pref_value", None)
    if isinstance(pref_value, dict):
        parts.extend(str(value) for value in pref_value.values() if value is not None)
    elif pref_value is not None:
        parts.append(str(pref_value))
    tags = getattr(item, "tags", None) or []
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)
    metadata = getattr(item, "metadata_payload", None) or getattr(item, "metadata", None) or {}
    if isinstance(metadata, dict):
        parts.extend(str(value) for value in metadata.values() if isinstance(value, (str, int, float)))
    return " ".join(parts)

def _relevance_score(item: Any, query_text: str | None) -> float:
    query_tokens = _tokens(str(query_text or ""))
    if not query_tokens:
        return 0.0
    item_tokens = _tokens(_item_text(item))
    if not item_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(item_tokens))
    return _clamp(overlap / max(1, min(len(query_tokens), 8)))


def _normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    defaults = _default_weights()
    values = {}
    for key in defaults:
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
    query_text: str | None = None,
) -> float:
    now = now or _utcnow()
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
    score = (
        (weights["evidence"] * evidence_score)
        + (weights["freshness"] * freshness)
        + (weights["confidence"] * _confidence_score(item, evidence_score))
        + (weights["goal_linkage"] * _goal_linkage_score(item))
        + (weights["importance"] * _importance_score(item))
        + (weights["relevance"] * _relevance_score(item, query_text))
        - (weights["correction"] * penalty)
    )
    return _clamp(score)


def rank_items(
    items: Iterable[T],
    kind: str,
    now: datetime | None = None,
    weights: dict[str, float] | None = None,
    query_text: str | None = None,
) -> list[RankedItem[T]]:
    now = now or _utcnow()
    ranked = [
        RankedItem(item=item, score=_score_item(item, kind=kind, now=now, weights=weights, query_text=query_text))
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
