"""
Celery 任务模块 - 任务包装器

提供与应用服务的集成,确保任务可以访问应用上下文

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

from loguru import logger

from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="app.core.celery_tasks.health_check_task")
def health_check_task(self):
    """健康检查任务"""
    from app.core.task_manager import task_manager

    stats = task_manager.health_check()
    logger.info(f"Health check: {stats}")
    return stats


@celery_app.task(bind=True, max_retries=3, name="generate_node_embedding")
def generate_node_embedding(self, node_id: str, title: str, summary: str, user_id: str = None):
    """
    生成节点 Embedding (完整版本)

    这是 galaxy_service 中 _process_node_background 的 Celery 版本
    """
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.models.galaxy import KnowledgeNode
    from app.services.embedding_service import embedding_service
    from app.services.galaxy.retrieval_service import KnowledgeRetrievalService

    async def _process():
        async with AsyncSessionLocal() as session:
            try:
                # 1. 生成 Embedding
                text = f"{title}\n{summary}"
                embedding = await embedding_service.get_embedding(text)

                # 2. 更新节点
                node = await session.get(KnowledgeNode, UUID(node_id))
                if not node:
                    raise ValueError(f"Node {node_id} not found")

                node.embedding = embedding
                session.add(node)
                await session.commit()

                logger.info(f"✅ Generated embedding for node {node_id}")

                # 3. 查重检查
                retrieval = KnowledgeRetrievalService(session)
                similar = await retrieval.semantic_search_nodes(title, limit=2, threshold=0.1)

                for sim in similar:
                    if sim.id != UUID(node_id):
                        logger.warning(
                            f"⚠️ Potential duplicate found for {node_id}: "
                            f"{sim.id} ({sim.name})"
                        )
                        # 可以在这里触发通知
                        break

                return {
                    "status": "success",
                    "node_id": node_id,
                    "has_duplicate": len(similar) > 1
                }

            except Exception as e:
                logger.error(f"❌ Failed to process node {node_id}: {e}")
                raise

    try:
        return asyncio.run(_process())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="analyze_error_batch")
def analyze_error_batch(self, error_ids: list, user_id: str):
    """
    批量错题分析 (完整版本)

    这是 error_book_grpc_service 中 _run_analysis_task 的 Celery 版本
    """
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.error_book_service import ErrorBookService

    async def _analyze():
        async with AsyncSessionLocal() as session:
            service = ErrorBookService(session)
            results = []

            for error_id in error_ids:
                try:
                    await service.analyze_and_link(UUID(error_id), UUID(user_id))
                    results.append({"error_id": error_id, "status": "success"})
                except Exception as e:
                    results.append({"error_id": error_id, "status": "failed", "error": str(e)})

            return {
                "total": len(error_ids),
                "success": sum(1 for r in results if r["status"] == "success"),
                "results": results
            }

    try:
        return asyncio.run(_analyze())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2, name="process_stored_file")
def process_stored_file(
    self,
    file_id: str,
    user_id: str,
    download_url: str,
    file_name: str,
    mime_type: str,
    thumbnail_upload_url: str = None,
):
    """
    Process uploaded file: chunking, embeddings, optional thumbnail.
    """
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.file_processing_orchestrator import FileProcessingOrchestrator

    async def _process():
        async with AsyncSessionLocal() as session:
            orchestrator = FileProcessingOrchestrator(session)
            return await orchestrator.process_file(
                file_id=UUID(file_id),
                user_id=UUID(user_id),
                download_url=download_url,
                file_name=file_name,
                mime_type=mime_type,
                thumbnail_upload_url=thumbnail_upload_url,
            )

    try:
        return asyncio.run(_process())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@celery_app.task(bind=True, max_retries=2, name="record_token_usage")
def record_token_usage(self, user_id: str, session_id: str, request_id: str,
                      prompt_tokens: int, completion_tokens: int, model: str, cost: float):
    """
    记录 Token 使用量 (异步)

    这是 orchestrator 中 token_tracker.record_usage 的 Celery 版本
    """
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.services.token_tracker import TokenTracker

    async def _record():
        async with AsyncSessionLocal() as session:
            tracker = TokenTracker(session)
            await tracker.record_usage(
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=model,
                cost=cost
            )
            return {"status": "success", "user_id": user_id}

    try:
        return asyncio.run(_record())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=3, name="save_learning_state")
def save_learning_state(self, user_id: str, state_data: dict):
    """
    保存学习状态 (异步)

    这是 multi_dimensional_learner 中 _save 的 Celery 版本
    """
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.learning.multi_dimensional_learner import MultiDimensionalLearner

    async def _save():
        async with AsyncSessionLocal() as session:
            learner = MultiDimensionalLearner(session)
            await learner.save_state(user_id, state_data)
            return {"status": "success", "user_id": user_id}

    try:
        return asyncio.run(_save())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="persist_bayesian_data")
def persist_bayesian_data(self, user_id: str, data: dict):
    """
    持久化贝叶斯学习数据 (异步)

    这是 persistent_bayesian_learner 中 _save_to_redis 的 Celery 版本
    """
    import asyncio
    import json

    from loguru import logger

    from app.core.cache import redis_client

    async def _persist():
        try:
            key = f"bayesian_learner:{user_id}"
            await redis_client.setex(
                key,
                86400,  # 24小时
                json.dumps(data)
            )
            logger.info(f"✅ Persisted Bayesian data for {user_id}")
            return {"status": "success", "user_id": user_id}
        except Exception as e:
            logger.error(f"❌ Failed to persist Bayesian data for {user_id}: {e}")
            raise

    try:
        return asyncio.run(_persist())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2, name="invalidate_cache")
def invalidate_cache(self, cache_key: str):
    """
    缓存失效 (异步)

    这是 route_cache 中 _invalidate_redis 的 Celery 版本
    """
    import asyncio

    from app.core.cache import redis_client

    async def _invalidate():
        try:
            await redis_client.delete(cache_key)
            return {"status": "success", "cache_key": cache_key}
        except Exception:
            raise

    try:
        return asyncio.run(_invalidate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)


@celery_app.task(bind=True, max_retries=3, name="cleanup_pending_actions")
def cleanup_pending_actions(self):
    """
    清理过期待处理动作 (定时)

    这是 pending_actions 中 _cleanup_expired 的 Celery 版本
    """
    import asyncio
    from datetime import datetime, timedelta

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.models.pending_actions import PendingAction

    async def _cleanup():
        async with AsyncSessionLocal() as session:
            cutoff = datetime.now() - timedelta(hours=24)

            result = await session.execute(
                PendingAction.__table__.delete().where(
                    PendingAction.created_at < cutoff
                )
            )
            deleted = result.rowcount

            await session.commit()

            logger.info(f"✅ Cleaned up {deleted} pending actions")
            return {"status": "success", "deleted": deleted}

    try:
        return asyncio.run(_cleanup())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="rerank_documents")
def rerank_documents(self, query: str, doc_ids: list, user_id: str):
    """
    文档重排序 (长时任务)

    这是 rerank_service 中模型加载和推理的 Celery 版本
    """
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.services.rerank_service import RerankService

    async def _rerank():
        async with AsyncSessionLocal():
            service = RerankService()
            results = await service.rerank(query, doc_ids, user_id)
            return {"status": "success", "results": results}

    try:
        return asyncio.run(_rerank())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="expansion_worker_task")
def expansion_worker_task(self, node_id: str, operation: str):
    """
    知识扩展 worker (长时任务)

    这是 expansion_worker 的 Celery 版本
    """
    import asyncio
    from uuid import UUID

    from loguru import logger

    from app.db.session import AsyncSessionLocal
    from app.services.galaxy.expansion_service import ExpansionService

    async def _expand():
        async with AsyncSessionLocal() as session:
            service = ExpansionService(session)

            if operation == "auto_link":
                result = await service.auto_link_nodes(UUID(node_id))
            elif operation == "expand":
                result = await service.expand_node(UUID(node_id))
            else:
                raise ValueError(f"Unknown operation: {operation}")

            logger.info(f"✅ Expansion worker completed: {node_id} - {operation}")
            return {"status": "success", "node_id": node_id, "operation": operation, "result": result}

    try:
        return asyncio.run(_expand())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2, name="visualize_graph")
def visualize_graph(self, user_id: str, graph_data: dict):
    """
    生成可视化数据 (长时任务)

    这是 visualization service 的 Celery 版本
    """
    import asyncio

    from app.services.visualization.graph_generator import GraphGenerator

    async def _visualize():
        generator = GraphGenerator()
        result = await generator.generate(graph_data, user_id)
        return {"status": "success", "visualization_id": result.id}

    try:
        return asyncio.run(_visualize())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.generate_weekly_learning_reports")
def generate_weekly_learning_reports(self, limit: int = 200):
    """
    聚合周级学习报告并写入 system updates。
    """
    import asyncio

    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.services.perceptible_intelligence_service import WeeklyLearningReportService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = WeeklyLearningReportService(session, cache_service.redis)
            return await service.enqueue_reports_for_active_users(limit=limit)

    try:
        result = asyncio.run(_run())
        logger.info(f"✅ Weekly learning reports generated: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to generate weekly learning reports: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.capture_ai_metric_baseline")
def capture_ai_metric_baseline(self):
    """Capture AI metric baseline snapshots into Redis."""
    import asyncio

    from app.core.cache import cache_service
    from app.services.self_evolution_service import MetricBaselineService

    async def _run():
        service = MetricBaselineService(cache_service.redis)
        return await service.capture_snapshot()

    try:
        result = asyncio.run(_run())
        logger.info(f"✅ AI metric baseline snapshot captured: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to capture AI metric baseline: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.promote_perceptible_cohort")
def promote_perceptible_cohort(self):
    """Evaluate perceptible cohorts and promote baseline strategy when ready."""
    import asyncio

    from app.core.cache import cache_service
    from app.services.self_evolution_service import CohortPromotionService

    async def _run():
        service = CohortPromotionService(cache_service.redis)
        return await service.evaluate_and_promote()

    try:
        result = asyncio.run(_run())
        logger.info(f"✅ Perceptible cohort evaluation completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to promote perceptible cohort: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=2, name="send_task_reminders")
def send_task_reminders(self):
    """
    发送任务提醒（每15分钟执行一次）

    检查启用任务提醒的用户，为即将到期的任务发送通知。
    提醒时间默认为：24小时前、1小时前、15分钟前
    """
    import asyncio
    from datetime import datetime, timedelta
    from uuid import UUID

    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.models.task import Task
    from app.models.user_settings import UserSettings
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService
    from sqlalchemy import and_, select

    async def _send():
        async with AsyncSessionLocal() as session:
            # 获取启用任务提醒的用户
            result = await session.execute(
                select(UserSettings).where(
                    UserSettings.task_reminders_enabled == True,
                    UserSettings.deleted_at.is_(None),
                )
            )
            users_settings = result.scalars().all()

            sent_count = 0
            skipped_count = 0

            for settings in users_settings:
                try:
                    reminder_times = settings.task_reminder_times or [1440, 60, 15]
                    user_id = settings.user_id

                    # 计算提醒时间窗口
                    now = datetime.utcnow()
                    windows = []
                    for minutes in reminder_times:
                        # 窗口：目标时间前后 30 秒（因为任务是每 15 分钟运行一次）
                        window_start = now + timedelta(minutes=minutes, seconds=-30)
                        window_end = now + timedelta(minutes=minutes, seconds=30)
                        windows.append((window_start, window_end, minutes))

                    # 查询即将到期的任务
                    for window_start, window_end, minutes in windows:
                        tasks_result = await session.execute(
                            select(Task).where(
                                and_(
                                    Task.user_id == user_id,
                                    Task.due_date.between(window_start, window_end),
                                    Task.status != "completed",
                                    Task.deleted_at.is_(None),
                                )
                            )
                        )
                        tasks = tasks_result.scalars().all()

                        for task in tasks:
                            # 检查是否已发送提醒（使用 Redis 去重）
                            reminder_key = f"task_reminder:{task.id}:{minutes}"
                            if await cache_service.redis.get(reminder_key):
                                skipped_count += 1
                                continue

                            # 格式化提醒消息
                            if minutes >= 1440:
                                time_desc = f"{minutes // 1440}天"
                            elif minutes >= 60:
                                time_desc = f"{minutes // 60}小时"
                            else:
                                time_desc = f"{minutes}分钟"

                            # 发送提醒
                            await NotificationService.create(
                                session,
                                user_id,
                                NotificationCreate(
                                    title="任务即将到期",
                                    content=f"任务「{task.title}」将在{time_desc}后到期",
                                    type="task_reminder",
                                    data={
                                        "task_id": str(task.id),
                                        "minutes": minutes,
                                        "due_date": task.due_date.isoformat() if task.due_date else None,
                                    },
                                ),
                            )

                            # 标记已发送（24小时内有效）
                            await cache_service.redis.setex(reminder_key, 86400, "1")
                            sent_count += 1

                    await session.commit()

                except Exception as e:
                    logger.warning(f"Failed to send reminders for user {settings.user_id}: {e}")

            logger.info(f"✅ Task reminders sent: {sent_count}, skipped (duplicate): {skipped_count}")
            return {"sent_count": sent_count, "skipped_count": skipped_count}

    try:
        return asyncio.run(_send())
    except Exception as exc:
        logger.error(f"❌ Task reminders failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


# =============================================================================
# 任务监控装饰器
# =============================================================================

def monitor_task_execution(task_func):
    """
    任务执行监控装饰器

    自动记录任务执行时间、成功率等指标
    """
    import time
    from functools import wraps

    @wraps(task_func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        task_name = task_func.__name__

        try:
            result = task_func(*args, **kwargs)
            duration = time.time() - start_time

            # 记录成功指标
            try:
                from app.core.llm_monitoring import LLMMonitor
                LLMMonitor.record_performance_metric(
                    f"celery_{task_name}_duration",
                    duration,
                    {"status": "success"}
                )
            except:
                pass

            logger.info(f"✅ Task {task_name} completed in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time

            # 记录失败指标
            try:
                from app.core.llm_monitoring import LLMMonitor
                LLMMonitor.record_performance_metric(
                    f"celery_{task_name}_duration",
                    duration,
                    {"status": "failed"}
                )
            except:
                pass

            logger.error(f"❌ Task {task_name} failed after {duration:.2f}s: {e}")
            raise

    return wrapper


# 应用装饰器到所有任务
for task_name in dir():
    task_obj = globals().get(task_name)
    if hasattr(task_obj, 'apply_async'):
        # 可以在这里应用装饰器
        pass
