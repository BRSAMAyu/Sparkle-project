from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import app.services.capsule_share_service as capsule_share_module
from app.core.event_types import CAPSULE_CONTENT_UPDATED
from app.models.community import (
    Friendship,
    FriendshipStatus,
    Group,
    GroupMember,
    GroupMessage,
    GroupType,
    PrivateMessage,
)
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


@pytest.mark.asyncio
async def test_share_to_friend_rejects_non_owner_capsule(
    db_session,
    test_user,
) -> None:
    owner = User(
        username="capsule_owner",
        email="capsule_owner@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    friend = User(
        username="capsule_recipient",
        email="capsule_recipient@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    db_session.add_all([owner, friend])
    await db_session.flush()
    capsule = CuriosityCapsule(
        user_id=owner.id,
        title="Private Capsule",
        content="private content",
    )
    db_session.add(capsule)
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

    with pytest.raises(ValueError, match="not found"):
        await CapsuleShareService().share_to_friend(
            user_id=test_user.id,
            capsule_id=capsule.id,
            friend_id=friend.id,
            db=db_session,
        )

    messages = (
        await db_session.execute(select(PrivateMessage).where(PrivateMessage.sender_id == test_user.id))
    ).scalars().all()
    await db_session.refresh(capsule)
    assert messages == []
    assert capsule.share_count == 0


@pytest.mark.asyncio
async def test_share_to_group_rejects_non_owner_capsule(
    db_session,
    test_user,
) -> None:
    owner = User(
        username="capsule_group_owner",
        email="capsule_group_owner@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    group = Group(
        name="Study Group",
        type=GroupType.SQUAD,
    )
    db_session.add_all([owner, group])
    await db_session.flush()
    capsule = CuriosityCapsule(
        user_id=owner.id,
        title="Private Group Capsule",
        content="private group content",
    )
    db_session.add_all([
        capsule,
        GroupMember(group_id=group.id, user_id=test_user.id),
    ])
    await db_session.commit()
    await db_session.refresh(capsule)

    with pytest.raises(ValueError, match="not found"):
        await CapsuleShareService().share_to_group(
            user_id=test_user.id,
            capsule_id=capsule.id,
            group_id=group.id,
            db=db_session,
        )

    messages = (
        await db_session.execute(select(GroupMessage).where(GroupMessage.sender_id == test_user.id))
    ).scalars().all()
    await db_session.refresh(capsule)
    assert messages == []
    assert capsule.share_count == 0
