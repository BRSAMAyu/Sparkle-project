"""
责任伙伴系统定时任务
Accountability Partnership Scheduled Tasks

定时任务:
- 每日打卡提醒
- 进度检查和成就评估
- 里程碑庆祝
"""
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from celery import shared_task
from celery.schedules import crontab
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_context
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.notification import Notification
from app.models.notification_interaction import NotificationPreferences
from app.models.user import User
from app.services.accountability_notification_service import AccountabilityNotificationType
from app.services.policy_scheduler_service import PolicySchedulerService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _user_display_name(user: User | None, default: str) -> str:
    if not user:
        return default
    return user.nickname or user.full_name or user.username or default


async def _missed_days_for_user(
    db: AsyncSession,
    *,
    partnership_id: UUID,
    user_id: UUID,
) -> int:
    result = await db.execute(
        select(AccountabilityCheckin.created_at)
        .where(
            AccountabilityCheckin.partnership_id == partnership_id,
            AccountabilityCheckin.user_id == user_id,
        )
        .order_by(AccountabilityCheckin.created_at.desc())
        .limit(1)
    )
    last_checkin_at = result.scalar_one_or_none()
    if last_checkin_at is None:
        return 999
    return max(0, (_utcnow().date() - last_checkin_at.date()).days)


def _coerce_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _utc_naive(timestamp: datetime) -> datetime:
    return _coerce_utc(timestamp).replace(tzinfo=None)


def _user_timezone_name(user: User | None) -> str:
    timezone_name = getattr(getattr(user, "push_preference", None), "timezone", None) or "Asia/Shanghai"
    try:
        ZoneInfo(timezone_name)
    except Exception:
        timezone_name = "Asia/Shanghai"
    return timezone_name


def _local_day_window(timezone_name: str, now: datetime) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    local_now = _coerce_utc(now).astimezone(zone)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return (
        local_start.astimezone(UTC).replace(tzinfo=None),
        local_end.astimezone(UTC).replace(tzinfo=None),
    )


def _local_date(timestamp: datetime, timezone_name: str):
    return _coerce_utc(timestamp).astimezone(ZoneInfo(timezone_name)).date()


def _parse_minutes(value: str | None) -> int | None:
    if not value or ":" not in value:
        return None
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def _is_in_quiet_hours(
    *,
    timezone_name: str,
    now: datetime,
    quiet_start: str | None,
    quiet_end: str | None,
) -> bool:
    start_minutes = _parse_minutes(quiet_start)
    end_minutes = _parse_minutes(quiet_end)
    if start_minutes is None or end_minutes is None:
        return False

    local_now = _coerce_utc(now).astimezone(ZoneInfo(timezone_name))
    current_minutes = local_now.hour * 60 + local_now.minute
    if start_minutes == end_minutes:
        return True
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def _disabled_types(disabled_types: Any) -> set[str]:
    if not isinstance(disabled_types, list):
        return set()
    return {str(item).strip() for item in disabled_types if str(item).strip()}


async def _reminder_suppression_reason(
    db: AsyncSession,
    *,
    user_id: UUID,
    timezone_name: str,
    now: datetime,
) -> str | None:
    result = await db.execute(select(NotificationPreferences).where(NotificationPreferences.user_id == user_id))
    preferences = result.scalar_one_or_none()
    if preferences is None:
        return None

    reminder_type = AccountabilityNotificationType.DAILY_REMINDER.value
    disabled = _disabled_types(preferences.disabled_types)
    if not preferences.enable_system:
        return "system_notifications_disabled"
    if str(preferences.notification_level or "").lower() in {"minimal", "off", "silent", "none"}:
        return "notification_level_suppressed"
    if reminder_type in disabled or "accountability" in disabled or "accountability_reminders" in disabled:
        return "accountability_reminder_disabled"
    if preferences.quiet_hours_enabled and _is_in_quiet_hours(
        timezone_name=timezone_name,
        now=now,
        quiet_start=preferences.quiet_hours_start,
        quiet_end=preferences.quiet_hours_end,
    ):
        return "quiet_hours"
    return None


