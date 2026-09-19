"""V3-FIX-07 R7: public ``get_similar_users`` must bind the User join.

V3-FIX-01 REPORT §4 R7 (independent bug, non-cohort): the public
``CollaborativeFilteringService.get_similar_users`` joined ``User`` with an
ON clause that only matched ``UserSimilarity.user_id_1/2 == request.user_id``
without pinning ``User.id`` to the *other* similarity column. That is a
UserSimilarity × User cartesian product: every matching similarity row pairs
with every user row, so usernames/avatars returned for a similar user could
belong to an unrelated account, and LIMIT truncates real results.

The internal ``_get_similar_users`` (used by get_recommendations) already
binds both sides correctly — this test pins parity with it.

Note: currently dormant (user_similarity table absent from live DB,
user_item_interactions has 0 rows — 2026-09-19 re-check), which is why a
statement-level regression test is the right guard.
"""
from uuid import uuid4

import pytest

from app.schemas.recommendation import SimilarUsersRequest
from app.services.collaborative_filtering_service import CollaborativeFilteringService


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalars(self):
        return self


class _StatementCaptureDB:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()


@pytest.mark.asyncio
async def test_public_similar_users_join_binds_user_id_on_both_sides():
    db = _StatementCaptureDB()
    svc = CollaborativeFilteringService(db)

    user_id = uuid4()
    await svc.get_similar_users(
        SimilarUsersRequest(user_id=user_id, limit=20, min_common_items=3)
    )

    assert len(db.statements) == 1
    sql = str(db.statements[0].compile()).upper()

    assert "JOIN USERS ON" in sql, "statement must join User for display fields"
    assert "USERS.ID = USER_SIMILARITIES.USER_ID_2" in sql and (
        "USERS.ID = USER_SIMILARITIES.USER_ID_1" in sql
    ), (
        "public get_similar_users ON clause must pin users.id to the *other* "
        "similarity column on both disjuncts — without it the join is a "
        "UserSimilarity × User cartesian product (V3-FIX-01 §4 R7)"
    )


@pytest.mark.asyncio
async def test_public_and_internal_similar_users_have_equal_join_binding():
    """Parity: the public path must bind the join exactly like the internal
    ``_get_similar_users`` (the known-good reference implementation)."""
    db = _StatementCaptureDB()
    svc = CollaborativeFilteringService(db)
    user_id = uuid4()

    await svc.get_similar_users(
        SimilarUsersRequest(user_id=user_id, limit=20, min_common_items=3)
    )
    await svc._get_similar_users(user_id, limit=20)

    public_sql = str(db.statements[0].compile()).upper()
    internal_sql = str(db.statements[1].compile()).upper()

    for fragment in (
        "USERS.ID = USER_SIMILARITIES.USER_ID_2",
        "USERS.ID = USER_SIMILARITIES.USER_ID_1",
    ):
        assert fragment in public_sql, f"public join missing binding: {fragment}"
        assert fragment in internal_sql, f"internal join missing binding: {fragment}"
