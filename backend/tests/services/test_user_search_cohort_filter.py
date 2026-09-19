"""V3-FIX-07 R4: user search must exclude guest/seed cohort accounts.

Live-DB evidence (2026-09-19): 170 guest + 7 seed accounts, all
searchable_by 'everyone' and active — any real user's search that matches a
guest/seed username fragment surfaced demo accounts. The query also missed
``not_deleted_filter``.

Statement-capture technique; search_users issues the friendship query first,
then the search query (statement[1]).
"""
from uuid import uuid4

import pytest

from app.core.telemetry_boundary import EXCLUDED_COHORT_REGISTRATION_SOURCES
from app.services.community_service import UserSearchService


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


def _bound_scalars(compiled) -> set:
    values: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            values.update(value)
        else:
            values.add(value)
    return values


@pytest.mark.asyncio
async def test_search_users_query_excludes_guest_and_seed_cohorts():
    db = _StatementCaptureDB()

    users = await UserSearchService.search_users(db, "alice", uuid4())

    assert users == []
    assert len(db.statements) == 2
    compiled = db.statements[1].compile()
    sql = str(compiled).upper()

    assert "FROM USERS" in sql, "statement[1] must be the user search query"
    assert "REGISTRATION_SOURCE" in sql, (
        "user search has no registration_source predicate — guest/seed demo "
        "accounts are surfaced to real users (V3-FIX-07 R4)"
    )
    assert "NOT IN" in sql
    assert {"guest", "seed"}.issubset(_bound_scalars(compiled))


@pytest.mark.asyncio
async def test_search_users_keeps_soft_delete_and_match_filters():
    db = _StatementCaptureDB()

    await UserSearchService.search_users(db, "alice", uuid4())

    sql = str(db.statements[1].compile()).upper()
    assert "IS_ACTIVE" in sql
    # V3-FIX-07 R4: soft-delete filter was missing entirely before.
    assert "DELETED_AT" in sql
    # Existing username/nickname/full_name matching stays.
    assert "USERNAME" in sql
    assert "NICKNAME" in sql
    assert "FULL_NAME" in sql


def test_cohort_vocabulary_matches_telemetry_boundary_constant():
    assert EXCLUDED_COHORT_REGISTRATION_SOURCES == ("guest", "seed")
