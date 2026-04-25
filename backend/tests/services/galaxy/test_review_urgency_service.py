from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.services.galaxy.review_urgency_service import ReviewUrgencyService


def _status(*, mastery: float, updated_days_ago: int, study_count: int = 4):
    now = datetime(2026, 4, 25, 12, 0, 0)
    return SimpleNamespace(
        mastery_score=mastery,
        bkt_last_updated_at=now - timedelta(days=updated_days_ago),
        last_study_at=None,
        updated_at=now - timedelta(days=updated_days_ago),
        last_interacted_at=None,
        first_unlock_at=None,
        next_review_at=None,
        is_unlocked=True,
        is_collapsed=False,
        decay_paused=False,
        study_count=study_count,
        total_study_minutes=study_count * 25,
    )


def test_review_urgency_increases_when_mastery_is_lower():
    now = datetime(2026, 4, 25, 12, 0, 0)

    low = ReviewUrgencyService.score_status(
        _status(mastery=35, updated_days_ago=5),
        now=now,
    )
    high = ReviewUrgencyService.score_status(
        _status(mastery=85, updated_days_ago=5),
        now=now,
    )

    assert low.score > high.score


def test_review_urgency_increases_when_update_is_older():
    now = datetime(2026, 4, 25, 12, 0, 0)

    old = ReviewUrgencyService.score_status(
        _status(mastery=55, updated_days_ago=21),
        now=now,
    )
    fresh = ReviewUrgencyService.score_status(
        _status(mastery=55, updated_days_ago=1),
        now=now,
    )

    assert old.score > fresh.score


def test_score_graph_nodes_marks_top_recommendations_only():
    now = datetime(2026, 4, 25, 12, 0, 0)
    rows = []
    node_ids = []
    for mastery, age in [(40, 18), (45, 12), (50, 11), (92, 1)]:
        node_id = uuid4()
        node_ids.append(node_id)
        rows.append((SimpleNamespace(id=node_id), _status(mastery=mastery, updated_days_ago=age)))

    signals = ReviewUrgencyService.score_graph_nodes(
        rows,
        now=now,
        threshold=0.45,
        max_recommendations=2,
    )

    recommended = [node_id for node_id, signal in signals.items() if signal.is_recommended]
    assert len(recommended) == 2
    assert node_ids[0] in recommended
    assert node_ids[1] in recommended
    assert not signals[node_ids[-1]].is_recommended
