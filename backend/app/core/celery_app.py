"""
Sparkle Celery 应用配置

提供分布式任务队列,用于处理长时任务:
- Embedding 生成
- 批量错题分析
- 数据清理
- 定时任务

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import os
from celery import Celery
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Celery 配置
# =============================================================================

# 从环境变量读取配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Celery 应用实例
celery_app = Celery(
    "sparkle",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.core.celery_tasks",
        "workers.signals_learning_worker",
    ]
)

# 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务配置
    task_track_started=True,
    task_send_sent_event=True,

    # 重试配置
    task_reject_on_worker_lost=True,
    task_acks_late=True,

    # 队列配置
    task_queues={
        "high_priority": {
            "exchange": "sparkle",
            "routing_key": "high",
            "priority": 0,
        },
        "default": {
            "exchange": "sparkle",
            "routing_key": "default",
            "priority": 5,
        },
        "low_priority": {
            "exchange": "sparkle",
            "routing_key": "low",
            "priority": 10,
        },
    },

    # 默认路由
    task_routes={
        "app.core.celery_tasks.generate_embedding": {"queue": "high_priority"},
        "app.core.celery_tasks.batch_error_analysis": {"queue": "default"},
        "app.core.celery_tasks.cleanup_old_data": {"queue": "low_priority"},
    },

    # 监控
    worker_send_task_events=True,

    # 结果过期时间 (24小时)
    result_expires=86400,

    # 日志级别
    worker_log_level="INFO",
)

# Ensure tasks are registered when importing celery_app.
from app.core import celery_tasks  # noqa: F401

# =============================================================================
# 任务定义
# =============================================================================

@celery_app.task(bind=True, max_retries=3, name="generate_embedding")
def generate_embedding(self, node_id: str, text: str, user_id: Optional[str] = None):
    """
    生成节点 Embedding (长时任务)

    Args:
        node_id: 节点ID
        text: 要生成embedding的文本
        user_id: 用户ID (用于追踪)

    Returns:
        dict: 包含embedding和状态
    """
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.services.embedding_service import embedding_service
    from app.models.galaxy import KnowledgeNode
    from loguru import logger

    async def _generate():
        async with AsyncSessionLocal() as session:
            try:
                # 生成 embedding
                embedding = await embedding_service.get_embedding(text)

                # 更新节点
                node = await session.get(KnowledgeNode, node_id)
                if node:
                    node.embedding = embedding
                    session.add(node)
                    await session.commit()

                    logger.info(f"✅ Celery: Generated embedding for node {node_id}")
                    return {
                        "status": "success",
                        "node_id": node_id,
                        "embedding_length": len(embedding)
                    }
                else:
                    raise ValueError(f"Node {node_id} not found")

            except Exception as e:
                logger.error(f"❌ Celery: Failed to generate embedding for {node_id}: {e}")
                raise

    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Task failed, attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="batch_error_analysis")
def batch_error_analysis(self, error_ids: List[str], user_id: str):
    """
    批量错题分析

    Args:
        error_ids: 错题ID列表
        user_id: 用户ID

    Returns:
        dict: 分析结果统计
    """
    import asyncio
    from uuid import UUID
    from app.db.session import AsyncSessionLocal
    from app.services.error_book_service import ErrorBookService
    from loguru import logger

    async def _analyze():
        async with AsyncSessionLocal() as session:
            service = ErrorBookService(session)
            results = []

            for error_id in error_ids:
                try:
                    error_uuid = UUID(error_id)
                    await service.analyze_and_link(error_uuid, UUID(user_id))
                    results.append({"error_id": error_id, "status": "success"})
                    logger.info(f"✅ Celery: Analyzed error {error_id}")
                except Exception as e:
                    results.append({"error_id": error_id, "status": "failed", "error": str(e)})
                    logger.error(f"❌ Celery: Failed to analyze error {error_id}: {e}")

            return {
                "total": len(error_ids),
                "success": sum(1 for r in results if r["status"] == "success"),
                "failed": sum(1 for r in results if r["status"] == "failed"),
                "results": results
            }

    try:
        return asyncio.run(_analyze())
    except Exception as exc:
        logger.error(f"Batch analysis failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="cleanup_old_data")
def cleanup_old_data(self, days_to_keep: int = 30):
    """
    清理旧数据 (定时任务)

    Args:
        days_to_keep: 保留天数

    Returns:
        dict: 清理统计
    """
    import asyncio
    from datetime import datetime, timedelta
    from app.db.session import AsyncSessionLocal
    from app.models.idempotency_key import IdempotencyKey
    from loguru import logger

    async def _cleanup():
        async with AsyncSessionLocal() as session:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # 清理过期幂等键
            result = await session.execute(
                IdempotencyKey.__table__.delete().where(
                    IdempotencyKey.created_at < cutoff_date
                )
            )
            deleted = result.rowcount

            await session.commit()

            logger.info(f"✅ Celery: Cleaned up {deleted} old records")
            return {
                "status": "success",
                "deleted_records": deleted,
                "cutoff_date": cutoff_date.isoformat()
            }

    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="notify_user")
def notify_user(self, user_id: str, message: str, notification_type: str = "system"):
    """
    发送用户通知 (异步通知)

    Args:
        user_id: 用户ID
        message: 消息内容
        notification_type: 通知类型
    """
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.services.notification_service import NotificationService
    from loguru import logger

    async def _notify():
        async with AsyncSessionLocal() as session:
            service = NotificationService(session)
            try:
                await service.create_system_notification(
                    user_id=user_id,
                    message=message,
                    notification_type=notification_type
                )
                logger.info(f"✅ Celery: Notification sent to {user_id}")
                return {"status": "success", "user_id": user_id}
            except Exception as e:
                logger.error(f"❌ Celery: Failed to notify {user_id}: {e}")
                raise

    try:
        return asyncio.run(_notify())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, name="daily_report")
def daily_report(self):
    """
    生成每日报告 (定时任务)

    Returns:
        dict: 报告摘要
    """
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.services.dashboard_service import DashboardService
    from loguru import logger

    async def _generate():
        async with AsyncSessionLocal() as session:
            service = DashboardService(session)
            try:
                # 生成报告
                report = await service.generate_daily_report()
                logger.info("✅ Celery: Daily report generated")
                return report
            except Exception as e:
                logger.error(f"❌ Celery: Failed to generate daily report: {e}")
                raise

    try:
        return asyncio.run(_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


# =============================================================================
# 周期任务 (Beat Schedule)
# =============================================================================

celery_app.conf.beat_schedule = {
    # 每天凌晨2点清理旧数据
    "cleanup-every-day": {
        "task": "cleanup_old_data",
        "schedule": 86400.0,  # 24小时
        "args": (30,),  # 保留30天
        "options": {"queue": "low_priority"}
    },

    # 每天早上8点生成日报
    "daily-report": {
        "task": "daily_report",
        "schedule": 86400.0,
        "args": (),
        "options": {"queue": "default"}
    },

    # 每小时检查一次系统健康
    "health-check": {
        "task": "app.core.celery_tasks.health_check_task",
        "schedule": 3600.0,
        "options": {"queue": "low_priority"}
    },

    # 每天凌晨3点运行信号学习分析
    "signals-learning-daily": {
        "task": "signals_learning_daily",
        "schedule": 86400.0,  # 24小时
        "args": (),
        "options": {"queue": "default"}
    },
}


# =============================================================================
# 工具函数
# =============================================================================

def get_celery_status():
    """获取 Celery 状态"""
    try:
        # 检查 Broker 连接
        celery_app.broker_connection().ensure_connection(max_retries=1)

        # 获取活动 worker
        inspect = celery_app.control.inspect()
        active_workers = inspect.active() or {}

        return {
            "status": "healthy",
            "broker": "connected",
            "active_workers": len(active_workers),
            "scheduled_tasks": len(celery_app.conf.beat_schedule),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "broker": "disconnected",
            "error": str(e)
        }


def schedule_long_task(task_name: str, args: tuple = (), kwargs: dict = None, queue: str = "default"):
    """
    调度长时任务

    Args:
        task_name: 任务名称
        args: 任务参数
        kwargs: 任务关键字参数
        queue: 队列名称

    Returns:
        task_id: 任务ID
    """
    if kwargs is None:
        kwargs = {}

    try:
        task = celery_app.send_task(
            task_name,
            args=args,
            kwargs=kwargs,
            queue=queue
        )
    except Exception as exc:
        raise RuntimeError(f"Broker connection error: {exc}") from exc

    logger.info(f"📅 Scheduled task: {task_name} (ID: {task.id}, Queue: {queue})")
    return task.id


def get_task_result(task_id: str, timeout: float = 10.0):
    """
    获取任务结果

    Args:
        task_id: 任务ID
        timeout: 等待超时(秒)

    Returns:
        dict: 任务结果
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        return {
            "status": result.status,
            "result": result.result,
            "ready": True
        }
    else:
        return {
            "status": result.status,
            "result": None,
            "ready": False
        }


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    print("Celery 配置示例")
    print("=" * 60)

    # 检查配置
    status = get_celery_status()
    print(f"状态: {status}")

    # 示例: 调度任务
    print("\n示例任务调度:")
    print("  1. generate_embedding('node_123', '学习内容标题\\n详细摘要')")
    print("  2. batch_error_analysis(['error_1', 'error_2'], 'user_123')")
    print("  3. cleanup_old_data(30)")
    print("  4. notify_user('user_123', '您的分析已完成')")

    # 查看周期任务
    print("\n周期任务:")
    for name, config in celery_app.conf.beat_schedule.items():
        print(f"  - {name}: {config['task']} (每 {config['schedule']}秒)")