async def _last_checkin_at(
    db: AsyncSession,
    *,
    partnership_id: UUID,
    user_id: UUID,
) -> datetime | None:
    result = await db.execute(
        select(AccountabilityCheckin.created_at)
        .where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == user_id,
            )
        )
        .order_by(AccountabilityCheckin.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _is_checkin_due_for_cadence(
    *,
    partnership: AccountabilityPartnership,
    last_checkin_at: datetime | None,
    timezone_name: str,
    now: datetime,
) -> bool:
    cadence_days = max(1, int(partnership.check_in_days or 1))
    if cadence_days == 1:
        return True

    reference_at = last_checkin_at or partnership.started_at or partnership.created_at
    if reference_at is None:
        return True

    days_since_reference = (_local_date(now, timezone_name) - _local_date(reference_at, timezone_name)).days
    if last_checkin_at is None:
        return days_since_reference == 0 or days_since_reference >= cadence_days
    return days_since_reference >= cadence_days


async def _already_sent_reminder_today(
    db: AsyncSession,
    *,
    user_id: UUID,
    partnership_id: UUID,
    day_start: datetime,
    day_end: datetime,
) -> bool:
    result = await db.execute(
        select(Notification)
        .where(
            and_(
                Notification.user_id == user_id,
                Notification.type == AccountabilityNotificationType.DAILY_REMINDER.value,
                Notification.created_at >= day_start,
                Notification.created_at <= day_end,
            )
        )
        .order_by(Notification.created_at.desc())
    )
    for notification in result.scalars().all():
        data = notification.data or {}
        if data.get("partnership_id") == str(partnership_id):
            return True
    return False


# ============================================================================
# 任务定义
# ============================================================================

@shared_task(name="tasks.accountability.send_daily_reminders")
def send_daily_reminders():
    """
    发送每日打卡提醒

    执行时间: 每天 9:00, 21:00
    目标: 未打卡的活跃伙伴关系
    """
    logger.info("Starting daily accountability reminders task")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_send_daily_reminders(db))

        logger.info(f"Daily accountability reminders completed: {result}")
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Daily reminders failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.accountability.check_partner_progress")
def check_partner_progress():
    """
    检查伙伴进度，触发成就评估

    执行时间: 每天 23:59
    功能:
    - 计算双方连胜天数
    - 检查里程碑达成
    - 触发成就奖励
    """
    logger.info("Starting partner progress check task")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_check_partner_progress(db))

        logger.info(f"Partner progress check completed: {result}")
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Progress check failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.accountability.evaluate_achievements")
def evaluate_achievements():
    """
    评估并发放成就奖励

    执行时间: 每天 23:59 (在进度检查后执行)
    功能:
    - 检查连胜里程碑 (7天, 30天, 100天)
    - 检查协作成就 (双方同时打卡天数)
    - 发放成就奖励
    """
    logger.info("Starting achievement evaluation task")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_evaluate_achievements(db))

        logger.info(f"Achievement evaluation completed: {result}")
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Achievement evaluation failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.accountability.send_milestone_notification")
def send_milestone_notification(partnership_id: str, user_id: str, milestone_type: str, milestone_data: dict):
    """
    发送里程碑庆祝通知

    Args:
        partnership_id: 伙伴关系ID
        user_id: 用户ID
        milestone_type: 里程碑类型 (streak, checkin_count, etc.)
        milestone_data: 里程碑数据
    """
    logger.info(f"Sending milestone notification for partnership {partnership_id}")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_send_milestone_notification(
                db, UUID(partnership_id), UUID(user_id), milestone_type, milestone_data
            ))

        logger.info(f"Milestone notification sent: {result}")
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Milestone notification failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.accountability.notify_partner_checkin")
def notify_partner_checkin(checkin_id: str, partnership_id: str, checker_id: str):
    """
    通知伙伴已打卡

    当一方打卡时，通知另一方
    """
    logger.info(f"Notifying partner for checkin {checkin_id}")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_notify_partner_checkin(
                db, UUID(checkin_id), UUID(partnership_id), UUID(checker_id)
            ))

        logger.info(f"Partner notified for checkin: {result}")
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Partner notification failed: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# 异步实现函数
# ============================================================================

