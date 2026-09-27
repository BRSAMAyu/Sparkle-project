"""V3-FIX-08: post comment listing must exclude demo-cohort commenters.

Companion face to the feed fix (INV-15 family): ``GET /posts/{post_id}/comments``
returned every comment regardless of author cohort. Live DB at fix time had 0
comments, so the pollution is prospective — seeded demo accounts comment as
soon as content exists. Statement-capture technique; no database is touched.

V3-FIX-449 contract update (assertions preserved, layout re-indexed): the
endpoint now locates the post first (soft-delete gate → 404) and filters
comment authors through the feed's bidirectional block exclusion, so the
listing query is statements[1] and the caller passes a viewer.
"""

from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.community import list_post_comments


def _me():
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
    """Post lookup succeeds, comment listing returns empty — reaches statements[1]."""

    def __init__(self, post_id):
        super().__init__()
        self._post = SimpleNamespace(id=post_id)

    async def execute(self, stmt):
        self.statements.append(stmt)
        if len(self.statements) == 1:
            return SimpleNamespace(scalar_one_or_none=lambda: self._post)
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
    post_id = uuid4()
    db = _PostThenEmptyRec(post_id)

    comments = await list_post_comments(post_id=post_id, db=db, current_user=_me())

    assert comments == []
    assert len(db.statements) == 2
    # V3-FIX-449: statements[0] is now the post location with the soft-delete gate.
    post_sql = str(db.statements[0].compile()).upper()
    assert "FROM POSTS" in post_sql
    assert "DELETED_AT IS NULL" in post_sql, "post location lost the soft-delete gate (V3-FIX-449)"

    compiled = db.statements[1].compile()
    sql = str(compiled).upper()

    assert "FROM POST_COMMENTS" in sql, "statements[1] must be the comment listing query"
    assert "REGISTRATION_SOURCE" in sql, (
        "comment listing has no commenter cohort predicate — demo accounts "
        "commenting on a post surface to real users (V3-FIX-08)"
    )
    assert "NOT IN" in sql
    assert {"guest", "seed"}.issubset(_bound(compiled))


async def test_comment_listing_keeps_post_and_ordering_filters():
    post_id = uuid4()
    db = _PostThenEmptyRec(post_id)

    await list_post_comments(post_id=post_id, db=db, current_user=_me())

    sql = str(db.statements[1].compile()).upper()
    # Existing post scoping and newest-first ordering stay intact.
    assert "POST_ID" in sql
    assert "ORDER BY" in sql and "CREATED_AT" in sql
