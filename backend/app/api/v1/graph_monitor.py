"""
GraphRAG 监控 API

提供 GraphRAG 系统的详细监控指标和健康检查
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.api.deps import get_current_active_superuser
from app.core.cache import cache_service
from app.config import settings
try:
    from app.services.graph_knowledge_service import GraphKnowledgeService
    GRAPH_SERVICE_AVAILABLE = True
except ModuleNotFoundError as exc:
    GraphKnowledgeService = None
    GRAPH_SERVICE_AVAILABLE = False
    logger.warning(f"GraphKnowledgeService unavailable: {exc}")

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest
    from starlette.responses import Response
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

router = APIRouter(
    prefix="/monitor/graph",
    tags=["GraphRAG Monitoring"],
    dependencies=[Depends(get_current_active_superuser)],
)

# GraphRAG specific metrics
if PROMETHEUS_AVAILABLE:
    GRAPH_RAG_REQUESTS = Counter(
        'graph_rag_requests_total',
        'Total GraphRAG requests',
        ['status', 'query_type']
    )

    GRAPH_RAG_DURATION = Histogram(
        'graph_rag_duration_seconds',
        'GraphRAG query duration',
        ['operation']
    )

    GRAPH_DB_CONNECTION = Gauge(
        'graph_db_connection_status',
        'Graph database connection status (1=healthy, 0=unhealthy)'
    )

    GRAPH_NODE_COUNT = Gauge(
        'graph_nodes_total',
        'Total nodes in graph database'
    )

    GRAPH_RELATION_COUNT = Gauge(
        'graph_relations_total',
        'Total relations in graph database'
    )


def _require_graph_service(db: AsyncSession) -> "GraphKnowledgeService":
    if not GRAPH_SERVICE_AVAILABLE or GraphKnowledgeService is None:
        logger.warning("GraphRAG service not available; returning 501 for graph monitor endpoints.")
        raise HTTPException(
            status_code=501,
            detail="GraphRAG service is not available in this deployment."
        )
    return GraphKnowledgeService(db)


@router.get("/health", response_model=Dict[str, Any])
async def graph_rag_health(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    GraphRAG 系统健康检查

    检查:
    1. 图数据库连接状态
    2. 向量数据库连接状态
    3. 数据同步状态
    4. 查询性能
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
        "metrics": {},
        "alerts": []
    }

    try:
        graph_ks = _require_graph_service(db)

        # 1. 检查图数据库连接
        with GRAPH_RAG_DURATION.labels(operation="health_check").time():
            graph_connected = await graph_ks.check_graph_connection()

        health_status["components"]["graph_db"] = {
            "status": "connected" if graph_connected else "disconnected",
            "type": "Apache AGE"
        }

        if not graph_connected:
            health_status["status"] = "degraded"
            health_status["alerts"].append({
                "severity": "warning",
                "message": "Graph database connection failed"
            })
            if PROMETHEUS_AVAILABLE:
                GRAPH_DB_CONNECTION.set(0)
        else:
            if PROMETHEUS_AVAILABLE:
                GRAPH_DB_CONNECTION.set(1)

        # 2. 检查向量数据库连接
        try:
            vector_connected = await graph_ks.check_vector_connection()
            health_status["components"]["vector_db"] = {
                "status": "connected" if vector_connected else "disconnected",
                "type": "pgvector"
            }

            if not vector_connected:
                health_status["status"] = "degraded"
                health_status["alerts"].append({
                    "severity": "warning",
                    "message": "Vector database connection failed"
                })
        except Exception as e:
            health_status["components"]["vector_db"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"

        # 3. 获取图数据统计
        if graph_connected:
            try:
                stats = await graph_ks.get_graph_statistics()
                health_status["metrics"]["graph_stats"] = stats

                # 更新 Prometheus 指标
                if PROMETHEUS_AVAILABLE:
                    GRAPH_NODE_COUNT.set(stats.get("total_nodes", 0))
                    GRAPH_RELATION_COUNT.set(stats.get("total_relations", 0))

                # 检查数据量是否正常
                if stats.get("total_nodes", 0) == 0:
                    health_status["alerts"].append({
                        "severity": "info",
                        "message": "Graph database is empty (no nodes)"
                    })

            except Exception as e:
                logger.warning(f"Failed to get graph stats: {e}")
                health_status["metrics"]["graph_stats"] = {"error": str(e)}

        # 4. 检查数据同步状态（通过 Redis）
        try:
            redis_client = cache_service.redis
            if redis_client:
                # 检查同步队列长度
                sync_queue_length = await redis_client.llen("queue:graph_sync")
                health_status["metrics"]["sync_queue_length"] = sync_queue_length

                if sync_queue_length > 1000:
                    health_status["alerts"].append({
                        "severity": "warning",
                        "message": f"High sync queue length: {sync_queue_length}"
                    })
                    health_status["status"] = "degraded"

        except Exception as e:
            logger.warning(f"Failed to check sync queue: {e}")

        # 5. 性能测试（可选，快速模式）
        if health_status["status"] == "healthy":
            try:
                # 执行一个快速查询测试
                start = time.time()
                test_result = await graph_ks.graph_rag_search(
                    query="test",
                    user_id=None,
                    depth=1,
                    top_k=1
                )
                duration = time.time() - start

                health_status["metrics"]["performance_test"] = {
                    "duration_ms": round(duration * 1000, 2),
                    "status": "ok" if duration < 2.0 else "slow"
                }

                if duration > 2.0:
                    health_status["alerts"].append({
                        "severity": "info",
                        "message": f"Query performance is slow: {duration:.2f}s"
                    })

            except Exception as e:
                logger.warning(f"Performance test failed: {e}")

    except Exception as e:
        logger.error(f"GraphRAG health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["alerts"].append({
            "severity": "critical",
            "message": f"Health check failed: {str(e)}"
        })

        if PROMETHEUS_AVAILABLE:
            GRAPH_DB_CONNECTION.set(0)

    return health_status


@router.get("/statistics", response_model=Dict[str, Any])
async def graph_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取 GraphRAG 系统详细统计信息

    返回:
    - 节点数量和类型分布
    - 关系数量和类型分布
    - 用户数据分布
    - 同步状态
    """
    try:
        graph_ks = _require_graph_service(db)

        with GRAPH_RAG_DURATION.labels(operation="statistics").time():
            stats = await graph_ks.get_detailed_statistics()

        # 记录请求成功
        if PROMETHEUS_AVAILABLE:
            GRAPH_RAG_REQUESTS.labels(status="success", query_type="statistics").inc()

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")

        if PROMETHEUS_AVAILABLE:
            GRAPH_RAG_REQUESTS.labels(status="error", query_type="statistics").inc()

        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "message": "Failed to retrieve statistics"}
        )