async def _send_daily_reminders(db: AsyncSession, *, now: datetime | None = None) -> dict[str, Any]:
    """发送每日打卡提醒的核心逻辑"""
    now = now or _utcnow()
    # 获取所有活跃的伙伴关系
    active_partnerships_query = select(AccountabilityPartnership).where(
        AccountabilityPartnership.status == AccountabilityStatus.ACTIVE
    )
    result = await db.execute(active_partnerships_query)
    partnerships = result.scalars().all()

    reminder_count = 0
    skipped_count = 0
    skipped_by_cadence = 0
    skipped_by_preferences = 0
    skipped_duplicates = 0

    for partnership in partnerships:
        # 检查双方是否都已打卡
        users_by_id: dict[UUID, User | None] = {}
        for target_user_id in (partnership.initiator_id, partnership.partner_id):
            users_by_id[target_user_id] = await db.get(User, target_user_id)

        user_day_windows: dict[UUID, tuple[datetime, datetime]] = {
            target_user_id: _local_day_window(_user_timezone_name(user), now)
            for target_user_id, user in users_by_id.items()
        }
        earliest_day_start = min(day_start for day_start, _ in user_day_windows.values())
        latest_day_end = max(day_end for _, day_end in user_day_windows.values())
        checkin_query = select(AccountabilityCheckin).where(
            and_(
                AccountabilityCheckin.partnership_id == partnership.id,
                AccountabilityCheckin.created_at >= earliest_day_start,
                AccountabilityCheckin.created_at <= latest_day_end,
            )
        )
        checkin_result = await db.execute(checkin_query)
        today_checkins = {
            checkin.user_id
            for checkin in checkin_result.scalars().all()
            if user_day_windows.get(checkin.user_id)
            and user_day_windows[checkin.user_id][0]
            <= _utc_naive(checkin.created_at)
            <= user_day_windows[checkin.user_id][1]
        }

        # 确定需要提醒的用户
        users_to_remind = []
        if partnership.initiator_id not in today_checkins:
            users_to_remind.append(partnership.initiator_id)
        if partnership.partner_id not in today_checkins:
            users_to_remind.append(partnership.partner_id)

        if not users_to_remind:
            skipped_count += 1
            continue

        # 发送提醒通知
        from app.services.accountability_notification_service import (
            accountability_notification_service,
        )

        for user_id in users_to_remind:
            try:
                target_user = users_by_id.get(user_id)
                if target_user is None:
                    skipped_by_preferences += 1
                    continue

                timezone_name = _user_timezone_name(target_user)
                day_start, day_end = user_day_windows[user_id]
                last_checkin_at = await _last_checkin_at(
                    db,
                    partnership_id=partnership.id,
                    user_id=user_id,
                )
                if not _is_checkin_due_for_cadence(
                    partnership=partnership,
                    last_checkin_at=last_checkin_at,
                    timezone_name=timezone_name,
                    now=now,
                ):
                    skipped_by_cadence += 1
                    continue

                suppression_reason = await _reminder_suppression_reason(
                    db,
                    user_id=user_id,
                    timezone_name=timezone_name,
                    now=now,
                )
                if suppression_reason:
                    skipped_by_preferences += 1
                    logger.debug(
                        "Skipped accountability reminder for user {} partnership {}: {}",
                        user_id,
                        partnership.id,
                        suppression_reason,
                    )
                    continue

                if await _already_sent_reminder_today(
                    db,
                    user_id=user_id,
                    partnership_id=partnership.id,
                    day_start=day_start,
                    day_end=day_end,
                ):
                    skipped_duplicates += 1
                    continue

                # 获取伙伴名称
                partner_id = (
                    partnership.partner_id
                    if user_id == partnership.initiator_id
                    else partnership.initiator_id
                )
                partner = users_by_id.get(partner_id)
                partner_name = _user_display_name(partner, "你的责任伙伴")

                await accountability_notification_service.send_daily_reminder(
                    db, user_id, partnership.id, partner_name
                )
                reminder_count += 1
                missed_days = await _missed_days_for_user(
                    db,
                    partnership_id=partnership.id,
                    user_id=user_id,
                )
                if missed_days >= 3:
                    await PolicySchedulerService(db).handle_event(
                        event_type="peer_missed",
                        payload={
                            "user_id": str(user_id),
                            "partnership_id": str(partnership.id),
                            "missed_days": missed_days,
                        },
                    )

            except Exception as e:
                logger.warning(f"Failed to send reminder to user {user_id}: {e}")

    return {
        "sent_reminders": reminder_count,
        "skipped_partnerships": skipped_count,
        "skipped_by_cadence": skipped_by_cadence,
        "skipped_by_preferences": skipped_by_preferences,
        "skipped_duplicates": skipped_duplicates,
        "total_partnerships": len(partnerships),
    }


