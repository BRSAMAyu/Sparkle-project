"""
责任伙伴通知服务
Accountability Partnership Notification Service

处理责任伙伴系统的各类通知:
- 伙伴邀请通知
- 每日打卡提醒
- 里程碑庆祝通知
- 伙伴打卡通知
- 连胜中断提醒
"""
from datetime import timezone, datetime
from enum import Enum
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accountability import AccountabilityPartnership
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.notification_service import notification_service


class AccountabilityNotificationType(str, Enum):
    """责任伙伴通知类型"""
    PARTNER_REQUEST = "accountability_partner_request"
    PARTNER_ACCEPTED = "accountability_partner_accepted"
    PARTNER_DECLINED = "accountability_partner_declined"
    DAILY_REMINDER = "accountability_daily_reminder"
    CHECKIN_MISSED = "accountability_checkin_missed"
    STREAK_MILESTONE = "accountability_streak_milestone"
    PARTNER_CHECKED_IN = "accountability_partner_checked_in"
    PARTNERSHIP_ENDED = "accountability_partnership_ended"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AccountabilityNotificationService:
    """责任伙伴通知服务"""

    async def send_partner_request(
        self,
        db: AsyncSession,
        partnership_id: UUID,
        initiator_id: UUID,
        partner_id: UUID,
        initiator_goal: str,
    ) -> Notification:
        """
        发送伙伴邀请通知

        Args:
            db: 数据库会话
            partnership_id: 伙伴关系ID
            initiator_id: 发起人ID
            partner_id: 被邀请人ID
            initiator_goal: 发起人目标

        Returns:
            创建的通知对象
        """
        # 获取发起人信息
        initiator = await db.get(User, initiator_id)
        initiator_name = initiator.display_name if initiator else "好友"

        title = "🤝 责任伙伴邀请"
        content = f"{initiator_name} 邀请你成为责任伙伴\n目标: {initiator_goal}"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.PARTNER_REQUEST.value,
            data={
                "partnership_id": str(partnership_id),
                "initiator_id": str(initiator_id),
                "initiator_goal": initiator_goal,
            },
        )

        notification = await notification_service.create(
            db, partner_id, notification_data, push_via_websocket=True
        )

        logger.info(f"Sent partner request notification to {partner_id} for partnership {partnership_id}")
        return notification

    async def send_partner_accepted(
        self,
        db: AsyncSession,
        partnership_id: UUID,
        partner_id: UUID,
        initiator_id: UUID,
    ) -> Notification:
        """
        发送伙伴接受通知

        Args:
            db: 数据库会话
            partnership_id: 伙伴关系ID
            partner_id: 接受人ID
            initiator_id: 发起人ID

        Returns:
            创建的通知对象
        """
        partnership = await db.get(AccountabilityPartnership, partnership_id)

        title = "🎉 责任伙伴关系已建立"
        content = f"你们现在是责任伙伴了！开始互相监督，共同进步吧！"

        if partnership and partnership.partner_goal:
            content += f"\n伙伴的目标: {partnership.partner_goal}"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.PARTNER_ACCEPTED.value,
            data={
                "partnership_id": str(partnership_id),
                "partner_id": str(partner_id),
            },
        )

        notification = await notification_service.create(
            db, initiator_id, notification_data, push_via_websocket=True
        )

        logger.info(f"Sent partner accepted notification to {initiator_id} for partnership {partnership_id}")
        return notification

    async def send_partner_declined(
        self,
        db: AsyncSession,
        initiator_id: UUID,
        partner_id: UUID,
    ) -> Notification:
        """
        发送伙伴拒绝通知

        Args:
            db: 数据库会话
            initiator_id: 发起人ID
            partner_id: 拒绝人ID

        Returns:
            创建的通知对象
        """
        partner = await db.get(User, partner_id)
        partner_name = partner.display_name if partner else "好友"

        title = "责任伙伴邀请已 declined"
        content = f"{partner_name} 暂时无法接受你的责任伙伴邀请"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.PARTNER_DECLINED.value,
            data={
                "partner_id": str(partner_id),
            },
        )

        notification = await notification_service.create(
            db, initiator_id, notification_data, push_via_websocket=True
        )

        logger.info(f"Sent partner declined notification to {initiator_id}")
        return notification

    async def send_daily_reminder(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
        partner_name: str,
    ) -> Notification:
        """
        发送每日打卡提醒

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID
            partner_name: 伙伴名称

        Returns:
            创建的通知对象
        """
        title = "⏰ 今日打卡提醒"
        content = f"还没有今天打卡哦！{partner_name} 正在等你一起进步"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.DAILY_REMINDER.value,
            data={
                "partnership_id": str(partnership_id),
                "partner_name": partner_name,
            },
        )

        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )

        logger.debug(f"Sent daily reminder to {user_id} for partnership {partnership_id}")
        return notification

    async def send_streak_milestone(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
        message: str,
        milestone_data: dict,
    ) -> Notification:
        """
        发送连胜里程碑通知

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID
            message: 里程碑消息
            milestone_data: 里程碑数据

        Returns:
            创建的通知对象
        """
        title = "🏆 连胜里程碑达成！"

        notification_data = NotificationCreate(
            title=title,
            content=message,
            type=AccountabilityNotificationType.STREAK_MILESTONE.value,
            data={
                "partnership_id": str(partnership_id),
                "milestone_data": milestone_data,
            },
        )

        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )

        logger.info(f"Sent streak milestone notification to {user_id}: {message}")
        return notification

    async def send_partner_checked_in(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
        checker_name: str,
    ) -> Notification:
        """
        发送伙伴已打卡通知

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID
            checker_name: 打卡人名称

        Returns:
            创建的通知对象
        """
        title = "✅ 伙伴已打卡"
        content = f"{checker_name} 已经完成今日打卡，快来一起打卡吧！"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.PARTNER_CHECKED_IN.value,
            data={
                "partnership_id": str(partnership_id),
                "checker_name": checker_name,
            },
        )

        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )

        logger.debug(f"Sent partner checked in notification to {user_id}")
        return notification

    async def send_checkin_missed(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
        streak_days: int,
    ) -> Notification:
        """
        发送打卡中断提醒

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID
            streak_days: 之前连胜天数

        Returns:
            创建的通知对象
        """
        title = "💔 连胜中断"
        content = f"哎呀，{streak_days}天的连胜记录中断了。别灰心，明天重新开始！"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.CHECKIN_MISSED.value,
            data={
                "partnership_id": str(partnership_id),
                "streak_days": streak_days,
            },
        )

        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )

        logger.info(f"Sent checkin missed notification to {user_id}, streak was {streak_days}")
        return notification

    async def send_partnership_ended(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
        partner_id: UUID,
        ended_by: UUID,
    ) -> Notification:
        """
        发送伙伴关系结束通知

        Args:
            db: 数据库会话
            user_id: 用户ID
            partnership_id: 伙伴关系ID
            partner_id: 伙伴ID
            ended_by: 结束人ID

        Returns:
            创建的通知对象
        """
        partner = await db.get(User, partner_id)
        partner_name = partner.display_name if partner else "伙伴"

        is_self = str(ended_by) == str(user_id)
        title = "👋 责任伙伴关系已结束"

        if is_self:
            content = f"你已结束与 {partner_name} 的责任伙伴关系"
        else:
            content = f"{partner_name} 已结束责任伙伴关系"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.PARTNERSHIP_ENDED.value,
            data={
                "partnership_id": str(partnership_id),
                "partner_id": str(partner_id),
            },
        )

        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )

        logger.info(f"Sent partnership ended notification to {user_id} for partnership {partnership_id}")
        return notification


# 单例实例
accountability_notification_service = AccountabilityNotificationService()
