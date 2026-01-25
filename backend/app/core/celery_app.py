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
        # P1: Knowledge Galaxy auto-update tasks
        "update_knowledge_galaxy": {"queue": "default"},
        "sync_plan_progress_to_galaxy": {"queue": "low_priority"},
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


@celery_app.task(bind=True, max_retries=3, name="generate_capsules_batch")
def generate_capsules_batch(
    self,
    user_id: str,
    depth_preference: float = 0.5,
    curiosity_preference: float = 0.5,
    generation_type: str = "daily",
    requested_count: int = 1,
):
    """
    异步批量生成胶囊 (Celery 任务)

    Args:
        user_id: 用户ID
        depth_preference: 深度偏好 (0.0-1.0)
        curiosity_preference: 好奇心偏好 (0.0-1.0)
        generation_type: 生成类型 (daily/weekly/manual/push_triggered)
        requested_count: 请求生成的数量

    Returns:
        dict: 生成结果 {
            "job_id": str,
            "status": str,
            "capsule_count": int,
            "capsule_ids": list[str],
        }
    """
    import asyncio
    from uuid import UUID
    from app.db.session import AsyncSessionLocal
    from app.services.capsule_generation_service import capsule_generation_service
    from app.services.notification_service import NotificationService
    from loguru import logger

    async def _generate():
        async with AsyncSessionLocal() as session:
            try:
                # 调用生成服务
                job = await capsule_generation_service.generate_capsules_batch(
                    user_id=UUID(user_id),
                    db=session,
                    depth_preference=depth_preference,
                    curiosity_preference=curiosity_preference,
                    generation_type=generation_type,
                    requested_count=requested_count,
                )

                result = {
                    "job_id": str(job.id),
                    "status": job.status,
                    "capsule_count": job.actual_count or 0,
                    "capsule_ids": [str(cid) for cid in (job.capsule_ids or [])],
                }

                # 如果生成成功，发送通知
                if job.status == "completed" and result["capsule_count"] > 0:
                    notification_service = NotificationService(session)
                    await notification_service.create_system_notification(
                        user_id=user_id,
                        message=f"✨ 为你生成了 {result['capsule_count']} 个好奇心胶囊！",
                        notification_type="capsule",
                        metadata={
                            "job_id": str(job.id),
                            "capsule_count": result["capsule_count"],
                        },
                    )
                    logger.info(f"✅ Celery: Sent notification for capsule job {job.id}")

                logger.info(f"✅ Celery: Generated {result['capsule_count']} capsules for user {user_id}")
                return result

            except Exception as e:
                logger.error(f"❌ Celery: Failed to generate capsules for {user_id}: {e}")
                raise

    try:
        return asyncio.run(_generate())
    except Exception as exc:
        logger.error(f"Capsule generation task failed: {exc}")
        # 指数退避重试
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=3, name="update_knowledge_galaxy")
def update_knowledge_galaxy(
    self,
    user_id: str,
    plan_id: str,
    trigger_type: str = "plan_complete",
    milestone_data: Optional[dict] = None,
):
    """
    P1: 知识星图自动更新 (Celery 任务)

    当计划完成或里程碑达成时触发，更新用户的知识星图：
    - 创建新的知识节点
    - 建立节点间关联
    - 更新节点掌握度
    - 生成新的 embeddings

    Args:
        user_id: 用户ID
        plan_id: 计划ID
        trigger_type: 触发类型 (plan_complete/milestone_reached/task_complete)
        milestone_data: 里程碑数据 (可选)

    Returns:
        dict: 更新结果 {
            "status": str,
            "nodes_created": int,
            "links_created": int,
            "nodes_updated": int,
        }
    """
    import asyncio
    from uuid import UUID
    from app.db.session import AsyncSessionLocal
    from loguru import logger

    async def _update_galaxy():
        async with AsyncSessionLocal() as session:
            try:
                from app.services.knowledge_service import KnowledgeService
                from app.services.plan_service import PlanService

                knowledge_service = KnowledgeService(session)
                plan_service = PlanService(session)

                user_uuid = UUID(user_id)
                plan_uuid = UUID(plan_id)

                # Get plan details
                plan = await plan_service.get(plan_uuid)
                if not plan:
                    logger.warning(f"Plan {plan_id} not found, skipping galaxy update")
                    return {"status": "skipped", "reason": "plan_not_found"}

                result = {
                    "status": "success",
                    "trigger_type": trigger_type,
                    "nodes_created": 0,
                    "links_created": 0,
                    "nodes_updated": 0,
                }

                # Extract knowledge concepts from plan
                concepts = await _extract_plan_concepts(plan, milestone_data)

                # Create or update knowledge nodes
                for concept in concepts:
                    try:
                        # Check if node exists
                        existing_node = await knowledge_service.find_node_by_name(
                            user_uuid, concept["name"]
                        )

                        if existing_node:
                            # Update mastery level
                            await knowledge_service.update_node_mastery(
                                existing_node.id,
                                mastery_delta=concept.get("mastery_delta", 0.1),
                            )
                            result["nodes_updated"] += 1
                        else:
                            # Create new node
                            new_node = await knowledge_service.create_node(
                                user_id=user_uuid,
                                name=concept["name"],
                                subject=plan.subject,
                                description=concept.get("description", ""),
                                tags=concept.get("tags", []),
                            )
                            result["nodes_created"] += 1

                            # Schedule embedding generation
                            celery_app.send_task(
                                "generate_embedding",
                                args=(str(new_node.id), f"{concept['name']} {concept.get('description', '')}"),
                                kwargs={"user_id": user_id},
                                queue="high_priority",
                            )

                    except Exception as e:
                        logger.warning(f"Failed to process concept {concept['name']}: {e}")

                # Create links between related concepts
                if len(concepts) > 1:
                    for i, concept in enumerate(concepts[:-1]):
                        try:
                            link_created = await knowledge_service.create_or_update_link(
                                user_id=user_uuid,
                                source_name=concept["name"],
                                target_name=concepts[i + 1]["name"],
                                relation_type="sequential",
                                strength=0.5,
                            )
                            if link_created:
                                result["links_created"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to create link: {e}")

                # Link to plan's subject node
                if plan.subject:
                    try:
                        for concept in concepts:
                            await knowledge_service.create_or_update_link(
                                user_id=user_uuid,
                                source_name=plan.subject,
                                target_name=concept["name"],
                                relation_type="contains",
                                strength=0.7,
                            )
                            result["links_created"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to create subject link: {e}")

                await session.commit()

                logger.info(
                    f"✅ Celery: Galaxy updated for plan {plan_id}: "
                    f"{result['nodes_created']} created, "
                    f"{result['nodes_updated']} updated, "
                    f"{result['links_created']} links"
                )

                return result

            except Exception as e:
                logger.error(f"❌ Celery: Failed to update galaxy for plan {plan_id}: {e}")
                raise

    async def _extract_plan_concepts(plan, milestone_data: Optional[dict]) -> List[dict]:
        """Extract knowledge concepts from plan and milestone data"""
        concepts = []

        # Extract from plan name and description
        if plan.name:
            concepts.append({
                "name": plan.name,
                "description": plan.description or "",
                "mastery_delta": 0.2 if milestone_data else 0.1,
                "tags": [plan.subject] if plan.subject else [],
            })

        # Extract from milestone data if available
        if milestone_data:
            milestone_name = milestone_data.get("name", "")
            if milestone_name:
                concepts.append({
                    "name": milestone_name,
                    "description": milestone_data.get("description", ""),
                    "mastery_delta": 0.15,
                    "tags": milestone_data.get("tags", []),
                })

            # Extract learning outcomes
            for outcome in milestone_data.get("learning_outcomes", []):
                if isinstance(outcome, str):
                    concepts.append({
                        "name": outcome,
                        "mastery_delta": 0.1,
                    })
                elif isinstance(outcome, dict):
                    concepts.append({
                        "name": outcome.get("name", ""),
                        "description": outcome.get("description", ""),
                        "mastery_delta": outcome.get("mastery_delta", 0.1),
                    })

        return [c for c in concepts if c.get("name")]

    try:
        return asyncio.run(_update_galaxy())
    except Exception as exc:
        logger.error(f"Galaxy update task failed: {exc}")
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=2, name="sync_plan_progress_to_galaxy")
def sync_plan_progress_to_galaxy(self, user_id: str):
    """
    P1: 同步用户所有计划进度到知识星图 (定时任务)

    用于批量同步，确保知识星图与计划状态一致

    Args:
        user_id: 用户ID

    Returns:
        dict: 同步结果统计
    """
    import asyncio
    from uuid import UUID
    from app.db.session import AsyncSessionLocal
    from loguru import logger

    async def _sync():
        async with AsyncSessionLocal() as session:
            try:
                from app.services.plan_service import PlanService

                plan_service = PlanService(session)
                user_uuid = UUID(user_id)

                # Get all active plans
                plans = await plan_service.list_for_user(user_uuid, include_archived=False)

                stats = {
                    "total_plans": len(plans),
                    "synced_plans": 0,
                    "skipped_plans": 0,
                }

                for plan in plans:
                    try:
                        # Check if plan has milestones completed
                        if hasattr(plan, "completed_milestones") and plan.completed_milestones:
                            # Trigger galaxy update for each completed milestone
                            for milestone in plan.completed_milestones:
                                celery_app.send_task(
                                    "update_knowledge_galaxy",
                                    args=(user_id, str(plan.id), "milestone_reached"),
                                    kwargs={"milestone_data": milestone},
                                    queue="default",
                                )
                            stats["synced_plans"] += 1
                        else:
                            stats["skipped_plans"] += 1

                    except Exception as e:
                        logger.warning(f"Failed to sync plan {plan.id}: {e}")
                        stats["skipped_plans"] += 1

                logger.info(f"✅ Celery: Plan progress sync completed for user {user_id}: {stats}")
                return stats

            except Exception as e:
                logger.error(f"❌ Celery: Failed to sync plan progress: {e}")
                raise

    try:
        return asyncio.run(_sync())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="generate_daily_capsules_for_all")
