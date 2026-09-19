"""V3-FIX-01: the GLOBAL leaderboard must exclude guest/seed cohort accounts.

B-02 F1 evidence (live DB, 2026-09-19): 166 guest + 7 seed accounts seeded by
``guest_seed_service`` (flame=15, mastery rows, 944 achievements, streak
30/45) held 100% of the global top-100 (top_score 132.5) while all 75 real
email users scored ≤ 10.0 and were structurally pushed outside the top 168.

D20 decision: keep the guest experience mode, but seeded/guest cohort
accounts must never surface in user-visible aggregation. Minimal fix: the
global top-N query filters ``registration_source NOT IN ('guest', 'seed')``
on top of the existing ``is_active`` + ``not_deleted_filter`` semantics.

These tests follow the statement-capture pattern of
``tests/services/test_leaderboard_global_join.py`` (no DB needed): the
top-N query is compiled and inspected, because cohort exclusion is a SQL
predicate — the DB, not Python, owns the filtering.
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


@pytest.mark.asyncio
async def test_global_topn_query_excludes_guest_and_seed_cohorts():
    """The global top-N ranking statement must carry the cohort exclusion."""
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_global_leaderboard(
        LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=50), uuid4()
    )

    assert len(db.statements) >= 1
    topn_sql = str(db.statements[0].compile()).upper()

    assert "REGISTRATION_SOURCE" in topn_sql, (
        "global top-N query has no registration_source predicate — guest/seed "
        "seed accounts (B-02 F1: 100% of top-100, top_score 132.5) pollute the "
        "user-visible ranking"
    )
    assert "NOT IN" in topn_sql, (
        "registration_source predicate must exclude (NOT IN) the guest/seed "
        "cohort, not select it"
    )

    compiled = db.statements[0].compile()
    assert EXCLUDED_SOURCES.issubset(_bound_scalars(compiled)), (
        f"cohort exclusion must bind exactly the guest/seed values; "
        f"bound params were: {sorted(map(repr, _bound_scalars(compiled)))}"
    )


@pytest.mark.asyncio
async def test_existing_soft_filters_are_preserved():
    """The cohort exclusion must be additive: is_active + not_deleted stay."""
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_global_leaderboard(
        LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=50), uuid4()
    )

    topn_sql = str(db.statements[0].compile()).upper()
    assert "IS_ACTIVE" in topn_sql
    assert "DELETED_AT" in topn_sql


@pytest.mark.asyncio
async def test_own_score_fallback_is_not_cohort_filtered():
    """The per-user score fallback (statement[2] when the user is outside the
    top-N) stays unfiltered on purpose: a guest in experience mode may still
    see their own score without appearing in the ranking."""
    db = _StatementCaptureDB()
    svc = _make_service(db)

    await svc._get_global_leaderboard(
        LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=50), uuid4()
    )

    assert len(db.statements) == 2
    fallback_sql = str(db.statements[1].compile()).upper()
    assert "REGISTRATION_SOURCE" not in fallback_sql
