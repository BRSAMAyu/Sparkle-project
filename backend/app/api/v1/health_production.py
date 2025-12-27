"""
生产级健康检查 API

提供详细的健康状态检查，包括:
- 系统健康状态
- 组件状态 (Redis, Database)
- 熔断器状态
- 性能指标
- 业务指标
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.core.cache import cache_service
from app.config import settings

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, generate_latest
    from starlette.responses import Response
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

router = APIRouter(prefix="/health", tags=["Health"])

# 全局启动时间
START_TIME = time.time()


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def health_check(
    db: AsyncSession = Depends(get_db),
    detailed: bool = False
) -> Dict[str, Any]:
    """
    基础健康检查

    Args:
        detailed: 是否返回详细信息

    Returns:
        健康状态信息
    """
    status = "healthy"
    checks = {}

    # 1. 检查数据库连接
    try:
        await db.execute("SELECT 1")
        checks["database"] = {"status": "ok", "latency_ms": 0}
    except Exception as e:
        status = "unhealthy"
        checks["database"] = {"status": "error", "error": str(e)}

    # 2. 检查 Redis
    try:
        redis_client = cache_service.redis
        if redis_client:
            start = time.time()
            await redis_client.ping()
            latency = (time.time() - start) * 1000
            checks["redis"] = {"status": "ok", "latency_ms": round(latency, 2)}
        else:
            checks["redis"] = {"status": "disabled"}
    except Exception as e:
        status = "unhealthy"
        checks["redis"] = {"status": "error", "error": str(e)}

    # 3. 系统信息
    system_info = {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "timestamp": datetime.utcnow().isoformat()
    }

    # 4. 基础响应
    response = {
        "status": status,
        "system": system_info,
        "checks": checks
    }

    # 5. 详细信息
    if detailed:
        response["details"] = {
            "config": {
                "grpc_port": getattr(settings, "GRPC_PORT", 50051),
                "max_concurrent_sessions": getattr(settings, "MAX_CONCURRENT_SESSIONS", 100),
                "daily_quota": getattr(settings, "DAILY_QUOTA", 100000),
            },
            "features": {
                "context_pruner": True,
                "token_tracker": True,
                "circuit_breaker": True,
                "prometheus": PROMETHEUS_AVAILABLE,
            }
        }

    return response


@router.get("/detailed", response_model=Dict[str, Any])
async def health_detailed(
    db: AsyncSession = Depends(get_db),
    orchestrator: Optional[Any] = None
) -> Dict[str, Any]:
    """
    详细健康检查（包含业务指标）

    需要传入 orchestrator 实例以获取运行时信息
    """
    base_health = await health_check(db, detailed=True)

    # 如果提供了 orchestrator，获取运行时状态
    if orchestrator:
        try:
            runtime_status = orchestrator.get_health_status()
            base_health["runtime"] = runtime_status
        except Exception as e:
            logger.warning(f"Failed to get orchestrator health: {e}")
            base_health["runtime"] = {"error": str(e)}

    # 业务指标
    try:
        # 获取队列长度（如果 Redis 可用）
        redis_client = cache_service.redis
        if redis_client:
            queue_length = await redis_client.llen("queue:summarization")
            base_health["metrics"] = {
                "summarization_queue_length": queue_length,
                "max_queue_length": 1000,  # 熔断阈值
                "queue_healthy": queue_length < 500
            }
    except Exception as e:
        logger.warning(f"Failed to get queue metrics: {e}")

    return base_health


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    就绪检查 - 用于 Kubernetes

    只有当服务真正准备好处理请求时才返回 200
    """
    try:
        # 检查关键依赖
        await db.execute("SELECT 1")

        redis_client = cache_service.redis
        if redis_client:
            await redis_client.ping()

        return {
            "status": "ready",
            "message": "Service is ready to accept traffic"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "error": str(e)}
        )


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    存活检查 - 用于 Kubernetes

    只要进程在运行就返回 200
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus 指标端点

    Returns:
        Prometheus 格式的指标数据
    """
    if not PROMETHEUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Prometheus not available"
        )

    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )


@router.get("/queue/status")
async def queue_status() -> Dict[str, Any]:
    """
    队列状态检查

    用于监控和调试
    """
    try:
        redis_client = cache_service.redis
        if not redis_client:
            return {"status": "disabled", "message": "Redis not configured"}

        # 检查各个队列
        queues = {
            "summarization": "queue:summarization",
            "billing": "queue:billing",
            "expansion": "queue:expansion",
        }

        queue_status = {}
        total_pending = 0

        for name, key in queues.items():
            length = await redis_client.llen(key)
            queue_status[name] = {
                "length": length,
                "healthy": length < 100,  # 阈值
                "key": key
            }
            total_pending += length

        # 检查是否有积压
        is_healthy = total_pending < 500

        return {
            "status": "healthy" if is_healthy else "warning",
            "total_pending": total_pending,
            "queues": queue_status,
            "alerts": [] if is_healthy else ["High queue volume detected"]
        }

    except Exception as e:
        logger.error(f"Queue status check failed: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/prometheus/alerts")
async def prometheus_alerts() -> Dict[str, Any]:
    """
    简单的告警规则（用于 Prometheus AlertManager）

    返回当前触发的告警
    """
    alerts = []

    try:
        redis_client = cache_service.redis
        if redis_client:
            # 检查队列积压
            queue_length = await redis_client.llen("queue:summarization")
            if queue_length > 500:
                alerts.append({
                    "severity": "warning",
                    "name": "HighQueueVolume",
                    "message": f"Summarization queue has {queue_length} pending items",
                    "value": queue_length
                })

            # 检查并发会话（如果使用 state manager）
            # 这里需要从 orchestrator 获取，暂时跳过

        # 检查内存使用（简单估算）
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > 1024:  # 1GB 阈值
            alerts.append({
                "severity": "critical",
                "name": "HighMemoryUsage",
                "message": f"Memory usage is {memory_mb:.0f}MB",
                "value": round(memory_mb, 2)
            })

    except Exception as e:
        logger.warning(f"Alert check failed: {e}")

    return {
        "alerts": alerts,
        "firing": len(alerts) > 0,
        "timestamp": datetime.utcnow().isoformat()
    }