def generate_daily_capsules_for_all(self):
    """
    为所有活跃用户生成每日胶囊 (定时任务)

    仅为好奇心偏好 > 0.3 的用户生成

    Returns:
        dict: 生成统计
    """
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.services.user_service import get_active_users
    from app.services.personalization.preference_service import PreferenceService
    from loguru import logger

    async def _generate():
        async with AsyncSessionLocal() as session:
            try:
                # 获取活跃用户
                users = await get_active_users(session, days=7)
                pref_service = PreferenceService(session)

                stats = {
                    "total_users": len(users),
                    "eligible_users": 0,
                    "generated_jobs": 0,
                    "skipped_users": 0,
                }

                for user in users:
                    try:
                        # 获取用户偏好
                        prefs = await pref_service.get_preferences(user.id)
                        curiosity_pref = (prefs.explicit or {}).get("curiosity_preference", 0.5)

                        # 只为高好奇心偏好的用户生成
                        if curiosity_pref < 0.3:
                            stats["skipped_users"] += 1
                            continue

                        # 调度异步生成任务
                        celery_app.send_task(
                            "generate_capsules_batch",
                            args=(
                                str(user.id),
                                0.5,  # depth_preference - 默认中等
                                curiosity_pref,
                                "daily",
                                1,  # 每日1个
                            ),
                            queue="default",
                        )
                        stats["eligible_users"] += 1
                        stats["generated_jobs"] += 1

                    except Exception as e:
                        logger.warning(f"Failed to schedule capsule for user {user.id}: {e}")
                        stats["skipped_users"] += 1

                logger.info(f"✅ Celery: Scheduled {stats['generated_jobs']} daily capsule jobs")
                return stats

            except Exception as e:
                logger.error(f"❌ Celery: Failed to generate daily capsules: {e}")
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

    # ========== 胶囊生成任务 ==========

    # 每天早上8点生成每日胶囊
    "daily-capsules-generation": {
        "task": "generate_daily_capsules_for_all",
        "schedule": 86400.0,  # 每天
        "args": (),
        "options": {"queue": "default"}
    },

    # 每周日上午9点生成深度胶囊
    "weekly-deep-capsules": {
        "task": "generate_daily_capsules_for_all",
        "schedule": 604800.0,  # 7天
        "args": (),
        "options": {"queue": "default"}
    },

    # ========== P1: 知识星图自动更新 ==========

    # 注意: update_knowledge_galaxy 任务由 PlanService 在计划完成/里程碑达成时触发
    # 此处仅包含定期同步任务，不包含事件触发任务
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
