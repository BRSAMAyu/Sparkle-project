"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

社群功能服务层
Community Service - 好友、群组、消息、打卡、任务的业务逻辑
"""

from __future__ import annotations
import asyncio
import math
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import cache_service
from app.core.event_bus import GroupFileDeletedEvent, event_bus
from app.core.websocket import manager
from app.models.community import (
    Friendship,
    FriendshipStatus,
    Group,
    GroupMember,
    GroupMessage,
    GroupMessageRead,
    GroupRole,
    GroupTaskClaim,
    GroupTask,
    GroupType,
    MessageType,
    SharedResource,
    UserBlock,
)
from app.models.file_storage import StoredFile
from app.models.galaxy import CollaborativeGalaxy, KnowledgeNode, KnowledgeNodeDocument, NodeRelation
from app.models.group_files import GroupFile
from app.models.group_files import GroupFileTrustLevel
from app.models.plan import Plan, PlanType
from app.models.user import User
from app.schemas.community import (
    CheckinRequest,
    GroupCollaborativeGalaxyRelation,
    GroupCollaborativeGalaxyResponse,
    GroupCollaborativeGalaxyStats,
    GroupCollaborativeGalaxyNode,
    GroupCreate,
    GroupKnowledgeBaseStats,
    GroupTaskCreate,
    MessageEdit,
    MessageSend,
)
from app.services.community_signal_collector import CommunitySignalCollector
from app.services.group_file_service import GroupFileService


def _utcnow() -> datetime:
    """Return naive UTC datetime compatible with existing DB fields."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _record_community_signal(
    *,
    user_id: UUID,
    action: str,
    context: str,
    timestamp: datetime | None = None,
) -> None:
    asyncio.create_task(
        CommunitySignalCollector(cache_service.redis).record_interaction(
            user_id=user_id,
            action=action,
            context=context,
            timestamp=timestamp or _utcnow(),
        )
    )


def _is_visible_to(content_data: dict | None, user_id: UUID) -> bool:
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


async def _end_accountability_partnerships_between_users(
    db: AsyncSession,
    user1_id: UUID,
    user2_id: UUID,
) -> int:
    """End all non-ended accountability partnerships between two users."""
    from app.models.accountability import AccountabilityPartnership, AccountabilityStatus

    result = await db.execute(
        select(AccountabilityPartnership).where(
            or_(
                and_(
                    AccountabilityPartnership.initiator_id == user1_id,
                    AccountabilityPartnership.partner_id == user2_id,
                ),
                and_(
                    AccountabilityPartnership.initiator_id == user2_id,
                    AccountabilityPartnership.partner_id == user1_id,
                ),
            ),
            AccountabilityPartnership.status != AccountabilityStatus.ENDED,
            AccountabilityPartnership.not_deleted_filter(),
        )
    )
    partnerships = list(result.scalars().all())
    if not partnerships:
        return 0

    ended_at = _utcnow()
    for partnership in partnerships:
        partnership.status = AccountabilityStatus.ENDED
        partnership.ended_at = ended_at

    return len(partnerships)


async def _validate_group_mentions(
    db: AsyncSession,
    *,
    group_id: UUID,
    mention_user_ids: list[UUID] | None,
) -> list[str] | None:
    """Ensure all mentioned users are active group members before persisting mentions."""
    if not mention_user_ids:
        return None

    normalized_ids = []
    seen: set[str] = set()
    for user_id in mention_user_ids:
        user_id_str = str(user_id)
        if user_id_str not in seen:
            seen.add(user_id_str)
            normalized_ids.append(user_id_str)

    result = await db.execute(
        select(GroupMember.user_id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id.in_(mention_user_ids),
            GroupMember.not_deleted_filter(),
        )
    )
    member_ids = {str(user_id) for user_id in result.scalars().all()}
    if len(member_ids) != len(normalized_ids):
        raise ValueError("被提及用户必须是群组成员")

    return normalized_ids


