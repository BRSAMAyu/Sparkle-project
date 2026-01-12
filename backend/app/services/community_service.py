"""
社群功能服务层
Community Service - 好友、群组、消息、打卡、任务的业务逻辑
"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.core.websocket import manager
from app.models.user import User
from app.models.community import (
    Friendship, FriendshipStatus,
    Group, GroupType, GroupRole,
    GroupMember, GroupMessage, MessageType,
    GroupTask, GroupTaskClaim
)
from app.schemas.community import (
    GroupCreate, GroupUpdate, GroupTaskCreate,
    MessageSend, MessageEdit, CheckinRequest
)

def _is_visible_to(content_data: Optional[dict], user_id: UUID) -> bool:
    if not content_data:
        return True
    visibility = content_data.get("visibility")
    if visibility != "self":
        return True
    visible_to = content_data.get("visible_to")
    if visible_to is None:
        return False
    if isinstance(visible_to, list):
        return str(user_id) in [str(item) for item in visible_to]
    return str(visible_to) == str(user_id)


class FriendshipService:
    """好友系统服务"""

    @staticmethod
    async def send_friend_request(
        db: AsyncSession,
        user_id: UUID,
        target_id: UUID,
        match_reason: Optional[dict] = None
    ) -> Friendship:
        """
        发送好友请求

        逻辑说明：
        1. 检查是否已存在关系
        2. 如果存在反向的待处理请求，则自动接受（双向奔赴）
        3. 否则创建 pending 状态的好友关系
        """
        if user_id == target_id:
            raise ValueError("不能添加自己为好友")

        # 检查是否存在反向的待处理请求 (target -> user)
        reverse_pending = await db.execute(
            select(Friendship).where(
                Friendship.user_id == (target_id if str(target_id) < str(user_id) else user_id),
                Friendship.friend_id == (user_id if str(target_id) < str(user_id) else target_id),
                Friendship.status == FriendshipStatus.PENDING,
                Friendship.initiated_by == target_id,
                Friendship.not_deleted_filter()
            )
        )
        existing_reverse = reverse_pending.scalar_one_or_none()
        
        if existing_reverse:
            # 自动接受
            existing_reverse.status = FriendshipStatus.ACCEPTED
            await db.flush()
            await db.refresh(existing_reverse)
            return existing_reverse

        # 标准化顺序（使用字符串比较）
        if str(user_id) < str(target_id):
            small_id, large_id = user_id, target_id
        else:
            small_id, large_id = target_id, user_id

        # 检查是否已存在其他关系（包括黑名单）
        existing = await db.execute(
            select(Friendship).where(
                Friendship.user_id == small_id,
                Friendship.friend_id == large_id,
                Friendship.not_deleted_filter()
            )
        )
        existing_rel = existing.scalar_one_or_none()
        if existing_rel:
            if existing_rel.status == FriendshipStatus.BLOCKED:
                raise ValueError("由于对方的隐私设置，无法发送请求")
            raise ValueError("已存在好友关系或待处理请求")

        friendship = Friendship(
            user_id=small_id,
            friend_id=large_id,
            initiated_by=user_id,
            status=FriendshipStatus.PENDING,
            match_reason=match_reason
        )
        db.add(friendship)
        await db.flush()
        await db.refresh(friendship)
        return friendship

    @staticmethod
    async def respond_to_request(
        db: AsyncSession,
        user_id: UUID,
        friendship_id: UUID,
        accept: bool
    ) -> Optional[Friendship]:
        """
        响应好友请求

        逻辑说明：
        1. 验证当前用户是被请求方
        2. 更新状态为 accepted 或删除记录
        """
        friendship = await Friendship.get_by_id(db, friendship_id)
        if not friendship:
            raise ValueError("好友请求不存在")

        # 确认当前用户是被请求方
        if friendship.initiated_by == user_id:
            raise ValueError("不能响应自己发起的请求")

        if user_id not in (friendship.user_id, friendship.friend_id):
            raise ValueError("无权操作此请求")

        if accept:
            friendship.status = FriendshipStatus.ACCEPTED
            await db.flush()
            return friendship
        else:
            await friendship.delete(db, soft=True)
            return None

    @staticmethod
    async def get_friends(
        db: AsyncSession,
        user_id: UUID,
        status: FriendshipStatus = FriendshipStatus.ACCEPTED,
        limit: int = 50,
        offset: int = 0
    ) -> List[Tuple[Friendship, User]]:
        """获取好友列表（分页）"""
        query = select(Friendship, User).join(
            User, or_(
                and_(Friendship.user_id == user_id, User.id == Friendship.friend_id),
                and_(Friendship.friend_id == user_id, User.id == Friendship.user_id)
            )
        ).where(
            or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
            Friendship.status == status,
            Friendship.not_deleted_filter()
        ).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.all()

    @staticmethod
    async def get_pending_requests(
        db: AsyncSession,
        user_id: UUID
    ) -> List[Friendship]:
        """获取待处理的好友请求（收到的）"""
        result = await db.execute(
            select(Friendship).where(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
                Friendship.status == FriendshipStatus.PENDING,
                Friendship.initiated_by != user_id,  # 不是自己发起的
                Friendship.not_deleted_filter()
            ).options(
                selectinload(Friendship.initiator)
            )
        )
        return list(result.scalars().all())


class GroupService:
    """群组服务"""

    @staticmethod
    async def create_group(
        db: AsyncSession,
        creator_id: UUID,
        data: GroupCreate
    ) -> Group:
        """
        创建群组

        逻辑说明：
        1. 创建群组记录
        2. 将创建者设为群主
        """
        group = Group(
            name=data.name,
            description=data.description,
            type=data.type,
            focus_tags=data.focus_tags or [],
            deadline=data.deadline,
            sprint_goal=data.sprint_goal,
            max_members=data.max_members,
            is_public=data.is_public,
            join_requires_approval=data.join_requires_approval
        )
        db.add(group)
        await db.flush()

        # 添加创建者为群主
        owner = GroupMember(
            group_id=group.id,
            user_id=creator_id,
            role=GroupRole.OWNER,
            joined_at=datetime.utcnow(),
            last_active_at=datetime.utcnow()
        )
        db.add(owner)

        await db.flush()
        await db.refresh(group)
        return group

    @staticmethod
    async def get_group(
        db: AsyncSession,
        group_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取群组详情

        返回包含成员数量和当前用户角色的完整信息
        """
        group = await Group.get_by_id(db, group_id)
        if not group:
            return None

        # 计算成员数量
        member_count_result = await db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id,
                GroupMember.not_deleted_filter()
            )
        )
        member_count = member_count_result.scalar() or 0

        # 获取当前用户角色
        my_role = None
        if user_id:
            member_result = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter()
                )
            )
            member = member_result.scalar_one_or_none()
            if member:
                my_role = member.role

        # 计算剩余天数
        days_remaining = None
        if group.deadline:
            delta = group.deadline - datetime.utcnow()
            days_remaining = max(0, delta.days)

        return {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'avatar_url': group.avatar_url,
            'type': group.type,
            'focus_tags': group.focus_tags or [],
            'deadline': group.deadline,
            'sprint_goal': group.sprint_goal,
            'max_members': group.max_members,
            'is_public': group.is_public,
            'join_requires_approval': group.join_requires_approval,
            'total_flame_power': group.total_flame_power,
            'today_checkin_count': group.today_checkin_count,
            'total_tasks_completed': group.total_tasks_completed,
            'created_at': group.created_at,
            'updated_at': group.updated_at,
            'member_count': member_count,
            'my_role': my_role,
            'days_remaining': days_remaining
        }

    @staticmethod
    async def join_group(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> GroupMember:
        """加入群组"""
        # 检查群组是否存在
        group = await Group.get_by_id(db, group_id)
        if not group:
            raise ValueError("群组不存在")

        # 检查是否已是成员
        existing = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已是群组成员")

        # 检查成员上限
        member_count_result = await db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id,
                GroupMember.not_deleted_filter()
            )
        )
        member_count = member_count_result.scalar() or 0
        if member_count >= group.max_members:
            raise ValueError("群组已满")

        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role=GroupRole.MEMBER,
            joined_at=datetime.utcnow(),
            last_active_at=datetime.utcnow()
        )
        db.add(member)
        await db.flush()
        await db.refresh(member)
        return member

    @staticmethod
    async def leave_group(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> bool:
        """退出群组"""
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")

        if member.role == GroupRole.OWNER:
            raise ValueError("群主不能直接退出，请先转让群主")

        await member.delete(db, soft=True)
        return True

    @staticmethod
    async def get_my_groups(
        db: AsyncSession,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """获取用户加入的所有群组"""
        # Optimized query with subquery for member counts
        member_count_subquery = (
            select(
                GroupMember.group_id,
                func.count(GroupMember.id).label("count")
            )
            .where(GroupMember.not_deleted_filter())
            .group_by(GroupMember.group_id)
            .subquery()
        )

        result = await db.execute(
            select(Group, GroupMember, member_count_subquery.c.count)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .outerjoin(member_count_subquery, member_count_subquery.c.group_id == Group.id)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
                Group.not_deleted_filter()
            )
        )

        groups = []
        for group, membership, count in result.all():
            days_remaining = None
            if group.deadline:
                delta = group.deadline - datetime.utcnow()
                days_remaining = max(0, delta.days)

            groups.append({
                'id': group.id,
                'name': group.name,
                'type': group.type,
                'member_count': count or 0,
                'total_flame_power': group.total_flame_power,
                'deadline': group.deadline,
                'days_remaining': days_remaining,
                'focus_tags': group.focus_tags or [],
                'my_role': membership.role
            })

        return groups

    @staticmethod
    async def dissolve_group(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> bool:
        """解散群组"""
        # 1. 验证身份（必须是群主）
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.role == GroupRole.OWNER,
                GroupMember.not_deleted_filter()
            )
        )
        if not membership_result.scalar_one_or_none():
            raise ValueError("只有群主可以解散群组")

        group = await Group.get_by_id(db, group_id)
        if not group:
            raise ValueError("群组不存在")

        # 2. 软删除群组
        await group.delete(db, soft=True)
        
        # 3. 软删除所有成员关系
        from sqlalchemy import update
        await db.execute(
            update(GroupMember)
            .where(GroupMember.group_id == group_id)
            .values(is_deleted=True, deleted_at=datetime.utcnow())
        )
        
        return True

    @staticmethod
    async def transfer_owner(
        db: AsyncSession,
        group_id: UUID,
        current_owner_id: UUID,
        new_owner_id: UUID
    ) -> bool:
        """转让群主"""
        if current_owner_id == new_owner_id:
            return True

        # 1. 验证当前用户是群主
        owner_membership = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == current_owner_id,
                GroupMember.role == GroupRole.OWNER,
                GroupMember.not_deleted_filter()
            )
        )
        owner_member = owner_membership.scalar_one_or_none()
        if not owner_member:
            raise ValueError("无权操作")

        # 2. 验证新用户是群成员
        new_owner_membership = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == new_owner_id,
                GroupMember.not_deleted_filter()
            )
        )
        new_owner_member = new_owner_membership.scalar_one_or_none()
        if not new_owner_member:
            raise ValueError("目标用户不是群成员")

        # 3. 执行转让
        owner_member.role = GroupRole.ADMIN # 原群主降级为管理员
        new_owner_member.role = GroupRole.OWNER
        
        # 4. 发送系统消息
        await GroupMessageService.send_system_message(
            db, group_id, f"群主已转让给新成员"
        )
        
        return True


