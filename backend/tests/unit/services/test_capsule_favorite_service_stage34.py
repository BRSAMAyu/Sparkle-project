from __future__ import annotations

import pytest

from app.models.capsule_favorite import CapsuleFavorite
from app.models.curiosity_capsule import CuriosityCapsule, DepthLevel
from app.models.user import User
from app.services.capsule_favorite_service import CapsuleFavoriteService


@pytest.mark.asyncio
async def test_get_preferences_isolates_other_users_capsules(db_session, test_user) -> None:
    other_user = User(
        username="other_capsule_user",
        email="other_capsule_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(other_user)
    await db_session.flush()

    own_capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="Own capsule",
        content="content",
        related_subject="physics",
        depth_level=DepthLevel.DEEP,
    )
    other_capsule = CuriosityCapsule(
        user_id=other_user.id,
        title="Other capsule",
        content="content",
        related_subject="chemistry",
        depth_level=DepthLevel.SHALLOW,
    )
    db_session.add_all([own_capsule, other_capsule])
    await db_session.flush()

    db_session.add_all(
        [
            CapsuleFavorite(
                user_id=test_user.id,
                capsule_id=own_capsule.id,
                note="keep",
            ),
            CapsuleFavorite(
                user_id=test_user.id,
                capsule_id=other_capsule.id,
                note="should_not_leak",
            ),
            CapsuleFavorite(
                user_id=other_user.id,
                capsule_id=other_capsule.id,
                note="other_note",
            ),
        ]
    )
    await db_session.commit()

    preferences = await CapsuleFavoriteService().get_preferences(test_user.id, db_session)

    assert preferences["favorite_count"] == 1
    assert preferences["content_depth_preference"] == "deep"
    assert preferences["subject_affinity"] == ["physics"]
    assert preferences["recent_notes"] == ["keep"]
