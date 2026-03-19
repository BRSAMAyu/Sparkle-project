import pytest
from sqlalchemy import func, or_, select

from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.community import (
    Friendship,
    FriendshipStatus,
    GroupMember,
    GroupMessage,
    GroupTask,
    MessageFavorite,
    MessageType,
    PrivateMessage,
)
from app.models.user import User
from app.services.guest_seed_service import seed_guest_user_data


@pytest.mark.asyncio
async def test_guest_seed_populates_rich_community_graph(db_session):
    guest = User(
        username="guest_seed_test",
        email="guest_seed_test@guest.local",
        hashed_password="hashed",
        password_login_enabled=False,
        nickname="访客",
        registration_source="guest",
        is_active=True,
    )
    db_session.add(guest)
    await db_session.flush()

    await seed_guest_user_data(db_session, guest)
    await db_session.commit()

    accepted_friendships = await db_session.scalar(
        select(func.count(Friendship.id)).where(
            Friendship.status == FriendshipStatus.ACCEPTED,
            or_(Friendship.user_id == guest.id, Friendship.friend_id == guest.id),
        )
    )
    pending_friendships = await db_session.scalar(
        select(func.count(Friendship.id)).where(
            Friendship.status == FriendshipStatus.PENDING,
            or_(Friendship.user_id == guest.id, Friendship.friend_id == guest.id),
        )
    )
    joined_groups = await db_session.scalar(
        select(func.count(GroupMember.id)).where(GroupMember.user_id == guest.id)
    )
    group_messages = await db_session.scalar(
        select(func.count(GroupMessage.id)).where(
            GroupMessage.group_id.in_(
                select(GroupMember.group_id).where(GroupMember.user_id == guest.id)
            )
        )
    )
    group_task_types = await db_session.scalar(
        select(func.count(GroupTask.id)).where(
            GroupTask.group_id.in_(
                select(GroupMember.group_id).where(GroupMember.user_id == guest.id)
            )
        )
    )
    private_messages = await db_session.scalar(
        select(func.count(PrivateMessage.id)).where(
            or_(PrivateMessage.sender_id == guest.id, PrivateMessage.receiver_id == guest.id)
        )
    )
    favorites = await db_session.scalar(
        select(func.count(MessageFavorite.id)).where(MessageFavorite.user_id == guest.id)
    )
    active_partnerships = await db_session.scalar(
        select(func.count(AccountabilityPartnership.id)).where(
            AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
            or_(
                AccountabilityPartnership.initiator_id == guest.id,
                AccountabilityPartnership.partner_id == guest.id,
            ),
        )
    )
    pending_partnerships = await db_session.scalar(
        select(func.count(AccountabilityPartnership.id)).where(
            AccountabilityPartnership.status == AccountabilityStatus.PENDING,
            or_(
                AccountabilityPartnership.initiator_id == guest.id,
                AccountabilityPartnership.partner_id == guest.id,
            ),
        )
    )
    accountability_checkins = await db_session.scalar(
        select(func.count(AccountabilityCheckin.id)).where(
            AccountabilityCheckin.partnership_id.in_(
                select(AccountabilityPartnership.id).where(
                    or_(
                        AccountabilityPartnership.initiator_id == guest.id,
                        AccountabilityPartnership.partner_id == guest.id,
                    )
                )
            )
        )
    )
    task_share_messages = await db_session.scalar(
        select(func.count(GroupMessage.id)).where(
            GroupMessage.message_type == MessageType.TASK_SHARE
        )
    )
    plan_share_messages = await db_session.scalar(
        select(func.count(GroupMessage.id)).where(
            GroupMessage.message_type == MessageType.PLAN_SHARE
        )
    )

    assert accepted_friendships >= 6
    assert pending_friendships >= 1
    assert joined_groups >= 4
    assert group_messages >= 10
    assert group_task_types >= 3
    assert private_messages >= 6
    assert favorites >= 2
    assert active_partnerships >= 1
    assert pending_partnerships >= 1
    assert accountability_checkins >= 4
    assert task_share_messages >= 1
    assert plan_share_messages >= 2
