"""V3-FIX-192: ``POST /community/posts`` must honor the requested visibility.

Evidence (wt483 T36 align read, DYNAMIC_ISSUES row V3-FIX-192): the read side
filters on ``Post.visibility`` (global feed = public only; relational scopes =
public OR friends), but the create path hard-coded ``visibility="public"`` and
ignored the request body entirely — a friends/private post could not be written,
every post was silently upgraded to public (read/write asymmetry).

Fix contract: write side gates on the request value (domain = the
``Post.visibility`` column domain ``public|friends|private``), invalid values get
a human-readable 4xx, and the absent-value default stays ``public`` (existing
product default, unchanged). Read-side filters are not touched here.

Recording-db technique (FIX-08 family style, no database touched); a real
starlette Request is built per call because ``create_post`` is rate-limited
(slowapi) — each request gets a unique peer IP so the in-memory 5/minute bucket
is never shared between tests.
"""

import json
from itertools import count
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.community import POST_VISIBILITY_VALUES, create_post
from app.models.community import Post

_PORT_SEQ = count(2)


class _RecordingDB:
    """Captures ORM objects handed to add(); commit/refresh are no-ops."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj, attribute_names=None):
        return None


def _fake_request(payload: dict) -> Request:
    body = json.dumps(payload).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/community/posts",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
        # Unique peer per request: slowapi keys the in-memory bucket by
        # "<peer>:<path>", tests must not share the 5/minute quota.
        "client": (f"10.0.0.{next(_PORT_SEQ)}", 12345),
        "server": ("server", 80),
        "scheme": "http",
    }
    return Request(scope, receive=receive)


def _me():
    return SimpleNamespace(id=uuid4(), username="real-user")


def _added_post(db: _RecordingDB) -> Post:
    assert len(db.added) == 1, "create_post must persist exactly one Post"
    post = db.added[0]
    assert isinstance(post, Post)
    return post


def test_visibility_value_domain_matches_post_column():
    """The accepted domain is exactly the Post.visibility column domain."""
    assert POST_VISIBILITY_VALUES == ("public", "friends", "private")


async def test_create_post_honors_friends_visibility():
    """A friends-only request is stored as friends, not upgraded to public."""
    db = _RecordingDB()

    await create_post(
        request=_fake_request({"content": "friends only", "visibility": "friends"}),
        current_user=_me(),
        db=db,
    )

    post = _added_post(db)
    assert post.visibility == "friends", (
        f"requested visibility=friends was stored as {post.visibility!r} — "
        "write side must not silently upgrade to public (V3-FIX-192)"
    )


async def test_create_post_honors_private_visibility():
    """A private request is stored as private."""
    db = _RecordingDB()

    await create_post(
        request=_fake_request({"content": "just me", "visibility": "private"}),
        current_user=_me(),
        db=db,
    )

    post = _added_post(db)
    assert post.visibility == "private"


async def test_create_post_keeps_public_when_requested():
    """An explicit public request stays public (no behavior change)."""
    db = _RecordingDB()

    await create_post(
        request=_fake_request({"content": "hello world", "visibility": "public"}),
        current_user=_me(),
        db=db,
    )

    post = _added_post(db)
    assert post.visibility == "public"


async def test_create_post_defaults_to_public_when_absent():
    """Default semantics preserved: no visibility field means public (existing口径)."""
    db = _RecordingDB()

    await create_post(request=_fake_request({"content": "plain post"}), current_user=_me(), db=db)

    post = _added_post(db)
    assert post.visibility == "public"


async def test_create_post_rejects_unknown_visibility_value():
    """Values outside the column domain get a human-readable 4xx, not a silent store."""
    db = _RecordingDB()

    with pytest.raises(HTTPException) as err:
        await create_post(
            request=_fake_request({"content": "hi", "visibility": "everyone"}),
            current_user=_me(),
            db=db,
        )

    assert 400 <= err.value.status_code < 500
    assert "everyone" in str(err.value.detail)
    assert db.added == [], "invalid visibility must not persist anything"


async def test_create_post_normalizes_case_and_whitespace():
    """' Public ' is an accidental spelling of public, stored normalized."""
    db = _RecordingDB()

    await create_post(
        request=_fake_request({"content": "hi", "visibility": " Public "}),
        current_user=_me(),
        db=db,
    )

    post = _added_post(db)
    assert post.visibility == "public"
