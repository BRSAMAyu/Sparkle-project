from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from app.core.context_ranker import rank_items


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class DummyItem:
    evidence_score: float
    correction_count: int
    occurred_at: datetime
    updated_at: datetime
    status: str
    expires_at: datetime | None = None
    confidence: float | None = None
    importance_score: float | None = None
    linked_plan_id: str | None = None
    summary: str = ""
    tags: list[str] | None = None


def test_context_ranker_scores():
    now = _utcnow()
    item = DummyItem(
        evidence_score=0.8,
        correction_count=2,
        occurred_at=now - timedelta(days=30),
        updated_at=now,
        status="active",
    )
    ranked = rank_items([item], kind="episodic", now=now)
    assert len(ranked) == 1
    assert ranked[0].score == pytest.approx(0.438, rel=1e-2)


def test_context_ranker_prefers_relevant_goal_linked_confirmed_memory():
    now = _utcnow()
    relevant = DummyItem(
        evidence_score=0.72,
        correction_count=0,
        occurred_at=now - timedelta(days=3),
        updated_at=now,
        status="active",
        confidence=0.9,
        importance_score=0.8,
        linked_plan_id="plan_1",
        summary="TCP flow control review for the networking sprint",
        tags=["networking"],
    )
    recent_noise = DummyItem(
        evidence_score=0.85,
        correction_count=3,
        occurred_at=now - timedelta(hours=1),
        updated_at=now,
        status="active",
        confidence=0.35,
        summary="Random music preference",
        tags=["music"],
    )

    ranked = rank_items(
        [recent_noise, relevant],
        kind="episodic",
        now=now,
        query_text="networking TCP review",
    )

    assert ranked[0].item is relevant
    assert ranked[0].score > ranked[1].score