class GroupMessageService:
    """群消息服务"""

    @staticmethod
    async def send_message(
        db: AsyncSession,
        group_id: UUID,
        sender_id: UUID,
        data: MessageSend
    ) -> GroupMessage:
        """发送消息"""
        # 验证是否是群成员
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == sender_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = membership_result.scalar_one_or_none()
        if not member:
            # 尝试踢出已断开连接但仍在 active_connections 中的用户（容错）
            await manager.kick_user_from_group(str(group_id), str(sender_id), "Not a member")
            raise ValueError("不是群组成员")
            
        if member.is_muted:
            # 如果被禁言，可以在此处显式断开其群组 WS
            # await manager.kick_user_from_group(str(group_id), str(sender_id), "Muted")
            raise ValueError("您已被禁言")

        if data.reply_to_id:
            reply_msg = await db.get(GroupMessage, data.reply_to_id)
            if not reply_msg or reply_msg.group_id != group_id:
                raise ValueError("回复消息不存在")

        if data.thread_root_id:
            root_msg = await db.get(GroupMessage, data.thread_root_id)
            if not root_msg or root_msg.group_id != group_id:
                raise ValueError("线程根消息不存在")

        mention_user_ids = None
        if data.mention_user_ids:
            mention_user_ids = [str(uid) for uid in data.mention_user_ids]

        message = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            message_type=data.message_type,
            content=data.content,
            content_data=data.content_data,
            reply_to_id=data.reply_to_id,
            thread_root_id=data.thread_root_id,
            mention_user_ids=mention_user_ids
        )
        db.add(message)

        # 更新最后活跃时间
        member.last_active_at = datetime.utcnow()

        await db.flush()
        
        # Re-fetch with relationships to ensure reply_to is loaded
        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).where(GroupMessage.id == message.id)
        
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def edit_message(
        db: AsyncSession,
        group_id: UUID,
        message_id: UUID,
        editor_id: UUID,
        data: MessageEdit
    ) -> GroupMessage:
        """编辑消息"""
        msg = await db.get(GroupMessage, message_id)
        if not msg or msg.group_id != group_id or msg.is_deleted:
            raise ValueError("消息不存在")
        if msg.sender_id != editor_id:
            raise ValueError("无权限编辑该消息")
        if msg.is_revoked:
            raise ValueError("消息已撤回，无法编辑")
        if msg.message_type == MessageType.SYSTEM:
            raise ValueError("系统消息不可编辑")

        if data.content is not None:
            msg.content = data.content
        if data.content_data is not None:
            msg.content_data = data.content_data
        if data.mention_user_ids is not None:
            msg.mention_user_ids = [str(uid) for uid in data.mention_user_ids]

        if msg.message_type == MessageType.TEXT and not msg.content:
            raise ValueError("文本消息必须有内容")

        msg.edited_at = datetime.utcnow()
        db.add(msg)
        await db.flush()

        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).where(GroupMessage.id == msg.id)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def revoke_message(
        db: AsyncSession,
        group_id: UUID,
        message_id: UUID,
        user_id: UUID
    ) -> GroupMessage:
        """撤回消息"""
        msg = await db.get(GroupMessage, message_id)
        if not msg or msg.group_id != group_id or msg.is_deleted:
            raise ValueError("消息不存在")

        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = membership_result.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")

        is_sender = msg.sender_id == user_id
        is_admin = member.role in [GroupRole.ADMIN, GroupRole.OWNER]
        if not is_sender and not is_admin:
            raise ValueError("无权限撤回该消息")

        if is_sender and datetime.utcnow().difference(msg.created_at).total_seconds() > 86400:
            raise ValueError("超过撤回时限")

        if msg.is_revoked:
            return msg

        msg.is_revoked = True
        msg.revoked_at = datetime.utcnow()
        msg.content = None
        msg.content_data = None
        msg.reactions = None
        db.add(msg)
        await db.flush()

        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).where(GroupMessage.id == msg.id)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def update_reaction(
        db: AsyncSession,
        group_id: UUID,
        message_id: UUID,
        user_id: UUID,
        emoji: str,
        is_add: bool
    ) -> GroupMessage:
        """更新消息表情反应"""
        msg = await db.get(GroupMessage, message_id)
        if not msg or msg.group_id != group_id or msg.is_deleted:
            raise ValueError("消息不存在")
        if msg.is_revoked:
            raise ValueError("消息已撤回")

        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        if not membership_result.scalar_one_or_none():
            raise ValueError("不是群组成员")

        reactions = msg.reactions or {}
        user_key = str(user_id)
        users = set(reactions.get(emoji, []))
        if is_add:
            users.add(user_key)
        else:
            users.discard(user_key)
        if users:
            reactions[emoji] = list(users)
        else:
            reactions.pop(emoji, None)

        msg.reactions = reactions
        db.add(msg)
        await db.flush()

        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).where(GroupMessage.id == msg.id)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_thread_messages(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        thread_root_id: UUID,
        limit: int = 100
    ) -> List[GroupMessage]:
        """获取线程消息"""
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        if not membership_result.scalar_one_or_none():
            raise ValueError("不是群组成员，无法查看消息")

        root_stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).where(GroupMessage.id == thread_root_id)
        root_result = await db.execute(root_stmt)
        root = root_result.scalar_one_or_none()
        if not root or root.group_id != group_id or root.is_deleted:
            raise ValueError("线程不存在")
        if not _is_visible_to(root.content_data, user_id):
            raise ValueError("线程不存在")

        query = select(GroupMessage).where(
            GroupMessage.group_id == group_id,
            GroupMessage.thread_root_id == thread_root_id,
            GroupMessage.not_deleted_filter()
        ).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).order_by(GroupMessage.created_at.asc()).limit(limit)

        result = await db.execute(query)
        replies = [msg for msg in result.scalars().all() if _is_visible_to(msg.content_data, user_id)]
        return [root, *replies]

    @staticmethod
    async def search_messages(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        keyword: str,
        limit: int = 50
    ) -> List[GroupMessage]:
        """搜索群消息"""
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        if not membership_result.scalar_one_or_none():
            raise ValueError("不是群组成员，无法搜索消息")

        query = select(GroupMessage).where(
            GroupMessage.group_id == group_id,
            GroupMessage.not_deleted_filter(),
            GroupMessage.content.ilike(f"%{keyword}%")
        ).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).order_by(desc(GroupMessage.created_at)).limit(limit)

        result = await db.execute(query)
        return [msg for msg in result.scalars().all() if _is_visible_to(msg.content_data, user_id)]

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID, # Added user_id for permission check
        before_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[GroupMessage]:
        """获取群消息（分页）"""
        # Check membership first
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        if not membership_result.scalar_one_or_none():
            raise ValueError("不是群组成员，无法查看消息")

        query = select(GroupMessage).where(
            GroupMessage.group_id == group_id,
            GroupMessage.not_deleted_filter()
        ).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender)
        ).order_by(desc(GroupMessage.created_at))

        if before_id:
            # 获取before_id对应消息的创建时间
            before_msg = await GroupMessage.get_by_id(db, before_id)
            if before_msg:
                query = query.where(GroupMessage.created_at < before_msg.created_at)

        query = query.limit(limit)
        result = await db.execute(query)
        messages = list(result.scalars().all())
        return [msg for msg in messages if _is_visible_to(msg.content_data, user_id)]

    @staticmethod
    async def send_system_message(
        db: AsyncSession,
        group_id: UUID,
        content: str,
        content_data: Optional[dict] = None
    ) -> GroupMessage:
        """发送系统消息"""
        message = GroupMessage(
            group_id=group_id,
            sender_id=None,
            message_type=MessageType.SYSTEM,
            content=content,
            content_data=content_data
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message


class CheckinService:
    """打卡服务"""

    @staticmethod
    async def checkin(
        db: AsyncSession,
        user_id: UUID,
        data: CheckinRequest
    ) -> Dict[str, Any]:
        """
        群组打卡

        逻辑说明：
        1. 验证群成员身份
        2. 检查今日是否已打卡
        3. 更新打卡连续天数
        4. 计算火苗奖励
        5. 发送打卡消息到群组
        """
        # 获取成员信息
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == data.group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")

        # 检查今日是否已打卡
        today = datetime.utcnow().date()
        if member.last_checkin_date and member.last_checkin_date.date() == today:
            raise ValueError("今日已打卡")

        # 计算连续打卡天数
        yesterday = today - timedelta(days=1)
        if member.last_checkin_date and member.last_checkin_date.date() == yesterday:
            member.checkin_streak += 1
        else:
            member.checkin_streak = 1

        member.last_checkin_date = datetime.utcnow()

        # 计算火苗奖励
        base_flame = 10
        streak_bonus = min(member.checkin_streak * 2, 20)  # 最多+20
        duration_bonus = min(data.today_duration_minutes // 30 * 5, 30)  # 每30分钟+5，最多+30
        flame_earned = base_flame + streak_bonus + duration_bonus

        member.flame_contribution += flame_earned

        # 更新群组统计
        group = await Group.get_by_id(db, data.group_id)
        group.total_flame_power += flame_earned
        group.today_checkin_count += 1

        # 发送打卡消息
        message = GroupMessage(
            group_id=data.group_id,
            sender_id=user_id,
            message_type=MessageType.CHECKIN,
            content=data.message,
            content_data={
                'flame_power': flame_earned,
                'streak': member.checkin_streak,
                'today_duration': data.today_duration_minutes
            }
        )
        db.add(message)

        await db.flush()

        # 计算排名
        rank_result = await db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == data.group_id,
                GroupMember.flame_contribution > member.flame_contribution,
                GroupMember.not_deleted_filter()
            )
        )
        rank = (rank_result.scalar() or 0) + 1

        return {
            'success': True,
            'new_streak': member.checkin_streak,
            'flame_earned': flame_earned,
            'rank_in_group': rank,
            'group_checkin_count': group.today_checkin_count
        }


