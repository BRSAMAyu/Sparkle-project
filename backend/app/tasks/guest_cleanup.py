"""
游客数据清理任务
Guest User Cleanup Tasks

定期清理长期未活跃的游客用户数据
"""
from datetime import UTC, datetime, timedelta

from celery import shared_task
from celery.schedules import crontab
from loguru import logger
from sqlalchemy import delete, select

from app.db.session import get_db_context
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@shared_task(name="tasks.cleanup_expired_guests")
def cleanup_expired_guests():
    """
    清理长期未活跃的游客用户（每周执行）

    清理条件：
    - registration_source == "guest"
    - last_login_at < 30天前

    注意：游客升级后的数据不会被清理
    """
    logger.info("Starting expired guest users cleanup task")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_cleanup_expired_guests(db))

        logger.info(f"Expired guest cleanup completed: {result}")
        return {"status": "success", "deleted_count": result}

    except Exception as e:
        logger.error(f"Expired guest cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="tasks.cleanup_guest_sessions")
def cleanup_guest_sessions():
    """
    清理游客用户的过期会话数据（每日执行）

    清理超过7天未活跃的游客会话缓存
    """
    logger.info("Starting guest session cleanup task")

    try:
        with get_db_context() as db:
            import asyncio
            result = asyncio.run(_cleanup_guest_sessions(db))

        logger.info(f"Guest session cleanup completed: {result}")
        return {"status": "success", "cleaned_count": result}

    except Exception as e:
        logger.error(f"Guest session cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


# ==================== 异步实现函数 ====================

async def _cleanup_expired_guests(db) -> int:
    """
    清理过期游客用户的核心逻辑

    Args:
        db: 数据库会话

    Returns:
        删除的用户数量
    """
    cutoff_date = _utcnow() - timedelta(days=30)

    # 先统计要删除的数量
    count_query = select(User.id).where(
        User.registration_source == "guest",
        User.last_login_at < cutoff_date,
    )
    result = await db.execute(count_query)
    user_ids_to_delete = [row[0] for row in result.all()]

    if not user_ids_to_delete:
        logger.info("No expired guest users to clean up")
        return 0

    logger.info(f"Found {len(user_ids_to_delete)} expired guest users to delete")

    # 执行删除
    delete_query = delete(User).where(
        User.id.in_(user_ids_to_delete),
        User.registration_source == "guest",
    )
    await db.execute(delete_query)
    await db.commit()

    logger.info(f"Deleted {len(user_ids_to_delete)} expired guest users")
    return len(user_ids_to_delete)


async def _cleanup_guest_sessions(db) -> int:
    """
    清理游客会话数据

    注意：这部分主要是清理Redis中的会话缓存
    实际实现需要根据会话存储机制调整

    Args:
        db: 数据库会话

    Returns:
        清理的会话数量
    """
    # 这里主要是占位实现
    # 实际的会话清理应该在Redis层面进行
    # 可以通过 session_id 前缀或 TTL 自动过期来处理

    cutoff_date = _utcnow() - timedelta(days=7)

    # 查询7天未活跃的游客用户
    query = select(User.id).where(
        User.registration_source == "guest",
        User.last_login_at < cutoff_date,
    )
    result = await db.execute(query)
    inactive_guests = [row[0] for row in result.all()]

    # 这里可以添加Redis会话清理逻辑
    # 例如: await redis.delete(f"session:{user_id}")

    logger.info(f"Identified {len(inactive_guests)} guests with stale sessions")
    return len(inactive_guests)


# Celery Beat 配置
CELERYBEAT_SCHEDULE = {
    "cleanup-expired-guests": {
        "task": "tasks.guest_cleanup.cleanup_expired_guests",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),  # 每周日凌晨5点
    },
    "cleanup-guest-sessions": {
        "task": "tasks.guest_cleanup.cleanup_guest_sessions",
        "schedule": crontab(hour=6, minute=0),  # 每天凌晨6点
    },
}
