"""
Capsule Share Service

处理胶囊分享功能（分享到群组/好友）
"""
from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.core.event_types import CAPSULE_CONTENT_UPDATED
from app.models.community import Friendship, Group, GroupMember, GroupMessage, MessageType, PrivateMessage
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.user import User


class CapsuleShareService:
    """
    胶囊分享服务

    核心功能：
    - 分享到群组
    - 分享给好友
    - 生成分享消息
    """

    async def share_to_group(
        self,
        user_id: UUID,
        capsule_id: UUID,
        group_id: UUID,
        db: AsyncSession,
        message: str | None = None,
    ) -> GroupMessage:
        """
        分享胶囊到群组

        Args:
            user_id: 分享者ID
            capsule_id: 胶囊ID
            group_id: 群组ID
            db: 数据库会话
            message: 附加消息

        Returns:
            创建的群组消息

        Raises:
            ValueError: 如果胶囊不存在或用户不在群组中
        """
        # 验证胶囊
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if not capsule:
            raise ValueError(f"Capsule {capsule_id} not found")

        # 验证群组成员身份
        member_result = await db.execute(
            select(GroupMember).where(
                GroupMember.user_id == user_id,
                GroupMember.group_id == group_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if not member:
            raise ValueError("User is not a member of this group")

        # 验证群组
        group = await db.get(Group, group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")

        # 构建分享消息
        share_message = self._build_share_message(capsule, message)

        # 创建群组消息
        group_message = GroupMessage(
            group_id=group_id,
            sender_id=user_id,
            message_type=MessageType.CAPSULE_SHARE,
            content=share_message,
            metadata={
                "capsule_id": str(capsule_id),
                "capsule_title": capsule.title,
                "capsule_content": capsule.content[:200],  # 前200字符预览
                "share_type": "capsule",
            },
        )
        db.add(group_message)

        # 更新胶囊分享计数
        capsule.share_count += 1

        await db.commit()
        await db.refresh(group_message)
        await self._publish_content_update_event(
            user_id=user_id,
            capsule_id=capsule_id,
            action="shared_to_group",
        )

        logger.info(
            f"[Share] User {user_id} shared capsule {capsule_id} to group {group_id}"
        )
        return group_message

    async def share_to_friend(
        self,
        user_id: UUID,
        capsule_id: UUID,
        friend_id: UUID,
        db: AsyncSession,
        message: str | None = None,
    ) -> PrivateMessage:
        """
        分享胶囊给好友

        Args:
            user_id: 分享者ID
            capsule_id: 胶囊ID
            friend_id: 好友ID
            db: 数据库会话
            message: 附加消息

        Returns:
            创建的私聊消息

        Raises:
            ValueError: 如果胶囊不存在或不是好友关系
        """
        # 验证胶囊
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if not capsule:
            raise ValueError(f"Capsule {capsule_id} not found")

        # 验证好友关系
        friendship_result = await db.execute(
            select(Friendship).where(
                Friendship.user_id == user_id,
                Friendship.friend_id == friend_id,
                Friendship.status == "accepted",
            )
        )
        friendship = friendship_result.scalar_one_or_none()
        if not friendship:
            # 检查反向关系
            friendship_result = await db.execute(
                select(Friendship).where(
                    Friendship.user_id == friend_id,
                    Friendship.friend_id == user_id,
                    Friendship.status == "accepted",
                )
            )
            friendship = friendship_result.scalar_one_or_none()

        if not friendship:
            raise ValueError("Users are not friends")

        # 构建分享消息
        share_message = self._build_share_message(capsule, message)

        # 创建私聊消息
        private_message = PrivateMessage(
            sender_id=user_id,
            receiver_id=friend_id,
            content=share_message,
            metadata={
                "capsule_id": str(capsule_id),
                "capsule_title": capsule.title,
                "capsule_content": capsule.content[:200],
                "share_type": "capsule",
            },
        )
        db.add(private_message)

        # 更新胶囊分享计数
        capsule.share_count += 1

        await db.commit()
        await db.refresh(private_message)
        await self._publish_content_update_event(
            user_id=user_id,
            capsule_id=capsule_id,
            action="shared_to_friend",
        )

        logger.info(
            f"[Share] User {user_id} shared capsule {capsule_id} to friend {friend_id}"
        )
        return private_message

    def _build_share_message(
        self,
        capsule: CuriosityCapsule,
        additional_message: str | None = None,
    ) -> str:
        """
        构建分享消息文本

        格式：
        💡 [好奇心胶囊] {capsule.title}

        {capsule.content[:100]}...

        ---
        来自 Sparkle AI 学习助手
        """
        depth_emoji = {
            "shallow": "⚡",
            "medium": "💡",
            "deep": "🔬",
        }
        emoji = depth_emoji.get(capsule.depth_level_value or "medium", "💡")

        message = f"{emoji} [好奇心胶囊] {capsule.title}\n\n"

        # 内容预览
        content_preview = capsule.content[:150]
        if len(capsule.content) > 150:
            content_preview += "..."
        message += content_preview + "\n\n"

        if additional_message:
            message += f"附言：{additional_message}\n\n"

        message += "---\n来自 Sparkle AI 学习助手"

        return message

    async def get_sharable_groups(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> list[Group]:
        """
        获取用户可分享的群组列表

        Returns:
            用户加入的群组列表
        """
        result = await db.execute(
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(GroupMember.user_id == user_id)
            .order_by(Group.name)
        )
        return list(result.scalars().all())

    async def get_sharable_friends(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> list[User]:
        """
        获取用户可分享的好友列表

        Returns:
            好友用户列表
        """
        # 获取所有好友关系
        result = await db.execute(
            select(Friendship).where(
                Friendship.user_id == user_id,
                Friendship.status == "accepted",
            )
        )
        friendships = result.scalars().all()

        friend_ids = [f.friend_id for f in friendships]
        if not friend_ids:
            return []

        # 获取好友用户信息
        users_result = await db.execute(
            select(User).where(User.id.in_(friend_ids))
        )
        return list(users_result.scalars().all())

    async def _publish_content_update_event(
        self,
        *,
        user_id: UUID,
        capsule_id: UUID,
        action: str,
    ) -> None:
        await event_bus.publish(
            CAPSULE_CONTENT_UPDATED,
            {
                "event_type": CAPSULE_CONTENT_UPDATED,
                "user_id": str(user_id),
                "capsule_id": str(capsule_id),
                "action": action,
            },
        )


# 全局单例
capsule_share_service = CapsuleShareService()