class FriendshipService:
    """好友系统服务"""

    @staticmethod
    async def send_friend_request(
        db: AsyncSession,
        user_id: UUID,
        target_id: UUID,
        match_reason: dict | None = None
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

        canonical_user_ids = sorted([user_id, target_id], key=lambda value: str(value))
        await db.execute(
            select(User.id)
            .where(User.id.in_(canonical_user_ids))
            .order_by(User.id.asc())
            .with_for_update()
        )

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
        try:
            async with db.begin_nested():
                db.add(friendship)
                await db.flush()
        except IntegrityError:
            existing = await db.execute(
                select(Friendship).where(
                    Friendship.user_id == small_id,
                    Friendship.friend_id == large_id,
                    Friendship.not_deleted_filter(),
                )
            )
            existing_rel = existing.scalar_one_or_none()
            if existing_rel:
                if existing_rel.status == FriendshipStatus.PENDING and existing_rel.initiated_by == target_id:
                    existing_rel.status = FriendshipStatus.ACCEPTED
                    await db.flush()
                    await db.refresh(existing_rel)
                    return existing_rel
                if existing_rel.status == FriendshipStatus.BLOCKED:
                    raise ValueError("由于对方的隐私设置，无法发送请求")
                raise ValueError("已存在好友关系或待处理请求")
            raise

        await db.refresh(friendship)
        return friendship

    @staticmethod
    async def respond_to_request(
        db: AsyncSession,
        user_id: UUID,
        friendship_id: UUID,
        accept: bool
    ) -> Friendship | None:
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
    ) -> list[tuple[Friendship, User]]:
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
    async def are_friends(
        db: AsyncSession,
        user_id: UUID,
        target_id: UUID,
    ) -> bool:
        """Return whether two users have an active accepted friendship."""
        if user_id == target_id:
            return True

        small_id, large_id = sorted([user_id, target_id], key=lambda value: str(value))
        result = await db.execute(
            select(Friendship.id).where(
                Friendship.user_id == small_id,
                Friendship.friend_id == large_id,
                Friendship.status == FriendshipStatus.ACCEPTED,
                Friendship.not_deleted_filter(),
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_pending_requests(
        db: AsyncSession,
        user_id: UUID
    ) -> list[Friendship]:
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

    @staticmethod
    async def delete_friendship(
        db: AsyncSession,
        user_id: UUID,
        friendship_id: UUID
    ) -> bool:
        """
        删除好友关系

        - 双方都会解除好友关系
        - 不会拉黑对方
        """
        friendship = await Friendship.get_by_id(db, friendship_id)
        if not friendship:
            raise ValueError("好友关系不存在")

        # 验证当前用户是好友关系的一方
        if user_id not in (friendship.user_id, friendship.friend_id):
            raise ValueError("无权操作此好友关系")

        # 软删除好友关系
        await friendship.delete(db, soft=True)
        other_user_id = friendship.friend_id if friendship.user_id == user_id else friendship.user_id
        await _end_accountability_partnerships_between_users(db, user_id, other_user_id)
        await db.flush()
        return True


class GroupService:
    """群组服务"""

    @staticmethod
    async def _get_active_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupMember | None:
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _require_active_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupMember:
        member = await GroupService._get_active_member(db, group_id, user_id)
        if not member:
            raise ValueError("不是群组成员")
        return member

    @staticmethod
    def _can_manage_member(
        operator_role: GroupRole,
        target_role: GroupRole,
    ) -> bool:
        if operator_role == GroupRole.OWNER:
            return target_role != GroupRole.OWNER
        if operator_role == GroupRole.ADMIN:
            return target_role == GroupRole.MEMBER
        return False

    @staticmethod
    async def search_groups(
        db: AsyncSession,
        keyword: str | None = None,
        group_type: Any | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "latest",
        user_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """搜索公开群组并返回轻量列表数据。"""
        member_count_subquery = (
            select(
                GroupMember.group_id.label("group_id"),
                func.count(GroupMember.id).label("member_count"),
            )
            .where(GroupMember.not_deleted_filter())
            .group_by(GroupMember.group_id)
            .subquery()
        )
        recent_window_start = _utcnow() - timedelta(days=7)
        message_count_subquery = (
            select(
                GroupMessage.group_id.label("group_id"),
                func.count(GroupMessage.id).label("message_count"),
            )
            .where(
                GroupMessage.created_at >= recent_window_start,
                GroupMessage.not_deleted_filter(),
            )
            .group_by(GroupMessage.group_id)
            .subquery()
        )
        membership_subquery = None
        if user_id is not None:
            membership_subquery = (
                select(
                    GroupMember.group_id.label("group_id"),
                    GroupMember.role.label("my_role"),
                )
                .where(
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter(),
                )
                .subquery()
            )

        activity_score = (
            func.coalesce(message_count_subquery.c.message_count, 0) * 2
            + Group.today_checkin_count * 4
            + func.coalesce(member_count_subquery.c.member_count, 0)
            + (Group.total_flame_power / 100.0)
        )

        stmt = (
            select(
                Group,
                func.coalesce(member_count_subquery.c.member_count, 0).label("member_count"),
                func.coalesce(message_count_subquery.c.message_count, 0).label("message_count"),
                activity_score.label("activity_score"),
            )
            .outerjoin(member_count_subquery, member_count_subquery.c.group_id == Group.id)
            .outerjoin(message_count_subquery, message_count_subquery.c.group_id == Group.id)
            .where(Group.is_public.is_(True), Group.not_deleted_filter())
        )
        if membership_subquery is not None:
            stmt = stmt.add_columns(membership_subquery.c.my_role).outerjoin(
                membership_subquery,
                membership_subquery.c.group_id == Group.id,
            )

        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    Group.name.ilike(pattern),
                    Group.description.ilike(pattern),
                )
            )
        if group_type is not None:
            stmt = stmt.where(Group.type == group_type)
        if tags:
            stmt = stmt.where(Group.focus_tags.contains(tags))

        if sort_by == "hot":
            stmt = stmt.order_by(desc(activity_score), desc(Group.updated_at))
        elif sort_by == "random":
            stmt = stmt.order_by(func.random())
        else:
            stmt = stmt.order_by(desc(Group.created_at), desc(Group.updated_at))

        stmt = stmt.offset(offset).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()
        groups = []
        for row in rows:
            if membership_subquery is not None:
                group, member_count, message_count, score, my_role = row
            else:
                group, member_count, message_count, score = row
                my_role = None
            groups.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "type": group.type,
                    "member_count": int(member_count or 0),
                    "total_flame_power": group.total_flame_power,
                    "today_checkin_count": group.today_checkin_count,
                    "deadline": group.deadline,
                    "focus_tags": group.focus_tags or [],
                    "is_public": group.is_public,
                    "join_requires_approval": group.join_requires_approval,
                    "activity_score": float(score or 0.0),
                    "message_count_7d": int(message_count or 0),
                    "my_role": my_role,
                }
            )
        return groups

    @staticmethod
    async def count_public_groups(
        db: AsyncSession,
        keyword: str | None = None,
        group_type: Any | None = None,
        tags: list[str] | None = None,
    ) -> int:
        stmt = select(func.count(Group.id)).where(
            Group.is_public.is_(True),
            Group.not_deleted_filter(),
        )

        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    Group.name.ilike(pattern),
                    Group.description.ilike(pattern),
                )
            )
        if group_type is not None:
            stmt = stmt.where(Group.type == group_type)
        if tags:
            stmt = stmt.where(Group.focus_tags.contains(tags))

        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    @staticmethod
    async def get_public_group_tags(
        db: AsyncSession,
        *,
        limit: int = 24,
    ) -> list[str]:
        result = await db.execute(
            select(Group.focus_tags).where(
                Group.is_public.is_(True),
                Group.not_deleted_filter(),
            )
        )
        tag_counts: dict[str, int] = {}
        for tags in result.scalars().all():
            if not tags:
                continue
            for tag in tags:
                normalized = str(tag).strip()
                if not normalized:
                    continue
                tag_counts[normalized] = tag_counts.get(normalized, 0) + 1
        return [
            tag
            for tag, _ in sorted(
                tag_counts.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )[:limit]
        ]

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
            joined_at=_utcnow(),
            last_active_at=_utcnow()
        )
        db.add(owner)

        await db.flush()
        await db.refresh(group)
        return group

    @staticmethod
    async def get_group(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID | None = None
    ) -> dict[str, Any] | None:
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
            delta = group.deadline - _utcnow()
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
            'days_remaining': days_remaining,
            'announcement': group.announcement,
        }

    @staticmethod
    async def get_group_members(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> list[GroupMember]:
        """获取群成员列表，仅允许群成员查看。"""
        group = await Group.get_by_id(db, group_id)
        if not group or group.is_deleted:
            raise ValueError("群组不存在")

        await GroupService._require_active_member(db, group_id, user_id)

        result = await db.execute(
            select(GroupMember)
            .options(selectinload(GroupMember.user))
            .where(
                GroupMember.group_id == group_id,
                GroupMember.not_deleted_filter(),
            )
            .order_by(
                GroupMember.role.asc(),
                GroupMember.flame_contribution.desc(),
                GroupMember.joined_at.asc(),
            )
        )
        members = list(result.scalars().all())
        role_priority = {
            GroupRole.OWNER: 0,
            GroupRole.ADMIN: 1,
            GroupRole.MEMBER: 2,
        }
        members.sort(
            key=lambda member: (
                role_priority.get(member.role, 99),
                -(member.flame_contribution or 0),
                member.joined_at,
            )
        )
        return members

    @staticmethod
    async def join_group(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> GroupMember:
        """加入群组"""
        # 检查群组是否存在
        group_result = await db.execute(
            select(Group)
            .where(
                Group.id == group_id,
                Group.not_deleted_filter(),
            )
            .with_for_update()
        )
        group = group_result.scalar_one_or_none()
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
            joined_at=_utcnow(),
            last_active_at=_utcnow()
        )
        try:
            async with db.begin_nested():
                db.add(member)
                await db.flush()
        except IntegrityError:
            raise ValueError("已是群组成员")
        await db.refresh(member)
        _record_community_signal(
            user_id=user_id,
            action="join",
            context="group",
            timestamp=member.joined_at,
        )
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
    ) -> list[dict[str, Any]]:
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
                delta = group.deadline - _utcnow()
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

        deleted_at = _utcnow()
        active_group_files = (
            await db.execute(
                select(GroupFile.id, GroupFile.file_id, GroupFile.shared_by_id).where(
                    GroupFile.group_id == group_id,
                    GroupFile.not_deleted_filter(),
                )
            )
        ).all()

        # 2. 软删除群组
        await group.delete(db, soft=True)

        # 3. 软删除所有直接关联资源，避免产生僵尸数据
        await db.execute(
            update(GroupMember)
            .where(
                GroupMember.group_id == group_id,
                GroupMember.not_deleted_filter(),
            )
            .values(deleted_at=deleted_at)
        )
        await db.execute(
            update(GroupMessage)
            .where(
                GroupMessage.group_id == group_id,
                GroupMessage.not_deleted_filter(),
            )
            .values(deleted_at=deleted_at)
        )
        task_ids = select(GroupTask.id).where(GroupTask.group_id == group_id)
        await db.execute(
            update(GroupTaskClaim)
            .where(
                GroupTaskClaim.group_task_id.in_(task_ids),
                GroupTaskClaim.not_deleted_filter(),
            )
            .values(deleted_at=deleted_at)
        )
        await db.execute(
            update(GroupTask)
            .where(
                GroupTask.group_id == group_id,
                GroupTask.not_deleted_filter(),
            )
            .values(deleted_at=deleted_at)
        )
        await db.execute(
            update(GroupFile)
            .where(
                GroupFile.group_id == group_id,
                GroupFile.not_deleted_filter(),
            )
            .values(deleted_at=deleted_at)
        )
        await db.execute(
            update(SharedResource)
            .where(
                SharedResource.group_id == group_id,
                SharedResource.not_deleted_filter(),
            )
            .values(deleted_at=deleted_at)
        )
        for group_file_id, file_id, shared_by_id in active_group_files:
            event = GroupFileDeletedEvent(
                group_id=str(group_id),
                file_id=str(file_id),
                group_file_id=str(group_file_id),
                shared_by_user_id=str(shared_by_id),
                triggered_at=deleted_at.replace(tzinfo=timezone.utc).isoformat(),
            )
            await event_bus.publish(event.event_type, event.to_dict())

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
            db, group_id, "群主已转让给新成员"
        )

        return True

    @staticmethod
    async def kick_member(
        db: AsyncSession,
        group_id: UUID,
        operator_id: UUID,
        target_user_id: UUID,
    ) -> bool:
        """移出群成员。"""
        if operator_id == target_user_id:
            raise ValueError("不能移除自己，请使用退出群组")

        operator = await GroupService._require_active_member(db, group_id, operator_id)
        target = await GroupService._get_active_member(db, group_id, target_user_id)
        if not target:
            raise ValueError("目标用户不是群成员")
        if not GroupService._can_manage_member(operator.role, target.role):
            raise ValueError("无权移除此成员")

        await target.delete(db, soft=True)
        await GroupMessageService.send_system_message(
            db,
            group_id,
            f"成员已被移出群组：{target.nickname or target.username}",
        )
        return True

    @staticmethod
    async def promote_member(
        db: AsyncSession,
        group_id: UUID,
        operator_id: UUID,
        target_user_id: UUID,
    ) -> GroupMember:
        """将成员提升为管理员，仅群主可操作。"""
        operator = await GroupService._require_active_member(db, group_id, operator_id)
        if operator.role != GroupRole.OWNER:
            raise ValueError("只有群主可以提升管理员")

        target = await GroupService._get_active_member(db, group_id, target_user_id)
        if not target:
            raise ValueError("目标用户不是群成员")
        if target.role == GroupRole.OWNER:
            raise ValueError("不能修改群主角色")
        if target.role == GroupRole.ADMIN:
            return target

        target.role = GroupRole.ADMIN
        await db.flush()
        await GroupMessageService.send_system_message(
            db,
            group_id,
            f"成员已晋升为管理员：{target.user_id}",
        )
        return target

    @staticmethod
    async def demote_member(
        db: AsyncSession,
        group_id: UUID,
        operator_id: UUID,
        target_user_id: UUID,
    ) -> GroupMember:
        """将管理员降级为普通成员，仅群主可操作。"""
        operator = await GroupService._require_active_member(db, group_id, operator_id)
        if operator.role != GroupRole.OWNER:
            raise ValueError("只有群主可以调整管理员角色")

        target = await GroupService._get_active_member(db, group_id, target_user_id)
        if not target:
            raise ValueError("目标用户不是群成员")
        if target.role == GroupRole.OWNER:
            raise ValueError("不能修改群主角色")
        if target.role == GroupRole.MEMBER:
            return target

        target.role = GroupRole.MEMBER
        await db.flush()
        await GroupMessageService.send_system_message(
            db,
            group_id,
            f"管理员已调整为普通成员：{target.user_id}",
        )
        return target


