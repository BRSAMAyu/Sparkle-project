from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from app.models.community import (
    SharedResource,
    GroupMember,
    SharedResourceType,
    Friendship,
    FriendshipStatus,
)

class CollaborationService:
    @staticmethod
    async def share_resource(
        db: AsyncSession,
        user_id: UUID,
        resource_type: SharedResourceType,
        resource_id: UUID,
        target_group_id: Optional[UUID] = None,
        target_user_id: Optional[UUID] = None,
        permission: str = "view",
        comment: str = None
    ) -> SharedResource:
        """
        Share a resource (Plan, Task, Fragment) with a Group or User.
        """
        if target_group_id and target_user_id:
            raise ValueError("Only one of target_group_id or target_user_id can be set")
        if not target_group_id and not target_user_id:
            raise ValueError("Must specify either target_group_id or target_user_id")
        if target_user_id and target_user_id == user_id:
            raise ValueError("Cannot share to yourself")

        if target_group_id:
            membership_result = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == target_group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.not_deleted_filter()
                )
            )
            if not membership_result.scalar_one_or_none():
                raise ValueError("Not a member of the target group")

        if target_user_id:
            u1, u2 = (
                (user_id, target_user_id)
                if str(user_id) < str(target_user_id)
                else (target_user_id, user_id)
            )
            rel_result = await db.execute(
                select(Friendship).where(
                    Friendship.user_id == u1,
                    Friendship.friend_id == u2,
                    Friendship.status == FriendshipStatus.ACCEPTED,
                    Friendship.not_deleted_filter()
                )
            )
            if not rel_result.scalar_one_or_none():
                raise ValueError("Can only share to accepted friends")

        # Create SharedResource
        shared = SharedResource(
            shared_by=user_id,
            group_id=target_group_id,
            target_user_id=target_user_id,
        )
        
        # Adjusting assignment based on resource_type enum
        if resource_type == SharedResourceType.PLAN:
            shared.plan_id = resource_id
        elif resource_type == SharedResourceType.TASK:
            shared.task_id = resource_id
        elif resource_type == SharedResourceType.COGNITIVE_FRAGMENT:
            shared.cognitive_fragment_id = resource_id
        elif resource_type == SharedResourceType.CURIOSITY_CAPSULE:
            shared.curiosity_capsule_id = resource_id
        elif resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
            shared.behavior_pattern_id = resource_id
        
        shared.permission = permission
        shared.comment = comment

        db.add(shared)
        await db.flush()

        # Send Notification
        if target_group_id:
            # Notify group members (this might be expensive for large groups, maybe just create a GroupMessage?)
            # Better: Create a GroupMessage of type *_SHARE
            pass 
            # We will handle message creation in the API layer or here.
        
        return shared

    @staticmethod
    async def get_group_resources(
        db: AsyncSession,
        group_id: UUID,
        resource_type: Optional[SharedResourceType] = None,
        limit: int = 50
    ) -> List[SharedResource]:
        """Get resources shared with a group"""
        stmt = select(SharedResource).where(
            SharedResource.group_id == group_id,
            SharedResource.deleted_at.is_(None)
        )
        
        if resource_type:
            if resource_type == SharedResourceType.PLAN:
                stmt = stmt.where(SharedResource.plan_id.isnot(None))
            elif resource_type == SharedResourceType.TASK:
                stmt = stmt.where(SharedResource.task_id.isnot(None))
            elif resource_type == SharedResourceType.COGNITIVE_FRAGMENT:
                stmt = stmt.where(SharedResource.cognitive_fragment_id.isnot(None))
            elif resource_type == SharedResourceType.CURIOSITY_CAPSULE:
                stmt = stmt.where(SharedResource.curiosity_capsule_id.isnot(None))
            elif resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
                stmt = stmt.where(SharedResource.behavior_pattern_id.isnot(None))
        
        stmt = stmt.order_by(SharedResource.created_at.desc()).limit(limit)
        
        # Eager load relationships
        stmt = stmt.options(
            joinedload(SharedResource.sharer),
            joinedload(SharedResource.plan),
            joinedload(SharedResource.task),
            joinedload(SharedResource.cognitive_fragment),
            joinedload(SharedResource.curiosity_capsule),
            joinedload(SharedResource.behavior_pattern),
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()

collaboration_service = CollaborationService()
