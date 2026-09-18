"""Regression tests for gamification-eval P1-3 (global leaderboard 500).

Two defects in ``_get_global_leaderboard``:

1. ``user_score_q`` selects only aggregate expressions (no ``User`` entity
   columns), so SQLAlchemy cannot infer the implicit left side of the
   ``outerjoin(UserNodeStatus, ...)`` chain and raises at execution time::

       sqlalchemy.exc.InvalidRequestError: Don't know how to join to
       UserNodeStatus. Please use the .select_from() method ...

   It triggers whenever the current user is outside the top-N rows — which is
   why GET /leaderboards/summary (limit=10) 500'd consistently.

2. The node/achievement counts were plain ``count(...)`` over a three-way
   outer join, i.e. counted the cartesian product (nodes x achievements),
   inflating every entry's stats (observed: everyone at 276/276).

Both queries must compile with an explicit ``select_from(User)`` and count
``DISTINCT`` entity keys.
"""
from datetime import UTC
from uuid import uuid4

import pytest

from app.schemas.leaderboard import LeaderboardRequest, LeaderboardType
from app.services.leaderboard_service import LeaderboardService


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None


class _StatementCaptureDB:
    """Minimal async-session stand-in that records every executed statement."""

    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()


def _make_service(db):
    svc = LeaderboardService.__new__(LeaderboardService)
    svc.db = db
    return svc


@pytest.mark.asyncio
async def test_global_leaderboard_queries_compile_with_explicit_left_side():
    db = _StatementCaptureDB()
    svc = _make_service(db)
    # Empty rows force the user_score_q fallback (the statement that used to
    # raise InvalidRequestError for any user outside the top-N).
    response = await svc._get_global_leaderboard(
        LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=10), uuid4()
    )

    assert response.entries == []
    assert len(db.statements) == 2

    for stmt in db.statements:
        # Invokes the ORM compile state factory — the exact step that raised
        # "Don't know how to join to UserNodeStatus" before the fix.
        compiled = stmt.compile()
        sql = str(compiled)
        assert "FROM users" in sql
        # select_from(User) pins the left side explicitly.
        assert "LEFT OUTER JOIN user_node_status" in sql


@pytest.mark.asyncio
async def test_global_leaderboard_counts_are_distinct_not_cartesian():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_global_leaderboard(
        LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=10), uuid4()
    )

    top_sql = str(db.statements[0].compile()).upper()
    assert "COUNT(DISTINCT" in top_sql, (
        "node/achievement counts must be COUNT(DISTINCT ...) — plain counts "
        "multiply across the outer-join cartesian product"
    )


@pytest.mark.asyncio
async def test_get_summary_dispatches_all_boards():
    """get_summary (endpoint behind /leaderboards/summary) fans out to every
    board; the global board must not raise InvalidRequestError mid-fanout."""
    from unittest.mock import AsyncMock

    from app.schemas.leaderboard import (
        LeaderboardEntry,
        LeaderboardPeriod,
        LeaderboardResponse,
    )

    def _board_response(request, _user_id):
        from datetime import datetime

        return LeaderboardResponse(
            type=request.type,
            title="t",
            entries=[
                LeaderboardEntry(
                    rank=1,
                    user_id=uuid4(),
                    username="u",
                    score=1.0,
                    score_label="1",
                )
            ],
            my_rank=1,
            my_score=1.0,
            total_participants=1,
            last_updated=datetime.now(UTC),
            period=LeaderboardPeriod.ALL_TIME,
        )

    db = _StatementCaptureDB()
    svc = _make_service(db)
    svc._get_global_leaderboard = AsyncMock(side_effect=_board_response)
    svc._get_friends_leaderboard = AsyncMock(side_effect=_board_response)
    svc._get_weekly_leaderboard = AsyncMock(side_effect=_board_response)
    svc._get_streak_leaderboard = AsyncMock(side_effect=_board_response)
    svc._get_my_stats = AsyncMock(return_value={"nodes": 0, "achievements": 0})

    summary = await svc.get_summary(uuid4())

    assert summary is not None
    svc._get_global_leaderboard.assert_awaited_once()
