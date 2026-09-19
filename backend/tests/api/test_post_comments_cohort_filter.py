"""V3-FIX-08: post comment listing must exclude demo-cohort commenters.

Companion face to the feed fix (INV-15 family): ``GET /posts/{post_id}/comments``
returned every comment regardless of author cohort. Live DB at fix time had 0
comments, so the pollution is prospective — seeded demo accounts comment as
soon as content exists. Statement-capture technique; no database is touched.
"""

from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.community import list_post_comments


class _EmptyResult:
    def all(self):
        return []

    def first(self):
        return None

    def scalars(self):
        return self


class Rec:
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


async def test_comment_listing_excludes_guest_and_seed_commenters():
    db = Rec()

    comments = await list_post_comments(post_id=uuid4(), db=db)

    assert comments == []
    assert len(db.statements) == 1
    compiled = db.statements[0].compile()
    sql = str(compiled).upper()

    assert "FROM POST_COMMENTS" in sql, "statements[0] must be the comment listing query"
    assert "REGISTRATION_SOURCE" in sql, (
        "comment listing has no commenter cohort predicate — demo accounts "
        "commenting on a post surface to real users (V3-FIX-08)"
    )
    assert "NOT IN" in sql
    assert {"guest", "seed"}.issubset(_bound(compiled))


async def test_comment_listing_keeps_post_and_ordering_filters():
    db = Rec()

    await list_post_comments(post_id=uuid4(), db=db)

    sql = str(db.statements[0].compile()).upper()
    # Existing post scoping and newest-first ordering stay intact.
    assert "POST_ID" in sql
    assert "ORDER BY" in sql and "CREATED_AT" in sql
