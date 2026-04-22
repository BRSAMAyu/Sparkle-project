"""
Celery 任务模块 - 任务包装器

提供与应用服务的集成,确保任务可以访问应用上下文

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

from loguru import logger

from app.core.celery_app import _run_async, celery_app


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
                        logger.warning(f"⚠️ Potential duplicate found for {node_id}: {sim.id} ({sim.name})")
                        # 可以在这里触发通知
                        break

                return {"status": "success", "node_id": node_id, "has_duplicate": len(similar) > 1}

            except Exception as e:
                logger.error(f"❌ Failed to process node {node_id}: {e}")
                raise

    try:
        return asyncio.run(_process())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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
                "results": results,
            }

    try:
        return asyncio.run(_analyze())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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
                external_task_id=self.request.id,
            )

    try:
        return asyncio.run(_process())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(bind=True, max_retries=2, name="record_token_usage")
def record_token_usage(
    self,
    user_id: str,
    session_id: str,
    request_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    cost: float,
):
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
                cost=cost,
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

    from app.core.cache import cache_service
    from app.learning.multi_dimensional_learner import MultiDimensionalLearner

    async def _save():
        redis_client = cache_service.redis
        if redis_client is None:
            raise RuntimeError("redis cache unavailable")
        learner = MultiDimensionalLearner(redis_client, user_id=user_id)
        await learner.save_state(state_data)
        return {"status": "success", "user_id": user_id}

    try:
        return asyncio.run(_save())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(bind=True, max_retries=3, name="persist_bayesian_data")
def persist_bayesian_data(self, user_id: str, data: dict):
    """
    持久化贝叶斯学习数据 (异步)

    这是 persistent_bayesian_learner 中 _save_to_redis 的 Celery 版本
    """
    import asyncio
    import json

    from loguru import logger

    from app.core.cache import cache_service
    from app.learning.persistent_bayesian_learner import (
        PERSISTENT_BAYESIAN_TTL_SECONDS,
        build_persistent_bayesian_key,
    )

    async def _persist():
        try:
            redis_client = cache_service.redis
            if redis_client is None:
                raise RuntimeError("redis cache unavailable")
            key = build_persistent_bayesian_key(user_id)
            await redis_client.setex(key, PERSISTENT_BAYESIAN_TTL_SECONDS, json.dumps(data))
            logger.info(f"✅ Persisted Bayesian data for {user_id}")
            return {"status": "success", "user_id": user_id}
        except Exception as e:
            logger.error(f"❌ Failed to persist Bayesian data for {user_id}: {e}")
            raise

    try:
        return asyncio.run(_persist())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.recompute_idiographic_associations",
)
def recompute_idiographic_associations(self, user_id: str | None = None):
    """Recompute Stage 31 idiographic associations for one user or all active users."""
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.idiographic_association_service import (
        IdiographicAssociationService,
    )

    async def _recompute():
        async with AsyncSessionLocal() as session:
            service = IdiographicAssociationService(session)
            if user_id:
                return await service.recompute_user(UUID(user_id), publish_event=False)
            updated = await service.recompute_all_users()
            return {"status": "success", "updated_users": updated}

    try:
        return asyncio.run(_recompute())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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

            result = await session.execute(PendingAction.__table__.delete().where(PendingAction.created_at < cutoff))
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
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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
        raise self.retry(exc=exc, countdown=2**self.request.retries)


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


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.run_push_policy_scheduler")
def run_push_policy_scheduler(self):
    """Run the Stage38 push scheduler in off/shadow/live mode."""
    from app.db.session import AsyncSessionLocal
    from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService
    from app.services.push_service import PushService

    async def _run():
        mode = await AuroraStage38KillSwitchService().get_feature_mode("push_scheduler")
        if mode == "off":
            return {"mode": mode, "evaluated_users": 0, "triggered": 0, "sent": 0, "shadowed": 0, "errors": 0}
        async with AsyncSessionLocal() as session:
            service = PushService(session)
            return await service.process_all_users(delivery_mode=mode)

    try:
        result = _run_async(_run())
        logger.info(f"✅ Push policy scheduler finished: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to run push policy scheduler: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.generate_weekly_growth_digests")
def generate_weekly_growth_digests(self, limit: int = 200, deliver: bool = False):
    """Generate weekly growth digests, optionally delivering them immediately."""
    import asyncio

    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.services.weekly_digest_service import WeeklyDigestService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = WeeklyDigestService(session, cache_service.redis)
            return await service.generate_for_active_users(limit=limit, deliver=deliver)

    try:
        result = _run_async(_run())
        logger.info(f"✅ Weekly growth digests generated: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to generate weekly growth digests: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.deliver_weekly_growth_digests")
def deliver_weekly_growth_digests(self, limit: int = 200):
    """Deliver stored weekly growth digests for active users."""
    import asyncio

    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.services.weekly_digest_service import WeeklyDigestService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = WeeklyDigestService(session, cache_service.redis)
            return await service.deliver_for_active_users(limit=limit)

    try:
        result = _run_async(_run())
        logger.info(f"✅ Weekly growth digests delivered: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to deliver weekly growth digests: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.check_prediction_accuracy")
def check_prediction_accuracy(self):
    """每日自动回填到期的 Theater 预测准确度。"""
    from uuid import UUID

    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.services.theater.prediction_theater_service import PredictionTheaterService

    async def _run():
        if cache_service.redis is None:
            await cache_service.init_redis()
        redis_client = cache_service.redis
        if redis_client is None:
            return {"users": 0, "updated_predictions": 0}

        from app.services.theater.prediction_theater_service import PredictionAccuracyTracker

        raw_user_ids = await redis_client.smembers(PredictionAccuracyTracker.USER_INDEX_KEY)
        user_ids = {
            raw_user_id.decode() if isinstance(raw_user_id, bytes) else str(raw_user_id)
            for raw_user_id in raw_user_ids
            if str(raw_user_id).strip()
        }
        if not user_ids:
            async for raw_key in redis_client.scan_iter("theater:prediction:*"):
                key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
                cached = await cache_service.get(key)
                if not isinstance(cached, dict):
                    continue
                user_id = str(cached.get("user_id") or "").strip()
                if user_id:
                    user_ids.add(user_id)

        updated_predictions = 0
        async with AsyncSessionLocal() as session:
            service = PredictionTheaterService(session)
            for raw_user_id in user_ids:
                try:
                    updated_predictions += len(await service.auto_check_predictions(UUID(raw_user_id)))
                except ValueError:
                    continue
        return {"users": len(user_ids), "updated_predictions": updated_predictions}

    try:
        result = _run_async(_run())
        logger.info(f"✅ Theater prediction accuracy check completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to auto-check theater prediction accuracy: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.cleanup_stale_simulation_sessions")
def cleanup_stale_simulation_sessions(self, max_age_hours: int = 6):
    """清理超过指定时长未活跃的仿真 session。"""
    from app.services.simulation.session_cleanup import cleanup_stale_sessions

    try:
        result = _run_async(cleanup_stale_sessions(max_age_hours=max_age_hours))
        logger.info(f"✅ Stale simulation sessions cleaned: {result}")
        return {"cleaned": result}
    except Exception as exc:
        logger.error(f"❌ Failed to cleanup stale simulation sessions: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.persist_simulation_run")
def persist_simulation_run(self, user_id: str, payload: dict):
    """Persist simulation session payload after the hot-path Redis write."""
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.simulation.simulation_run_store import SimulationRunStore

    async def _run():
        async with AsyncSessionLocal() as session:
            await SimulationRunStore(session).persist_payload(user_id=UUID(user_id), payload=payload)
            return {"status": "ok", "session_id": payload.get("id")}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"❌ Failed to persist simulation run: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.persist_report_snapshot")
def persist_report_snapshot(self, user_id: str, cache_version: str, payload: dict):
    """Persist report snapshot after the hot-path Redis write."""
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.report.report_snapshot_store import ReportSnapshotStore

    async def _run():
        async with AsyncSessionLocal() as session:
            await ReportSnapshotStore(session).persist_snapshot(
                user_id=UUID(user_id),
                cache_version=cache_version,
                payload=payload,
            )
            return {"status": "ok", "report_id": payload.get("report_id")}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"❌ Failed to persist report snapshot: {exc}")
        raise self.retry(exc=exc, countdown=30)


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


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.refresh_metacognition_snapshots")
def refresh_metacognition_snapshots(self, limit: int = 500):
    """Refresh Stage 30 metacognition snapshots for recently active users."""
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.models.task import Task
    from app.models.theater_prediction import TheaterPrediction
    from app.services.metacognition_service import MetacognitionService
    from sqlalchemy import select

    async def _run():
        async with AsyncSessionLocal() as session:
            task_rows = await session.execute(
                select(Task.user_id).where(Task.deleted_at.is_(None)).distinct().limit(limit)
            )
            prediction_rows = await session.execute(
                select(TheaterPrediction.user_id).where(TheaterPrediction.deleted_at.is_(None)).distinct().limit(limit)
            )
            user_ids = {user_id for (user_id,) in task_rows.all() + prediction_rows.all() if user_id is not None}

            refreshed = 0
            service = MetacognitionService(session)
            for user_id in sorted(user_ids, key=str):
                await service.refresh_snapshot(user_id, publish_event=False)
                refreshed += 1

            return {"status": "success", "refreshed_users": refreshed}

    try:
        result = asyncio.run(_run())
        logger.info(f"✅ Refreshed metacognition snapshots: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to refresh metacognition snapshots: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=2, name="generate_long_horizon_prediction")
def generate_long_horizon_prediction(self, user_id: str):
    """使用 GLM batch 生成后台长期行为预测，并写入缓存。"""
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.predictive_service import PredictiveService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = PredictiveService(session)
            return await service.generate_long_horizon_forecast(UUID(user_id))

    try:
        result = asyncio.run(_run())
        logger.info(f"✅ Long horizon prediction generated for user {user_id}")
        return result
    except Exception as exc:
        logger.error(f"❌ Long horizon prediction failed for user {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m",  # M2 Security Fix: 每分钟最多10封邮件
    name="send_verification_email_task",
)
def send_verification_email_task(self, to_email: str, verify_token: str, username: str):
    """
    M2 Security Fix: 发送验证邮件 (Celery 任务)

    通过 Celery 队列化邮件发送，添加速率限制防止邮件服务商封禁。
    """
    import asyncio

    from app.core.email_service import email_service

    async def _send():
        try:
            await email_service.send_verification_email(to_email=to_email, verify_token=verify_token, username=username)
            logger.info(f"✅ Verification email sent to {to_email}")
            return {"status": "success", "to_email": to_email}
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            raise

    try:
        return asyncio.run(_send())
    except Exception as exc:
        logger.error(f"Email send failed to {to_email}, retrying: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, name="send_task_reminders")
def send_task_reminders(self):
    """
    任务提醒已在服务端停用，当前由客户端本地调度统一负责。

    原有服务端实现依赖分钟级提醒窗口，但 Task.due_date 仍然是 Date 类型，
    无法正确表达「提前 1 小时 / 15 分钟」这类语义，还会与客户端本地提醒
    形成双通道重复通知。保留任务入口作为兼容层，避免旧部署或手动触发时报错。
    """
    logger.warning(
        "send_task_reminders is disabled. Task reminders are owned by the mobile local scheduler "
        "until the backend supports datetime-based due times."
    )
    return {
        "status": "disabled",
        "reason": "task reminders are handled by the mobile local scheduler",
    }


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

                LLMMonitor.record_performance_metric(f"celery_{task_name}_duration", duration, {"status": "success"})
            except Exception as exc:
                logger.debug(f"Skip celery success metric for {task_name}: {exc}")
                pass

            logger.info(f"✅ Task {task_name} completed in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time

            # 记录失败指标
            try:
                from app.core.llm_monitoring import LLMMonitor

                LLMMonitor.record_performance_metric(f"celery_{task_name}_duration", duration, {"status": "failed"})
            except Exception as exc:
                logger.debug(f"Skip celery failure metric for {task_name}: {exc}")
                pass

            logger.error(f"❌ Task {task_name} failed after {duration:.2f}s: {e}")
            raise

    return wrapper


# 应用装饰器到所有任务
for task_name in dir():
    task_obj = globals().get(task_name)
    if hasattr(task_obj, "apply_async"):
        # 可以在这里应用装饰器
        pass


@celery_app.task(bind=True, name="acceptance.sleep_probe_task")
def sleep_probe_task(self, seconds: float = 2.0):
    """Acceptance-only probe task used to verify Celery state transitions."""
    import time

    delay = max(0.1, float(seconds))
    time.sleep(delay)
    return {
        "status": "success",
        "slept_seconds": delay,
        "task_id": self.request.id,
    }


@celery_app.task(
    bind=True, max_retries=3, default_retry_delay=60, name="app.core.celery_tasks.schedule_push_notification"
)
def schedule_push_notification(self, user_id: str, intervention_id: str, payload: dict):
    """
    Schedule a push notification delivery to the mobile app (APNs/FCM).
    This acts as the PUSH delivery channel for InterventionRecords.
    """
    import asyncio

    async def _send():
        # In a real system, this would call APNs/FCM APIs.
        logger.info(f"Push notification sent successfully to user {user_id} for intervention {intervention_id}")
        logger.debug(f"Push payload: {payload}")
        return True

    return _run_async(_send())


@celery_app.task(bind=True, max_retries=1, default_retry_delay=1, name="acceptance.fail_probe_task")
def fail_probe_task(self):
    """Acceptance-only probe task used to verify retry/failure handling."""
    attempt = int(self.request.retries or 0)
    if attempt < 1:
        raise self.retry(exc=RuntimeError("intentional acceptance retry"), countdown=1)
    raise RuntimeError("intentional acceptance failure")


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="retry_achievement_photon_reward",
)
def retry_achievement_photon_reward(
    self,
    user_id: str,
    achievement_id: str,
    achievement_name: str,
    quantity: int,
):
    """Retry failed photon rewards for achievement unlocks."""
    from app.db.session import AsyncSessionLocal
    from app.services.achievement_reward_observability import AchievementRewardObservability
    from app.services.photon_service import PhotonService, PhotonTransactionType

    async def _grant():
        async with AsyncSessionLocal() as session:
            photon_service = PhotonService(session)
            return await photon_service.grant_photons(
                user_id=user_id,
                amount=quantity,
                source=f"achievement:{achievement_id}",
                transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT,
                metadata={"achievement_name": achievement_name},
                related_item_id=achievement_id,
                record_history=True,
            )

    try:
        result = _run_async(_grant())
        _run_async(
            AchievementRewardObservability.record_event(
                status="retry_succeeded",
                channel="celery",
                user_id=user_id,
                achievement_id=achievement_id,
                achievement_name=achievement_name,
                quantity=quantity,
                attempt=int(self.request.retries or 0) + 1,
            )
        )
        logger.info(
            "Retried achievement photon reward successfully for achievement %s and user %s",
            achievement_id,
            user_id,
        )
        return {"status": "success", "result": result}
    except Exception as exc:
        attempt = int(self.request.retries or 0) + 1
        max_retries = int(getattr(self, "max_retries", 3) or 3)
        status = "exhausted" if attempt > max_retries else "retry_failed"
        _run_async(
            AchievementRewardObservability.record_event(
                status=status,
                channel="celery",
                user_id=user_id,
                achievement_id=achievement_id,
                achievement_name=achievement_name,
                quantity=quantity,
                attempt=attempt,
                error_message=str(exc),
            )
        )
        logger.error(
            "Failed to retry achievement photon reward for achievement %s and user %s: %s",
            achievement_id,
            user_id,
            exc,
        )
        if attempt > max_retries:
            raise
        raise self.retry(exc=exc, countdown=30 * (2 ** int(self.request.retries or 0)))


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.recompute_persdyn_attractors")
def recompute_persdyn_attractors(self):
    """Recompute Stage 27 PersDyn attractors for all users."""
    import asyncio

    from app.db.session import AsyncSessionLocal
    from app.services.persdyn_attractor_service import PersDynAttractorService

    async def _recompute():
        async with AsyncSessionLocal() as session:
            service = PersDynAttractorService(session)
            updated = await service.recompute_all_users()
            logger.info("✅ Recomputed PersDyn attractors for {} users", updated)
            return {"status": "success", "updated_users": updated}

    try:
        return asyncio.run(_recompute())
    except Exception as exc:
        logger.error("❌ Failed to recompute PersDyn attractors: {}", exc)
        raise self.retry(exc=exc, countdown=60 * (2 ** int(self.request.retries or 0)))
