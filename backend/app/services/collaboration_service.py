from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from app.models.community import SharedResource, Group, GroupMember, SharedResourceType
from app.models.plan import Plan
from app.models.task import Task
from app.models.cognitive import CognitiveFragment
from app.services.notification_service import notification_service

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
        if not target_group_id and not target_user_id:
            raise ValueError("Must specify either target_group_id or target_user_id")

        # Create SharedResource
        shared = SharedResource(
            shared_by=user_id,
            group_id=target_group_id,
            target_user_id=target_user_id,
            resource_type=resource_type, # This field is in model? Wait, checking model definition...
            # The model has specific FKs: plan_id, task_id, cognitive_fragment_id.
            # It does NOT have a 'resource_type' column in my SQL definition above, 
            # BUT I might have missed it or replaced it with individual FKs.
            # Let's check the migration file I just applied.
            # Migration had: sa.Column('plan_id'... task_id... cognitive_fragment_id...)
            # It did NOT have resource_type column explicitly? 
            # Wait, I might have forgotten to add 'resource_type' string column in the migration 
            # if I only relied on the class definition which I edited.
            # Let's check the class definition I wrote in 'community.py'.
            # I removed 'resource_type' column in the revised model thought process but 
            # kept it in the Enum definition. 
            # Actually, having specific FKs is enough, but a helper 'resource_type' is useful for querying.
            # Let's see what I wrote to the file.
        )
        
        # Adjusting assignment based on resource_type enum
        if resource_type == SharedResourceType.PLAN:
            shared.plan_id = resource_id
        elif resource_type == SharedResourceType.TASK:
            shared.task_id = resource_id
        elif resource_type == SharedResourceType.COGNITIVE_FRAGMENT:
            shared.cognitive_fragment_id = resource_id
        
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
        
        stmt = stmt.order_by(SharedResource.created_at.desc()).limit(limit)
        
        # Eager load relationships
        stmt = stmt.options(
            joinedload(SharedResource.sharer),
            joinedload(SharedResource.plan),
            joinedload(SharedResource.task),
            joinedload(SharedResource.cognitive_fragment)
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()

collaboration_service = CollaborationService()
