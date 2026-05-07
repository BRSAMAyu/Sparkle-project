"""
LoginAttempt GDPR retention cleanup task.
Deletes login attempt records older than 90 days to comply with
GDPR storage limitation principle.
"""
from datetime import UTC, datetime, timedelta

from app.core.time_utils import utcnow as _utcnow
from celery import shared_task
from celery.schedules import crontab
from loguru import logger
from sqlalchemy import delete, select

from app.db.session import get_db_context
from app.models.user import LoginAttempt


@shared_task(
    name="tasks.cleanup_old_login_attempts",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def cleanup_old_login_attempts():
    """
    Remove login attempt records older than 90 days (GDPR storage limitation).

    Runs daily at 04:00 UTC.
    """
    logger.info("Starting old login attempt cleanup (90-day retention)")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_cleanup_old_login_attempts(db))

        logger.info("Old login attempt cleanup completed: {}", result)
        return {"status": "success", "deleted_count": result}

    except Exception as e:
        logger.error("Old login attempt cleanup failed: {}", str(e))
        return {"status": "error", "message": str(e)}


async def _cleanup_old_login_attempts(db) -> int:
    """
    Delete login_attempts records older than 90 days.

    Returns:
        Number of deleted records.
    """
    cutoff_date = _utcnow() - timedelta(days=90)

    # Count records to delete
    count_query = select(LoginAttempt.id).where(
        LoginAttempt.attempted_at < cutoff_date,
    )
    result = await db.execute(count_query)
    ids_to_delete = [row[0] for row in result.all()]

    if not ids_to_delete:
        logger.info("No expired login attempts to clean up")
        return 0

    logger.info("Found {} login attempts older than 90 days to delete", len(ids_to_delete))

    # Execute deletion in batches to avoid long-running transactions
    batch_size = 500
    total_deleted = 0
    for i in range(0, len(ids_to_delete), batch_size):
        batch = ids_to_delete[i : i + batch_size]
        delete_query = delete(LoginAttempt).where(LoginAttempt.id.in_(batch))
        await db.execute(delete_query)
        await db.commit()
        total_deleted += len(batch)

    logger.info("Deleted {} expired login attempts", total_deleted)
    return total_deleted


# Celery Beat schedule
CELERYBEAT_SCHEDULE = {
    "cleanup-old-login-attempts": {
        "task": "tasks.login_attempt_cleanup.cleanup_old_login_attempts",
        "schedule": crontab(hour=4, minute=0),  # Daily at 04:00 UTC
    },
}
