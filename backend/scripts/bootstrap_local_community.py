#!/usr/bin/env python3
"""Bootstrap a minimal real community graph for local mobile/device testing."""
import asyncio
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.community import Friendship, FriendshipStatus, Group, GroupMember, GroupMessage, GroupRole, GroupType, MessageType
from app.models.user import User

LOCAL_GROUP_NAME = "本地联调学习群"
PRIMARY_GUEST_USERNAME = "guest_user"
SECONDARY_USERNAME = "chat_test"
SECONDARY_PASSWORD = "Chat123456"
SECONDARY_EMAIL = "chat_test@sparkle.demo"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _get_or_create_user(
    session,
    *,
    username: str,
    email: str,
    nickname: str,
    password: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password or username),
            nickname=nickname,
            registration_source="local_bootstrap",
            is_active=True,
        )
        session.add(user)
        await session.flush()
    else:
        user.email = email
        user.nickname = nickname
        user.is_active = True
        if password:
            user.hashed_password = get_password_hash(password)
    return user


async def _ensure_friendship(session, left: User, right: User) -> None:
    user_id, friend_id = sorted((left.id, right.id), key=str)
    result = await session.execute(
        select(Friendship).where(
            Friendship.user_id == user_id,
            Friendship.friend_id == friend_id,
            Friendship.not_deleted_filter(),
        )
    )
    friendship = result.scalar_one_or_none()
    if friendship is None:
        session.add(
            Friendship(
                user_id=user_id,
                friend_id=friend_id,
                initiated_by=left.id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        return
    friendship.status = FriendshipStatus.ACCEPTED
    friendship.initiated_by = left.id
    friendship.deleted_at = None


async def _ensure_group_member(session, group: Group, user: User, role: GroupRole) -> None:
    result = await session.execute(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        session.add(
            GroupMember(
                group_id=group.id,
                user_id=user.id,
                role=role,
                flame_contribution=100,
                tasks_completed=3,
                checkin_streak=2,
                last_checkin_date=_utcnow(),
                last_active_at=_utcnow(),
            )
        )
        return
    member.role = role
    member.deleted_at = None
    member.last_active_at = _utcnow()


async def _ensure_seed_messages(session, group: Group, users: list[User]) -> None:
    seed_messages = [
        (users[0], "这是一条本地联调用的真实群消息。"),
        (users[1], "收到，我这边可以用它验证群聊、已读和文件分享。"),
    ]
    for sender, content in seed_messages:
        result = await session.execute(
            select(GroupMessage).where(
                GroupMessage.group_id == group.id,
                GroupMessage.content == content,
                GroupMessage.not_deleted_filter(),
            )
        )
        if result.scalar_one_or_none() is not None:
            continue
        session.add(
            GroupMessage(
                group_id=group.id,
                sender_id=sender.id,
                message_type=MessageType.TEXT,
                content=content,
            )
        )


async def main() -> int:
    async with AsyncSessionLocal() as session:
        guest = await _get_or_create_user(
            session,
            username=PRIMARY_GUEST_USERNAME,
            email=f"{PRIMARY_GUEST_USERNAME}@guest.local",
            nickname="访客用户",
        )
        secondary = await _get_or_create_user(
            session,
            username=SECONDARY_USERNAME,
            email=SECONDARY_EMAIL,
            nickname="联调伙伴",
            password=SECONDARY_PASSWORD,
        )
        await _ensure_friendship(session, guest, secondary)

        group_result = await session.execute(
            select(Group).where(Group.name == LOCAL_GROUP_NAME, Group.not_deleted_filter())
        )
        group = group_result.scalar_one_or_none()
        if group is None:
            group = Group(
                name=LOCAL_GROUP_NAME,
                description="用于本地模拟器和脚本联调的真实群组",
                type=GroupType.SQUAD,
                focus_tags=["local", "integration"],
                max_members=20,
                is_public=False,
                join_requires_approval=False,
            )
            session.add(group)
            await session.flush()

        await _ensure_group_member(session, group, guest, GroupRole.OWNER)
        await _ensure_group_member(session, group, secondary, GroupRole.MEMBER)
        await _ensure_seed_messages(session, group, [guest, secondary])

        await session.commit()
        print(
            f"bootstrap complete: group_id={group.id} guest={guest.username} partner={secondary.username}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
