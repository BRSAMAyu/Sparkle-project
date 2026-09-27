"""V3-FIX-419: community write face must gate on soft-delete AND block like the feed read face.

Evidence (wt713 hunt1 + wt719 re-check, DYNAMIC_ISSUES row V3-FIX-419): the
comment/like write endpoints located the target post with ONLY
``_cohort_visible_post_clause`` — no ``Post.not_deleted_filter()``, no
``UserBlock`` check — while the feed read face applies both (not_deleted_filter
at get_feed entry, bidirectional block exclusion before pagination). Asymmetry:
a soft-deleted post stayed commentable/likable (counters increment on the
deleted row, so the filtered read face shows inflated counts), and either side
of an active block could still write to the other's posts and fire
``NotificationPushService`` at the blocker.

Fix contract (FIX-192 write-gate family): both write endpoints locate the post
through soft-delete + bidirectional-block + cohort predicates; a gated post is
"missing" (404), counters and notifications cannot fire past the gate. The
read face is untouched: the feed keeps its exact filter stack (verified by the
existing feed tests plus the shape assertion here).

Two techniques:
- functional: real in-memory sqlite via the ``db`` fixture — rows, counters and
  Notification rows are actually inspected (red-before-green evidence);
- statement-capture (FIX-08 family style) for the lookup SQL shape.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.community import _cohort_visible_post_clause, create_post_comment, get_feed, toggle_like_post
from app.models.community import Post, PostComment, PostLike, UserBlock
from app.models.notification import Notification
from app.models.user import User


def _me():
    """Statement-capture viewer (FIX-08 family style)."""
    return SimpleNamespace(id=uuid4(), username="real-user")


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


async def _mk_user(db, name: str) -> User:
    user = User(
        username=name,
        email=f"{name}@example.com",
        hashed_password="x",
        registration_source="email",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _mk_post(db, author: User, content: str = "hello") -> Post:
    post = Post(user_id=author.id, content=content, visibility="public", like_count=0, comment_count=0)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _count(db, model):
    return len((await db.execute(select(model))).scalars().all())


# ============ functional: soft-delete gate ============


async def test_comment_on_soft_deleted_post_is_404_and_landless(db):
    author, commenter = await _mk_user(db, "author"), await _mk_user(db, "commenter")
    post = await _mk_post(db, author)
    post.soft_delete()
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await create_post_comment(post_id=post.id, request=_FakeRequest(), current_user=commenter, db=db)

    assert err.value.status_code == 404
    assert await _count(db, PostComment) == 0, "comment must not land on a soft-deleted post"
    await db.refresh(post)
    assert (post.comment_count or 0) == 0, "comment_count must not increment on the deleted row"
    assert await _count(db, Notification) == 0, "no notification may fire past the gate"


async def test_like_on_soft_deleted_post_is_404_and_landless(db):
    author, liker = await _mk_user(db, "author"), await _mk_user(db, "liker")
    post = await _mk_post(db, author)
    post.soft_delete()
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await toggle_like_post(post_id=post.id, current_user=liker, db=db)

    assert err.value.status_code == 404
    assert await _count(db, PostLike) == 0, "like must not land on a soft-deleted post"
    await db.refresh(post)
    assert (post.like_count or 0) == 0, "like_count must not increment on the deleted row"
    assert await _count(db, Notification) == 0, "no notification may fire past the gate"


# ============ functional: bidirectional block gate ============


async def test_comment_on_author_blocked_post_is_404_and_landless(db):
    """Author blocks the commenter (forward direction of the feed guard)."""
    author, commenter = await _mk_user(db, "author"), await _mk_user(db, "commenter")
    post = await _mk_post(db, author)
    db.add(UserBlock(blocker_id=author.id, blocked_id=commenter.id))
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await create_post_comment(post_id=post.id, request=_FakeRequest(), current_user=commenter, db=db)

    assert err.value.status_code == 404
    assert await _count(db, PostComment) == 0
    await db.refresh(post)
    assert (post.comment_count or 0) == 0
    assert await _count(db, Notification) == 0, "blocker must not be notified past the gate"


async def test_comment_on_reverse_blocked_post_is_404(db):
    """Commenter blocks the author (reverse direction) — write must still gate."""
    author, commenter = await _mk_user(db, "author"), await _mk_user(db, "commenter")
    post = await _mk_post(db, author)
    db.add(UserBlock(blocker_id=commenter.id, blocked_id=author.id))
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await create_post_comment(post_id=post.id, request=_FakeRequest(), current_user=commenter, db=db)

    assert err.value.status_code == 404
    assert await _count(db, PostComment) == 0


async def test_like_under_block_either_direction_is_404(db):
    author, liker = await _mk_user(db, "author"), await _mk_user(db, "liker")
    post = await _mk_post(db, author)
    db.add(UserBlock(blocker_id=author.id, blocked_id=liker.id))
    await db.commit()

    with pytest.raises(HTTPException):
        await toggle_like_post(post_id=post.id, current_user=liker, db=db)
    assert await _count(db, PostLike) == 0
    assert await _count(db, Notification) == 0

    # Unblock, re-block in the reverse direction — same gate.
    (await db.execute(select(UserBlock))).scalars().all()[0].soft_delete()
    db.add(UserBlock(blocker_id=liker.id, blocked_id=author.id))
    await db.commit()

    with pytest.raises(HTTPException):
        await toggle_like_post(post_id=post.id, current_user=liker, db=db)
    assert await _count(db, PostLike) == 0
    await db.refresh(post)
    assert (post.like_count or 0) == 0


# ============ functional: healthy path unchanged (fix must not over-gate) ============


async def test_healthy_post_still_commentable_likable_and_notified(db):
    author, actor = await _mk_user(db, "author"), await _mk_user(db, "actor")
    post = await _mk_post(db, author)

    comment = await create_post_comment(post_id=post.id, request=_FakeRequest(), current_user=actor, db=db)
    assert comment["content"] == "hello"
    await db.refresh(post)
    assert (post.comment_count or 0) == 1

    like = await toggle_like_post(post_id=post.id, current_user=actor, db=db)
    assert like == {"liked": True, "like_count": 1}

    notes = (await db.execute(select(Notification))).scalars().all()
    assert len(notes) == 2, "healthy interactions keep reaching the author (gate is not a blanket mute)"
    assert {n.user_id for n in notes} == {author.id}


# ============ statement-capture: lookup SQL shape (FIX-08 family style) ============


async def test_like_lookup_sql_carries_softdel_and_bidirectional_block_gates():
    db = Rec()

    with pytest.raises(HTTPException) as err:
        await toggle_like_post(post_id=uuid4(), current_user=_me(), db=db)

    assert err.value.status_code == 404
    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    sql = str(compiled).upper()

    assert "FROM POSTS" in sql
    assert "DELETED_AT" in sql, "like lookup lost the soft-delete gate (V3-FIX-419)"
    assert "USER_BLOCKS" in sql, "like lookup lost the block gate (V3-FIX-419)"
    # Bidirectional: the guard must exclude authors I blocked AND authors who blocked me.
    assert "BLOCKER_ID" in sql and "BLOCKED_ID" in sql
    assert "REGISTRATION_SOURCE" in sql, "pre-existing cohort gate must stay (V3-FIX-08)"


async def test_comment_lookup_sql_carries_softdel_and_bidirectional_block_gates():
    db = Rec()

    with pytest.raises(HTTPException) as err:
        await create_post_comment(post_id=uuid4(), request=_FakeRequest(), current_user=_me(), db=db)

    assert err.value.status_code == 404
    assert len(db.statements) == 1
    sql = str(db.statements[0].compile()).upper()

    assert "FROM POSTS" in sql
    assert "DELETED_AT" in sql, "comment lookup lost the soft-delete gate (V3-FIX-419)"
    assert "USER_BLOCKS" in sql, "comment lookup lost the block gate (V3-FIX-419)"
    assert "BLOCKER_ID" in sql and "BLOCKED_ID" in sql
    assert "REGISTRATION_SOURCE" in sql


async def test_write_lookup_uses_same_block_clause_as_feed():
    """The write gate reuses the feed's block exclusion verbatim (same helper)."""
    viewer = _me()
    like_db, feed_db = Rec(), Rec()

    with pytest.raises(HTTPException):
        await toggle_like_post(post_id=uuid4(), current_user=viewer, db=like_db)

    await get_feed(page=1, limit=20, scope=None, current_user=viewer, db=feed_db)

    like_sql = str(like_db.statements[0].compile()).upper()
    feed_sql = str(feed_db.statements[0].compile()).upper()
    for marker in ("USER_BLOCKS", "BLOCKER_ID", "BLOCKED_ID", "DELETED_AT"):
        assert marker in like_sql and marker in feed_sql, (
            f"write face missing read-face gate marker {marker} — read/write asymmetry (V3-FIX-419)"
        )


# ============ read-face zero relaxation ============


async def test_feed_read_face_filter_stack_unrelaxed():
    """V3-FIX-419 touches write face only — feed keeps its full filter stack."""
    db = Rec()

    await get_feed(page=1, limit=20, scope=None, current_user=_me(), db=db)

    sql = str(db.statements[0].compile()).upper()
    assert "DELETED_AT" in sql, "feed soft-delete gate must stay"
    assert "VISIBILITY" in sql, "feed visibility gate must stay"
    assert "REGISTRATION_SOURCE" in sql, "feed cohort gate must stay"
    assert "USER_BLOCKS" in sql and "BLOCKER_ID" in sql and "BLOCKED_ID" in sql, (
        "feed bidirectional block guard must stay bidirectional"
    )


def test_cohort_clause_helper_unchanged():
    """_cohort_visible_post_clause keeps author-self OR non-cohort authors shape."""
    clause = _cohort_visible_post_clause(_me())
    sql = str(clause.compile()).upper()
    assert "POSTS.USER_ID =" in sql and " OR " in sql
    assert "REGISTRATION_SOURCE" in sql
