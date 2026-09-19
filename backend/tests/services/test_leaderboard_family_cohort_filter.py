"""V3-FIX-07 regression tests: family leaderboards must exclude guest/seed.

V3-FIX-01 fixed the GLOBAL board only; its REPORT §4 flagged the same
pollution on the streak / photon / photon-weekly / weekly boards (R1/R2/R5).
Live-DB re-verification (2026-09-19, wt6): streak top-20 = 16 guest + 3 seed
+ 1 email; photon top-20 = 20/20 guest (max 1020 vs email max 50); the
current study week holds 167 guest accounts that enter the weekly board.

Same statement-capture technique as ``test_leaderboard_global_join.py`` /
``test_leaderboard_global_cohort_filter.py`` — no database is touched.

Pinned semantics (mirrors the V3-FIX-01 red test 3):
- ranking queries (the top-N entries) MUST carry ``registration_source NOT
  IN ('guest', 'seed')`` on top of the existing ``is_active`` + soft-delete
  filters (additive, not replacing);
- per-user own-score fallback queries (streak my-streak, photon my-balance,
  photon-weekly my-income) MUST stay unfiltered — a guest in experience mode
  still sees their own score, they just never appear on the board.
"""
from uuid import uuid4

import pytest

from app.schemas.leaderboard import LeaderboardRequest, LeaderboardType
from app.services.leaderboard_service import LeaderboardService

EXCLUDED_SOURCES = {"guest", "seed"}


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return None

    def scalar(self):
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


def _bound_scalars(compiled) -> set:
    """Flatten compiled bind params (incl. expanded IN values) into a set."""
    values: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            values.update(value)
        else:
            values.add(value)
    return values


def _assert_ranking_excludes_cohort(stmt, label: str) -> None:
    compiled = stmt.compile()
    topn_sql = str(compiled).upper()

    assert "REGISTRATION_SOURCE" in topn_sql, (
        f"{label} ranking query has no registration_source predicate — "
        "guest/seed accounts pollute the user-visible ranking "
        "(V3-FIX-01 REPORT §4 R1/R2/R5)"
    )
    assert "NOT IN" in topn_sql, (
        f"{label} must exclude (NOT IN) the guest/seed cohort, not select it"
    )
    assert EXCLUDED_SOURCES.issubset(_bound_scalars(compiled)), (
        f"{label} cohort exclusion must bind exactly the guest/seed values; "
        f"bound params were: {sorted(map(repr, _bound_scalars(compiled)))}"
    )
    # Existing soft filters stay additive.
    assert "IS_ACTIVE" in topn_sql
    assert "DELETED_AT" in topn_sql


@pytest.mark.asyncio
async def test_streak_topn_query_excludes_guest_and_seed():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    response = await svc._get_streak_leaderboard(
        LeaderboardRequest(type=LeaderboardType.STREAK, limit=20), uuid4()
    )

    assert response.entries == []
    assert len(db.statements) == 2
    _assert_ranking_excludes_cohort(db.statements[0], "streak board")


@pytest.mark.asyncio
async def test_streak_own_streak_fallback_is_not_cohort_filtered():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_streak_leaderboard(
        LeaderboardRequest(type=LeaderboardType.STREAK, limit=20), uuid4()
    )

    own_sql = str(db.statements[1].compile()).upper()
    assert "REGISTRATION_SOURCE" not in own_sql, (
        "own-streak fallback must stay unfiltered (guests keep seeing their "
        "own streak — V3-FIX-01 pinned semantics)"
    )
    assert "USER_STREAK_STATS.USER_ID" in own_sql


@pytest.mark.asyncio
async def test_photon_topn_query_excludes_guest_and_seed():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    response = await svc._get_photon_leaderboard(
        LeaderboardRequest(type=LeaderboardType.PHOTON, limit=20), uuid4()
    )

    assert response.entries == []
    assert len(db.statements) == 2
    _assert_ranking_excludes_cohort(db.statements[0], "photon board")


@pytest.mark.asyncio
async def test_photon_own_balance_fallback_is_not_cohort_filtered():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_photon_leaderboard(
        LeaderboardRequest(type=LeaderboardType.PHOTON, limit=20), uuid4()
    )

    own_sql = str(db.statements[1].compile()).upper()
    assert "REGISTRATION_SOURCE" not in own_sql
    assert "PHOTON_BALANCE" in own_sql


@pytest.mark.asyncio
async def test_photon_weekly_topn_query_excludes_guest_and_seed():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    response = await svc._get_photon_weekly_leaderboard(
        LeaderboardRequest(type=LeaderboardType.PHOTON_WEEKLY, limit=20), uuid4()
    )

    assert response.entries == []
    assert len(db.statements) == 2
    _assert_ranking_excludes_cohort(db.statements[0], "photon weekly board")


@pytest.mark.asyncio
async def test_photon_weekly_own_income_fallback_is_not_cohort_filtered():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_photon_weekly_leaderboard(
        LeaderboardRequest(type=LeaderboardType.PHOTON_WEEKLY, limit=20), uuid4()
    )

    own_sql = str(db.statements[1].compile()).upper()
    assert "REGISTRATION_SOURCE" not in own_sql
    assert "USER_ID" in own_sql


@pytest.mark.asyncio
async def test_weekly_topn_query_excludes_guest_and_seed():
    db = _StatementCaptureDB()
    svc = _make_service(db)

    response = await svc._get_weekly_leaderboard(
        LeaderboardRequest(type=LeaderboardType.WEEKLY, limit=20), uuid4()
    )

    assert response.entries == []
    assert len(db.statements) == 1
    _assert_ranking_excludes_cohort(db.statements[0], "weekly board")


@pytest.mark.asyncio
async def test_excluded_cohort_constant_matches_fix01_vocabulary():
    """The vocabulary must stay byte-identical with the V3-FIX-01 constant."""
    assert LeaderboardService.EXCLUDED_COHORT_REGISTRATION_SOURCES == (
        "guest",
        "seed",
    )
