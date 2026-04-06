from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

import app.services.capsule_share_service as capsule_share_module
from app.core.event_types import CAPSULE_CONTENT_UPDATED
from app.models.community import Friendship, FriendshipStatus
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.user import User
from app.services.capsule_share_service import CapsuleShareService


@pytest.mark.asyncio
async def test_share_to_friend_publishes_content_refresh_event(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    publish = AsyncMock()
    monkeypatch.setattr(capsule_share_module.event_bus, "publish", publish)

    friend = User(
        username="capsule_friend",
        email="capsule_friend@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    capsule = CuriosityCapsule(
        user_id=test_user.id,
        title="Capsule",
        content="content",
    )
    db_session.add_all([friend, capsule])
    await db_session.flush()
    db_session.add(
        Friendship(
            user_id=test_user.id,
            friend_id=friend.id,
            initiated_by=test_user.id,
            status=FriendshipStatus.ACCEPTED,
        )
    )
    await db_session.commit()
    await db_session.refresh(capsule)
    await db_session.refresh(friend)

    message = await CapsuleShareService().share_to_friend(
        user_id=test_user.id,
        capsule_id=capsule.id,
        friend_id=friend.id,
        db=db_session,
    )

    assert message.receiver_id == friend.id
    publish.assert_awaited_once_with(
        CAPSULE_CONTENT_UPDATED,
        {
            "event_type": CAPSULE_CONTENT_UPDATED,
            "user_id": str(test_user.id),
            "capsule_id": str(capsule.id),
            "action": "shared_to_friend",
        },
    )
