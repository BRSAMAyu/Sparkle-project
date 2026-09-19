"""V3-FIX-08: the public community feed must exclude guest/seed cohort authors.

Live-DB evidence (2026-09-19, re-run of B-02X INV-15): every undeleted public
post (341 total) is authored by a demo-cohort account (336 guest + 5 seed);
email users authored 0 posts. The global ``GET /community/feed`` branch
filtered only on ``visibility == 'public'``, so real users saw a 100%
demo-cohort feed.

Statement-capture technique (FIX-07 family style); the global feed issues a
single posts query (statements[0]). Relational scopes (squad/goal_mates/
following) are explicit-relationship faces and must stay un-cohort-filtered
(same boundary FIX-07 drew for friend lists).
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.v1.community import (
    FEED_EXAMPLE_CONTENT_SOURCES as SLOT,
    _excluded_feed_cohorts,
    get_feed,
)
from app.core.telemetry_boundary import (
    EXCLUDED_COHORT_REGISTRATION_SOURCES as COHORT_BLOCKLIST,
)


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalars(self):
        return self


class Rec:
    """Statement capture: records every execute() call."""

    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()


def _bound(compiled) -> set:
    out: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            out.update(value)
        else:
            out.add(value)
    return out


def _me():
    return SimpleNamespace(id=uuid4(), username="real-user")


async def test_global_feed_excludes_guest_and_seed_authors():
    db = Rec()

    posts = await get_feed(page=1, limit=20, scope=None, current_user=_me(), db=db)

    assert posts == []
    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    sql = str(compiled).upper()

    assert "FROM POSTS" in sql, "statements[0] must be the feed posts query"
    assert "REGISTRATION_SOURCE" in sql, (
        "global feed has no author cohort predicate — guest/seed demo posts "
        "surface to real users (V3-FIX-08, INV-15)"
    )
    assert "NOT IN" in sql
    assert {"guest", "seed"}.issubset(_bound(compiled))


async def test_global_feed_keeps_visibility_and_soft_delete_filters():
    db = Rec()

    await get_feed(page=1, limit=20, scope=None, current_user=_me(), db=db)

    sql = str(db.statements[0].compile()).upper()
    assert "VISIBILITY" in sql
    assert "DELETED_AT" in sql
    # Pagination ordering stays intact.
    assert "ORDER BY" in sql and "CREATED_AT" in sql


async def test_global_feed_keeps_self_posts_visible():
    """Author-self branch: a demo-cohort viewer still sees their own posts."""
    db = Rec()

    await get_feed(page=1, limit=20, scope=None, current_user=_me(), db=db)

    sql = str(db.statements[0].compile()).upper()
    # or_(posts.user_id == :self, posts.user_id IN (non-cohort authors))
    assert "POSTS.USER_ID =" in sql, (
        "cohort filter must keep self-authored posts visible "
        "(FIX-07 parity: viewers see their own content, it just does not aggregate)"
    )
    assert " OR " in sql


@pytest.mark.parametrize("scope", ["squad", "goal_mates", "following"])
async def test_relational_scopes_stay_unfiltered(scope):
    """Explicit-relationship faces keep relational semantics (no cohort cut)."""
    db = Rec()

    await get_feed(page=1, limit=20, scope=scope, current_user=_me(), db=db)

    sql = str(db.statements[0].compile()).upper()
    assert "REGISTRATION_SOURCE" not in sql, (
        f"scope={scope} is a relational face — adding a cohort cut here would "
        "change explicit-relationship semantics (documented boundary)"
    )


def test_example_content_switch_defaults_to_off():
    """产品裁决槽（V3-FIX-08）：默认无任何 cohort 被回投公开 feed（D20 口径）。"""
    assert SLOT == ()
    assert _excluded_feed_cohorts() == COHORT_BLOCKLIST
    assert COHORT_BLOCKLIST == ("guest", "seed")


def test_example_content_switch_admits_only_named_source(monkeypatch):
    """Flip slot admits ONLY the named cohort (e.g. badged official examples)."""
    monkeypatch.setattr("app.api.v1.community.FEED_EXAMPLE_CONTENT_SOURCES", ("seed",))
    assert _excluded_feed_cohorts() == ("guest",)