class GroupTaskService:
    """群任务服务"""

    @staticmethod
    async def create_task(
        db: AsyncSession,
        group_id: UUID,
        creator_id: UUID,
        data: GroupTaskCreate
    ) -> GroupTask:
        """创建群任务"""
        # 验证权限（群主或管理员）
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == creator_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = membership_result.scalar_one_or_none()
        if not member or member.role == GroupRole.MEMBER:
            raise ValueError("只有群主或管理员可以创建群任务")

        task = GroupTask(
            group_id=group_id,
            created_by=creator_id,
            title=data.title,
            description=data.description,
            tags=data.tags or [],
            estimated_minutes=data.estimated_minutes,
            difficulty=data.difficulty,
            due_date=data.due_date
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def claim_task(
        db: AsyncSession,
        task_id: UUID,
        user_id: UUID
    ) -> GroupTaskClaim:
        """
        认领群任务

        逻辑说明:
        1. 锁定群任务行防止并发冲突
        2. 检查是否已认领
        3. 创建个人任务系统中的副本
        4. 建立关联记录
        """
        # 获取群任务 (Use with_for_update to lock row)
        result = await db.execute(
            select(GroupTask)
            .where(GroupTask.id == task_id)
            .with_for_update()
        )
        group_task = result.scalar_one_or_none()
        
        if not group_task:
            raise ValueError("任务不存在")

        # 检查是否已认领
        existing = await db.execute(
            select(GroupTaskClaim).where(
                GroupTaskClaim.group_task_id == task_id,
                GroupTaskClaim.user_id == user_id,
                GroupTaskClaim.not_deleted_filter()
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已认领此任务")

        # 创建个人任务副本
        from app.services.task_service import TaskService
        from app.schemas.task import TaskCreate
        from app.models.task import TaskType as PersonalTaskType
        
        # 转换日期 (DateTime -> Date)
        personal_due_date = group_task.due_date.date() if group_task.due_date else None
        
        personal_task_in = TaskCreate(
            title=f"[{group_task.group.name}] {group_task.title}" if group_task.group else f"[群任务] {group_task.title}",
            type=PersonalTaskType.LEARNING, # 默认设为学习类
            tags=group_task.tags or [],
            estimated_minutes=group_task.estimated_minutes,
            difficulty=group_task.difficulty,
            due_date=personal_due_date,
            priority=2 # 中高优先级
        )
        
        # 注意：这里调用 TaskService.create，它内部会执行 commit
        # 但我们在事务中，最好让外部统一 commit。
        # 修改：TaskService.create 目前内部有 commit，这在复合操作中不太理想。
        # 暂时保持，但理想状态下 Service 层应该分 open/save 逻辑。
        personal_task = await TaskService.create(db, personal_task_in, user_id)

        # 记录认领
        claim = GroupTaskClaim(
            group_task_id=task_id,
            user_id=user_id,
            personal_task_id=personal_task.id,
            claimed_at=datetime.utcnow()
        )
        db.add(claim)

        # 更新认领计数
        group_task.total_claims += 1

        await db.flush()
        await db.refresh(claim)
        return claim

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        claim_id: UUID
    ) -> Optional[GroupTaskClaim]:
        """完成群任务（由个人任务完成时触发）"""
        claim = await GroupTaskClaim.get_by_id(db, claim_id)
        if not claim or claim.is_completed:
            return claim

        claim.is_completed = True
        claim.completed_at = datetime.utcnow()

        # 更新群任务完成计数
        group_task = await GroupTask.get_by_id(db, claim.group_task_id)
        group_task.total_completions += 1

        # 更新成员完成任务数
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_task.group_id,
                GroupMember.user_id == claim.user_id,
                GroupMember.not_deleted_filter()
            )
        )
        member = membership_result.scalar_one_or_none()
        if member:
            member.tasks_completed += 1

        # 更新群组统计
        group = await Group.get_by_id(db, group_task.group_id)
        group.total_tasks_completed += 1

        await db.flush()
        return claim

    @staticmethod
    async def get_group_tasks(
        db: AsyncSession,
        group_id: UUID,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """获取群任务列表"""
        result = await db.execute(
            select(GroupTask).where(
                GroupTask.group_id == group_id,
                GroupTask.not_deleted_filter()
            ).options(
                selectinload(GroupTask.creator),
                selectinload(GroupTask.claims)
            ).order_by(desc(GroupTask.created_at))
        )

        tasks = []
        for task in result.scalars():
            completion_rate = (
                task.total_completions / task.total_claims
                if task.total_claims > 0 else 0
            )

            task_dict = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'tags': task.tags or [],
                'estimated_minutes': task.estimated_minutes,
                'difficulty': task.difficulty,
                'total_claims': task.total_claims,
                'total_completions': task.total_completions,
                'completion_rate': completion_rate,
                'due_date': task.due_date,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'creator': task.creator,
                'is_claimed_by_me': False,
                'my_completion_status': None
            }

            if user_id:
                for claim in task.claims:
                    if claim.user_id == user_id and not claim.is_deleted:
                        task_dict['is_claimed_by_me'] = True
                        task_dict['my_completion_status'] = claim.is_completed
                        break

            tasks.append(task_dict)

        return tasks


