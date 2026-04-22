"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

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

import logging
import os
import asyncio

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)
_worker_event_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro):
    global _worker_event_loop
    if _worker_event_loop is None or _worker_event_loop.is_closed():
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)
    return _worker_event_loop.run_until_complete(coro)


# =============================================================================
# Celery 配置
# =============================================================================

# 从环境变量读取配置
REDIS_URL = str(settings.REDIS_URL or os.getenv("REDIS_URL") or "redis://localhost:6379/1")
CELERY_BROKER_URL = str(os.getenv("CELERY_BROKER_URL") or REDIS_URL)
CELERY_RESULT_BACKEND = str(os.getenv("CELERY_RESULT_BACKEND") or REDIS_URL)

# Celery 应用实例
celery_app = Celery(
    "sparkle",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.core.celery_tasks",
        "app.tasks.accountability_tasks",
        "app.tasks.policy_tasks",
        "workers.signals_learning_worker",
    ],
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
    task_ignore_result=False,
    # 重试配置
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    # 任务名称配置（支持短名称和完整路径）
    task_create_missing_queues=True,
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
        "glm_batch": {
            "exchange": "sparkle",
            "routing_key": "glm_batch",
            "priority": 7,
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
        "app.core.celery_tasks.health_check_task": {"queue": "high_priority"},
        "generate_capsules_batch": {"queue": "glm_batch"},
        "analyze_cognitive_fragment_batch": {"queue": "glm_batch"},
        "classify_node_sector_batch": {"queue": "glm_batch"},
        "daily_report": {"queue": "default"},
        "send_task_reminders": {"queue": "default"},
        "generate_daily_capsules_for_all": {"queue": "default"},
        "app.core.celery_tasks.check_prediction_accuracy": {"queue": "low_priority"},
        "app.core.celery_tasks.cleanup_stale_simulation_sessions": {"queue": "low_priority"},
        "app.core.celery_tasks.persist_simulation_run": {"queue": "low_priority"},
        "app.core.celery_tasks.persist_report_snapshot": {"queue": "low_priority"},
        "app.core.celery_tasks.recompute_idiographic_associations": {"queue": "low_priority"},
        "app.core.celery_tasks.run_push_policy_scheduler": {"queue": "default"},
        # P1: Knowledge Galaxy auto-update tasks
        "update_knowledge_galaxy": {"queue": "default"},
        "sync_plan_progress_to_galaxy": {"queue": "low_priority"},
        # Accountability tasks
        "tasks.accountability.send_daily_reminders": {"queue": "default"},
        "tasks.accountability.check_partner_progress": {"queue": "low_priority"},
        "tasks.accountability.evaluate_achievements": {"queue": "low_priority"},
        "tasks.accountability.send_milestone_notification": {"queue": "default"},
        "tasks.accountability.notify_partner_checkin": {"queue": "default"},
        "tasks.policy.process_due_policies": {"queue": "default"},
        "verify_intervention_outcomes_engaged": {"queue": "low_priority"},
        "verify_intervention_outcomes_full": {"queue": "low_priority"},
        "app.core.celery_tasks.generate_weekly_growth_digests": {"queue": "default"},
        "app.core.celery_tasks.deliver_weekly_growth_digests": {"queue": "default"},
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
def generate_embedding(self, node_id: str, text: str, user_id: str | None = None):
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

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.models.galaxy import KnowledgeNode
    from app.services.embedding_service import embedding_service

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
                    return {"status": "success", "node_id": node_id, "embedding_length": len(embedding)}
                else:
                    raise ValueError(f"Node {node_id} not found")

            except Exception as e:
                logger.error(f"❌ Celery: Failed to generate embedding for {node_id}: {e}")
                raise

    try:
        return _run_async(_generate())
    except Exception as exc:
        logger.error(f"Task failed, attempt {self.request.retries + 1}: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="batch_error_analysis")
def batch_error_analysis(self, error_ids: list[str], user_id: str):
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

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.services.error_book_service import ErrorBookService

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
                "results": results,
            }

    try:
        return _run_async(_analyze())
    except Exception as exc:
        logger.error(f"Batch analysis failed: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.models.idempotency_key import IdempotencyKey

    async def _cleanup():
        async with AsyncSessionLocal() as session:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # 清理过期幂等键
            result = await session.execute(
                IdempotencyKey.__table__.delete().where(IdempotencyKey.created_at < cutoff_date)
            )
            deleted = result.rowcount

            await session.commit()

            logger.info(f"✅ Celery: Cleaned up {deleted} old records")
            return {"status": "success", "deleted_records": deleted, "cutoff_date": cutoff_date.isoformat()}

    try:
        return _run_async(_cleanup())
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

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async def _notify():
        async with AsyncSessionLocal() as session:
            service = NotificationService(session)
            try:
                await service.create_system_notification(
                    user_id=user_id, message=message, notification_type=notification_type
                )
                logger.info(f"✅ Celery: Notification sent to {user_id}")
                return {"status": "success", "user_id": user_id}
            except Exception as e:
                logger.error(f"❌ Celery: Failed to notify {user_id}: {e}")
                raise

    try:
        return _run_async(_notify())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, name="daily_report")
def daily_report(self):
    """
    生成每日报告 (定时任务)

    Returns:
        dict: 报告摘要
    """
    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.services.dashboard_service import DashboardService

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
        return _run_async(_generate())
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
    model_key: str | None = None,
    execution_mode: str = "online",
    job_id: str | None = None,
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

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.schemas.notification import NotificationCreate
    from app.services.capsule_generation_service import capsule_generation_service
    from app.services.notification_service import NotificationService

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
                    model_key=model_key,
                    execution_mode=execution_mode,
                    existing_job_id=UUID(job_id) if job_id else None,
                )

                result = {
                    "job_id": str(job.id),
                    "status": job.status,
                    "capsule_count": job.actual_count or 0,
                    "capsule_ids": [str(cid) for cid in (job.capsule_ids or [])],
                }

                # 如果生成成功，发送通知
                if job.status == "completed" and result["capsule_count"] > 0:
                    try:
                        await NotificationService.create(
                            session,
                            UUID(user_id),
                            NotificationCreate(
                                title="新的好奇心胶囊",
                                content=f"✨ 为你生成了 {result['capsule_count']} 个好奇心胶囊！",
                                type="capsule",
                                data={
                                    "job_id": str(job.id),
                                    "capsule_count": result["capsule_count"],
                                },
                            ),
                            push_via_websocket=False,
                        )
                        logger.info(f"✅ Celery: Sent notification for capsule job {job.id}")
                    except Exception as notify_exc:
                        logger.warning(
                            f"Capsule job {job.id} completed, but notification dispatch failed: {notify_exc}"
                        )

                logger.info(f"✅ Celery: Generated {result['capsule_count']} capsules for user {user_id}")
                return result

            except Exception as e:
                logger.error(f"❌ Celery: Failed to generate capsules for {user_id}: {e}")
                raise

    try:
        return _run_async(_generate())
    except Exception as exc:
        logger.error(f"Capsule generation task failed: {exc}")
        # 指数退避重试
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=3, name="analyze_cognitive_fragment_batch")
def analyze_cognitive_fragment_batch(
    self,
    user_id: str,
    fragment_id: str,
    model_key: str | None = None,
):
    """使用 GLM batch 队列分析认知碎片。"""
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.cognitive_service import CognitiveService

    async def _analyze():
        async with AsyncSessionLocal() as session:
            service = CognitiveService(session)
            return await service.analyze_behavior(
                UUID(user_id),
                UUID(fragment_id),
                batch_model_key=model_key,
            )

    try:
        return _run_async(_analyze())
    except Exception as exc:
        logger.error(f"Cognitive batch analysis task failed: {exc}")
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=3, name="classify_node_sector_batch")
def classify_node_sector_batch(
    self,
    user_id: str,
    node_ids: list[str],
    model_key: str | None = None,
):
    """使用 GLM batch 队列为知识节点回填多星域归属。"""
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.node_sector_service import NodeSectorService

    async def _classify():
        async with AsyncSessionLocal() as session:
            service = NodeSectorService(session)
            return await service.classify_nodes_by_ids(
                user_id=UUID(user_id),
                node_ids=[UUID(node_id) for node_id in node_ids],
                model_key=model_key,
            )

    try:
        return _run_async(_classify())
    except Exception as exc:
        logger.error(f"Node sector batch classification failed: {exc}")
        countdown = 60 * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, max_retries=3, name="update_knowledge_galaxy")
