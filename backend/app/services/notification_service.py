from __future__ import annotations
from datetime import datetime, time, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.notification_interaction import NotificationPreferences
from app.models.user import PushPreference
from app.schemas.notification import NotificationCreate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NotificationService:
    @staticmethod
    def source_type_for_notification(notification_type: str | None) -> str:
        normalized = str(notification_type or "").strip().lower()
        if normalized in {"intervention", "intervention_push"}:
            return "intervention"
        return "system"

    @staticmethod
    def _normalize_timezone(timezone_name: str | None) -> str:
        timezone_name = timezone_name or "Asia/Shanghai"
        try:
            ZoneInfo(timezone_name)
        except Exception:
            timezone_name = "Asia/Shanghai"
        return timezone_name

    @staticmethod
    def _parse_clock(value: str | None) -> time | None:
        if not value:
            return None
        try:
            hour, minute = value.split(":", 1)
            return time(hour=int(hour), minute=int(minute))
        except Exception:
            return None

    @classmethod
    def _is_quiet_hours_active(
        cls,
        *,
        local_now: datetime,
        start: str | None,
        end: str | None,
    ) -> bool:
        start_time = cls._parse_clock(start)
        end_time = cls._parse_clock(end)
        if start_time is None or end_time is None:
            return False

        current_time = local_now.time()
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        return current_time >= start_time or current_time <= end_time

    @classmethod
    async def _should_push_notification(
        cls,
        db: AsyncSession,
        *,
        user_id: UUID,
    ) -> tuple[bool, str | None]:
        prefs_result = await db.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        )
        prefs = prefs_result.scalar_one_or_none()
        if prefs and not prefs.enable_system:
            return False, "system_notifications_disabled"

        if not prefs or not prefs.quiet_hours_enabled:
            return True, None

        timezone_result = await db.execute(
            select(PushPreference.timezone).where(PushPreference.user_id == user_id)
        )
        zone = ZoneInfo(cls._normalize_timezone(timezone_result.scalar_one_or_none()))

        local_now = datetime.now(zone)
        if cls._is_quiet_hours_active(
            local_now=local_now,
            start=prefs.quiet_hours_start,
            end=prefs.quiet_hours_end,
        ):
            return False, "quiet_hours"

        return True, None

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: UUID,
        obj_in: NotificationCreate | dict,
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
        if isinstance(obj_in, dict):
            obj_in = NotificationCreate(**obj_in)

        should_push = False
        suppression_reason = None
        if push_via_websocket:
            should_push, suppression_reason = await NotificationService._should_push_notification(
                db,
                user_id=user_id,
            )

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
        if should_push:
            await NotificationService._push_notification_via_websocket(
                user_id=user_id,
                notification=db_obj,
            )
        elif push_via_websocket and suppression_reason:
            logger.info(
                f"Skipped websocket push for notification {db_obj.id} to user {user_id}: {suppression_reason}"
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
            "notification_type": NotificationService.source_type_for_notification(notification.type),
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
            stmt = stmt.where(Notification.is_read.is_(False))

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
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar() or 0


notification_service = NotificationService()
