"""
推荐缓存过期清理任务
Recommendation Cache Expiry Cleanup Task

V3-FIX-340 接线裁决（wt646）：本任务自 update_similarities.py 拆出并真实接入
celery（include + beat + 路由）。激活依据=RecommendationCache 有活写入方——
community 好友推荐（FriendMatchService._cache_recommendations）与群组推荐
（GroupRecommendationService._cache_recommendations）在每次推荐 miss 时落行，
过期行只在用户反馈时被逐用户软删，无全局清扫；本任务每小时硬删
expires_at < now 的过期行与墓碑。
"""
from typing import TYPE_CHECKING, Any, cast

from celery import shared_task
from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import utcnow as _utcnow
from app.db.session import get_db_context

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


@shared_task(
    name="tasks.expire_old_recommendation_cache",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def expire_old_recommendation_cache():
    """
    清理过期的推荐缓存

    每小时执行一次
    """
    logger.info("Starting recommendation cache cleanup")

    try:
        with get_db_context() as db:
            import asyncio
            asyncio.run(_cleanup_expired_cache(db))

        logger.info("Recommendation cache cleanup completed")
        return {"status": "success", "cleaned": True}

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return {"status": "error", "message": str(e)}


async def _cleanup_expired_cache(db: AsyncSession) -> int:
    """清理过期的推荐缓存"""
    from app.models.recommendation import RecommendationCache

    # 删除过期的缓存
    delete_query = delete(RecommendationCache).where(
        RecommendationCache.expires_at < _utcnow()
    )
    result = await db.execute(delete_query)
    deleted_count = cast("CursorResult[Any]", (result)).rowcount

    await db.commit()
    logger.info(f"Cleaned up {deleted_count} expired cache entries")
    return cast("int", (deleted_count))