def update_knowledge_galaxy(
    self,
    user_id: str,
    plan_id: str,
    trigger_type: str = "plan_complete",
    milestone_data: dict | None = None,
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

    from loguru import logger

    from app.db.session import AsyncSessionLocal

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
                        existing_node = await knowledge_service.find_node_by_name(user_uuid, concept["name"])

                        if existing_node:
                            # Update mastery level
                            await knowledge_service.update_node_mastery(
                                user_id=user_uuid,
                                node_id=existing_node.id,
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

    async def _extract_plan_concepts(plan, milestone_data: dict | None) -> list[dict]:
        """Extract knowledge concepts from plan and milestone data"""
        concepts = []

        # Extract from plan name and description
        if plan.name:
            concepts.append(
                {
                    "name": plan.name,
                    "description": plan.description or "",
                    "mastery_delta": 0.2 if milestone_data else 0.1,
                    "tags": [plan.subject] if plan.subject else [],
                }
            )

        # Extract from milestone data if available
        if milestone_data:
            milestone_name = milestone_data.get("name", "")
            if milestone_name:
                concepts.append(
                    {
                        "name": milestone_name,
                        "description": milestone_data.get("description", ""),
                        "mastery_delta": 0.15,
                        "tags": milestone_data.get("tags", []),
                    }
                )

            # Extract learning outcomes
            for outcome in milestone_data.get("learning_outcomes", []):
                if isinstance(outcome, str):
                    concepts.append(
                        {
                            "name": outcome,
                            "mastery_delta": 0.1,
                        }
                    )
                elif isinstance(outcome, dict):
                    concepts.append(
                        {
                            "name": outcome.get("name", ""),
                            "description": outcome.get("description", ""),
                            "mastery_delta": outcome.get("mastery_delta", 0.1),
                        }
                    )

        return [c for c in concepts if c.get("name")]

    try:
        return _run_async(_update_galaxy())
    except Exception as exc:
        logger.error(f"Galaxy update task failed: {exc}")
        countdown = 30 * (2**self.request.retries)
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

    from loguru import logger

    from app.db.session import AsyncSessionLocal

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
        return _run_async(_sync())
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
    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.services.personalization.preference_service import PreferenceService
    from app.services.user_service import get_active_users

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
        return _run_async(_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(bind=True, max_retries=3, name="verify_intervention_outcomes_engaged")
def verify_intervention_outcomes_engaged(self):
    """Resolve engaged intervention outcomes older than 24 hours."""
    from app.core.event_bus import event_bus
    from app.db.session import AsyncSessionLocal
    from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier

    async def _verify():
        async with AsyncSessionLocal() as session:
            verifier = InterventionOutcomeVerifier(session, event_bus)
            return await verifier.verify_engaged_pending()

    try:
        return _run_async(_verify())
    except Exception as exc:
        logger.error(f"Engaged intervention outcome verification failed: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="verify_intervention_outcomes_full")
def verify_intervention_outcomes_full(self):
    """Run the nightly full pending outcome sweep."""
    from app.core.event_bus import event_bus
    from app.db.session import AsyncSessionLocal
    from app.services.card_protocol.outcome_verifier import InterventionOutcomeVerifier

    async def _verify():
        async with AsyncSessionLocal() as session:
            verifier = InterventionOutcomeVerifier(session, event_bus)
            return await verifier.verify_full_pending()

    try:
        return _run_async(_verify())
    except Exception as exc:
        logger.error(f"Full intervention outcome verification failed: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="sweep_profile_outcome_learning")
def sweep_profile_outcome_learning(self):
    """Rebuild validated profile learning from profile-ledger behavioral evidence."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.intervention_adaptive import BehavioralOutcome
    from app.services.outcome_promotion_governor import OutcomePromotionGovernor

    async def _sweep():
        async with AsyncSessionLocal() as session:
            governor = OutcomePromotionGovernor(session)
            result = await session.execute(select(BehavioralOutcome.user_id).distinct())
            user_ids = [row[0] for row in result.all() if row[0] is not None]
            return await governor.sweep_profile_ledger_learning(user_ids=user_ids)

    try:
        return _run_async(_sweep())
    except Exception as exc:
        logger.error(f"Profile outcome learning sweep failed: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)


# =============================================================================
# 周期任务 (Beat Schedule)
# =============================================================================

celery_app.conf.beat_schedule = {
    # 每天凌晨2点清理旧数据
    "cleanup-every-day": {
        "task": "cleanup_old_data",
        "schedule": 86400.0,  # 24小时
        "args": (30,),  # 保留30天
        "options": {"queue": "low_priority"},
    },
    # 每天早上8点生成日报
    "daily-report": {"task": "daily_report", "schedule": 86400.0, "args": (), "options": {"queue": "default"}},
    # 每小时检查一次系统健康
    "health-check": {
        "task": "app.core.celery_tasks.health_check_task",
        "schedule": 3600.0,
        "options": {"queue": "low_priority"},
    },
    "policy-compiler-due-scan": {
        "task": "tasks.policy.process_due_policies",
        "schedule": 30.0,
        "options": {"queue": "default"},
    },
    "intervention-outcomes-engaged": {
        "task": "verify_intervention_outcomes_engaged",
        "schedule": crontab(minute=0, hour="*/4"),
        "options": {"queue": "low_priority"},
    },
    "intervention-outcomes-full": {
        "task": "verify_intervention_outcomes_full",
        "schedule": crontab(minute=0, hour=2),
        "options": {"queue": "low_priority"},
    },
    "profile-outcome-learning-sweep": {
        "task": "sweep_profile_outcome_learning",
        "schedule": crontab(minute=20, hour="*/6"),
        "options": {"queue": "low_priority"},
    },
    # ========== 胶囊生成任务 ==========
    # 每天早上8点生成每日胶囊
    "daily-capsules-generation": {
        "task": "generate_daily_capsules_for_all",
        "schedule": 86400.0,  # 每天
        "args": (),
        "options": {"queue": "default"},
    },
    # 每周日上午9点生成深度胶囊
    "weekly-deep-capsules": {
        "task": "generate_daily_capsules_for_all",
        "schedule": 604800.0,  # 7天
        "args": (),
        "options": {"queue": "default"},
    },
    # 每周一上午9点生成学习报告
    "weekly-learning-report": {
        "task": "app.core.celery_tasks.generate_weekly_learning_reports",
        "schedule": crontab(day_of_week="mon", hour=9, minute=0),
        "options": {"queue": "default"},
    },
    "push-policy-scheduler": {
        "task": "app.core.celery_tasks.run_push_policy_scheduler",
        "schedule": float(max(settings.AURORA_STAGE38_PUSH_SCHEDULER_INTERVAL_MINUTES, 1) * 60),
        "options": {"queue": "default"},
    },
    "weekly-growth-digest-generation": {
        "task": "app.core.celery_tasks.generate_weekly_growth_digests",
        "schedule": crontab(day_of_week="sun", hour=22, minute=0),
        "args": (200, False),
        "options": {"queue": "default"},
    },
    "weekly-growth-digest-delivery": {
        "task": "app.core.celery_tasks.deliver_weekly_growth_digests",
        "schedule": crontab(day_of_week="mon", hour=8, minute=0),
        "options": {"queue": "default"},
    },
    "theater-prediction-accuracy-daily": {
        "task": "app.core.celery_tasks.check_prediction_accuracy",
        "schedule": crontab(hour=4, minute=10),
        "options": {"queue": "low_priority"},
    },
    "cleanup-stale-simulation-sessions-hourly": {
        "task": "app.core.celery_tasks.cleanup_stale_simulation_sessions",
        "schedule": 3600.0,
        "args": (6,),
        "options": {"queue": "low_priority"},
    },
    "ai-metric-baseline-daily": {
        "task": "app.core.celery_tasks.capture_ai_metric_baseline",
        "schedule": crontab(hour=3, minute=15),
        "options": {"queue": "low_priority"},
    },
    "persdyn-attractor-recompute-daily": {
        "task": "app.core.celery_tasks.recompute_persdyn_attractors",
        "schedule": crontab(hour=0, minute=5),
        "options": {"queue": "low_priority"},
    },
    "metacognition-snapshot-refresh-daily": {
        "task": "app.core.celery_tasks.refresh_metacognition_snapshots",
        "schedule": crontab(hour=4, minute=30),
        "args": (500,),
        "options": {"queue": "low_priority"},
    },
    "idiographic-association-weekly-recompute": {
        "task": "app.core.celery_tasks.recompute_idiographic_associations",
        "schedule": crontab(day_of_week="mon", hour=1, minute=0),
        "options": {"queue": "low_priority"},
    },
    "perceptible-cohort-promotion-biweekly": {
        "task": "app.core.celery_tasks.promote_perceptible_cohort",
        "schedule": crontab(day_of_week="mon", hour=10, minute=0),
        "options": {"queue": "low_priority"},
    },
    # ========== P1: 知识星图自动更新 ==========
    # 注意: update_knowledge_galaxy 任务由 PlanService 在计划完成/里程碑达成时触发
    # 此处仅包含定期同步任务，不包含事件触发任务
    # ========== 责任伙伴系统任务 ==========
    # 每天早上9点发送打卡提醒
    "accountability-daily-reminders-morning": {
        "task": "tasks.accountability.send_daily_reminders",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "default"},
    },
    # 每天晚上9点再次发送提醒
    "accountability-daily-reminders-evening": {
        "task": "tasks.accountability.send_daily_reminders",
        "schedule": crontab(hour=21, minute=0),
        "options": {"queue": "default"},
    },
    # 每天晚上11:59检查进度
    "accountability-progress-check": {
        "task": "tasks.accountability.check_partner_progress",
        "schedule": crontab(hour=23, minute=59),
        "options": {"queue": "low_priority"},
    },
    # 每天晚上11:59评估成就
    "accountability-achievement-evaluation": {
        "task": "tasks.accountability.evaluate_achievements",
        "schedule": crontab(hour=23, minute=59),
        "options": {"queue": "low_priority"},
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
        active_queues = inspect.active_queues() or {}

        return {
            "status": "healthy",
            "broker": "connected",
            "active_workers": len(active_workers),
            "workers": sorted(active_workers.keys()),
            "active_queues": active_queues,
            "scheduled_tasks": len(celery_app.conf.beat_schedule),
        }
    except Exception as e:
        return {"status": "unhealthy", "broker": "disconnected", "error": str(e)}


def get_celery_queue_status(queue_name: str):
    """检查特定队列是否有可消费的 worker。"""
    status = get_celery_status()
    if status.get("status") != "healthy":
        return status

    active_queues = status.get("active_queues") or {}
    matched_workers: list[str] = []
    for worker_name, queue_defs in active_queues.items():
        if not isinstance(queue_defs, list):
            continue
        for queue_def in queue_defs:
            if isinstance(queue_def, dict) and str(queue_def.get("name") or "") == str(queue_name):
                matched_workers.append(str(worker_name))
                break

    status = dict(status)
    status["queue"] = queue_name
    status["queue_workers"] = matched_workers
    status["queue_worker_count"] = len(matched_workers)
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active() or {}
    reserved_tasks = inspect.reserved() or {}

    def _count_tasks(task_map):
        count = 0
        for worker_name in matched_workers:
            for task in task_map.get(worker_name, []) or []:
                delivery_info = task.get("delivery_info") if isinstance(task, dict) else None
                routing_key = str((delivery_info or {}).get("routing_key") or "")
                if routing_key == str(queue_name):
                    count += 1
        return count

    status["queue_active_tasks"] = _count_tasks(active_tasks)
    status["queue_reserved_tasks"] = _count_tasks(reserved_tasks)
    return status


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
        task = celery_app.send_task(task_name, args=args, kwargs=kwargs, queue=queue)
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
        return {"status": result.status, "result": result.result, "ready": True}
    else:
        return {"status": result.status, "result": None, "ready": False}


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
