from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate

class NotificationService:
    @staticmethod
    async def create(db: AsyncSession, user_id: UUID, obj_in: NotificationCreate) -> Notification:
        db_obj = Notification(
            user_id=user_id,
            title=obj_in.title,
            content=obj_in.content,
            type=obj_in.type,
            data=obj_in.data
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        
        stmt = stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await db.commit()
            await db.refresh(notification)
        return notification

notification_service = NotificationService()