class GroupKnowledgeService:
    """Group knowledge-base and collaborative galaxy projection service."""

    @staticmethod
    async def _require_moderator_member(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupMember:
        member = await GroupService._require_active_member(db, group_id, user_id)
        if member.role not in (GroupRole.ADMIN, GroupRole.OWNER):
            raise ValueError("需要群管理员或群主权限")
        return member

    @staticmethod
    async def _load_group_file(
        db: AsyncSession,
        group_id: UUID,
        file_id: UUID,
    ) -> GroupFile | None:
        result = await db.execute(
            select(GroupFile)
            .options(
                selectinload(GroupFile.file),
                selectinload(GroupFile.shared_by),
            )
            .where(
                GroupFile.group_id == group_id,
                GroupFile.file_id == file_id,
                GroupFile.not_deleted_filter(),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _ensure_group_collaborative_galaxy(
        db: AsyncSession,
        group_id: UUID,
        created_by: UUID,
    ) -> CollaborativeGalaxy:
        result = await db.execute(
            select(CollaborativeGalaxy).where(
                CollaborativeGalaxy.group_id == group_id,
                CollaborativeGalaxy.not_deleted_filter(),
            )
        )
        galaxy = result.scalar_one_or_none()
        if galaxy:
            return galaxy

        group = await Group.get_by_id(db, group_id)
        if not group:
            raise ValueError("群组不存在")

        galaxy = CollaborativeGalaxy(
            name=f"{group.name} Knowledge Galaxy",
            description=group.description,
            created_by=created_by,
            group_id=group_id,
            galaxy_scope="group_knowledge",
            visibility="shared",
        )
        db.add(galaxy)
        await db.flush()
        return galaxy

    @staticmethod
    def _knowledge_base_ordering():
        trust_rank = case(
            (GroupFile.trust_level == GroupFileTrustLevel.OFFICIAL, 3),
            (GroupFile.trust_level == GroupFileTrustLevel.VERIFIED, 2),
            else_=1,
        )
        rating_value = case(
            (GroupFile.rating_count > 0, GroupFile.rating_total / GroupFile.rating_count),
            else_=0.0,
        )
        return [
            desc(trust_rank),
            desc(GroupFile.citation_count),
            desc(rating_value),
            desc(GroupFile.download_count),
            desc(GroupFile.created_at),
        ]

    @staticmethod
    async def designate_official_document(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        file_id: UUID,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[GroupFile, CollaborativeGalaxy]:
        await GroupKnowledgeService._require_moderator_member(db, group_id, user_id)

        group_file = await GroupKnowledgeService._load_group_file(db, group_id, file_id)
        if group_file is None:
            stored_file = await StoredFile.get_by_id(db, file_id)
            if stored_file is None:
                raise ValueError("文件不存在")
            if stored_file.user_id != user_id:
                raise ValueError("只能将已共享到群组的文件或你自己的文件加入知识库")
            group_file, _, _ = await GroupFileService.share_file(
                db,
                group_id=group_id,
                user_id=user_id,
                file_id=file_id,
                category=category,
                description=None,
                tags=tags,
                view_role=GroupRole.MEMBER,
                download_role=GroupRole.MEMBER,
                manage_role=GroupRole.ADMIN,
                trust_level=GroupFileTrustLevel.OFFICIAL,
                is_knowledge_base=True,
            )
        else:
            if category is not None:
                group_file.category = category
            if tags is not None:
                group_file.tags = tags
            group_file.trust_level = GroupFileTrustLevel.OFFICIAL
            group_file.is_knowledge_base = True
            group_file.view_role = GroupRole.MEMBER
            group_file.download_role = GroupRole.MEMBER
            group_file.manage_role = GroupRole.ADMIN
            db.add(group_file)
            await db.flush()

        galaxy = await GroupKnowledgeService._ensure_group_collaborative_galaxy(db, group_id, user_id)
        loaded = await GroupKnowledgeService._load_group_file(db, group_id, file_id)
        if loaded is None:
            raise ValueError("知识库文档加载失败")
        return loaded, galaxy

    @staticmethod
    async def _list_knowledge_base_documents_for_member(
        db: AsyncSession,
        group_id: UUID,
        member_role: GroupRole,
    ) -> list[GroupFile]:
        allowed_roles = GroupFileService._allowed_roles(member_role)
        result = await db.execute(
            select(GroupFile)
            .options(
                selectinload(GroupFile.file),
                selectinload(GroupFile.shared_by),
            )
            .where(
                GroupFile.group_id == group_id,
                GroupFile.is_knowledge_base.is_(True),
                GroupFile.not_deleted_filter(),
                GroupFile.view_role.in_(allowed_roles),
            )
            .order_by(*GroupKnowledgeService._knowledge_base_ordering())
        )
        return list(result.scalars().all())

    @staticmethod
    def _knowledge_base_stats(documents: list[GroupFile]) -> GroupKnowledgeBaseStats:
        total_rating = sum(float(doc.rating_total or 0.0) for doc in documents)
        total_rating_count = sum(int(doc.rating_count or 0) for doc in documents)
        average_rating = round(total_rating / total_rating_count, 2) if total_rating_count else None
        return GroupKnowledgeBaseStats(
            total_documents=len(documents),
            official_count=sum(1 for doc in documents if doc.trust_level == GroupFileTrustLevel.OFFICIAL),
            verified_count=sum(1 for doc in documents if doc.trust_level == GroupFileTrustLevel.VERIFIED),
            member_count=sum(1 for doc in documents if doc.trust_level == GroupFileTrustLevel.MEMBER),
            total_downloads=sum(int(doc.download_count or 0) for doc in documents),
            total_citations=sum(int(doc.citation_count or 0) for doc in documents),
            average_rating=average_rating,
        )

    @staticmethod
    async def get_knowledge_base(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> tuple[list[GroupFile], GroupKnowledgeBaseStats, CollaborativeGalaxy | None]:
        member = await GroupService._require_active_member(db, group_id, user_id)
        documents = await GroupKnowledgeService._list_knowledge_base_documents_for_member(db, group_id, member.role)
        galaxy = None
        if documents:
            galaxy = await GroupKnowledgeService._ensure_group_collaborative_galaxy(db, group_id, user_id)
        return documents, GroupKnowledgeService._knowledge_base_stats(documents), galaxy

    @staticmethod
    def _document_node_id(file_id: UUID) -> str:
        return f"doc:{file_id}"

    @staticmethod
    def _knowledge_node_id(node_id: UUID) -> str:
        return f"kn:{node_id}"

    @staticmethod
    def _polar_position(index: int, total: int, radius: float) -> tuple[float, float]:
        if total <= 0:
            return 0.0, 0.0
        angle = (2 * math.pi * index) / total
        return round(math.cos(angle) * radius, 2), round(math.sin(angle) * radius, 2)

    @staticmethod
    async def get_group_galaxy(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
    ) -> GroupCollaborativeGalaxyResponse:
        member = await GroupService._require_active_member(db, group_id, user_id)
        documents = await GroupKnowledgeService._list_knowledge_base_documents_for_member(db, group_id, member.role)
        galaxy = await GroupKnowledgeService._ensure_group_collaborative_galaxy(db, group_id, user_id)

        nodes: list[GroupCollaborativeGalaxyNode] = []
        relations: list[GroupCollaborativeGalaxyRelation] = []

        if not documents:
            return GroupCollaborativeGalaxyResponse(
                galaxy_id=galaxy.id,
                group_id=group_id,
                name=galaxy.name,
                scope=galaxy.galaxy_scope,
                nodes=[],
                relations=[],
                edges=[],
                stats=GroupCollaborativeGalaxyStats(),
            )

        file_map = {doc.file_id: doc for doc in documents}
        doc_positions: dict[UUID, tuple[float, float]] = {}
        for index, group_file in enumerate(documents):
            pos_x, pos_y = GroupKnowledgeService._polar_position(index, len(documents), 240.0)
            doc_positions[group_file.file_id] = (pos_x, pos_y)
            nodes.append(
                GroupCollaborativeGalaxyNode(
                    id=GroupKnowledgeService._document_node_id(group_file.file_id),
                    label=group_file.file.file_name if group_file.file else str(group_file.file_id),
                    node_type="document",
                    trust_level=group_file.trust_level.value,
                    knowledge_base=group_file.is_knowledge_base,
                    file_id=group_file.file_id,
                    source_document_id=group_file.file_id,
                    category=group_file.category,
                    tags=list(group_file.tags or []),
                    quality_score=GroupFileService.quality_score(group_file),
                    citation_count=int(group_file.citation_count or 0),
                    download_count=int(group_file.download_count or 0),
                    average_rating=GroupFileService.average_rating(group_file),
                    position_x=pos_x,
                    position_y=pos_y,
                )
            )

        file_ids = list(file_map.keys())
        node_ids_by_file: dict[UUID, set[UUID]] = {}
        node_result = await db.execute(
            select(KnowledgeNode)
            .options(selectinload(KnowledgeNode.parent))
            .where(
                KnowledgeNode.not_deleted_filter(),
                or_(
                    KnowledgeNode.source_file_id.in_(file_ids),
                    KnowledgeNode.id.in_(
                        select(KnowledgeNodeDocument.node_id).where(
                            KnowledgeNodeDocument.file_id.in_(file_ids),
                            KnowledgeNodeDocument.deleted_at.is_(None),
                        )
                    ),
                ),
            )
        )
        knowledge_nodes = list(node_result.scalars().all())

        for node in knowledge_nodes:
            linked_file_ids: set[UUID] = set()
            if node.source_file_id in file_map:
                linked_file_ids.add(node.source_file_id)
            node_ids_by_file.setdefault(node.source_file_id, set()) if node.source_file_id in file_map else None

            link_rows = await db.execute(
                select(KnowledgeNodeDocument.file_id).where(
                    KnowledgeNodeDocument.node_id == node.id,
                    KnowledgeNodeDocument.file_id.in_(file_ids),
                    KnowledgeNodeDocument.deleted_at.is_(None),
                )
            )
            linked_file_ids.update(link_rows.scalars().all())
            if not linked_file_ids:
                continue

            primary_file_id = sorted(linked_file_ids, key=str)[0]
            primary_doc = file_map[primary_file_id]
            base_x, base_y = doc_positions[primary_file_id]
            concept_index = len(node_ids_by_file.setdefault(primary_file_id, set()))
            offset_x, offset_y = GroupKnowledgeService._polar_position(concept_index, max(len(linked_file_ids), 1), 90.0)
            node_ids_by_file[primary_file_id].add(node.id)

            nodes.append(
                GroupCollaborativeGalaxyNode(
                    id=GroupKnowledgeService._knowledge_node_id(node.id),
                    label=node.name,
                    node_type="knowledge_node",
                    trust_level=primary_doc.trust_level.value,
                    knowledge_base=True,
                    file_id=primary_file_id,
                    source_document_id=primary_file_id,
                    category=primary_doc.category,
                    tags=list(node.keywords or []),
                    quality_score=GroupFileService.quality_score(primary_doc),
                    citation_count=int(primary_doc.citation_count or 0),
                    download_count=int(primary_doc.download_count or 0),
                    average_rating=GroupFileService.average_rating(primary_doc),
                    position_x=round(base_x * 0.55 + offset_x, 2),
                    position_y=round(base_y * 0.55 + offset_y, 2),
                )
            )

            for linked_file_id in sorted(linked_file_ids, key=str):
                relations.append(
                    GroupCollaborativeGalaxyRelation(
                        source_id=GroupKnowledgeService._document_node_id(linked_file_id),
                        target_id=GroupKnowledgeService._knowledge_node_id(node.id),
                        relation_type="contains",
                        strength=1.0,
                    )
                )

        knowledge_node_ids = [node.id for node in knowledge_nodes]
        if knowledge_node_ids:
            relation_result = await db.execute(
                select(NodeRelation).where(
                    NodeRelation.not_deleted_filter(),
                    NodeRelation.source_node_id.in_(knowledge_node_ids),
                    NodeRelation.target_node_id.in_(knowledge_node_ids),
                )
            )
            for relation in relation_result.scalars().all():
                relations.append(
                    GroupCollaborativeGalaxyRelation(
                        source_id=GroupKnowledgeService._knowledge_node_id(relation.source_node_id),
                        target_id=GroupKnowledgeService._knowledge_node_id(relation.target_node_id),
                        relation_type=relation.relation_type,
                        strength=float(relation.strength or 0.5),
                    )
                )

        for left_index, left_doc in enumerate(documents):
            left_tags = set(left_doc.tags or [])
            for right_doc in documents[left_index + 1 :]:
                shared_tags = left_tags & set(right_doc.tags or [])
                same_category = bool(left_doc.category and left_doc.category == right_doc.category)
                if not shared_tags and not same_category:
                    continue
                relations.append(
                    GroupCollaborativeGalaxyRelation(
                        source_id=GroupKnowledgeService._document_node_id(left_doc.file_id),
                        target_id=GroupKnowledgeService._document_node_id(right_doc.file_id),
                        relation_type="shared_topic" if shared_tags else "shared_category",
                        strength=round(min(1.0, 0.35 + 0.15 * len(shared_tags) + (0.25 if same_category else 0.0)), 2),
                    )
                )

        deduped_relations: dict[tuple[str, str, str], GroupCollaborativeGalaxyRelation] = {}
        for relation in relations:
            key = (relation.source_id, relation.target_id, relation.relation_type)
            existing = deduped_relations.get(key)
            if existing is None or relation.strength > existing.strength:
                deduped_relations[key] = relation
        relations = list(deduped_relations.values())

        concept_nodes = sum(1 for node in nodes if node.node_type == "knowledge_node")
        stats = GroupCollaborativeGalaxyStats(
            total_nodes=len(nodes),
            document_nodes=len(documents),
            concept_nodes=concept_nodes,
            total_relations=len(relations),
        )
        return GroupCollaborativeGalaxyResponse(
            galaxy_id=galaxy.id,
            group_id=group_id,
            name=galaxy.name,
            scope=galaxy.galaxy_scope,
            nodes=nodes,
            relations=relations,
            edges=relations,
            stats=stats,
        )


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

        # Slow mode enforcement
        group = await db.get(Group, group_id)
        if group and group.slow_mode_seconds and group.slow_mode_seconds > 0:
            if member.last_active_at:
                elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - member.last_active_at).total_seconds()
                if elapsed < group.slow_mode_seconds:
                    raise ValueError(f"慢速模式：请等待 {int(group.slow_mode_seconds - elapsed)} 秒后再发送")

        # Keyword filter enforcement
        from app.services.community_advanced_service import ModerationService

        keyword_ok, matched = await ModerationService.check_keyword_filter(db, group_id, data.content)
        if not keyword_ok:
            raise ValueError(f"消息包含不允许的关键词：{', '.join(matched)}")

        if data.reply_to_id:
            reply_msg = await db.get(GroupMessage, data.reply_to_id)
            if not reply_msg or reply_msg.group_id != group_id or reply_msg.is_deleted:
                raise ValueError("回复消息不存在")
            if reply_msg.is_revoked:
                raise ValueError("不能回复已撤回的消息")

        if data.thread_root_id:
            root_msg = await db.get(GroupMessage, data.thread_root_id)
            if not root_msg or root_msg.group_id != group_id or root_msg.is_deleted:
                raise ValueError("线程根消息不存在")
            if root_msg.is_revoked:
                raise ValueError("不能在线程中回复已撤回的消息")

        mention_user_ids = await _validate_group_mentions(
            db,
            group_id=group_id,
            mention_user_ids=data.mention_user_ids,
        )

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
        member.last_active_at = _utcnow()

        await db.flush()
        action = "comment" if (message.reply_to_id or message.thread_root_id) else "post"
        _record_community_signal(
            user_id=sender_id,
            action=action,
            context="group",
            timestamp=message.created_at,
        )

        # Re-fetch with relationships to ensure reply_to is loaded
        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).where(GroupMessage.id == message.id).execution_options(populate_existing=True)

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
            msg.mention_user_ids = await _validate_group_mentions(
                db,
                group_id=group_id,
                mention_user_ids=data.mention_user_ids,
            )

        if msg.message_type == MessageType.TEXT and not msg.content:
            raise ValueError("文本消息必须有内容")

        msg.edited_at = _utcnow()
        db.add(msg)
        await db.flush()

        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).where(GroupMessage.id == msg.id).execution_options(populate_existing=True)
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

        if is_sender and (_utcnow() - msg.created_at).total_seconds() > 86400:
            raise ValueError("超过撤回时限")

        if msg.is_revoked:
            return msg

        msg.is_revoked = True
        msg.revoked_at = _utcnow()
        msg.content = None
        msg.content_data = None
        msg.reactions = None
        db.add(msg)
        await db.flush()

        # 发送WebSocket通知给群组成员
        await manager.broadcast({
            "type": "group_message_revoke",
            "message_id": str(message_id),
            "group_id": str(group_id),
            "revoked_by": str(user_id),
            "revoked_at": msg.revoked_at.isoformat()
        }, str(group_id))

        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).where(GroupMessage.id == msg.id).execution_options(populate_existing=True)
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
        if is_add:
            _record_community_signal(
                user_id=user_id,
                action="like",
                context="group",
                timestamp=msg.updated_at or _utcnow(),
            )

        stmt = select(GroupMessage).options(
            selectinload(GroupMessage.sender),
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).where(GroupMessage.id == msg.id).execution_options(populate_existing=True)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_thread_messages(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        thread_root_id: UUID,
        limit: int = 100
    ) -> list[GroupMessage]:
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
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).where(GroupMessage.id == thread_root_id).execution_options(populate_existing=True)
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
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).order_by(GroupMessage.created_at.asc()).limit(limit).execution_options(populate_existing=True)

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
    ) -> list[GroupMessage]:
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
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).order_by(desc(GroupMessage.created_at)).limit(limit).execution_options(populate_existing=True)

        result = await db.execute(query)
        return [msg for msg in result.scalars().all() if _is_visible_to(msg.content_data, user_id)]

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID, # Added user_id for permission check
        before_id: UUID | None = None,
        limit: int = 50
    ) -> list[GroupMessage]:
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
            selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
            selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
        ).order_by(desc(GroupMessage.created_at)).execution_options(populate_existing=True)

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
    async def mark_as_read(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        up_to_message_id: UUID,
    ) -> tuple[int, GroupMessage]:
        """标记群消息已读到某条消息。"""
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
            )
        )
        if not membership_result.scalar_one_or_none():
            raise ValueError("不是群组成员，无法标记已读")

        target_stmt = (
            select(GroupMessage)
            .options(
                selectinload(GroupMessage.sender),
                selectinload(GroupMessage.reply_to).selectinload(GroupMessage.sender),
                selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
            )
            .where(
                GroupMessage.id == up_to_message_id,
                GroupMessage.group_id == group_id,
                GroupMessage.not_deleted_filter(),
            )
        )
        target_result = await db.execute(target_stmt)
        target_message = target_result.scalar_one_or_none()
        if not target_message:
            raise ValueError("消息不存在")
        if not _is_visible_to(target_message.content_data, user_id):
            raise ValueError("消息不可见")

        messages_stmt = (
            select(GroupMessage)
            .options(
                selectinload(GroupMessage.read_receipts).selectinload(GroupMessageRead.user),
            )
            .where(
                GroupMessage.group_id == group_id,
                GroupMessage.created_at <= target_message.created_at,
                GroupMessage.not_deleted_filter(),
            )
            .order_by(GroupMessage.created_at.asc())
        )
        messages_result = await db.execute(messages_stmt)
        updated_count = 0
        for message in messages_result.scalars().all():
            if message.sender_id == user_id:
                continue
            if not _is_visible_to(message.content_data, user_id):
                continue
            already_read = any(receipt.user_id == user_id for receipt in message.read_receipts)
            if already_read:
                continue
            db.add(
                GroupMessageRead(
                    message_id=message.id,
                    user_id=user_id,
                    read_at=_utcnow(),
                )
            )
            updated_count += 1

        await db.flush()
        refreshed_target = await db.execute(
            target_stmt.execution_options(populate_existing=True)
        )
        return updated_count, refreshed_target.scalar_one()

    @staticmethod
    async def send_system_message(
        db: AsyncSession,
        group_id: UUID,
        content: str,
        content_data: dict | None = None
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
    ) -> dict[str, Any]:
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
        today = _utcnow().date()
        if member.last_checkin_date and member.last_checkin_date.date() == today:
            raise ValueError("今日已打卡")

        # 计算连续打卡天数
        yesterday = today - timedelta(days=1)
        if member.last_checkin_date and member.last_checkin_date.date() == yesterday:
            member.checkin_streak += 1
        else:
            member.checkin_streak = 1

        member.last_checkin_date = _utcnow()

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
            .options(selectinload(GroupTask.group))
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
        from app.models.task import Task, TaskStatus, TaskType as PersonalTaskType
        from app.services.task_service import TaskService

        # 转换日期 (DateTime -> Date)
        personal_due_date = group_task.due_date.date() if group_task.due_date else None
        linked_plan_id = None
        if group_task.group and group_task.group.type == GroupType.SPRINT:
            linked_plan_result = await db.execute(
                select(Plan.id)
                .where(
                    Plan.user_id == user_id,
                    Plan.is_active.is_(True),
                    Plan.type == PlanType.SPRINT,
                )
                .order_by(desc(Plan.is_primary), desc(Plan.created_at))
                .limit(1)
            )
            linked_plan_id = linked_plan_result.scalar_one_or_none()

        try:
            async with db.begin_nested():
                personal_task = Task(
                    user_id=user_id,
                    plan_id=linked_plan_id,
                    title=f"[{group_task.group.name}] {group_task.title}" if group_task.group else f"[群任务] {group_task.title}",
                    type=PersonalTaskType.LEARNING,
                    tags=group_task.tags or [],
                    estimated_minutes=group_task.estimated_minutes,
                    difficulty=group_task.difficulty,
                    priority=2,
                    due_date=personal_due_date,
                    order_index=await TaskService._next_top_order_index(db, user_id),
                    status=TaskStatus.PENDING,
                )
                db.add(personal_task)
                await db.flush()

                claim = GroupTaskClaim(
                    group_task_id=task_id,
                    user_id=user_id,
                    personal_task_id=personal_task.id,
                    claimed_at=_utcnow()
                )
                db.add(claim)

                # 更新认领计数
                group_task.total_claims += 1
                await db.flush()
        except IntegrityError:
            raise ValueError("已认领此任务")

        await db.refresh(claim)
        return claim

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        claim_id: UUID
    ) -> GroupTaskClaim | None:
        """
        完成群任务（由个人任务完成时触发）

        数据一致性保护：
        - 使用 SAVEPOINT 确保原子性
        - 使用 SELECT FOR UPDATE 锁定相关行防止并发问题
        - 确保群任务、成员统计、群组统计在同一事务中更新
        """
        # 使用 SAVEPOINT 确保操作原子性
        async with db.begin_nested():
            # 锁定认领记录
            claim_result = await db.execute(
                select(GroupTaskClaim)
                .where(GroupTaskClaim.id == claim_id)
                .with_for_update()
            )
            claim = claim_result.scalar_one_or_none()

            if not claim or claim.is_completed:
                return claim

            # 锁定群任务
            group_task_result = await db.execute(
                select(GroupTask)
                .where(GroupTask.id == claim.group_task_id)
                .with_for_update()
            )
            group_task = group_task_result.scalar_one_or_none()

            if not group_task:
                raise ValueError("群任务不存在")

            # 锁定群成员记录
            member_result = await db.execute(
                select(GroupMember)
                .where(
                    GroupMember.group_id == group_task.group_id,
                    GroupMember.user_id == claim.user_id,
                    GroupMember.not_deleted_filter()
                )
                .with_for_update()
            )
            member = member_result.scalar_one_or_none()

            # 锁定群组
            group_result = await db.execute(
                select(Group)
                .where(Group.id == group_task.group_id)
                .with_for_update()
            )
            group = group_result.scalar_one_or_none()

            if not group:
                raise ValueError("群组不存在")

            # 更新认领记录
            claim.is_completed = True
            claim.completed_at = _utcnow()

            # 更新群任务完成计数
            group_task.total_completions += 1

            # 更新成员完成任务数
            if member:
                member.tasks_completed += 1

            # 更新群组统计
            group.total_tasks_completed += 1

            await db.flush()

        return claim

    @staticmethod
    async def get_group_tasks(
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """获取群任务列表"""
        result = await db.execute(
            select(GroupTask).where(
                GroupTask.group_id == group_id,
                GroupTask.not_deleted_filter()
            ).options(
                selectinload(GroupTask.creator)
                # 注意：不使用 selectinload(GroupTask.claims)
                # 因为模型中配置了 lazy="dynamic"，与 selectinload 不兼容
                # 改为在循环中按需查询或使用统计字段
            ).order_by(desc(GroupTask.created_at))
        )

        task_rows = result.scalars().all()
        user_claims_by_task: dict[UUID, GroupTaskClaim] = {}
        if user_id and task_rows:
            claim_result = await db.execute(
                select(GroupTaskClaim).where(
                    GroupTaskClaim.group_task_id.in_([task.id for task in task_rows]),
                    GroupTaskClaim.user_id == user_id,
                    GroupTaskClaim.not_deleted_filter()
                )
            )
            user_claims_by_task = {
                claim.group_task_id: claim for claim in claim_result.scalars().all()
            }

        tasks = []
        for task in task_rows:
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
                user_claim = user_claims_by_task.get(task.id)
                if user_claim:
                    task_dict['is_claimed_by_me'] = True
                    task_dict['my_completion_status'] = user_claim.is_completed

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
        from app.models.community import Friendship, FriendshipStatus, PrivateMessage

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
            if reply_msg.is_revoked:
                raise ValueError("不能回复已撤回的消息")
            if sender_id not in [reply_msg.sender_id, reply_msg.receiver_id]:
                raise ValueError("不能回复非会话内消息")

        if data.thread_root_id:
            root_msg = await db.get(PrivateMessage, data.thread_root_id)
            if not root_msg or root_msg.is_deleted:
                raise ValueError("线程根消息不存在")
            if root_msg.is_revoked:
                raise ValueError("不能在线程中回复已撤回的消息")
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
            created_at=_utcnow()
        )
        db.add(message)
        await db.flush()
        _record_community_signal(
            user_id=sender_id,
            action="dm",
            context="direct",
            timestamp=message.created_at,
        )

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

        msg.edited_at = _utcnow()
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
        from app.schemas.community import MESSAGE_REVOKE_TIME_LIMIT_SECONDS

        msg = await db.get(PrivateMessage, message_id)
        if not msg or msg.is_deleted:
            raise ValueError("消息不存在")
        if msg.sender_id != user_id:
            raise ValueError("无权限撤回该消息")
        if msg.is_revoked:
            return msg

        # 使用配置的撤回时间限制
        revoke_time_limit = MESSAGE_REVOKE_TIME_LIMIT_SECONDS
        if (_utcnow() - msg.created_at).total_seconds() > revoke_time_limit:
            raise ValueError(f"超过撤回时限（{revoke_time_limit // 60}分钟内可撤回）")

        msg.is_revoked = True
        msg.revoked_at = _utcnow()
        msg.content = None
        msg.content_data = None
        msg.reactions = None
        db.add(msg)
        await db.flush()

        # 发送WebSocket通知给接收方
        await manager.send_personal_message({
            "type": "private_message_revoke",
            "message_id": str(message_id),
            "revoked_by": str(user_id),
            "revoked_at": msg.revoked_at.isoformat(),
            "conversation_id": str(msg.sender_id) if str(msg.sender_id) < str(msg.receiver_id) else str(msg.receiver_id)
        }, str(msg.receiver_id))

        # 也通知发送方（如果发送方和接收方不同）
        if msg.sender_id != msg.receiver_id:
            await manager.send_personal_message({
                "type": "private_message_revoke",
                "message_id": str(message_id),
                "revoked_by": str(user_id),
                "revoked_at": msg.revoked_at.isoformat(),
                "conversation_id": str(msg.sender_id) if str(msg.sender_id) < str(msg.receiver_id) else str(msg.receiver_id)
            }, str(msg.sender_id))

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
    ) -> list[Any]:
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
        before_id: UUID | None = None,
        limit: int = 50
    ) -> list[Any]: # List[PrivateMessage]
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
        from sqlalchemy import and_, update

        from app.models.community import PrivateMessage

        stmt = update(PrivateMessage).where(
            and_(
                PrivateMessage.receiver_id == user_id,
                PrivateMessage.sender_id == sender_id,
                PrivateMessage.is_read == False
            )
        ).values(
            is_read=True,
            read_at=_utcnow()
        )

        result = await db.execute(stmt)
        return result.rowcount