@router.post("/sync/trigger", response_model=Dict[str, Any])
async def trigger_sync(
    db: AsyncSession = Depends(get_db),
    full_sync: bool = False
) -> Dict[str, Any]:
    """
    手动触发数据同步

    Args:
        full_sync: 是否执行全量同步（默认为增量同步）

    Returns:
        同步任务信息
    """
    try:
        redis_client = cache_service.redis
        if not redis_client:
            raise HTTPException(
                status_code=503,
                detail="Redis not available for sync operations"
            )

        # 发送同步事件到 Redis Stream
        sync_event = {
            "type": "graph_sync",
            "mode": "full" if full_sync else "incremental",
            "timestamp": int(time.time()),
            "triggered_by": "api"
        }

        await redis_client.xadd(
            "stream:graph_sync",
            sync_event,
            maxlen=1000
        )

        # 记录指标
        if PROMETHEUS_AVAILABLE:
            GRAPH_RAG_REQUESTS.labels(status="success", query_type="sync_trigger").inc()

        return {
            "status": "queued",
            "mode": "full" if full_sync else "incremental",
            "event": sync_event,
            "message": "Sync event queued successfully"
        }

    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")

        if PROMETHEUS_AVAILABLE:
            GRAPH_RAG_REQUESTS.labels(status="error", query_type="sync_trigger").inc()

        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "message": "Failed to trigger sync"}
        )


@router.get("/sync/status", response_model=Dict[str, Any])
async def sync_status() -> Dict[str, Any]:
    """
    获取同步队列状态

    Returns:
        当前同步任务状态
    """
    try:
        redis_client = cache_service.redis
        if not redis_client:
            return {
                "status": "disabled",
                "message": "Redis not available"
            }

        # 检查同步队列
        sync_queue_length = await redis_client.llen("queue:graph_sync")
        stream_length = await redis_client.xlen("stream:graph_sync")

        # 检查最近的同步事件
        recent_events = []
        try:
            events = await redis_client.xrevrange(
                "stream:graph_sync",
                count=5
            )
            for event_id, event_data in events:
                recent_events.append({
                    "id": event_id,
                    "timestamp": event_data.get(b"timestamp", b"0").decode(),
                    "mode": event_data.get(b"mode", b"unknown").decode(),
                    "status": event_data.get(b"status", b"pending").decode()
                })
        except Exception:
            pass

        return {
            "status": "active" if (sync_queue_length + stream_length) > 0 else "idle",
            "queue_length": sync_queue_length,
            "stream_length": stream_length,
            "recent_events": recent_events,
            "alerts": []
            if sync_queue_length < 100
            else ["High sync queue volume"]
        }

    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/query/test", response_model=Dict[str, Any])
