"""
User Service
Handle user business logic
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, AvatarStatus
from app.schemas.user import UserRegister, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
// ...
    @staticmethod
    async def update(
        db: AsyncSession, db_obj: User, obj_in: UserUpdate
    ) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Avatar Moderation Logic
        if "avatar_url" in update_data:
            new_avatar = update_data.pop("avatar_url")
            
            # System presets (Dicebear) are pre-approved
            if new_avatar and ("dicebear.com" in new_avatar):
                db_obj.avatar_url = new_avatar
                db_obj.avatar_status = AvatarStatus.APPROVED
                db_obj.pending_avatar_url = None
            else:
                # Custom uploads need moderation
                db_obj.pending_avatar_url = new_avatar
                db_obj.avatar_status = AvatarStatus.PENDING
                # Keep existing avatar_url as is until approved
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