async def _check_partner_progress(db: AsyncSession) -> dict[str, Any]:
    """检查伙伴进度的核心逻辑"""
    # 获取所有活跃的伙伴关系
    active_partnerships_query = select(AccountabilityPartnership).where(
        AccountabilityPartnership.status == AccountabilityStatus.ACTIVE
    )
    result = await db.execute(active_partnerships_query)
    partnerships = result.scalars().all()

    stats = {
        "total_partnerships": len(partnerships),
        "streak_milestones": [],
        "perfect_days": [],
    }

    for partnership in partnerships:
        try:
            # 计算双方连胜天数
            initiator_streak = await _calculate_streak(db, partnership.id, partnership.initiator_id)
            partner_streak = await _calculate_streak(db, partnership.id, partnership.partner_id)

            # 检查连胜里程碑
            for user_id, streak in [
                (partnership.initiator_id, initiator_streak),
                (partnership.partner_id, partner_streak),
            ]:
                milestone = None
                if streak == 7:
                    milestone = "7_day_streak"
                elif streak == 30:
                    milestone = "30_day_streak"
                elif streak == 100:
                    milestone = "100_day_streak"

                if milestone:
                    stats["streak_milestones"].append({
                        "partnership_id": str(partnership.id),
                        "user_id": str(user_id),
                        "milestone": milestone,
                        "streak_days": streak,
                    })

                    # 调度里程碑通知任务
                    from app.core.celery_app import celery_app

                    celery_app.send_task(
                        "tasks.accountability.send_milestone_notification",
                        args=(str(partnership.id), str(user_id), milestone, {"streak_days": streak}),
                        queue="default",
                    )

            # 检查今天双方是否都打卡 (完美一天)
            today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            checkin_query = select(AccountabilityCheckin).where(
                and_(
                    AccountabilityCheckin.partnership_id == partnership.id,
                    AccountabilityCheckin.created_at >= today_start,
                )
            )
            checkin_result = await db.execute(checkin_query)
            today_checkins = {c.user_id for c in checkin_result.scalars().all()}

            if (
                partnership.initiator_id in today_checkins
                and partnership.partner_id in today_checkins
            ):
                stats["perfect_days"].append(str(partnership.id))

        except Exception as e:
            logger.warning(f"Failed to check progress for partnership {partnership.id}: {e}")

    return stats


async def _evaluate_achievements(db: AsyncSession) -> dict[str, Any]:
    """评估成就的核心逻辑"""
    from app.services.accountability_achievement_service import (
        accountability_achievement_service,
    )

    # 获取所有活跃的伙伴关系
    active_partnerships_query = select(AccountabilityPartnership).where(
        AccountabilityPartnership.status == AccountabilityStatus.ACTIVE
    )
    result = await db.execute(active_partnerships_query)
    partnerships = result.scalars().all()

    stats = {
        "achievements_awarded": [],
        "total_evaluated": len(partnerships),
    }

    for partnership in partnerships:
        try:
            # 检查双方的成就
            for user_id in [partnership.initiator_id, partnership.partner_id]:
                achievements = await accountability_achievement_service.check_streak_achievements(
                    db, user_id, partnership.id
                )

                for achievement in achievements:
                    stats["achievements_awarded"].append({
                        "user_id": str(user_id),
                        "partnership_id": str(partnership.id),
                        "achievement_id": achievement,
                    })

        except Exception as e:
            logger.warning(f"Failed to evaluate achievements for partnership {partnership.id}: {e}")

    return stats


