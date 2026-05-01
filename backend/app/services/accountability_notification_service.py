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
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import I18n
from app.models.accountability import AccountabilityPartnership
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.services.notification_service import notification_service


class AccountabilityNotificationType(StrEnum):
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
    return datetime.now(UTC).replace(tzinfo=None)


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
        locale: str = "zh",
    ) -> Notification:
        """发送伙伴邀请通知"""
        initiator = await db.get(User, initiator_id)
        initiator_name = _user_display_name(initiator, I18n.t("common.friend", locale=locale))

        title = I18n.t("accountability.partner_request_title", locale=locale)
        content = I18n.t("accountability.partner_request_content", locale=locale, name=initiator_name, goal=initiator_goal)

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
        locale: str = "zh",
    ) -> Notification:
        """发送伙伴接受通知"""
        partnership = await db.get(AccountabilityPartnership, partnership_id)

        title = I18n.t("accountability.partner_accepted_title", locale=locale)
        content = I18n.t("accountability.partner_accepted_content", locale=locale)

        if partnership and partnership.partner_goal:
            content += I18n.t("accountability.partner_accepted_goal", locale=locale, goal=partnership.partner_goal)

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
        locale: str = "zh",
    ) -> Notification:
        """发送伙伴拒绝通知"""
        partner = await db.get(User, partner_id)
        partner_name = _user_display_name(partner, I18n.t("common.friend", locale=locale))

        title = I18n.t("accountability.partner_declined_title", locale=locale)
        content = I18n.t("accountability.partner_declined_content", locale=locale, name=partner_name)

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
        locale: str = "zh",
    ) -> Notification:
        """发送每日打卡提醒"""
        title = I18n.t("accountability.daily_reminder_title", locale=locale)
        content = I18n.t("accountability.daily_reminder_content", locale=locale, partner=partner_name)

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
        locale: str = "zh",
    ) -> Notification:
        """发送连胜里程碑通知"""
        title = I18n.t("accountability.streak_milestone_title", locale=locale)

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
        locale: str = "zh",
    ) -> Notification:
        """发送伙伴已打卡通知"""
        title = I18n.t("accountability.partner_checked_in_title", locale=locale)
        content = I18n.t("accountability.partner_checked_in_content", locale=locale, checker=checker_name)

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
        locale: str = "zh",
    ) -> Notification:
        """发送打卡中断提醒"""
        title = I18n.t("accountability.checkin_missed_title", locale=locale)
        content = I18n.t("accountability.checkin_missed_content", locale=locale, days=streak_days)

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
        locale: str = "zh",
    ) -> Notification:
        """发送伙伴关系结束通知"""
        partner = await db.get(User, partner_id)
        partner_name = _user_display_name(partner, I18n.t("common.partner", locale=locale))

        is_self = str(ended_by) == str(user_id)
        title = I18n.t("accountability.partnership_ended_title", locale=locale)

        if is_self:
            content = I18n.t("accountability.partnership_ended_self", locale=locale, partner=partner_name)
        else:
            content = I18n.t("accountability.partnership_ended_other", locale=locale, partner=partner_name)

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
        locale: str = "zh",
    ) -> Notification:
        """发送手动督促提醒。"""
        title = I18n.t("accountability.manual_nudge_title", locale=locale)
        content = (
            I18n.t("accountability.manual_nudge_default", locale=locale, sender=sender_name)
            if not message
            else I18n.t("accountability.manual_nudge_custom", locale=locale, sender=sender_name, message=message)
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
        locale: str = "zh",
    ) -> Notification:
        actor_name = None
        if actor_user_id is not None:
            actor = await db.get(User, actor_user_id)
            actor_name = _user_display_name(actor, I18n.t("common.partner", locale=locale))
        due_label = due_at.strftime("%m-%d %H:%M") if due_at else I18n.t("accountability.due_label_fallback", locale=locale)

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
        locale: str = "zh",
    ) -> Notification:
        """Tell an accountability partner that their partner may need a light touch."""
        days = max(2, int(no_completion_days or 2))
        title = I18n.t("accountability.struggle_alert_title", locale=locale)
        content = I18n.t("accountability.struggle_alert_content", locale=locale, name=target_name, days=days)

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
                    "label": I18n.t("accountability.struggle_alert_action", locale=locale),
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
        locale: str = "zh",
    ) -> Notification:
        """Create a weak in-app hint for the struggling user without realtime push."""
        hint = I18n.t("accountability.encouragement_received_hint", locale=locale, sender=sender_name)
        notification_data = NotificationCreate(
            title=I18n.t("accountability.encouragement_received_title", locale=locale),
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
        locale: str = "zh",
    ) -> tuple[str, str]:
        if template_id == "policy_due_reminder_3d":
            return I18n.t("accountability.policy_due_3d_title", locale=locale), I18n.t("accountability.policy_due_3d_content", locale=locale, summary=commitment_summary, due=due_label)
        if template_id == "policy_due_reminder_1d":
            return I18n.t("accountability.policy_due_1d_title", locale=locale), I18n.t("accountability.policy_due_1d_content", locale=locale, summary=commitment_summary, due=due_label)
        if template_id == "policy_due_reminder_due_today":
            return I18n.t("accountability.policy_due_today_title", locale=locale), I18n.t("accountability.policy_due_today_content", locale=locale, summary=commitment_summary, due=due_label)
        if template_id == "policy_peer_missed_3d":
            partner_name = actor_name or I18n.t("common.partner", locale=locale)
            return I18n.t("accountability.policy_peer_missed_title", locale=locale), I18n.t("accountability.policy_peer_missed_content", locale=locale, partner=partner_name, summary=commitment_summary)
        if template_id == "policy_success_streak_7d":
            return I18n.t("accountability.policy_success_streak_title", locale=locale), I18n.t("accountability.policy_success_streak_content", locale=locale, summary=commitment_summary)
        if template_id == "policy_retro_request_due_without_outcome":
            return I18n.t("accountability.policy_retro_request_title", locale=locale), I18n.t("accountability.policy_retro_request_content", locale=locale, summary=commitment_summary)
        return I18n.t("accountability.policy_default_title", locale=locale), I18n.t("accountability.policy_default_content", locale=locale, summary=commitment_summary, due=due_label)


# 单例实例
accountability_notification_service = AccountabilityNotificationService()