async def test_query(
    db: AsyncSession = Depends(get_db),
    query: str = "test query",
    depth: int = 2,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    执行测试查询以验证 GraphRAG 功能

    Args:
        query: 测试查询文本
        depth: 图遍历深度
        top_k: 返回结果数量

    Returns:
        查询结果和性能指标
    """
    start_time = time.time()

    try:
        graph_ks = _require_graph_service(db)

        result = await graph_ks.graph_rag_search(
            query=query,
            user_id=None,  # 测试查询不关联用户
            depth=depth,
            top_k=top_k
        )

        duration = time.time() - start_time

        if PROMETHEUS_AVAILABLE:
            GRAPH_RAG_REQUESTS.labels(status="success", query_type="test").inc()
            GRAPH_RAG_DURATION.labels(operation="query").observe(duration)

        return {
            "status": "success",
            "query": query,
            "duration_ms": round(duration * 1000, 2),
            "result": result,
            "performance": {
                "duration_ms": round(duration * 1000, 2),
                "rating": "excellent" if duration < 0.5 else "good" if duration < 1.0 else "acceptable" if duration < 2.0 else "slow"
            }
        }

    except Exception as e:
        duration = time.time() - start_time

        if PROMETHEUS_AVAILABLE:
            GRAPH_RAG_REQUESTS.labels(status="error", query_type="test").inc()
            GRAPH_RAG_DURATION.labels(operation="query").observe(duration)

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "duration_ms": round(duration * 1000, 2),
                "message": "Test query failed"
            }
        )


@router.get("/prometheus/metrics")
async def prometheus_metrics():
    """
    Prometheus 格式的 GraphRAG 专用指标

    Returns:
        Prometheus 格式的指标数据
    """
    if not PROMETHEUS_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Prometheus not available"
        )

    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )


@router.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    详细的 GraphRAG 健康检查（包含所有组件）

    这是最高级别的健康检查，用于生产环境监控
    """
    start_time = time.time()

    health_report = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_ms": 0,
        "components": {},
        "metrics": {},
        "alerts": [],
        "recommendations": []
    }

    try:
        graph_ks = _require_graph_service(db)

        # 1. 图数据库健康
        graph_start = time.time()
        graph_connected = await graph_ks.check_graph_connection()
        graph_duration = time.time() - graph_start

        health_report["components"]["graph_db"] = {
            "status": "connected" if graph_connected else "disconnected",
            "latency_ms": round(graph_duration * 1000, 2),
            "type": "Apache AGE"
        }

        if not graph_connected:
            health_report["status"] = "unhealthy"
            health_report["alerts"].append({
                "severity": "critical",
                "component": "graph_db",
                "message": "Cannot connect to graph database"
            })
            health_report["recommendations"].append(
                "Check Apache AGE installation and PostgreSQL extensions"
            )

        # 2. 向量数据库健康
        try:
            vector_start = time.time()
            vector_connected = await graph_ks.check_vector_connection()
            vector_duration = time.time() - vector_start

            health_report["components"]["vector_db"] = {
                "status": "connected" if vector_connected else "disconnected",
                "latency_ms": round(vector_duration * 1000, 2),
                "type": "pgvector"
            }

            if not vector_connected:
                if health_report["status"] == "healthy":
                    health_report["status"] = "degraded"
                health_report["alerts"].append({
                    "severity": "warning",
                    "component": "vector_db",
                    "message": "Vector database connection issue"
                })
        except Exception as e:
            health_report["components"]["vector_db"] = {
                "status": "error",
                "error": str(e)
            }
            health_report["status"] = "degraded"

        # 3. 数据完整性检查
        if graph_connected:
            try:
                stats = await graph_ks.get_graph_statistics()
                health_report["metrics"]["data_integrity"] = {
                    "total_nodes": stats.get("total_nodes", 0),
                    "total_relations": stats.get("total_relations", 0),
                    "node_types": stats.get("node_types", {}),
                    "relation_types": stats.get("relation_types", {})
                }

                # 数据完整性告警
                if stats.get("total_nodes", 0) == 0:
                    health_report["alerts"].append({
                        "severity": "info",
                        "component": "data",
                        "message": "No nodes in graph database"
                    })
                    health_report["recommendations"].append(
                        "Run data migration or wait for initial sync"
                    )

                if stats.get("total_relations", 0) == 0 and stats.get("total_nodes", 0) > 0:
                    health_report["alerts"].append({
                        "severity": "warning",
                        "component": "data",
                        "message": "Nodes exist but no relations"
                    })

            except Exception as e:
                health_report["metrics"]["data_integrity"] = {"error": str(e)}
                health_report["alerts"].append({
                    "severity": "warning",
                    "component": "data",
                    "message": f"Cannot verify data integrity: {str(e)}"
                })

        # 4. Redis 连接检查（用于同步）
        try:
            redis_client = cache_service.redis
            if redis_client:
                redis_start = time.time()
                await redis_client.ping()
                redis_duration = time.time() - redis_start

                health_report["components"]["redis"] = {
                    "status": "connected",
                    "latency_ms": round(redis_duration * 1000, 2)
                }

                # 检查同步队列
                sync_queue = await redis_client.llen("queue:graph_sync")
                health_report["metrics"]["sync_queue"] = sync_queue

                if sync_queue > 500:
                    health_report["alerts"].append({
                        "severity": "warning",
                        "component": "sync",
                        "message": f"High sync queue: {sync_queue} items"
                    })
                    health_report["recommendations"].append(
                        "Consider scaling up sync workers"
                    )
            else:
                health_report["components"]["redis"] = {
                    "status": "disabled",
                    "note": "Redis not configured"
                }
        except Exception as e:
            health_report["components"]["redis"] = {
                "status": "error",
                "error": str(e)
            }
            if health_report["status"] == "healthy":
                health_report["status"] = "degraded"

        # 5. 性能基准测试
        if health_report["status"] in ["healthy", "degraded"]:
            try:
                test_queries = [
                    ("simple", "test", 1, 1),
                    ("moderate", "knowledge graph query", 2, 3),
                ]

                performance_results = {}

                for name, q, d, k in test_queries:
                    test_start = time.time()
                    await graph_ks.graph_rag_search(query=q, user_id=None, depth=d, top_k=k)
                    duration = time.time() - test_start

                    performance_results[name] = {
                        "duration_ms": round(duration * 1000, 2),
                        "status": "ok" if duration < 1.0 else "slow" if duration < 2.0 else "critical"
                    }

                    if duration > 2.0:
                        health_report["alerts"].append({
                            "severity": "warning",
                            "component": "performance",
                            "message": f"Slow query performance ({name}): {duration:.2f}s"
                        })

                health_report["metrics"]["performance"] = performance_results

            except Exception as e:
                health_report["metrics"]["performance"] = {"error": str(e)}

        # 6. 整体健康评分
        health_report["metrics"]["health_score"] = calculate_health_score(health_report)

        # 7. 生成总结
        health_report["summary"] = generate_health_summary(health_report)

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        health_report["status"] = "unhealthy"
        health_report["alerts"].append({
            "severity": "critical",
            "message": f"Health check system failure: {str(e)}"
        })

    finally:
        health_report["uptime_ms"] = round((time.time() - start_time) * 1000, 2)

    return health_report


