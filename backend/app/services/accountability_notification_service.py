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
    MANUAL_NUDGE = "accountability_manual_nudge"
    POLICY_TRIGGERED = "accountability_policy_triggered"
    STRUGGLE_ALERT = "accountability_struggle_alert"
    ENCOURAGEMENT_RECEIVED = "accountability_encouragement_received"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _user_display_name(user: User | None, default: str) -> str:
    if not user:
        return default
    return user.nickname or user.full_name or user.username or default


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
        initiator_name = _user_display_name(initiator, "好友")

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
        partner_name = _user_display_name(partner, "好友")

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
        partner_name = _user_display_name(partner, "伙伴")

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

    async def send_manual_nudge(
        self,
        db: AsyncSession,
        user_id: UUID,
        partnership_id: UUID,
        sender_name: str,
        message: str | None = None,
    ) -> Notification:
        """发送手动督促提醒。"""
        title = "⏱️ 伙伴提醒"
        content = (
            f"{sender_name} 提醒你看看今天的目标，别让节奏断掉。"
            if not message
            else f"{sender_name} 提醒你：{message}"
        )

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.MANUAL_NUDGE.value,
            data={
                "partnership_id": str(partnership_id),
                "sender_name": sender_name,
                "message": message,
                "kind": "manual_nudge",
            },
        )

        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )
        logger.info(f"Sent manual nudge to {user_id} for partnership {partnership_id}")
        return notification

    async def send_policy_notification(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        policy_id: str,
        template_id: str,
        commitment_summary: str,
        due_at: datetime | None,
        partnership_id: UUID | None = None,
        actor_user_id: UUID | None = None,
    ) -> Notification:
        actor_name = None
        if actor_user_id is not None:
            actor = await db.get(User, actor_user_id)
            actor_name = _user_display_name(actor, "你的伙伴")
        due_label = due_at.strftime("%m-%d %H:%M") if due_at else "约定时间"

        title, content = self._render_policy_template(
            template_id=template_id,
            commitment_summary=commitment_summary,
            due_label=due_label,
            actor_name=actor_name,
        )
        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.POLICY_TRIGGERED.value,
            data={
                "policy_id": policy_id,
                "template_id": template_id,
                "partnership_id": str(partnership_id) if partnership_id else None,
                "commitment_summary": commitment_summary,
                "due_at": due_at.isoformat() if due_at else None,
            },
        )
        notification = await notification_service.create(
            db, user_id, notification_data, push_via_websocket=True
        )
        logger.info(f"Sent policy notification {policy_id} to {user_id}")
        return notification

    async def send_struggle_alert(
        self,
        db: AsyncSession,
        *,
        partner_id: UUID,
        target_user_id: UUID,
        partnership_id: UUID,
        plan_id: UUID,
        target_name: str,
        no_completion_days: int,
        struggle_score: float,
        dedupe_key: str,
        preset_encouragements: list[dict],
    ) -> Notification:
        """Tell an accountability partner that their partner may need a light touch."""
        days = max(2, int(no_completion_days or 2))
        title = "责任伙伴轻提醒"
        content = f"{target_name} 已经 {days} 天没有完成学习任务了，也许可以发一条鼓励。"

        notification_data = NotificationCreate(
            title=title,
            content=content,
            type=AccountabilityNotificationType.STRUGGLE_ALERT.value,
            data={
                "kind": "accountability_struggle_alert",
                "partnership_id": str(partnership_id),
                "target_user_id": str(target_user_id),
                "target_name": target_name,
                "plan_id": str(plan_id),
                "no_completion_days": days,
                "struggle_score": struggle_score,
                "dedupe_key": dedupe_key,
                "encouragement_status": "pending",
                "preset_encouragements": preset_encouragements,
                "primary_action": {
                    "type": "send_accountability_encouragement",
                    "label": "发个鼓励",
                },
            },
        )

        notification = await notification_service.create(
            db,
            partner_id,
            notification_data,
            push_via_websocket=True,
        )
        logger.info(
            "Sent accountability struggle alert to partner {} for target {} partnership {}",
            partner_id,
            target_user_id,
            partnership_id,
        )
        return notification

    async def send_encouragement_received(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        partnership_id: UUID,
        sender_id: UUID,
        sender_name: str,
        message: str,
        source_notification_id: UUID | None = None,
        plan_id: UUID | None = None,
    ) -> Notification:
        """Create a weak in-app hint for the struggling user without realtime push."""
        hint = f"{sender_name} 正在看着你，加油"
        notification_data = NotificationCreate(
            title="伙伴鼓励",
            content=hint,
            type=AccountabilityNotificationType.ENCOURAGEMENT_RECEIVED.value,
            data={
                "kind": "accountability_encouragement_hint",
                "partnership_id": str(partnership_id),
                "sender_id": str(sender_id),
                "sender_name": sender_name,
                "message": message,
                "hint": hint,
                "source_notification_id": str(source_notification_id) if source_notification_id else None,
                "plan_id": str(plan_id) if plan_id else None,
                "display_mode": "weak_in_app_hint",
            },
        )
        notification = await notification_service.create(
            db,
            user_id,
            notification_data,
            push_via_websocket=False,
        )
        logger.info(
            "Created in-app accountability encouragement hint for user {} from {}",
            user_id,
            sender_id,
        )
        return notification

    @staticmethod
    def _render_policy_template(
        *,
        template_id: str,
        commitment_summary: str,
        due_label: str,
        actor_name: str | None = None,
    ) -> tuple[str, str]:
        if template_id == "policy_due_reminder_3d":
            return "🗓️ 承诺提醒", f"还有 3 天到期：{commitment_summary}\n目标时间：{due_label}"
        if template_id == "policy_due_reminder_1d":
            return "⏰ 明日到期提醒", f"明天就到期了：{commitment_summary}\n目标时间：{due_label}"
        if template_id == "policy_due_reminder_due_today":
            return "📌 今日承诺提醒", f"今天要收口这件事：{commitment_summary}\n目标时间：{due_label}"
        if template_id == "policy_peer_missed_3d":
            partner_name = actor_name or "你的伙伴"
            return "🤝 伙伴协同提醒", f"{partner_name} 连续 3 天没有推进这项承诺：{commitment_summary}"
        if template_id == "policy_success_streak_7d":
            return "🌟 连续兑现 7 天", f"你已经连续 7 天稳稳推进了承诺：{commitment_summary}"
        if template_id == "policy_retro_request_due_without_outcome":
            return "📝 到期复盘请求", f"这项承诺已到期且还没有结果记录：{commitment_summary}\n花 2 分钟补一个复盘吧。"
        return "📣 承诺策略提醒", f"{commitment_summary}\n目标时间：{due_label}"


# 单例实例
accountability_notification_service = AccountabilityNotificationService()
