"""V3-FIX-08: interactions with demo-cohort posts are blocked for real users.

Defense-in-depth companion to the feed fix (INV-15 family): once the feed
hides guest/seed posts, a stale post UUID reaching ``POST /posts/{post_id}/like``
or ``POST /posts/{post_id}/comments`` must behave exactly like a deleted post
(404) instead of resurrecting demo content via like-count/comment-count.
Author-self stays allowed (FIX-07 parity: own content stays manageable).

Statement-capture technique; no database is touched.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.community import create_post_comment, toggle_like_post


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self


class Rec:
    def __init__(self):
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()


class _FakeRequest:
    async def json(self):
        return {"content": "hello"}


def _me():
    return SimpleNamespace(id=uuid4(), username="real-user")


def _bound(compiled) -> set:
    out: set = set()
    for value in (compiled.params or {}).values():
        if isinstance(value, (list, tuple, set)):
            out.update(value)
        else:
            out.add(value)
    return out


async def test_toggle_like_treats_cohort_posts_as_missing():
    db = Rec()

    with pytest.raises(HTTPException) as err:
        await toggle_like_post(post_id=uuid4(), current_user=_me(), db=db)

    assert err.value.status_code == 404
    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    sql = str(compiled).upper()

    assert "FROM POSTS" in sql
    assert "REGISTRATION_SOURCE" in sql, (
        "like toggle fetches the post without the author cohort predicate — "
        "stale UUIDs keep demo posts interactive for real users (V3-FIX-08)"
    )
    assert "NOT IN" in sql
    assert {"guest", "seed"}.issubset(_bound(compiled))


async def test_create_comment_treats_cohort_posts_as_missing():
    db = Rec()

    with pytest.raises(HTTPException) as err:
        await create_post_comment(
            post_id=uuid4(), request=_FakeRequest(), current_user=_me(), db=db
        )

    assert err.value.status_code == 404
    assert len(db.statements) == 1
    sql = str(db.statements[0].compile()).upper()

    assert "FROM POSTS" in sql
    assert "REGISTRATION_SOURCE" in sql
    assert "NOT IN" in sql


async def test_interaction_guard_keeps_self_posts_manageable():
    """Author-self branch: owners (incl. demo-cohort owners) keep their posts."""
    db = Rec()

    with pytest.raises(HTTPException):
        await toggle_like_post(post_id=uuid4(), current_user=_me(), db=db)

    sql = str(db.statements[0].compile()).upper()
    # or_(posts.user_id == :self, posts.user_id IN (non-cohort authors))
    assert "POSTS.USER_ID =" in sql
    assert " OR " in sql
