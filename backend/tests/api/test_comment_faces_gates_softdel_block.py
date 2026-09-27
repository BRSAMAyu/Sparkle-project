"""V3-FIX-449: comment read/delete faces must gate like the 419 write face.

Evidence (wt733 DYNAMIC_ISSUES row V3-FIX-449, code-read on 419@59291208 base):
``list_post_comments`` located the post with NO predicate at all — a
soft-deleted post kept serving its comment list (read half of the 419 counter
pollution family) — and comment authors were filtered by the cohort wordlist
only, with no bidirectional ``UserBlock`` exclusion even though the feed hides
the same authors bidirectionally. ``delete_post_comment`` fetched the counter
post with a bare ``select(Post).where(Post.id == post_id)`` and decremented
``comment_count`` on soft-deleted rows (delete half of the same family).

Fix contract (419 isomorphic, per wt733 ruling in WT733-WRITE419 notes §5):
- list face: post location reuses ``Post.not_deleted_filter()`` — a gated post
  is "missing" (404), same as the write face; comment authors go through the
  feed's bidirectional block exclusion (shared helper, comment-author column);
- delete face: the counter decrement only applies to ACTIVE post rows
  (``not_deleted_filter`` on the counter lookup); the delete action itself
  stays available on soft-deleted posts (explicit wt733 ruling — do not
  widen the gate into a 404 there).

Two techniques, mirroring test_post_write_gates_softdel_block.py:
- functional: real in-memory sqlite via the ``db`` fixture — rows, counters
  and visibility are actually inspected (red-before-green evidence);
- statement-capture (FIX-08 family style) for the lookup SQL shape.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.community import delete_post_comment, get_feed, list_post_comments
from app.models.community import Post, PostComment, UserBlock
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


class _PostThenEmptyRec(Rec):
    """Post lookup succeeds, everything after returns empty — reaches the
    comment-listing query so its SQL shape can be pinned."""

    def __init__(self, post_id):
        super().__init__()
        self._post = SimpleNamespace(id=post_id)

    async def execute(self, stmt):
        self.statements.append(stmt)
        if len(self.statements) == 1:
            return SimpleNamespace(scalar_one_or_none=lambda: self._post)
        return _EmptyResult()


class _CommentThenNoPostRec:
    """Comment lookup returns the given comment, the counter post lookup
    returns None — reaches the counter query of delete_post_comment."""

    def __init__(self, comment):
        self._comment = comment
        self.statements = []
        self.deleted = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        if len(self.statements) == 1:
            return SimpleNamespace(scalar_one_or_none=lambda: self._comment)
        return _EmptyResult()

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commits += 1


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


async def _mk_comment(db, author: User, post: Post, content: str = "nice") -> PostComment:
    comment = PostComment(user_id=author.id, post_id=post.id, content=content)
    db.add(comment)
    post.comment_count = (post.comment_count or 0) + 1
    await db.commit()
    await db.refresh(comment)
    return comment


# ============ list face: soft-delete gate ============


async def test_list_comments_on_soft_deleted_post_is_404(db):
    author, viewer = await _mk_user(db, "author"), await _mk_user(db, "viewer")
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post)
    post.soft_delete()
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert err.value.status_code == 404, "soft-deleted post must read as missing (419 same ruling)"


async def test_list_comments_on_missing_post_is_404(db):
    viewer = await _mk_user(db, "viewer")

    with pytest.raises(HTTPException) as err:
        await list_post_comments(post_id=uuid4(), current_user=viewer, db=db)

    assert err.value.status_code == 404


# ============ list face: bidirectional block exclusion of comment authors ============


async def test_list_comments_hides_comment_of_author_i_blocked(db):
    """Forward direction: viewer blocked the commenter — comment hidden (feed parity)."""
    author, viewer, commenter = (
        await _mk_user(db, "author"),
        await _mk_user(db, "viewer"),
        await _mk_user(db, "commenter"),
    )
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post, "author speaks")
    await _mk_comment(db, commenter, post, "blocked commenter speaks")
    db.add(UserBlock(blocker_id=viewer.id, blocked_id=commenter.id))
    await db.commit()

    comments = await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert [c["content"] for c in comments] == ["author speaks"], (
        "comment of an author I blocked must not surface (feed hides the same author)"
    )


async def test_list_comments_hides_comment_of_author_who_blocked_me(db):
    """Reverse direction: the commenter blocked the viewer — comment still hidden."""
    author, viewer, commenter = (
        await _mk_user(db, "author"),
        await _mk_user(db, "viewer"),
        await _mk_user(db, "commenter"),
    )
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post, "author speaks")
    await _mk_comment(db, commenter, post, "reverse-blocked commenter speaks")
    db.add(UserBlock(blocker_id=commenter.id, blocked_id=viewer.id))
    await db.commit()

    comments = await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert [c["content"] for c in comments] == ["author speaks"], (
        "comment of an author who blocked me must not surface (bidirectional, not cohort-only)"
    )


async def test_list_comments_soft_deleted_block_row_restores_comment(db):
    """A soft-deleted (lifted) block must not keep gating — same as feed unblock."""
    author, viewer, commenter = (
        await _mk_user(db, "author"),
        await _mk_user(db, "viewer"),
        await _mk_user(db, "commenter"),
    )
    post = await _mk_post(db, author)
    await _mk_comment(db, commenter, post, "unblocked again")
    block = UserBlock(blocker_id=viewer.id, blocked_id=commenter.id)
    db.add(block)
    await db.commit()
    block.soft_delete()
    await db.commit()

    comments = await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert [c["content"] for c in comments] == ["unblocked again"]


async def test_list_comments_healthy_post_shows_all_commenters(db):
    """Positive control: the new gates must not over-hide unrelated commenters."""
    author, viewer = await _mk_user(db, "author"), await _mk_user(db, "viewer")
    other = await _mk_user(db, "other")
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post, "a")
    await _mk_comment(db, other, post, "b")

    comments = await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert sorted(c["content"] for c in comments) == ["a", "b"]


# ============ delete face: counter decrement only on active post rows ============


async def test_delete_comment_on_soft_deleted_post_keeps_counter(db):
    """wt733 ruling: delete action stays available; soft-deleted row keeps its count."""
    author = await _mk_user(db, "author")
    post = await _mk_post(db, author)
    comment = await _mk_comment(db, author, post)
    assert (post.comment_count or 0) == 1
    post.soft_delete()
    await db.commit()

    result = await delete_post_comment(post_id=post.id, comment_id=comment.id, current_user=author, db=db)

    assert result == {"deleted": True}, "delete action itself stays available (wt733 ruling)"
    assert (await db.execute(select(PostComment))).scalars().all() == [], "comment row is gone"
    await db.refresh(post)
    assert (post.comment_count or 0) == 1, "comment_count must not decrement on the deleted row"


async def test_delete_comment_on_active_post_still_decrements(db):
    """Positive control: healthy-path deletion keeps decrementing the counter."""
    author = await _mk_user(db, "author")
    post = await _mk_post(db, author)
    comment = await _mk_comment(db, author, post)

    result = await delete_post_comment(post_id=post.id, comment_id=comment.id, current_user=author, db=db)

    assert result == {"deleted": True}
    await db.refresh(post)
    assert (post.comment_count or 0) == 0


# ============ statement-capture: lookup SQL shape (FIX-08 family style) ============


async def test_list_comments_post_lookup_sql_carries_softdel_gate():
    post_id = uuid4()
    db = _PostThenEmptyRec(post_id)

    comments = await list_post_comments(post_id=post_id, current_user=_me(), db=db)

    assert comments == []
    assert len(db.statements) == 2
    sql = str(db.statements[0].compile()).upper()
    assert "FROM POSTS" in sql, "statements[0] must be the post location query"
    # "DELETED_AT IS NULL" (not_deleted_filter) — the column also appears in the
    # SELECT list of any select(Post), so pin the WHERE-clause gate itself.
    assert "DELETED_AT IS NULL" in sql, "list face lost the soft-delete gate (V3-FIX-449)"


async def test_list_comments_comment_sql_carries_bidirectional_block_and_cohort():
    post_id = uuid4()
    db = _PostThenEmptyRec(post_id)

    await list_post_comments(post_id=post_id, current_user=_me(), db=db)

    sql = str(db.statements[1].compile()).upper()
    assert "FROM POST_COMMENTS" in sql
    assert "USER_BLOCKS" in sql, "comment listing lost the block gate (V3-FIX-449)"
    # Bidirectional: exclude authors I blocked AND authors who blocked me.
    assert "BLOCKER_ID" in sql and "BLOCKED_ID" in sql
    assert "REGISTRATION_SOURCE" in sql, "pre-existing cohort gate must stay (V3-FIX-08)"
    assert "NOT IN" in sql


async def test_list_comments_block_clause_shares_feed_helper_shape():
    """The comment face reuses the feed's block exclusion (same helper, author column)."""
    viewer = _me()
    list_db, feed_db = _PostThenEmptyRec(uuid4()), Rec()

    await list_post_comments(post_id=list_db._post.id, current_user=viewer, db=list_db)
    await get_feed(page=1, limit=20, scope=None, current_user=viewer, db=feed_db)

    list_sql = str(list_db.statements[1].compile()).upper()
    feed_sql = str(feed_db.statements[0].compile()).upper()
    for marker in ("USER_BLOCKS", "BLOCKER_ID", "BLOCKED_ID"):
        assert marker in list_sql and marker in feed_sql, (
            f"comment face missing read-face gate marker {marker} — read asymmetry (V3-FIX-449)"
        )


async def test_delete_comment_counter_lookup_sql_carries_softdel_gate():
    viewer = _me()
    comment = SimpleNamespace(id=uuid4(), post_id=uuid4(), user_id=viewer.id)
    db = _CommentThenNoPostRec(comment)

    result = await delete_post_comment(post_id=comment.post_id, comment_id=comment.id, current_user=viewer, db=db)

    assert result == {"deleted": True}
    assert len(db.statements) == 2
    assert "FROM POST_COMMENTS" in str(db.statements[0].compile()).upper()
    sql = str(db.statements[1].compile()).upper()
    assert "FROM POSTS" in sql, "statements[1] must be the counter post lookup"
    assert "DELETED_AT IS NULL" in sql, (
        "counter decrement reaches soft-deleted rows — delete half of the 419 counter pollution (V3-FIX-449)"
    )