def calculate_health_score(health_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    计算健康评分 (0-100)
    """
    score = 100
    deductions = []

    # 组件健康扣分
    for component, info in health_report.get("components", {}).items():
        if info.get("status") == "disconnected":
            score -= 20
            deductions.append(f"{component}: disconnected")
        elif info.get("status") == "error":
            score -= 30
            deductions.append(f"{component}: error")
        elif info.get("status") == "disabled":
            score -= 5
            deductions.append(f"{component}: disabled")

        # 延迟扣分
        latency = info.get("latency_ms", 0)
        if latency > 1000:
            score -= 10
            deductions.append(f"{component}: high latency ({latency}ms)")
        elif latency > 500:
            score -= 5

    # 告警扣分
    for alert in health_report.get("alerts", []):
        if alert.get("severity") == "critical":
            score -= 15
        elif alert.get("severity") == "warning":
            score -= 5

    # 数据完整性扣分
    metrics = health_report.get("metrics", {})
    data_integrity = metrics.get("data_integrity", {})
    if isinstance(data_integrity, dict):
        if data_integrity.get("total_nodes", 0) == 0:
            score -= 10

    # 性能扣分
    performance = metrics.get("performance", {})
    if isinstance(performance, dict):
        for test_name, result in performance.items():
            if isinstance(result, dict) and result.get("status") == "critical":
                score -= 10
            elif isinstance(result, dict) and result.get("status") == "slow":
                score -= 5

    score = max(0, min(100, score))

    rating = "excellent" if score >= 90 else "good" if score >= 70 else "fair" if score >= 50 else "poor"

    return {
        "score": score,
        "rating": rating,
        "deductions": deductions
    }


def generate_health_summary(health_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成健康状态摘要
    """
    status = health_report["status"]
    alerts = health_report.get("alerts", [])
    recommendations = health_report.get("recommendations", [])

    if status == "healthy":
        message = "All systems operational"
        if not alerts:
            action = "No action required"
        else:
            action = f"{len(alerts)} informational alerts present"
    elif status == "degraded":
        message = f"{len(alerts)} issues detected, system partially operational"
        action = "Review alerts and consider recommendations"
    else:
        message = f"Critical issues detected ({len(alerts)} alerts)"
        action = "Immediate action required - check alerts and recommendations"

    return {
        "message": message,
        "action_required": action,
        "alert_count": len(alerts),
        "recommendation_count": len(recommendations)
    }
