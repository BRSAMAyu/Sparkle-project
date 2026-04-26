"""
Notification Push Service

统一处理通知的创建和实时推送，确保：
1. 数据库记录创建
2. WebSocket 实时推送
3. 通知中心数据同步
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import I18n
from app.core.websocket import get_ws_manager
from app.models.notification import Notification
from app.services.notification_service import NotificationService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class NotificationPushService:
    """统一通知推送服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ws_manager = get_ws_manager()

    async def create_and_push(
        self,
        user_id: UUID,
        title: str,
        content: str,
        notification_type: str = "system",
        data: dict[str, Any] | None = None,
        priority: str = "normal",
    ) -> Notification:
        """
        创建通知并实时推送

        Args:
            user_id: 用户ID
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型 (system, task_reminder, achievement, etc.)
            data: 附加数据
            priority: 优先级 (low, normal, high)

        Returns:
            创建的 Notification 对象
        """
        # 1. 创建数据库记录
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
            data=data or {},
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        logger.info(
            f"Created notification {notification.id} for user {user_id}: {title}"
        )

        # 2. 通过 WebSocket 推送
        should_push, suppression_reason = await NotificationService._should_push_notification(
            self.db,
            user_id=user_id,
            notification_type=notification_type,
            category=(data or {}).get("category") if isinstance(data, dict) else None,
        )
        if should_push:
            await self._push_via_websocket(user_id, notification, priority)
        elif suppression_reason:
            logger.info(
                f"Skipped websocket push for notification {notification.id} to user {user_id}: {suppression_reason}"
            )

        return notification

    async def _push_via_websocket(
        self,
        user_id: UUID,
        notification: Notification,
        priority: str,
    ) -> None:
        """通过 WebSocket 推送通知"""
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
            await self.ws_manager.send_personal_message(message, str(user_id))
            logger.debug(f"Pushed notification {notification.id} to user {user_id} via WebSocket")
        except Exception as e:
            # WebSocket 推送失败不应影响通知创建
            logger.warning(f"Failed to push notification via WebSocket: {e}")

    async def push_intervention_notification(
        self,
        user_id: UUID,
        intervention_id: UUID,
        intervention_type: str,
        title: str,
        content: str,
        data: dict[str, Any] | None = None,
        priority: str = "high",
    ) -> None:
        """
        推送干预通知（不创建数据库记录，InterventionRequest 已存在）
        Respects user notification preferences.
        """
        # Check notification preferences before pushing
        should_push, reason = await NotificationService._should_push_notification(
            self.db, user_id, "intervention"
        )
        if not should_push:
            logger.debug(f"Intervention notification skipped for user {user_id}: {reason}")
            return
        message = {
            "type": "notification",
            "notification_type": "intervention",
            "notification": {
                "id": str(intervention_id),
                "title": title,
                "content": content,
                "type": intervention_type,
                "data": data or {},
                "is_read": False,
                "created_at": _utcnow().isoformat(),
                "priority": priority,
            },
            "response_id": str(uuid4()),
        }

        try:
            await self.ws_manager.send_personal_message(message, str(user_id))
            logger.debug(
                f"Pushed intervention notification {intervention_id} to user {user_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to push intervention notification: {e}")

    async def push_task_reminder(
        self,
        user_id: UUID,
        task_id: UUID,
        task_title: str,
        minutes_until_due: int,
    ) -> Notification:
        """
        推送任务提醒通知

        Args:
            user_id: 用户ID
            task_id: 任务ID
            task_title: 任务标题
            minutes_until_due: 距离到期还有多少分钟

        Returns:
            创建的 Notification 对象
        """
        title = I18n.t("notification.task_reminder_title", locale="zh")
        content = I18n.t("notification.task_reminder_content", locale="zh", title=task_title, minutes=minutes_until_due)

        return await self.create_and_push(
            user_id=user_id,
            title=title,
            content=content,
            notification_type="task_reminder",
            data={
                "task_id": str(task_id),
                "task_title": task_title,
                "minutes_until_due": minutes_until_due,
            },
            priority="high",
        )

    async def push_achievement_notification(
        self,
        user_id: UUID,
        achievement_id: str,
        achievement_name: str,
        rarity: str,
        is_first: bool = False,
    ) -> Notification:
        """
        推送成就解锁通知

        Args:
            user_id: 用户ID
            achievement_id: 成就ID
            achievement_name: 成就名称
            rarity: 稀有度
            is_first: 是否首位解锁者

        Returns:
            创建的 Notification 对象
        """
        title = I18n.t("notification.achievement_title", locale="zh")
        content = I18n.t("notification.achievement_content", locale="zh", name=achievement_name)
        if is_first:
            content += I18n.t("notification.achievement_first", locale="zh")

        return await self.create_and_push(
            user_id=user_id,
            title=title,
            content=content,
            notification_type="achievement",
            data={
                "achievement_id": achievement_id,
                "achievement_name": achievement_name,
                "rarity": rarity,
                "is_first": is_first,
            },
            priority="high",
        )

    async def push_system_notification(
        self,
        user_id: UUID,
        title: str,
        content: str,
        data: dict[str, Any] | None = None,
        priority: str = "normal",
    ) -> Notification:
        """
        推送系统通知

        Args:
            user_id: 用户ID
            title: 通知标题
            content: 通知内容
            data: 附加数据
            priority: 优先级

        Returns:
            创建的 Notification 对象
        """
        return await self.create_and_push(
            user_id=user_id,
            title=title,
            content=content,
            notification_type="system",
            data=data,
            priority=priority,
        )

    async def push_state_change_notification(
        self,
        user_id: UUID,
        change_type: str,
        title: str,
        content: str,
        change_data: dict[str, Any],
        priority: str = "normal",
        create_db_record: bool = True,
    ) -> Notification | None:
        """
        推送状态变更通知（计划归档/恢复/删除、设置更新等）

        Args:
            user_id: 用户ID
            change_type: 变更类型 (plan_archived, plan_restored, plan_deleted, user_settings_updated, etc.)
            title: 通知标题
            content: 通知内容
            change_data: 变更数据
            priority: 优先级
            create_db_record: 是否创建数据库记录

        Returns:
            创建的 Notification 对象（如果 create_db_record=True）
        """
        notification_data = {
            "change_type": change_type,
            **change_data,
        }

        if create_db_record:
            return await self.create_and_push(
                user_id=user_id,
                title=title,
                content=content,
                notification_type=f"state_change.{change_type}",
                data=notification_data,
                priority=priority,
            )
        else:
            # 只推送 WebSocket，不创建数据库记录
            message = {
                "type": "notification",
                "notification_type": "state_change",
                "notification": {
                    "id": str(uuid4()),
                    "title": title,
                    "content": content,
                    "type": f"state_change.{change_type}",
                    "data": notification_data,
                    "is_read": False,
                    "created_at": _utcnow().isoformat(),
                    "priority": priority,
                },
                "response_id": str(uuid4()),
            }

            try:
                await self.ws_manager.send_personal_message(message, str(user_id))
                logger.debug(
                    f"Pushed state change notification to user {user_id}: {change_type}"
                )
            except Exception as e:
                logger.warning(f"Failed to push state change notification: {e}")

            return None


# Factory function for dependency injection
def get_notification_push_service(db: AsyncSession) -> NotificationPushService:
    """获取 NotificationPushService 实例"""
    return NotificationPushService(db)
