"""
UserSession retention cleanup task (SESSION-GC, AUTH-DEEP A-2 末行 P2).

user_sessions 每 login/refresh upsert 一行，revoke 只置 revoked_at/is_active，
此前无任何清理路径 → 行只增不减（live 探针：500 行、12 行 revoked）。
本任务按保留期物理删除过期行：

判据（两侧都过保活期才删）：
- ``coalesce(revoked_at, last_active_at) < cutoff``：revoked 行看 revoked_at，
  从未 revoke 的行自然回退到 last_active_at；
- ``last_active_at < cutoff``：保活期内无任何请求（touch_session 会刷新该列，
  真实在用会话不可能命中）。

安全边界：
- 刚 revoke 但 TTL 内的行保留——Redis ``session_revoked:{sid}`` 标记 TTL 与
  SESSION_TTL_SECONDS 同源（auth.py 的 SESSION_TTL_SECONDS），TTL 内仍可审计查询；
- 未 revoke 但长期不活跃的行，其 refresh token 寿命即 REFRESH_TOKEN_EXPIRE_DAYS
  （与 SESSION_TTL_SECONDS 同一配置源），token 已过期且任何使用都会刷新
  last_active_at，删除不扩大风险面。

删除分批（BATCH_SIZE 行/批，每批独立短事务提交）避免长事务锁表；
结构沿用 login_attempt_cleanup 先例（get_db_context + asyncio.run 驱动协程）。
"""

from datetime import timedelta

from celery import shared_task
from loguru import logger
from sqlalchemy import and_ as sa_and
from sqlalchemy import delete, func, select

from app.config import settings
from app.core.time_utils import utcnow as _utcnow
from app.db.session import get_db_context
from app.models.auth_security import UserSession

# 会话保留期：与 auth 域 SESSION_TTL_SECONDS（app/api/v1/auth.py:78）同源，
# 都锚定 settings.REFRESH_TOKEN_EXPIRE_DAYS。
SESSION_TTL_SECONDS = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

# 每批删除行数（每批一个短事务，避免长事务锁表）
BATCH_SIZE = 500


@shared_task(
    name="tasks.cleanup_expired_user_sessions",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def cleanup_expired_user_sessions():
    """
    删除过保活期的 user_sessions 行（两侧判据见模块 docstring）。

    每日低峰执行（beat: cleanup-expired-user-sessions-daily，low_priority 车道）。
    """
    logger.info("Starting expired user session cleanup (TTL={}s)", SESSION_TTL_SECONDS)

    try:
        with get_db_context() as db:
            import asyncio

            deleted = asyncio.run(_cleanup_expired_user_sessions(db))
    except Exception as e:
        logger.error("Expired user session cleanup failed: {}", str(e))
        return {"status": "error", "message": str(e)}

    logger.info("Expired user session cleanup completed: deleted {} rows", deleted)
    _record_deleted_metric(deleted)
    return {"status": "success", "deleted_count": deleted}


def _record_deleted_metric(deleted: int) -> None:
    """清理行数计数器（复用全局 metrics 面，失败不影响清理结果）。"""
    try:
        from prometheus_client import Counter

        from app.core.metrics import get_or_create_metric

        counter = get_or_create_metric(
            Counter,
            "sparkle_user_sessions_cleanup_deleted_total",
            "Expired user_sessions rows deleted by retention cleanup",
        )
        counter.inc(deleted)
    except Exception as e:  # noqa: BLE001 — 可观测面绝不阻塞清理任务本身
        logger.warning("user session cleanup metric record failed: {}", e)


async def _cleanup_expired_user_sessions(db) -> int:
    """
    分批删除过保活期的 user_sessions 行。

    Returns:
        物理删除的总行数。
    """
    cutoff = _utcnow() - timedelta(seconds=SESSION_TTL_SECONDS)
    expired_criterion = sa_and(
        func.coalesce(UserSession.revoked_at, UserSession.last_active_at) < cutoff,
        UserSession.last_active_at < cutoff,
    )

    total_deleted = 0
    while True:
        # 每批先取主键再按主键删：批内短事务（select+delete+commit），
        # 批间释放锁，避免长事务锁表。
        ids_result = await db.execute(select(UserSession.id).where(expired_criterion).limit(BATCH_SIZE))
        batch_ids = [row[0] for row in ids_result.all()]
        if not batch_ids:
            break

        await db.execute(delete(UserSession).where(UserSession.id.in_(batch_ids)))
        await db.commit()
        total_deleted += len(batch_ids)

        if len(batch_ids) < BATCH_SIZE:
            break

    return total_deleted
