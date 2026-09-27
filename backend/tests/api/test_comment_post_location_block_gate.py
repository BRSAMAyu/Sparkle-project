"""V3-FIX-465: the comment face's POST LOCATION must pass the block gate too.

Evidence (V3-FIX-465 DYNAMIC_ISSUES row, wt741 residual, coordinator ruling
"补闸"): after V3-FIX-449 the ``list_post_comments`` post lookup carries
``Post.not_deleted_filter()`` only — a post hidden by the feed's bidirectional
``UserBlock`` gate (viewer blocked the author, or the author blocked the
viewer, either direction) stays reachable through ``GET /posts/{post_id}/comments``:
third-party comments keep coming back and post existence can be probed by id
(side channel = comment-line visibility). Comment authors themselves are
already bidirectionally filtered (449 face); this closes the post-level
location: same gate, same wordlist (``_active_block_exclusion_clause``),
404 semantics identical in shape to the soft-delete gate.

Red-before-green: a feed-hidden post answered 200 with its comment list;
after the fix it reads as missing (404) — write face / feed parity.

Two techniques, mirroring test_comment_faces_gates_softdel_block.py:
- functional: real in-memory sqlite via the ``db`` fixture (rows actually
  inspected, red evidence is a runtime assertion);
- statement-capture (FIX-08 family style) for the post-location SQL shape.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.community import list_post_comments
from app.models.community import Post, PostComment, UserBlock
from app.models.user import User


def _me():
    """Statement-capture viewer (FIX-08 family style)."""
    return SimpleNamespace(id=uuid4(), username="real-user")


class _EmptyResult:
    def all(self):
        return []

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self


class _PostThenEmptyRec:
    """Post lookup succeeds, everything after returns empty — reaches the
    comment-listing query so its SQL shape can be pinned."""

    def __init__(self, post_id):
        self.statements = []
        self._post = SimpleNamespace(id=post_id)

    async def execute(self, stmt):
        self.statements.append(stmt)
        if len(self.statements) == 1:
            return SimpleNamespace(scalar_one_or_none=lambda: self._post)
        return _EmptyResult()


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


# ============ post location: bidirectional block gate (404, softdel-gate shape) ============


async def test_list_comments_on_post_of_author_i_blocked_is_404(db):
    """Forward direction: viewer blocked the post author — comment line reads as missing."""
    author, viewer = await _mk_user(db, "author"), await _mk_user(db, "viewer")
    third = await _mk_user(db, "third")
    post = await _mk_post(db, author)
    await _mk_comment(db, third, post, "third party speaks")
    db.add(UserBlock(blocker_id=viewer.id, blocked_id=author.id))
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert err.value.status_code == 404, (
        "feed-hidden post (I blocked the author) must read as missing on the comment line — "
        "existence probe via post_id is a side channel otherwise"
    )


async def test_list_comments_on_post_of_author_who_blocked_me_is_404(db):
    """Reverse direction: the post author blocked the viewer — same 404."""
    author, viewer = await _mk_user(db, "author"), await _mk_user(db, "viewer")
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post)
    db.add(UserBlock(blocker_id=author.id, blocked_id=viewer.id))
    await db.commit()

    with pytest.raises(HTTPException) as err:
        await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert err.value.status_code == 404, "bidirectional: author-blocked-me hides the post on the comment line too"


async def test_list_comments_lifted_block_restores_comment_line(db):
    """A soft-deleted (lifted) block must not keep gating the post line — feed unblock parity."""
    author, viewer = await _mk_user(db, "author"), await _mk_user(db, "viewer")
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post, "visible again")
    block = UserBlock(blocker_id=viewer.id, blocked_id=author.id)
    db.add(block)
    await db.commit()
    block.soft_delete()
    await db.commit()

    comments = await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert [c["content"] for c in comments] == ["visible again"]


async def test_list_comments_unrelated_post_line_untouched(db):
    """Positive control: no block relation — comment line keeps working (no over-hide)."""
    author, viewer = await _mk_user(db, "author"), await _mk_user(db, "viewer")
    post = await _mk_post(db, author)
    await _mk_comment(db, author, post, "a")

    comments = await list_post_comments(post_id=post.id, current_user=viewer, db=db)

    assert [c["content"] for c in comments] == ["a"]


# ============ statement-capture: post-location SQL shape (FIX-08 family style) ============


async def test_list_comments_post_lookup_sql_carries_block_gate():
    """The post location query itself must carry the bidirectional UserBlock exclusion."""
    post_id = uuid4()
    db = _PostThenEmptyRec(post_id)

    comments = await list_post_comments(post_id=post_id, current_user=_me(), db=db)

    assert comments == []
    sql = str(db.statements[0].compile()).upper()
    assert "FROM POSTS" in sql, "statements[0] must be the post location query"
    assert "USER_BLOCKS" in sql, "post location lost the block gate (V3-FIX-465)"
    # Bidirectional, same wordlist as the feed gate.
    assert "BLOCKER_ID" in sql and "BLOCKED_ID" in sql
