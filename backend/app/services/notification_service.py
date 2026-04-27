from __future__ import annotations

from datetime import UTC, datetime, time
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
    return datetime.now(UTC).replace(tzinfo=None)


PER_TYPE_NOTIFICATION_ALIASES: dict[str, set[str]] = {
    "reminder": {
        "reminder",
        "task_reminder",
        "sprint_reminder",
        "daily_sprint_reminder",
        "comeback_nudge",
        "fragmented_time",
    },
    "task_reminder": {"reminder", "task_reminder"},
    "spaced_repetition": {"spaced_repetition", "spaced_repetition_reminder"},
    "spaced_repetition_reminder": {"spaced_repetition", "spaced_repetition_reminder"},
    "sprint_reminder": {"reminder", "sprint_reminder", "daily_sprint_reminder"},
    "daily_sprint_reminder": {"reminder", "sprint_reminder", "daily_sprint_reminder"},
    "weekly_report": {"weekly_report", "weekly_digest", "weekly_growth_narrative", "weekly_learning_report"},
    "weekly_digest": {"weekly_report", "weekly_digest"},
    "weekly_growth_narrative": {"weekly_report", "weekly_growth_narrative"},
    "milestone": {"milestone", "milestone_notification", "achievement", "achievement_progress"},
    "milestone_notification": {"milestone", "milestone_notification"},
    "achievement": {"milestone", "achievement"},
    "achievement_progress": {"milestone", "achievement_progress"},
}


def _normalize_disabled_type(value: object) -> str:
    return str(value or "").strip().lower()


def notification_type_disabled(
    disabled_types: list[str] | tuple[str, ...] | set[str] | None,
    *,
    notification_type: str | None = None,
    category: str | None = None,
) -> bool:
    disabled = {_normalize_disabled_type(item) for item in (disabled_types or [])}
    disabled.discard("")
    if not disabled:
        return False

    candidates = {
        _normalize_disabled_type(notification_type),
        _normalize_disabled_type(category),
    }
    expanded_candidates: set[str] = set()
    for candidate in candidates:
        expanded_candidates.add(candidate)
        expanded_candidates.update(PER_TYPE_NOTIFICATION_ALIASES.get(candidate, set()))
    expanded_candidates.discard("")

    for disabled_type in disabled:
        aliases = PER_TYPE_NOTIFICATION_ALIASES.get(disabled_type, {disabled_type})
        if expanded_candidates.intersection(aliases):
            return True
    return False


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
        notification_type: str | None = None,
        category: str | None = None,
    ) -> tuple[bool, str | None]:
        prefs_result = await db.execute(
            select(NotificationPreferences).where(NotificationPreferences.user_id == user_id)
        )
        prefs = prefs_result.scalar_one_or_none()
        if prefs and not prefs.enable_system:
            return False, "system_notifications_disabled"
        if (
            prefs
            and cls.source_type_for_notification(notification_type) == "intervention"
            and not prefs.enable_interventions
        ):
            return False, "intervention_notifications_disabled"
        if prefs and notification_type_disabled(
            prefs.disabled_types,
            notification_type=notification_type,
            category=category,
        ):
            return False, "notification_type_disabled"

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
                notification_type=obj_in.type,
                category=(obj_in.data or {}).get("category") if isinstance(obj_in.data, dict) else None,
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


    # ── Spine NotificationDirective Consumer ────────────────────────────

    @classmethod
    async def consume_spine_notification_directive(
        cls,
        db: AsyncSession,
        user_id: UUID,
        *,
        redis_client,
        title: str,
        content: str,
        notification_type: str = "intervention",
    ) -> Notification | None:
        """
        Consume a NotificationDirective from the Spine and send the notification
        if the directive permits it.

        This is the integration point between SpineOrchestrator's NotificationDirective
        and the actual notification delivery pipeline. Call this instead of create()
        when the notification originates from a Spine-generated directive.

        Returns the created Notification or None if suppressed by the directive.
        """
        from app.signals.spine_orchestrator import SpineOrchestrator

        spine = SpineOrchestrator(redis_client)
        directive = await spine.get_notification_directive(str(user_id))

        if directive is None:
            # No active directive — fall back to standard notification creation
            return await cls.create(
                db,
                user_id,
                NotificationCreate(title=title, content=content, type=notification_type),
            )

        if not directive.allowed:
            logger.info(
                "NotificationDirective suppressed notification for user {}: allowed=False",
                user_id,
            )
            return None

        # Respect quiet hours if directive demands it
        if directive.respect_quiet_hours:
            should_push, reason = await cls._should_push_notification(
                db,
                user_id=user_id,
                notification_type=notification_type,
            )
            if not should_push:
                logger.info(
                    "NotificationDirective: quiet hours suppressed for user {}: {}",
                    user_id, reason,
                )
                return None

        # Frequency throttle — directive max_frequency maps to a per-day cap
        freq_cap = {
            "1_per_day": 1,
            "2_per_day": 2,
            "1_per_sprint": 1,
        }.get(directive.max_frequency, 1)
        freq_key = f"spine:notif_freq:{user_id}:{directive.trigger}"
        sent_today = await redis_client.incr(freq_key)
        if sent_today == 1:
            await redis_client.expire(freq_key, 86400)  # reset each 24 h
        if sent_today > freq_cap:
            logger.info(
                "NotificationDirective: frequency cap ({}) reached for user {} trigger={}",
                freq_cap, user_id, directive.trigger,
            )
            return None

        # Choose push channel
        push_via_ws = directive.channel in ("push", "in_app")
        notification = await cls.create(
            db,
            user_id,
            NotificationCreate(
                title=title,
                content=content,
                type=notification_type,
                data={
                    "spine_directive_id": directive.directive_id,
                    "trigger": directive.trigger,
                    "message_strategy": directive.message_strategy,
                    "channel": directive.channel,
                },
            ),
            push_via_websocket=push_via_ws,
        )

        # Clear the directive after consumption (one-shot)
        await redis_client.delete(f"spine:notification_directive:{user_id}:latest")
        logger.info(
            "NotificationDirective consumed for user {}: trigger={} channel={}",
            user_id, directive.trigger, directive.channel,
        )
        return notification


notification_service = NotificationService()