class UserBlockService:
    """用户拉黑服务"""

    @staticmethod
    async def block_user(
        db: AsyncSession,
        blocker_id: UUID,
        blocked_id: UUID,
        reason: str | None = None
    ) -> UserBlock:
        """
        拉黑用户

        逻辑说明：
        1. 检查是否已拉黑
        2. 自动解除好友关系
        3. 创建拉黑记录
        """
        if blocker_id == blocked_id:
            raise ValueError("不能拉黑自己")

        # 检查是否已拉黑（包括软删除的记录）
        existing = await db.execute(
            select(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        existing_block = existing.scalar_one_or_none()

        if existing_block:
            if existing_block.deleted_at is None:
                raise ValueError("已拉黑该用户")
            # 恢复已解除的拉黑
            existing_block.deleted_at = None
            existing_block.reason = reason
            await db.flush()
            await db.refresh(existing_block)
        else:
            existing_block = UserBlock(
                blocker_id=blocker_id,
                blocked_id=blocked_id,
                reason=reason
            )
            db.add(existing_block)
            await db.flush()
            await db.refresh(existing_block)

        # 自动解除好友关系
        if str(blocker_id) < str(blocked_id):
            small_id, large_id = blocker_id, blocked_id
        else:
            small_id, large_id = blocked_id, blocker_id

        friendship = await db.execute(
            select(Friendship).where(
                Friendship.user_id == small_id,
                Friendship.friend_id == large_id,
                Friendship.not_deleted_filter()
            )
        )
        existing_friendship = friendship.scalar_one_or_none()
        if existing_friendship:
            existing_friendship.soft_delete()

        await _end_accountability_partnerships_between_users(db, blocker_id, blocked_id)
        await db.flush()
        return existing_block

    @staticmethod
    async def unblock_user(
        db: AsyncSession,
        blocker_id: UUID,
        blocked_id: UUID
    ) -> bool:
        """
        解除拉黑

        Returns:
            是否成功解除
        """
        existing = await db.execute(
            select(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
                UserBlock.not_deleted_filter()
            )
        )
        existing_block = existing.scalar_one_or_none()

        if not existing_block:
            raise ValueError("未拉黑该用户")

        existing_block.soft_delete()
        await db.flush()
        return True

    @staticmethod
    async def get_blocked_users(
        db: AsyncSession,
        blocker_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> list[UserBlock]:
        """获取拉黑列表"""
        result = await db.execute(
            select(UserBlock)
            .where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.not_deleted_filter()
            )
            .options(selectinload(UserBlock.blocked))
            .order_by(desc(UserBlock.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def is_blocked(
        db: AsyncSession,
        user_id: UUID,
        target_id: UUID
    ) -> bool:
        """
        检查用户是否被目标用户拉黑

        Returns:
            True 如果 target_id 拉黑了 user_id
        """
        result = await db.execute(
            select(UserBlock).where(
                UserBlock.blocker_id == target_id,
                UserBlock.blocked_id == user_id,
                UserBlock.not_deleted_filter()
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def has_block_relationship(
        db: AsyncSession,
        user1_id: UUID,
        user2_id: UUID
    ) -> bool:
        """
        检查两个用户之间是否存在拉黑关系（任一方拉黑另一方）

        Returns:
            True 如果任一方拉黑了另一方
        """
        result = await db.execute(
            select(UserBlock).where(
                or_(
                    and_(
                        UserBlock.blocker_id == user1_id,
                        UserBlock.blocked_id == user2_id,
                        UserBlock.not_deleted_filter()
                    ),
                    and_(
                        UserBlock.blocker_id == user2_id,
                        UserBlock.blocked_id == user1_id,
                        UserBlock.not_deleted_filter()
                    )
                )
            )
        )
        return result.scalar_one_or_none() is not None


class UserSearchService:
    """用户搜索服务（带隐私控制）"""

    @staticmethod
    async def search_users(
        db: AsyncSession,
        query: str,
        current_user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> list[User]:
        """
        搜索用户（带隐私过滤）

        逻辑说明：
        1. 过滤不可搜索的用户
        2. 过滤已拉黑当前用户的用户
        3. 按匹配度排序
        """
        from app.models.user import SearchVisibility

        # 获取当前用户的好友ID列表
        friends_result = await db.execute(
            select(Friendship).where(
                or_(
                    Friendship.user_id == current_user_id,
                    Friendship.friend_id == current_user_id
                ),
                Friendship.status == FriendshipStatus.ACCEPTED,
                Friendship.not_deleted_filter()
            )
        )
        friends = friends_result.scalars().all()
        friend_ids = set()
        for f in friends:
            if f.user_id == current_user_id:
                friend_ids.add(f.friend_id)
            else:
                friend_ids.add(f.user_id)

        # 构建查询
        search_query = select(User).where(
            User.is_active == True,
            User.id != current_user_id,
            or_(
                User.username.ilike(f"%{query}%"),
                User.nickname.ilike(f"%{query}%"),
                User.full_name.ilike(f"%{query}%")
            )
        )

        # 执行查询
        result = await db.execute(search_query.limit(limit).offset(offset))
        users = list(result.scalars().all())

        # 过滤不可搜索的用户
        filtered_users = []
        for user in users:
            # 检查隐私设置
            if user.searchable_by == SearchVisibility.NOBODY:
                continue
            if user.searchable_by == SearchVisibility.FRIENDS and user.id not in friend_ids:
                continue

            # 检查拉黑关系
            if await UserBlockService.has_block_relationship(db, current_user_id, user.id):
                continue

            filtered_users.append(user)

        return filtered_users

    @staticmethod
    async def get_user_searchability(
        db: AsyncSession,
        user_id: UUID
    ) -> str:
        """获取用户的搜索可见性设置"""
        from app.models.user import SearchVisibility

        user = await db.get(User, user_id)
        if not user:
            return SearchVisibility.EVERYONE.value
        return user.searchable_by.value if user.searchable_by else SearchVisibility.EVERYONE.value

    @staticmethod
    async def update_searchability(
        db: AsyncSession,
        user_id: UUID,
        searchable_by: str
    ) -> bool:
        """更新用户搜索可见性设置"""
        from app.models.user import SearchVisibility

        user = await db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")

        try:
            user.searchable_by = SearchVisibility(searchable_by)
        except ValueError:
            raise ValueError(f"无效的搜索可见性设置: {searchable_by}")

        await db.flush()
        return True
