"""WT713 hunt1 TEMP evidence probe — DELETE AFTER RUN.

Write-side dual of the soft-delete / block read filters (community):
create_post_comment / like_post look up the target post with ONLY
_cohort_visible_post_clause — no Post.not_deleted_filter(), no UserBlock
check — while the feed read face applies both. Probe: soft-delete a post,
then exercise the same lookup the write endpoints use; show a deleted post
(and a block-related author's post) still passes and the comment/like write
would land + increment counters.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models.theater_candidate_bundle  # noqa: F401
from app.models.base import Base
from app.models.community import Post, UserBlock
from app.models.user import User


def _cohort_visible_post_clause(current_user: User):
    """Verbatim copy of app/api/v1/community.py:310 (the ONLY post filter the
    comment/like write endpoints apply)."""
    from sqlalchemy import or_

    visible_authors = select(User.id).where(User.registration_source.not_in(("guest", "seed")))
    return or_(
        Post.user_id == current_user.id,
        Post.user_id.in_(visible_authors),
    )


async def main() -> int:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()

    author = User(id=uuid4(), username="author", email="a@x.io", hashed_password="t", registration_source="email")
    commenter = User(id=uuid4(), username="commenter", email="c@x.io", hashed_password="t", registration_source="email")
    db.add_all([author, commenter])
    await db.flush()

    post = Post(user_id=author.id, content="hello", visibility="public", comment_count=0, like_count=0)
    db.add(post)
    await db.flush()

    # Author blocks the commenter (read face hides author's posts from commenter).
    block = UserBlock(blocker_id=author.id, blocked_id=commenter.id)
    db.add(block)
    await db.flush()

    # Soft-delete the post (delete_post endpoint path: post.soft_delete()).
    post.soft_delete()
    await db.commit()

    # The exact lookup create_post_comment / like_post perform:
    found = (
        await db.execute(select(Post).where(Post.id == post.id, _cohort_visible_post_clause(commenter)))
    ).scalar_one_or_none()
    print("deleted+blocked post visible to comment/like write path:", found is not None)

    # Block active?
    blk = (
        await db.execute(
            select(UserBlock).where(
                UserBlock.blocker_id == author.id, UserBlock.blocked_id == commenter.id, UserBlock.not_deleted_filter()
            )
        )
    ).scalar_one_or_none()
    print("active block relationship in place:", blk is not None)

    # For contrast: the feed read face filters — prove the asymmetry.
    feed_row = (
        await db.execute(
            select(Post).where(Post.id == post.id, Post.not_deleted_filter(), _cohort_visible_post_clause(commenter))
        )
    ).scalar_one_or_none()
    print("same post visible to feed read face:", feed_row is not None)

    await db.close()
    await engine.dispose()

    if found is not None and blk is not None and feed_row is None:
        print("RED: write face accepts soft-deleted + block-hidden posts the read face filters")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
