"""
Community Group Check-in Reminder Task

Sends push notifications to group members who have not yet checked in today.
Runs on a daily schedule (morning + evening) alongside accountability reminders.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from celery import shared_task
from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_context


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _send_group_checkin_reminders(db: AsyncSession, *, now: datetime | None = None) -> dict[str, Any]:
    """Send check-in reminder notifications to group members who haven't checked in today."""
    from app.models.community import Group, GroupMember
    from app.models.user import User
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService

    now = now or _utcnow()
    today = now.date()

    # Get all active group members who haven't checked in today
    members_stmt = select(GroupMember).where(
        GroupMember.not_deleted_filter(),
        or_(
            GroupMember.last_checkin_date.is_(None),
            func.date(GroupMember.last_checkin_date) < today,
        ),
    )
    result = await db.execute(members_stmt)
    overdue_members = result.scalars().all()

    reminders_sent = 0
    groups_processed: set[str] = set()

    for member in overdue_members:
        group_id_str = str(member.group_id)

        # Get group info (cache-friendly: one query per group)
        group = await db.get(Group, member.group_id)
        if not group or group.is_deleted:
            continue
        groups_processed.add(group_id_str)

        group_name = group.name or "群组"

        try:
            await NotificationService.create(
                db,
                member.user_id,
                NotificationCreate(
                    title="群组打卡提醒",
                    content=f"「{group_name}」的伙伴们还在等你打卡哦，坚持就是胜利！",
                    type="community_checkin_reminder",
                    data={
                        "group_id": group_id_str,
                        "group_name": group_name,
                        "kind": "community_checkin_reminder",
                    },
                ),
            )
            reminders_sent += 1
        except Exception:
            logger.opt(exception=True).debug(
                "Failed to send checkin reminder to user {} for group {}",
                member.user_id,
                group_id_str,
            )

    return {
        "reminders_sent": reminders_sent,
        "groups_processed": len(groups_processed),
    }


@shared_task(name="tasks.community.send_checkin_reminders")
def send_checkin_reminders():
    """
    Send group check-in reminder notifications.

    Runs twice daily to nudge members who haven't checked in.
    """
    logger.info("Starting community check-in reminders task")

    try:
        with get_db_context() as db:
            result = asyncio.run(_send_group_checkin_reminders(db))

        logger.info(f"Community check-in reminders completed: {result}")
        return {"status": "success", **result}

    except Exception as e:
        logger.error(f"Community check-in reminders failed: {e}")
        return {"status": "error", "message": str(e)}
