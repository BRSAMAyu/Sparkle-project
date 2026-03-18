from __future__ import annotations
from datetime import timezone, datetime
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NotificationService:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: UUID,
        obj_in: NotificationCreate,
        push_via_websocket: bool = True,
    ) -> Notification:
        """
        创建通知并可选地通过 WebSocket 推送

        Args:
            db: 数据库会话
            user_id: 用户ID
            obj_in: 通知创建数据
            push_via_websocket: 是否通过 WebSocket 推送（默认 True）

        Returns:
            创建的 Notification 对象
        """
        db_obj = Notification(
            user_id=user_id,
            title=obj_in.title,
            content=obj_in.content,
            type=obj_in.type,
            data=obj_in.data,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        logger.info(f"Created notification {db_obj.id} for user {user_id}: {obj_in.title}")

        # 通过 WebSocket 实时推送
        if push_via_websocket:
            await NotificationService._push_notification_via_websocket(
                user_id=user_id,
                notification=db_obj,
            )

        return db_obj

    @staticmethod
    async def _push_notification_via_websocket(
        user_id: UUID,
        notification: Notification,
        priority: str = "normal",
    ) -> None:
        """
        通过 WebSocket 推送通知到客户端

        Args:
            user_id: 用户ID
            notification: 通知对象
            priority: 优先级 (low, normal, high)
        """
        from app.core.websocket import get_ws_manager

        ws_manager = get_ws_manager()

        message = {
            "type": "notification",
            "notification_type": "system",
            "notification": {
                "id": str(notification.id),
                "title": notification.title,
                "content": notification.content,
                "type": notification.type,
                "data": notification.data or {},
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat()
                if notification.created_at
                else _utcnow().isoformat(),
                "priority": priority,
            },
            "response_id": str(uuid4()),
        }

        try:
            await ws_manager.send_personal_message(message, str(user_id))
            logger.debug(f"Pushed notification {notification.id} to user {user_id} via WebSocket")
        except Exception as e:
            # WebSocket 推送失败不应影响通知创建
            logger.warning(f"Failed to push notification via WebSocket: {e}")

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(not Notification.is_read)

        stmt = stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def mark_as_read(
        db: AsyncSession, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            notification.read_at = _utcnow()
            await db.commit()
            await db.refresh(notification)
        return notification

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
        """获取用户未读通知数量"""
        from sqlalchemy import func

        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, not Notification.is_read
            )
        )
        return result.scalar() or 0


notification_service = NotificationService()
