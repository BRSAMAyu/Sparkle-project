"""V3-FIX-07 R3: friend-match public candidate pool must exclude guest/seed.

Live-DB evidence (2026-09-19 re-run): all 283 accounts are searchable_by
'everyone'; the pool head (MAX_CANDIDATES=60, ordered by last_login_at DESC /
flame_level DESC) held 58 guest + 2 seed and 0 email accounts — friend
recommendations for real users were ~100% guest/seed (guest flame=15/seed
flame=20 vs email flame=1). The query also missed ``not_deleted_filter``.

Same statement-capture technique as the leaderboard cohort tests — no DB.
"""
from uuid import uuid4

import pytest

from app.core.telemetry_boundary import EXCLUDED_COHORT_REGISTRATION_SOURCES
from app.services.friend_match_service import FriendMatchService


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return None


class _StatementCaptureDB:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()

    async def connection(self):
        raise NotImplementedError


def _bound_scalars(compiled) -> set:
    values: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            values.update(value)
        else:
            values.add(value)
    return values


@pytest.mark.asyncio
async def test_public_candidates_exclude_guest_and_seed_cohorts():
    db = _StatementCaptureDB()

    users = await FriendMatchService._load_public_candidates(
        db,
        uuid4(),
        accepted_friend_ids=set(),
        pending_user_ids=set(),
        blocked_user_ids=set(),
    )

    assert users == []
    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    sql = str(compiled).upper()

    assert "REGISTRATION_SOURCE" in sql, (
        "public candidate pool has no registration_source predicate — the "
        "guest/seed cohort (flame 15/20 vs email 1) monopolises the pool head "
        "and gets recommended to real users (V3-FIX-07 R3)"
    )
    assert "NOT IN" in sql
    assert {"guest", "seed"}.issubset(_bound_scalars(compiled)), (
        "cohort exclusion must bind exactly the guest/seed values; bound "
        f"params were: {sorted(map(repr, _bound_scalars(compiled)))}"
    )


@pytest.mark.asyncio
async def test_public_candidates_keep_soft_delete_and_visibility_filters():
    db = _StatementCaptureDB()

    await FriendMatchService._load_public_candidates(
        db,
        uuid4(),
        accepted_friend_ids=set(),
        pending_user_ids=set(),
        blocked_user_ids=set(),
    )

    sql = str(db.statements[0].compile()).upper()
    # Existing filters stay (search visibility + active).
    assert "SEARCHABLE_BY" in sql
    assert "IS_ACTIVE" in sql
    # V3-FIX-07 R3: soft-delete filter was missing entirely before.
    assert "DELETED_AT" in sql


@pytest.mark.asyncio
async def test_cohort_vocabulary_matches_telemetry_boundary_constant():
    """The pool filter must reuse the shared cohort vocabulary (D-02 style):
    word-for-word identical to the leaderboard constant."""
    assert EXCLUDED_COHORT_REGISTRATION_SOURCES == ("guest", "seed")
    from app.services.leaderboard_service import LeaderboardService

    assert tuple(EXCLUDED_COHORT_REGISTRATION_SOURCES) == (
        LeaderboardService.EXCLUDED_COHORT_REGISTRATION_SOURCES
    )
