"""
User Service
Handle user business logic
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.schemas.user import UserRegister, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        return await User.get_by_id(db, user_id)

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
        query = select(User).where(User.username == username)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, obj_in: UserRegister) -> User:
        db_obj = User(
            username=obj_in.username,
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            nickname=obj_in.nickname,
            flame_level=1,
            flame_brightness=0.5,
            depth_preference=0.5,
            curiosity_preference=0.5,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def authenticate(
        db: AsyncSession, username_or_email: str, password: str
    ) -> Optional[User]:
        # Try by email first
        user = await UserService.get_by_email(db, username_or_email)
        if not user:
            # Try by username
            user = await UserService.get_by_username(db, username_or_email)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
            
        return user

    @staticmethod
    async def update(
        db: AsyncSession, db_obj: User, obj_in: UserUpdate
    ) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