class PrivateMessageService:
    """私聊消息服务"""

    @staticmethod
    async def send_message(
        db: AsyncSession,
        sender_id: UUID,
        data: Any # PrivateMessageSend
    ) -> Any: # PrivateMessage
        """发送私聊消息"""
        from app.models.community import PrivateMessage, Friendship, FriendshipStatus
        
        # 检查是否被拉黑
        u1, u2 = (sender_id, data.target_user_id) if str(sender_id) < str(data.target_user_id) else (data.target_user_id, sender_id)
        rel_result = await db.execute(
            select(Friendship).where(
                Friendship.user_id == u1,
                Friendship.friend_id == u2,
                Friendship.status == FriendshipStatus.BLOCKED
            )
        )
        if rel_result.scalar_one_or_none():
            raise ValueError("消息发送失败")

        if data.reply_to_id:
            reply_msg = await db.get(PrivateMessage, data.reply_to_id)
            if not reply_msg or reply_msg.is_deleted:
                raise ValueError("回复消息不存在")
            if sender_id not in [reply_msg.sender_id, reply_msg.receiver_id]:
                raise ValueError("不能回复非会话内消息")

        if data.thread_root_id:
            root_msg = await db.get(PrivateMessage, data.thread_root_id)
            if not root_msg or root_msg.is_deleted:
                raise ValueError("线程根消息不存在")
            if sender_id not in [root_msg.sender_id, root_msg.receiver_id]:
                raise ValueError("不能回复非会话内消息")

        mention_user_ids = None
        if data.mention_user_ids:
            mention_user_ids = [str(uid) for uid in data.mention_user_ids]

        message = PrivateMessage(
            sender_id=sender_id,
            receiver_id=data.target_user_id,
            message_type=data.message_type,
            content=data.content,
            content_data=data.content_data,
            reply_to_id=data.reply_to_id,
            thread_root_id=data.thread_root_id,
            mention_user_ids=mention_user_ids,
            created_at=datetime.utcnow()
        )
        db.add(message)
        await db.flush()
        
        # Re-fetch with relationships
        stmt = select(PrivateMessage).options(
            selectinload(PrivateMessage.sender),
            selectinload(PrivateMessage.receiver),
            selectinload(PrivateMessage.reply_to).selectinload(PrivateMessage.sender)
        ).where(PrivateMessage.id == message.id)
        
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def edit_message(
        db: AsyncSession,
        message_id: UUID,
        editor_id: UUID,
        data: MessageEdit
    ) -> Any:
        """编辑私聊消息"""
        from app.models.community import PrivateMessage

        msg = await db.get(PrivateMessage, message_id)
        if not msg or msg.is_deleted:
            raise ValueError("消息不存在")
        if msg.sender_id != editor_id:
            raise ValueError("无权限编辑该消息")
        if msg.is_revoked:
            raise ValueError("消息已撤回，无法编辑")
        if msg.message_type == MessageType.SYSTEM:
            raise ValueError("系统消息不可编辑")

        if data.content is not None:
            msg.content = data.content
        if data.content_data is not None:
            msg.content_data = data.content_data
        if data.mention_user_ids is not None:
            msg.mention_user_ids = [str(uid) for uid in data.mention_user_ids]

        if msg.message_type == MessageType.TEXT and not msg.content:
            raise ValueError("文本消息必须有内容")

        msg.edited_at = datetime.utcnow()
        db.add(msg)
        await db.flush()

        stmt = select(PrivateMessage).options(
            selectinload(PrivateMessage.sender),
            selectinload(PrivateMessage.receiver),
            selectinload(PrivateMessage.reply_to).selectinload(PrivateMessage.sender)
        ).where(PrivateMessage.id == msg.id)

        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def revoke_message(
        db: AsyncSession,
        message_id: UUID,
        user_id: UUID
    ) -> Any:
        """撤回私聊消息"""
        from app.models.community import PrivateMessage

        msg = await db.get(PrivateMessage, message_id)
        if not msg or msg.is_deleted:
            raise ValueError("消息不存在")
        if msg.sender_id != user_id:
            raise ValueError("无权限撤回该消息")
        if msg.is_revoked:
            return msg
        if datetime.utcnow().difference(msg.created_at).total_seconds() > 86400:
            raise ValueError("超过撤回时限")

        msg.is_revoked = True
        msg.revoked_at = datetime.utcnow()
        msg.content = None
        msg.content_data = None
        msg.reactions = None
        db.add(msg)
        await db.flush()

        stmt = select(PrivateMessage).options(
            selectinload(PrivateMessage.sender),
            selectinload(PrivateMessage.receiver),
            selectinload(PrivateMessage.reply_to).selectinload(PrivateMessage.sender)
        ).where(PrivateMessage.id == msg.id)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def update_reaction(
        db: AsyncSession,
        message_id: UUID,
        user_id: UUID,
        emoji: str,
        is_add: bool
    ) -> Any:
        """更新私聊消息表情反应"""
        from app.models.community import PrivateMessage

        msg = await db.get(PrivateMessage, message_id)
        if not msg or msg.is_deleted:
            raise ValueError("消息不存在")
        if msg.is_revoked:
            raise ValueError("消息已撤回")
        if user_id not in [msg.sender_id, msg.receiver_id]:
            raise ValueError("无权限更新消息")

        reactions = msg.reactions or {}
        user_key = str(user_id)
        users = set(reactions.get(emoji, []))
        if is_add:
            users.add(user_key)
        else:
            users.discard(user_key)
        if users:
            reactions[emoji] = list(users)
        else:
            reactions.pop(emoji, None)

        msg.reactions = reactions
        db.add(msg)
        await db.flush()

        stmt = select(PrivateMessage).options(
            selectinload(PrivateMessage.sender),
            selectinload(PrivateMessage.receiver),
            selectinload(PrivateMessage.reply_to).selectinload(PrivateMessage.sender)
        ).where(PrivateMessage.id == msg.id)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def search_messages(
        db: AsyncSession,
        user_id: UUID,
        friend_id: UUID,
        keyword: str,
        limit: int = 50
    ) -> List[Any]:
        """搜索私聊消息"""
        from app.models.community import PrivateMessage

        query = select(PrivateMessage).where(
            or_(
                and_(PrivateMessage.sender_id == user_id, PrivateMessage.receiver_id == friend_id),
                and_(PrivateMessage.sender_id == friend_id, PrivateMessage.receiver_id == user_id)
            ),
            PrivateMessage.not_deleted_filter(),
            PrivateMessage.content.ilike(f"%{keyword}%")
        ).options(
            selectinload(PrivateMessage.sender),
            selectinload(PrivateMessage.receiver),
            selectinload(PrivateMessage.reply_to).selectinload(PrivateMessage.sender)
        ).order_by(desc(PrivateMessage.created_at)).limit(limit)

        result = await db.execute(query)
        return [msg for msg in result.scalars().all() if _is_visible_to(msg.content_data, user_id)]

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        user_id: UUID,
        friend_id: UUID,
        before_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Any]: # List[PrivateMessage]
        """获取与某好友的私聊记录"""
        from app.models.community import PrivateMessage
        
        query = select(PrivateMessage).where(
            or_(
                and_(PrivateMessage.sender_id == user_id, PrivateMessage.receiver_id == friend_id),
                and_(PrivateMessage.sender_id == friend_id, PrivateMessage.receiver_id == user_id)
            ),
            PrivateMessage.not_deleted_filter()
        ).options(
            selectinload(PrivateMessage.sender),
            selectinload(PrivateMessage.receiver),
            selectinload(PrivateMessage.reply_to).selectinload(PrivateMessage.sender)
        ).order_by(desc(PrivateMessage.created_at))

        if before_id:
            before_msg = await PrivateMessage.get_by_id(db, before_id)
            if before_msg:
                query = query.where(PrivateMessage.created_at < before_msg.created_at)

        query = query.limit(limit)
        result = await db.execute(query)
        messages = list(result.scalars().all())
        return [msg for msg in messages if _is_visible_to(msg.content_data, user_id)]

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        user_id: UUID,
        sender_id: UUID
    ) -> int:
        """标记来自某人的消息为已读"""
        from app.models.community import PrivateMessage
        from sqlalchemy import update
        
        stmt = update(PrivateMessage).where(
            PrivateMessage.receiver_id == user_id,
            PrivateMessage.sender_id == sender_id,
            PrivateMessage.is_read == False
        ).values(
            is_read=True,
            read_at=datetime.utcnow()
        )
        
        result = await db.execute(stmt)
        return result.rowcount
