"""
Health Check API
健康检查端点 - 包含数据库连接状态检查
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, engine
from app.config import settings

router = APIRouter()


class DatabaseHealth(BaseModel):
    """数据库健康状态"""
    connected: bool
    latency_ms: Optional[float] = None
    pool_size: Optional[int] = None
    pool_checked_out: Optional[int] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    version: str
    database: DatabaseHealth
    uptime_seconds: Optional[float] = None


# 记录启动时间
_start_time: Optional[datetime] = None


def set_start_time():
    """设置启动时间（在应用启动时调用）"""
    global _start_time
    _start_time = datetime.utcnow()


def get_uptime_seconds() -> Optional[float]:
    """获取运行时间（秒）"""
    if _start_time is None:
        return None
    return (datetime.utcnow() - _start_time).total_seconds()


async def check_database_health(db: AsyncSession) -> DatabaseHealth:
    """
    检查数据库连接健康状态

    执行简单的 SELECT 1 查询来验证连接
    """
    try:
        start = datetime.utcnow()

        # 执行简单查询验证连接
        await db.execute(text("SELECT 1"))

        end = datetime.utcnow()
        latency_ms = (end - start).total_seconds() * 1000

        # 获取连接池信息（仅 PostgreSQL）
        pool_size = None
        pool_checked_out = None

        if not settings.DATABASE_URL.startswith("sqlite"):
            try:
                pool = engine.pool
                pool_size = pool.size()
                pool_checked_out = pool.checkedout()
            except Exception:
                pass

        return DatabaseHealth(
            connected=True,
            latency_ms=round(latency_ms, 2),
            pool_size=pool_size,
            pool_checked_out=pool_checked_out,
        )

    except Exception as e:
        return DatabaseHealth(
            connected=False,
            error=str(e),
        )


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    完整健康检查

    返回应用和数据库的健康状态
    """
    db_health = await check_database_health(db)

    # 根据数据库状态确定整体健康状态
    if db_health.connected:
        if db_health.latency_ms and db_health.latency_ms > 1000:
            status = "degraded"  # 数据库响应慢
        else:
            status = "healthy"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        version=settings.APP_VERSION,
        database=db_health,
        uptime_seconds=get_uptime_seconds(),
    )


@router.get("/liveness")
async def liveness_check():
    """
    存活检查（Kubernetes liveness probe）

    仅检查应用是否运行，不检查依赖服务
    """
    return {"status": "alive"}


@router.get("/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    就绪检查（Kubernetes readiness probe）

    检查应用是否准备好接收流量
    """
    db_health = await check_database_health(db)

    if db_health.connected:
        return {"status": "ready"}
    else:
        return {"status": "not_ready", "reason": "database_unavailable"}


@router.get("/database")
async def database_health(db: AsyncSession = Depends(get_db)):
    """
    数据库详细健康信息

    返回数据库连接池和性能信息
    """
    health = await check_database_health(db)

    return {
        "database": {
            "type": "postgresql" if not settings.DATABASE_URL.startswith("sqlite") else "sqlite",
            "connected": health.connected,
            "latency_ms": health.latency_ms,
            "pool": {
                "size": health.pool_size,
                "checked_out": health.pool_checked_out,
                "config": {
                    "pool_size": settings.DB_POOL_SIZE if not settings.DATABASE_URL.startswith("sqlite") else None,
                    "max_overflow": settings.DB_MAX_OVERFLOW if not settings.DATABASE_URL.startswith("sqlite") else None,
                    "pool_recycle": settings.DB_POOL_RECYCLE if not settings.DATABASE_URL.startswith("sqlite") else None,
                }
            } if not settings.DATABASE_URL.startswith("sqlite") else None,
            "error": health.error,
        }
    }
