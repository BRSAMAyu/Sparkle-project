from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone, datetime, timedelta

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


import pytest

from app.core.context_ranker import rank_items


@dataclass
class DummyItem:
    evidence_score: float
    correction_count: int
    occurred_at: datetime
    updated_at: datetime
    status: str
    expires_at: datetime | None = None


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
    assert ranked[0].score == pytest.approx(0.57036, rel=1e-2)
