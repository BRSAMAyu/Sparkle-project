"""
责任伙伴系统定时任务
Accountability Partnership Scheduled Tasks

定时任务:
- 每日打卡提醒
- 进度检查和成就评估
- 里程碑庆祝
"""
from datetime import timezone, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

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
from app.models.user import User
from app.services.policy_scheduler_service import PolicySchedulerService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

async def _send_daily_reminders(db: AsyncSession) -> dict[str, Any]:
    """发送每日打卡提醒的核心逻辑"""
    # 获取所有活跃的伙伴关系
    active_partnerships_query = select(AccountabilityPartnership).where(
        AccountabilityPartnership.status == AccountabilityStatus.ACTIVE
    )
    result = await db.execute(active_partnerships_query)
    partnerships = result.scalars().all()

    # 获取今天的开始时间 (timezone.utc)
    today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    reminder_count = 0
    skipped_count = 0

    for partnership in partnerships:
        # 检查双方是否都已打卡
        checkin_query = select(AccountabilityCheckin).where(
            and_(
                AccountabilityCheckin.partnership_id == partnership.id,
                AccountabilityCheckin.created_at >= today_start,
            )
        )
        checkin_result = await db.execute(checkin_query)
        today_checkins = {c.user_id for c in checkin_result.scalars().all()}

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
                # 获取伙伴名称
                partner_id = (
                    partnership.partner_id
                    if user_id == partnership.initiator_id
                    else partnership.initiator_id
                )
                partner_result = await db.execute(select(User).where(User.id == partner_id))
                partner = partner_result.scalar_one_or_none()
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


async def _calculate_streak(db: AsyncSession, partnership_id: UUID, user_id: UUID) -> int:
    """计算用户的连续打卡天数"""
    from datetime import date

    # 获取所有打卡记录
    result = await db.execute(
        select(AccountabilityCheckin.created_at)
        .where(
            and_(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == user_id,
            )
        )
        .order_by(AccountabilityCheckin.created_at.desc())
    )

    checkin_dates: set[date] = set()
    for (ts,) in result.all():
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        checkin_dates.add(ts.date())

    # 计算连续天数
    today_utc = _utcnow().date()
    streak = 0
    current = today_utc

    while current in checkin_dates:
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