async def _send_milestone_notification(
    db: AsyncSession,
    partnership_id: UUID,
    user_id: UUID,
    milestone_type: str,
    milestone_data: dict,
) -> dict[str, Any]:
    """发送里程碑通知"""
    from app.services.accountability_notification_service import (
        accountability_notification_service,
    )

    milestone_messages = {
        "7_day_streak": "🔥 恭喜！你已经连续打卡7天了！",
        "30_day_streak": "🏆 太棒了！连续打卡30天达成！",
        "100_day_streak": "💯 了不起！连续打卡100天里程碑！",
        "perfect_month": "⭐ 完美月份！这个月你每天都坚持打卡！",
    }

    message = milestone_messages.get(
        milestone_type, f"🎉 恭喜达成里程碑: {milestone_type}"
    )

    await accountability_notification_service.send_streak_milestone(
        db, user_id, partnership_id, message, milestone_data
    )

    return {
        "partnership_id": str(partnership_id),
        "user_id": str(user_id),
        "milestone_type": milestone_type,
    }


async def _notify_partner_checkin(
    db: AsyncSession,
    checkin_id: UUID,
    partnership_id: UUID,
    checker_id: UUID,
) -> dict[str, Any]:
    """通知伙伴已打卡"""
    # 获取伙伴关系
    partnership = await db.get(AccountabilityPartnership, partnership_id)
    if not partnership:
        return {"status": "error", "message": "Partnership not found"}

    # 确定通知目标 (伙伴)
    partner_id = (
        partnership.partner_id
        if checker_id == partnership.initiator_id
        else partnership.initiator_id
    )

    # 获取打卡用户名称
    checker_result = await db.execute(select(User).where(User.id == checker_id))
    checker = checker_result.scalar_one_or_none()

    from app.services.accountability_notification_service import (
        accountability_notification_service,
    )

    await accountability_notification_service.send_partner_checked_in(
        db, partner_id, partnership_id, _user_display_name(checker, "你的伙伴")
    )

    return {
        "partnership_id": str(partnership_id),
        "partner_id": str(partner_id),
        "checkin_id": str(checkin_id),
    }


async def _calculate_streak(
    db: AsyncSession,
    partnership_id: UUID,
    user_id: UUID,
    *,
    quality_threshold: bool = True,
) -> int:
    """计算用户的连续打卡天数。

    当 quality_threshold=True 时，只有"高质量"打卡才计入连续天数：
    满足 mood >= 4 或 minutes >= 15 的打卡才视为有效日。
    这避免纯二进制计数——任何活动≠高质量日。
    """
    from collections import defaultdict
    from datetime import date

    result = await db.execute(
        select(
            AccountabilityCheckin.created_at,
            AccountabilityCheckin.mood,
            AccountabilityCheckin.minutes,
        )
        .where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == user_id,
            )
        )
        .order_by(AccountabilityCheckin.created_at.desc())
    )

    # 按日期分组，记录每日最高质量的检查
    daily_best: dict[date, dict] = defaultdict(lambda: {"mood": 0, "minutes": 0})
    for ts, mood, minutes in result.all():
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        d = ts.date()
        if mood and mood > daily_best[d]["mood"]:
            daily_best[d]["mood"] = mood
        if minutes and minutes > daily_best[d]["minutes"]:
            daily_best[d]["minutes"] = minutes

    def _is_quality_day(d: date) -> bool:
        if not quality_threshold:
            return d in daily_best
        best = daily_best.get(d)
        if best is None:
            return False
        return best["mood"] >= 4 or best["minutes"] >= 15

    # 计算连续天数
    today_utc = _utcnow().date()
    streak = 0
    current = today_utc

    while _is_quality_day(current):
        streak += 1
        current -= timedelta(days=1)

    return streak


# ============================================================================
# Celery Beat 配置
# ============================================================================

CELERYBEAT_SCHEDULE = {
    # 每天早上9点发送打卡提醒
    "accountability-daily-reminders-morning": {
        "task": "tasks.accountability.send_daily_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    # 每天晚上9点再次发送提醒
    "accountability-daily-reminders-evening": {
        "task": "tasks.accountability.send_daily_reminders",
        "schedule": crontab(hour=21, minute=0),
    },
    # 每天晚上11:59检查进度
    "accountability-progress-check": {
        "task": "tasks.accountability.check_partner_progress",
        "schedule": crontab(hour=23, minute=59),
    },
    # 每天晚上11:59评估成就
    "accountability-achievement-evaluation": {
        "task": "tasks.accountability.evaluate_achievements",
        "schedule": crontab(hour=23, minute=59),
    },
}
