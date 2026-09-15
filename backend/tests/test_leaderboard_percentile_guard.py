"""Regression test for ISSUE-20260503-1510-K1.

Verifies that leaderboard percentile calculation handles:
1. total_participants=-1 (GLOBAL sentinel) → percentile=None, total=0
2. total_participants=0 (empty leaderboard) → percentile=None
3. total_participants>0 (normal case) → percentile computed correctly
"""
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from datetime import datetime, timezone

from app.schemas.leaderboard import (
    LeaderboardEntry,
    LeaderboardResponse,
    LeaderboardType,
    LeaderboardPeriod,
    MyRankResponse,
)


def _make_entry(user_id, rank, score=100.0, is_me=True):
    return LeaderboardEntry(
        rank=rank,
        user_id=user_id,
        username="test_user",
        score=score,
        score_label=f"{score} pts",
        is_me=is_me,
    )


def _make_leaderboard(total_participants, entries, lb_type=LeaderboardType.GLOBAL):
    return LeaderboardResponse(
        type=lb_type,
        title="Test",
        entries=entries,
        my_rank=entries[0].rank if entries else 0,
        my_score=entries[0].score if entries else 0,
        last_updated=datetime.now(timezone.utc),
        total_participants=total_participants,
        period=LeaderboardPeriod.ALL_TIME,
    )


@pytest.mark.asyncio
async def test_percentile_guard_negative_sentinel():
    """GLOBAL leaderboard with total_participants=-1 → percentile=None, total=0."""
    from app.services.leaderboard_service import LeaderboardService

    uid = uuid4()
    entry = _make_entry(uid, rank=3)
    full_lb = _make_leaderboard(total_participants=-1, entries=[entry])

    svc = LeaderboardService.__new__(LeaderboardService)
    svc.db = AsyncMock()
    svc.get_leaderboard = AsyncMock(return_value=full_lb)

    result = await svc.get_my_rank(uid, LeaderboardType.GLOBAL)

    assert result.percentile is None
    assert result.total_participants == 0


@pytest.mark.asyncio
async def test_percentile_guard_zero_total():
    """Empty leaderboard (total_participants=0) → percentile=None."""
    from app.services.leaderboard_service import LeaderboardService

    uid = uuid4()
    entry = _make_entry(uid, rank=1)
    full_lb = _make_leaderboard(total_participants=0, entries=[entry])

    svc = LeaderboardService.__new__(LeaderboardService)
    svc.db = AsyncMock()
    svc.get_leaderboard = AsyncMock(return_value=full_lb)

    result = await svc.get_my_rank(uid, LeaderboardType.FRIENDS)

    assert result.percentile is None
    assert result.total_participants == 0


@pytest.mark.asyncio
async def test_percentile_normal():
    """Normal leaderboard computes percentile correctly."""
    from app.services.leaderboard_service import LeaderboardService

    uid = uuid4()
    entry = _make_entry(uid, rank=25)
    full_lb = _make_leaderboard(total_participants=100, entries=[entry])

    svc = LeaderboardService.__new__(LeaderboardService)
    svc.db = AsyncMock()
    svc.get_leaderboard = AsyncMock(return_value=full_lb)

    result = await svc.get_my_rank(uid, LeaderboardType.WEEKLY)

    assert result.percentile == pytest.approx(0.75)
    assert result.total_participants == 100


@pytest.mark.asyncio
async def test_user_not_found_returns_none_percentile():
    """User not in leaderboard → rank=0, percentile=None, safe total."""
    from app.services.leaderboard_service import LeaderboardService

    uid = uuid4()
    other_uid = uuid4()
    other_entry = _make_entry(other_uid, rank=1, is_me=False)
    full_lb = _make_leaderboard(total_participants=-1, entries=[other_entry])

    svc = LeaderboardService.__new__(LeaderboardService)
    svc.db = AsyncMock()
    svc.get_leaderboard = AsyncMock(return_value=full_lb)

    result = await svc.get_my_rank(uid, LeaderboardType.GLOBAL)

    assert result.rank == 0
    assert result.percentile is None
    assert result.total_participants == 0


def test_schema_percentile_nullable():
    """MyRankResponse.percentile should accept None."""
    resp = MyRankResponse(
        rank=1, score=100.0, score_label="100 pts",
        total_participants=0, percentile=None,
    )
    assert resp.percentile is None
