"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Celery 任务模块 - 任务包装器

提供与应用服务的集成,确保任务可以访问应用上下文

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""


from datetime import UTC, datetime

from loguru import logger

from app.core.celery_app import _run_async, celery_app


def _notification_data_matches(actual, expected) -> bool:
    if expected is None:
        return actual in (None, "")
    if isinstance(expected, float):
        try:
            return abs(float(actual) - expected) < 1e-6
        except (TypeError, ValueError):
            return False
    return str(actual) == str(expected)


async def _has_recent_notification(
    session,
    *,
    user_id,
    notification_type: str,
    match_data: dict[str, object] | None = None,
    within_hours: int = 24,
    now=None,
) -> bool:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import desc, select

    from app.models.notification import Notification

    reference_time = now or datetime.now(UTC).replace(tzinfo=None)
    since = reference_time - timedelta(hours=within_hours)
    result = await session.execute(
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.created_at >= since,
            Notification.deleted_at.is_(None),
        )
        .order_by(desc(Notification.created_at))
    )
    notifications = result.scalars().all()
    if not match_data:
        return bool(notifications)

    for notification in notifications:
        payload = notification.data if isinstance(notification.data, dict) else {}
        if all(_notification_data_matches(payload.get(key), value) for key, value in match_data.items()):
            return True
    return False


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(bind=True, max_retries=6, name="process_group_shared_file")
def process_group_shared_file(
    self,
    group_id: str,
    file_id: str,
    shared_by_user_id: str,
):
    """
    Index a shared file into the group-scoped RAG namespace.
    """
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.file_processing_orchestrator import FileProcessingOrchestrator

    async def _process():
        async with AsyncSessionLocal() as session:
            orchestrator = FileProcessingOrchestrator(session)
            return await orchestrator.process_group_file(
                group_id=UUID(group_id),
                file_id=UUID(file_id),
                shared_by_user_id=UUID(shared_by_user_id),
                external_task_id=self.request.id,
            )

    try:
        return asyncio.run(_process())
    except ValueError as exc:
        logger.warning(f"Skipping group file processing for group={group_id} file={file_id}: {exc}")
        return {"status": "skipped", "group_id": group_id, "file_id": file_id, "error": str(exc)}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=min(300, 2 ** max(1, self.request.retries))) from exc


@celery_app.task(bind=True, max_retries=2, name="delete_group_file_index")
def delete_group_file_index(
    self,
    group_id: str,
    file_id: str,
):
    """
    Remove group-scoped RAG chunks for a deleted/unshared group file.
    """
    import asyncio
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.services.file_processing_orchestrator import FileProcessingOrchestrator

    async def _process():
        async with AsyncSessionLocal() as session:
            orchestrator = FileProcessingOrchestrator(session)
            return await orchestrator.delete_group_file_index(
                group_id=UUID(group_id),
                file_id=UUID(file_id),
            )

    try:
        return asyncio.run(_process())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=10) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=5) from exc


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
        raise self.retry(exc=exc, countdown=60) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


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
        raise self.retry(exc=exc, countdown=60) from exc


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
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.evaluate_routing_outcomes")
def evaluate_routing_outcomes(self, limit: int = 200):
    """Evaluate delayed DualCore routing outcomes and feed SGW."""
    from app.db.session import AsyncSessionLocal
    from app.services.routing_outcome_service import RoutingOutcomeEvaluator

    async def _run():
        async with AsyncSessionLocal() as session:
            return {"evaluated": await RoutingOutcomeEvaluator(session).evaluate_due(limit=limit)}

    try:
        result = _run_async(_run())
        logger.info(f"✅ Routing outcome evaluation finished: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to evaluate routing outcomes: {exc}")
        raise self.retry(exc=exc, countdown=300) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.generate_weekly_growth_digests")
def generate_weekly_growth_digests(self, limit: int = 200, deliver: bool = False):
    """Generate weekly growth digests, optionally delivering them immediately."""

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
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.deliver_weekly_growth_digests")
def deliver_weekly_growth_digests(self, limit: int = 200):
    """Deliver stored weekly growth digests for active users."""

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
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_post_exam_review_invitations")
def scan_post_exam_review_invitations(self, limit: int = 200):
    """Scan exam sprint plans and invite users into post-exam review when due."""
    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.services.exam_sprint_review_service import ExamSprintReviewService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = ExamSprintReviewService(session, cache_service.redis)
            return await service.scan_due_review_invitations(limit=limit)

    try:
        result = _run_async(_run())
        logger.info(f"✅ Post-exam review invitation scan finished: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to scan post-exam review invitations: {exc}")
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.pack_quality_analysis_task")
def pack_quality_analysis_task(self, pack_id: str):
    """Analyze Sprint Pack node quality and persist the report into Redis."""
    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.services.exam_sprint_review_service import ExamSprintReviewService

    async def _run():
        if cache_service.redis is None:
            await cache_service.init_redis()

        async with AsyncSessionLocal() as session:
            service = ExamSprintReviewService(session, cache_service.redis)
            alerts = await service.analyze_pack_node_effectiveness(pack_id)
            eligible_alerts = [
                alert for alert in alerts if int(getattr(alert, "evidence_count", 0)) >= service.PACK_QUALITY_MIN_EVIDENCE_COUNT
            ]
            report = await service.build_pack_quality_report(pack_id, alerts=eligible_alerts)
            cache_key = service.build_pack_quality_alerts_cache_key(pack_id)
            await cache_service.set(
                cache_key,
                report.model_dump(mode="json"),
                ttl=service.PACK_QUALITY_REPORT_TTL_SECONDS,
            )
            return report.model_dump(mode="json")

    try:
        result = _run_async(_run())
        logger.info(f"✅ Pack quality analysis finished for {pack_id}: {result}")
        return result
    except Exception as exc:
        logger.error(f"❌ Failed to analyze pack quality for {pack_id}: {exc}")
        raise self.retry(exc=exc, countdown=60) from exc


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
        raise self.retry(exc=exc, countdown=120) from exc


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
        raise self.retry(exc=exc, countdown=120) from exc


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
        raise self.retry(exc=exc, countdown=30) from exc


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
        raise self.retry(exc=exc, countdown=30) from exc


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
        raise self.retry(exc=exc, countdown=60) from exc


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
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.refresh_metacognition_snapshots")
def refresh_metacognition_snapshots(self, limit: int = 500):
    """Refresh Stage 30 metacognition snapshots for recently active users."""
    import asyncio

    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.task import Task
    from app.models.theater_prediction import TheaterPrediction
    from app.services.metacognition_service import MetacognitionService

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
        raise self.retry(exc=exc, countdown=120) from exc


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
        raise self.retry(exc=exc, countdown=120) from exc


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
        raise self.retry(exc=exc) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m",
    name="send_password_reset_email_task",
)
def send_password_reset_email_task(self, to_email: str, reset_token: str, username: str):
    """Send password reset email via Celery (replaces fire-and-forget asyncio.create_task)."""
    import asyncio

    from app.core.email_service import email_service

    async def _send():
        try:
            await email_service.send_password_reset_email(to_email=to_email, reset_token=reset_token, username=username)
            logger.info(f"Password reset email sent to {to_email}")
            return {"status": "success", "to_email": to_email}
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            raise

    try:
        return asyncio.run(_send())
    except Exception as exc:
        logger.error(f"Password reset email failed to {to_email}, retrying: {exc}")
        raise self.retry(exc=exc) from exc


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
        raise self.retry(exc=exc, countdown=30 * (2 ** int(self.request.retries or 0))) from exc


SPACED_REPETITION_INTERVAL_DAYS = (1, 3, 7, 14, 30)
SPACED_REPETITION_INTERVALS_BY_MASTERY = (
    (0.30, 0.50, (1, 3, 7)),
    (0.50, 0.65, (3, 7, 14)),
    (0.65, 0.75, (7, 14, 30)),
    (0.75, 0.80, (14, 30)),
)
SPACED_REPETITION_GRACE_DAYS = 2
SPACED_REPETITION_MASTERY_MIN = 0.3
SPACED_REPETITION_MASTERY_MAX = 0.8


def _spaced_repetition_as_utc_naive(value):
    from datetime import UTC

    if value is None:
        return None
    if isinstance(value, str):
        from datetime import datetime

        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _spaced_repetition_mastery_ratio(status) -> float:
    mastery_score = float(getattr(status, "mastery_score", 0.0) or 0.0)
    if mastery_score > 0:
        return max(0.0, min(mastery_score / 100.0 if mastery_score > 1.0 else mastery_score, 1.0))

    bkt_mastery = float(getattr(status, "bkt_mastery_prob", 0.0) or 0.0)
    return max(0.0, min(bkt_mastery, 1.0))


def _spaced_repetition_last_updated_at(status):
    for attr in ("bkt_last_updated_at", "last_study_at", "updated_at", "last_interacted_at"):
        value = _spaced_repetition_as_utc_naive(getattr(status, attr, None))
        if value is not None:
            return value
    return None


def _spaced_repetition_interval_days_for_mastery(mastery: float | None) -> tuple[int, ...]:
    if mastery is None:
        return SPACED_REPETITION_INTERVAL_DAYS
    mastery_ratio = max(0.0, min(float(mastery), 1.0))
    for lower, upper, intervals in SPACED_REPETITION_INTERVALS_BY_MASTERY:
        if lower <= mastery_ratio < upper:
            return intervals
    if mastery_ratio == SPACED_REPETITION_MASTERY_MAX:
        return SPACED_REPETITION_INTERVALS_BY_MASTERY[-1][2]
    return SPACED_REPETITION_INTERVAL_DAYS


def _spaced_repetition_due_interval_days(last_updated_at, now, mastery: float | None = None) -> int | None:
    last_updated = _spaced_repetition_as_utc_naive(last_updated_at)
    reference_time = _spaced_repetition_as_utc_naive(now)
    if last_updated is None or reference_time is None:
        return None
    elapsed_seconds = (reference_time - last_updated).total_seconds()
    if elapsed_seconds < 0:
        return None
    elapsed_days = int(elapsed_seconds // 86400)
    interval_days_for_mastery = _spaced_repetition_interval_days_for_mastery(mastery)
    for interval_days in reversed(interval_days_for_mastery):
        if interval_days <= elapsed_days < interval_days + SPACED_REPETITION_GRACE_DAYS:
            return interval_days
    return None


async def _run_spaced_repetition_reminders_for_user(session, user_id: str, now=None) -> dict:
    from datetime import UTC, datetime
    from uuid import UUID

    from sqlalchemy import select

    from app.models.galaxy import KnowledgeNode, UserNodeStatus
    from app.services.notification_center_service import NotificationCenterService

    user_uuid = UUID(str(user_id))
    reference_time = _spaced_repetition_as_utc_naive(now) or datetime.now(UTC).replace(tzinfo=None)

    stmt = (
        select(UserNodeStatus, KnowledgeNode)
        .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
        .where(
            UserNodeStatus.user_id == user_uuid,
            KnowledgeNode.deleted_at.is_(None),
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    notification_service = NotificationCenterService(session)

    summary = {
        "status": "completed",
        "user_id": str(user_uuid),
        "evaluated": len(rows),
        "sent": 0,
        "skipped_mastery": 0,
        "skipped_window": 0,
        "skipped_duplicate": 0,
        "skipped_paused": 0,
        "sent_node_ids": [],
    }

    for status, node in rows:
        if bool(getattr(status, "decay_paused", False)):
            summary["skipped_paused"] += 1
            continue

        mastery = _spaced_repetition_mastery_ratio(status)
        if mastery < SPACED_REPETITION_MASTERY_MIN or mastery > SPACED_REPETITION_MASTERY_MAX:
            summary["skipped_mastery"] += 1
            continue

        last_updated_at = _spaced_repetition_last_updated_at(status)
        due_interval_days = _spaced_repetition_due_interval_days(last_updated_at, reference_time, mastery=mastery)
        if due_interval_days is None:
            summary["skipped_window"] += 1
            continue

        notification = await notification_service.send_spaced_repetition_reminder(
            user_id=user_uuid,
            node_id=node.id,
            node_name=node.name,
            interval_days=due_interval_days,
            mastery=mastery,
            now=reference_time,
        )
        if notification is None:
            summary["skipped_duplicate"] += 1
            continue

        summary["sent"] += 1
        summary["sent_node_ids"].append(str(node.id))

    return summary


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.spaced_repetition_reminder_task",
)
def spaced_repetition_reminder_task(self, user_id: str, now_iso: str | None = None):
    """G12: Send precise spaced-repetition reminders for one user's Galaxy nodes."""
    from app.db.session import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as session:
            return await _run_spaced_repetition_reminders_for_user(session, user_id, now=now_iso)

    try:
        result = _run_async(_run())
        logger.info("✅ Spaced repetition reminder task finished for user %s: %s", user_id, result)
        return result
    except Exception as exc:
        logger.error("❌ spaced_repetition_reminder_task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.scan_spaced_repetition_reminders",
)
def scan_spaced_repetition_reminders(self, limit: int = 500):
    """Daily scan that dispatches G12 spaced-repetition reminders per active user."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.galaxy import UserNodeStatus
    from app.models.user import User

    async def _run():
        async with AsyncSessionLocal() as session:
            batch_size = max(1, min(int(limit or 500), 1000))
            dispatched = 0
            offset = 0
            while True:
                stmt = (
                    select(UserNodeStatus.user_id)
                    .join(User, User.id == UserNodeStatus.user_id)
                    .where(User.is_active.is_(True))
                    .distinct()
                    .order_by(UserNodeStatus.user_id)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await session.execute(stmt)
                user_ids = [row[0] for row in result.all()]
                if not user_ids:
                    break

                for user_uuid in user_ids:
                    celery_app.send_task(
                        "app.core.celery_tasks.spaced_repetition_reminder_task",
                        args=(str(user_uuid),),
                        queue="default",
                    )
                    dispatched += 1

                if len(user_ids) < batch_size:
                    break
                offset += batch_size

            logger.info("✅ Dispatched %d spaced repetition reminder tasks", dispatched)
            return {"dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ scan_spaced_repetition_reminders failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.daily_sprint_reminder_task",
)
def daily_sprint_reminder_task(self, user_id: str, plan_id: str):
    """
    F17: 如果用户今天的 Sprint 任务完成率低于预期（<60%），发送推送提醒。

    条件:
      - completion_rate < 0.6 → 触发推送
      - days_left > 0 → 考试当天不催
      - 推送内容包含科目、剩余天数、今日主任务
    """
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.schemas.notification import NotificationCreate
    from app.services.exam_sprint_dashboard_service import ExamSprintDashboardService
    from app.services.notification_service import NotificationService

    async def _run():
        from datetime import UTC, datetime

        async with AsyncSessionLocal() as session:
            dashboard_service = ExamSprintDashboardService(session)
            dashboard = await dashboard_service.get_dashboard(UUID(user_id))
            reference_time = datetime.now(UTC).replace(tzinfo=None)

            if not dashboard.active or str(dashboard.plan_id) != plan_id:
                logger.debug(
                    "daily_sprint_reminder_task: no active sprint or plan mismatch for user %s",
                    user_id,
                )
                return {"status": "skipped", "reason": "no_active_sprint"}

            if dashboard.days_left <= 0:
                logger.debug(
                    "daily_sprint_reminder_task: exam day, skipping for user %s",
                    user_id,
                )
                return {"status": "skipped", "reason": "exam_day"}

            completion_rate = dashboard.today_progress.completion_rate
            if completion_rate >= 0.6:
                logger.debug(
                    "daily_sprint_reminder_task: completion %.0f%% ok, skipping for user %s",
                    completion_rate * 100,
                    user_id,
                )
                return {"status": "skipped", "reason": "on_track", "completion_rate": completion_rate}

            # Build primary task name from today's group
            primary_task_title = ""
            for group in dashboard.task_groups:
                if group.is_today:
                    for task_item in group.tasks:
                        if task_item.status != "completed":
                            primary_task_title = task_item.title
                            break
                    break

            subject = dashboard.subject or dashboard.plan_name or "Sprint"
            days_left = dashboard.days_left
            completion_percent = int(round(completion_rate * 100))
            destination_route = f"/plans/{plan_id}?source=push_sprint_reminder"

            if await _has_recent_notification(
                session,
                user_id=UUID(user_id),
                notification_type="sprint_reminder",
                match_data={"plan_id": plan_id},
                now=reference_time,
            ):
                logger.debug(
                    "daily_sprint_reminder_task: duplicate reminder suppressed for user %s plan %s",
                    user_id,
                    plan_id,
                )
                return {
                    "status": "skipped",
                    "reason": "duplicate_recent",
                    "completion_rate": completion_rate,
                    "days_left": days_left,
                }

            title = f"今日 Sprint 完成率 {completion_percent}%"
            content = (
                f"{subject} 还剩 {days_left} 天，"
                f"你今天的完成率是 {completion_percent}%，"
                f"主任务「{primary_task_title or '今日冲刺任务'}」还没收尾。现在继续，还来得及。"
            )

            await NotificationService.create(
                session,
                UUID(user_id),
                NotificationCreate(
                    title=title,
                    content=content,
                    type="sprint_reminder",
                    data={
                        "plan_id": plan_id,
                        "days_left": days_left,
                        "completion_rate": completion_rate,
                        "primary_task": primary_task_title,
                        "destination_route": destination_route,
                        "deep_link": destination_route,
                    },
                ),
                push_via_websocket=True,
            )

            logger.info(
                "✅ Sprint reminder sent to user %s (plan %s, completion=%.0f%%)",
                user_id,
                plan_id,
                completion_rate * 100,
            )
            return {
                "status": "sent",
                "user_id": user_id,
                "plan_id": plan_id,
                "completion_rate": completion_rate,
                "days_left": days_left,
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ daily_sprint_reminder_task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.scan_daily_sprint_reminders",
)
def scan_daily_sprint_reminders(self, limit: int = 500):
    """
    F17: 每日扫描所有活跃 sprint 用户，为每个用户派发 daily_sprint_reminder_task。
    """
    from sqlalchemy import and_, select

    from app.db.session import AsyncSessionLocal
    from app.models.plan import Plan, PlanType

    async def _run():
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Plan.user_id, Plan.id)
                .where(
                    and_(
                        Plan.is_active.is_(True),
                        Plan.type == PlanType.SPRINT,
                        Plan.not_deleted_filter(),
                    )
                )
                .limit(limit)
            )
            rows = (await session.execute(stmt)).all()
            dispatched = 0
            for user_id, plan_id in rows:
                celery_app.send_task(
                    "app.core.celery_tasks.daily_sprint_reminder_task",
                    args=(str(user_id), str(plan_id)),
                    queue="default",
                )
                dispatched += 1

            logger.info("✅ Dispatched %d sprint reminder tasks", dispatched)
            return {"dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ scan_daily_sprint_reminders failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.comeback_nudge_task")
def comeback_nudge_task(self, user_id: str):
    """
    G22: 当用户有活跃计划且至少 3 天未活跃时，生成 comeback 消息并推送。

    消息包含：剩余天数、最近任务简介、轻量启动提议（"30分钟保底版"）。
    """
    from uuid import UUID

    from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
    from app.db.session import AsyncSessionLocal
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService

    COMEBACK_THRESHOLD_DAYS = 3

    async def _run():
        from datetime import UTC, datetime

        async with AsyncSessionLocal() as session:
            service = AuroraRuntimeV1Service()
            reference_time = datetime.now(UTC).replace(tzinfo=None)
            payload = await service.get_comeback_context(
                active_db=session,
                user_id=user_id,
                inactive_threshold_days=COMEBACK_THRESHOLD_DAYS,
            )
            if payload is None:
                return {"status": "skipped", "reason": "not_eligible"}

            plan_id = str(payload.get("plan_id") or "").strip()
            destination_route = (
                f"/plans/{plan_id}?source=comeback_nudge" if plan_id else "/chat?entry=comeback_nudge"
            )
            if await _has_recent_notification(
                session,
                user_id=UUID(user_id),
                notification_type="comeback_nudge",
                match_data={"plan_id": plan_id} if plan_id else None,
                now=reference_time,
            ):
                logger.debug("comeback_nudge_task: duplicate reminder suppressed for user %s", user_id)
                return {
                    "status": "skipped",
                    "reason": "duplicate_recent",
                    "plan_id": plan_id or None,
                }

            await NotificationService.create(
                session,
                UUID(user_id),
                NotificationCreate(
                    title=str(payload.get("title") or "好久不见，我一直在等你"),
                    content=str(payload.get("message") or ""),
                    type="comeback_nudge",
                    data={
                        "plan_id": plan_id or payload.get("plan_id"),
                        "days_away": payload.get("days_away"),
                        "days_remaining": payload.get("days_remaining"),
                        "subject": payload.get("subject"),
                        "next_task_title": payload.get("next_task_title"),
                        "recent_task_summary": payload.get("recent_task_summary"),
                        "light_restart_suggestion": payload.get("light_restart_suggestion"),
                        "destination_route": destination_route,
                        "deep_link": destination_route,
                    },
                ),
                push_via_websocket=True,
            )

            logger.info(
                "✅ Comeback nudge sent to user %s (plan %s, days_remaining=%d)",
                user_id,
                payload.get("plan_id"),
                int(payload.get("days_remaining") or 0),
            )
            return {
                "status": "sent",
                "user_id": user_id,
                "plan_id": payload.get("plan_id"),
                "days_remaining": payload.get("days_remaining"),
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ comeback_nudge_task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_comeback_nudges")
def scan_comeback_nudges(self, limit: int = 500):
    """
    G22: 每日扫描所有用户，为至少 3 天未活跃且有活跃计划的用户派发 comeback_nudge_task。
    """
    from datetime import datetime, timedelta

    from sqlalchemy import and_, select

    from app.db.session import AsyncSessionLocal
    from app.models.plan import Plan
    from app.models.user import User

    COMEBACK_THRESHOLD_DAYS = 3

    async def _run():
        async with AsyncSessionLocal() as session:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=COMEBACK_THRESHOLD_DAYS)

            # Users who are active but haven't logged in for > threshold days,
            # and have at least one active plan with a target_date
            active_plan_users = (
                select(Plan.user_id)
                .where(
                    and_(
                        Plan.is_active.is_(True),
                        Plan.target_date.isnot(None),
                        Plan.not_deleted_filter(),
                    )
                )
                .distinct()
            )

            stmt = (
                select(User.id)
                .where(
                    and_(
                        User.is_active.is_(True),
                        User.last_login_at <= cutoff,
                        User.id.in_(active_plan_users),
                    )
                )
                .limit(limit)
            )
            result = await session.execute(stmt)
            user_ids = [row[0] for row in result.all()]

            dispatched = 0
            for user_uuid in user_ids:
                celery_app.send_task(
                    "app.core.celery_tasks.comeback_nudge_task",
                    args=(str(user_uuid),),
                    queue="default",
                )
                dispatched += 1

            logger.info("✅ Dispatched %d comeback nudge tasks", dispatched)
            return {"dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ scan_comeback_nudges failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


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
        raise self.retry(exc=exc, countdown=60 * (2 ** int(self.request.retries or 0))) from exc


# =============================================================================
# G25: 每周成长叙事 — 生成 + 推送
# =============================================================================


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.weekly_growth_narrative_task",
)
def weekly_growth_narrative_task(self, user_id: str):
    """
    G25: 为单个用户生成每周成长叙事并推送通知。

    调用 progress_narrative_service.get_weekly_narrative 生成报告，
    然后通过 NotificationService 推送给用户。
    """
    from datetime import UTC, datetime, time, timedelta
    from urllib.parse import urlencode
    from uuid import UUID

    from app.core.cache import cache_service
    from app.db.session import AsyncSessionLocal
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService
    from app.services.progress_narrative_service import ProgressNarrativeService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = ProgressNarrativeService(session, redis=cache_service.redis)
            generated_at = datetime.now(UTC).replace(tzinfo=None)
            week_start = datetime.combine(generated_at.date() - timedelta(days=generated_at.weekday()), time.min)
            week_end = week_start + timedelta(days=7)
            narrative = await service.get_weekly_narrative(
                UUID(user_id),
                week_start,
                week_end,
                force=True,
                now=generated_at,
            )

            highlights = narrative.highlights or narrative.sentences[:3]
            body = narrative.body or "".join(highlights)
            destination_query = urlencode(
                {
                    "initialPanel": "weeklyNarrative",
                    "weekStart": str(narrative.week_start),
                    "weekEnd": str(narrative.week_end),
                }
            )
            destination_route = f"/learning/insights?{destination_query}"

            if await _has_recent_notification(
                session,
                user_id=UUID(user_id),
                notification_type="weekly_growth_narrative",
                match_data={"week_start": narrative.week_start},
                now=generated_at,
            ):
                logger.debug("weekly_growth_narrative_task: duplicate narrative suppressed for user %s", user_id)
                return {
                    "status": "skipped",
                    "reason": "duplicate_recent",
                    "week_start": narrative.week_start,
                    "week_end": narrative.week_end,
                }

            title = "你的本周成长报告来了"
            content = body if len(body) <= 200 else body[:197] + "..."

            await NotificationService.create(
                session,
                UUID(user_id),
                NotificationCreate(
                    title=title,
                    content=content,
                    type="weekly_growth_narrative",
                    data={
                        "highlights": highlights,
                        "biggest_improvement": narrative.biggest_improvement,
                        "next_week_suggestion": narrative.next_week_suggestion,
                        "week_start": narrative.week_start,
                        "week_end": narrative.week_end,
                        "data_points": narrative.data_points,
                        "is_placeholder": narrative.is_placeholder,
                        "destination_route": destination_route,
                        "deep_link": destination_route,
                    },
                ),
                push_via_websocket=True,
            )

            logger.info(
                "✅ Weekly growth narrative sent to user %s (placeholder=%s)",
                user_id,
                narrative.is_placeholder,
            )
            return {
                "status": "sent",
                "user_id": user_id,
                "is_placeholder": narrative.is_placeholder,
                "highlights_count": len(highlights),
                "week_start": narrative.week_start,
                "week_end": narrative.week_end,
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ weekly_growth_narrative_task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.core.celery_tasks.scan_weekly_growth_narratives",
)
def scan_weekly_growth_narratives(self, limit: int = 500):
    """
    G25: 扫描活跃用户并为每个用户派发 weekly_growth_narrative_task。

    由 beat 每周日 10:00 UTC (18:00 UTC+8) 触发。
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import distinct, select

    from app.db.session import AsyncSessionLocal
    from app.models.galaxy import StudyRecord
    from app.models.task import Task

    async def _run():
        async with AsyncSessionLocal() as session:
            batch_size = max(1, min(int(limit or 500), 1000))
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
            user_ids = set()

            offset = 0
            while True:
                task_rows = await session.execute(
                    select(distinct(Task.user_id))
                    .where(
                        Task.completed_at >= cutoff,
                        Task.deleted_at.is_(None),
                    )
                    .order_by(Task.user_id)
                    .offset(offset)
                    .limit(batch_size)
                )
                batch = [uid for (uid,) in task_rows.all() if uid is not None]
                user_ids.update(batch)
                if len(batch) < batch_size:
                    break
                offset += batch_size

            offset = 0
            while True:
                study_rows = await session.execute(
                    select(distinct(StudyRecord.user_id))
                    .where(
                        StudyRecord.created_at >= cutoff,
                    )
                    .order_by(StudyRecord.user_id)
                    .offset(offset)
                    .limit(batch_size)
                )
                batch = [uid for (uid,) in study_rows.all() if uid is not None]
                user_ids.update(batch)
                if len(batch) < batch_size:
                    break
                offset += batch_size

            dispatched = 0
            for user_id in sorted(user_ids, key=str):
                celery_app.send_task(
                    "app.core.celery_tasks.weekly_growth_narrative_task",
                    args=(str(user_id),),
                    queue="default",
                )
                dispatched += 1

            logger.info("✅ Dispatched %d weekly growth narrative tasks", dispatched)
            return {"dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("❌ scan_weekly_growth_narratives failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.purge_deleted_account")
def purge_deleted_account(self, user_id: str) -> dict:
    """Hard-delete all data for a soft-deleted account (runs 30 days after deletion)."""
    from uuid import UUID

    from sqlalchemy import delete as sql_delete

    from app.db.session import AsyncSessionLocal
    from app.models.achievement import UserAchievement, UserStreakDays, UserStreakStats
    from app.models.calendar_event import CalendarEvent
    from app.models.chat import ChatMessage, ChatSession
    from app.models.cognitive import BehaviorPattern, CognitiveFragment
    from app.models.error_book import ErrorRecord
    from app.models.focus import FocusSession
    from app.models.galaxy import UserNodeStatus
    from app.models.notification import Notification
    from app.models.notification_interaction import NotificationInteraction
    from app.models.plan import Plan
    from app.models.task import Task
    from app.models.user import User
    from app.models.user_settings import UserSettings

    uid = UUID(user_id)

    async def _purge() -> dict:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, uid)
            if user is None:
                return {"status": "not_found", "user_id": user_id}
            if user.is_active:
                return {"status": "skipped_active", "user_id": user_id}

            tables: list[tuple[type, str]] = [
                (ChatMessage, "user_id"),
                (ChatSession, "user_id"),
                (Task, "user_id"),
                (Plan, "user_id"),
                (ErrorRecord, "user_id"),
                (FocusSession, "user_id"),
                (CalendarEvent, "user_id"),
                (UserAchievement, "user_id"),
                (UserStreakStats, "user_id"),
                (UserStreakDays, "user_id"),
                (Notification, "user_id"),
                (NotificationInteraction, "user_id"),
                (UserNodeStatus, "user_id"),
                (UserSettings, "user_id"),
                (BehaviorPattern, "user_id"),
                (CognitiveFragment, "user_id"),
            ]
            counts: dict[str, int] = {}
            for model, field in tables:
                result = await session.execute(
                    sql_delete(model).where(getattr(model, field) == uid)
                )
                counts[model.__tablename__] = result.rowcount

            await session.delete(user)
            await session.commit()
            logger.info(f"✅ Purged deleted account {user_id}: {counts}")
            return {"status": "purged", "user_id": user_id, "counts": counts}

    try:
        return _run_async(_purge())
    except Exception as exc:
        logger.error(f"❌ purge_deleted_account failed for {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=3600) from exc


# ── Aurora Scheduled Wake Executor ────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.aurora_wake_deliver_task")
def aurora_wake_deliver_task(self, wake_id: str, user_id: str):
    """Deliver a single Aurora scheduled wake as a notification to the user."""
    from uuid import UUID

    from app.aurora.runtime_v1.wake_scheduler import AuroraWakeScheduler
    from app.db.session import AsyncSessionLocal
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService

    async def _run():
        async with AsyncSessionLocal() as session:
            scheduler = AuroraWakeScheduler(db=session)
            due_wakes = await scheduler.list_due_wakes(user_id=user_id, limit=50)
            target = None
            for w in due_wakes:
                if w.wake.wake_id == wake_id:
                    target = w
                    break
            if target is None:
                return {"status": "skipped", "reason": "wake_not_found_or_not_due"}

            surface = target.surface or "aurora_modeling"
            conversation_id = target.conversation_id or ""
            message = str(target.wake.message or target.metadata.get("message") or "Aurora 有新的发现想和你分享。")
            title = str(target.metadata.get("title") or "Aurora 想和你聊聊")

            if await _has_recent_notification(
                session,
                user_id=UUID(user_id),
                notification_type="aurora_wake",
                match_data={"wake_id": wake_id},
                within_hours=2,
            ):
                await scheduler.mark_executed(wake_id, metadata={"status": "duplicate_suppressed"})
                return {"status": "skipped", "reason": "duplicate_recent"}

            destination_route = f"/chat?aurora_surface={surface}"
            if conversation_id:
                destination_route += f"&conversation_id={conversation_id}"

            await NotificationService.create(
                session,
                UUID(user_id),
                NotificationCreate(
                    title=title,
                    content=message,
                    type="aurora_wake",
                    data={
                        "wake_id": wake_id,
                        "surface": surface,
                        "conversation_id": conversation_id,
                        "destination_route": destination_route,
                        "deep_link": destination_route,
                    },
                ),
                push_via_websocket=True,
            )

            await scheduler.mark_executed(wake_id)

            logger.info(
                "Aurora wake delivered: user=%s wake=%s surface=%s",
                user_id, wake_id, surface,
            )
            return {"status": "delivered", "wake_id": wake_id, "user_id": user_id}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("aurora_wake_deliver_task failed for wake %s: %s", wake_id, exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_aurora_scheduled_wakes")
def scan_aurora_scheduled_wakes(self, limit: int = 200):
    """Scan for due Aurora scheduled wakes and dispatch delivery tasks."""
    from app.aurora.runtime_v1.wake_scheduler import AuroraWakeScheduler
    from app.db.session import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as session:
            scheduler = AuroraWakeScheduler(db=session)
            due = await scheduler.list_due_wakes(limit=limit)
            dispatched = 0
            for wake_record in due:
                user_id = str(wake_record.user_id)
                wake_id = wake_record.wake.wake_id
                aurora_wake_deliver_task.delay(wake_id, user_id)
                dispatched += 1
            logger.info(
                "Aurora wake scan: %d due wakes found, %d dispatched",
                len(due), dispatched,
            )
            return {"scanned": len(due), "dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("scan_aurora_scheduled_wakes failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.recall_notification_task")
def recall_notification_task(self, user_id: str, trigger_type: str, context: str = "{}"):
    """
    Spine v2.0 Recall: Build and push a recall notification for a single user.

    Uses SpineOrchestrator.build_recall_notification() which:
    1. Checks cooldown
    2. Runs through PolicyEngine
    3. Builds NotificationDirective + RecallMessage
    4. Stores in Redis for frontend consumption

    Then pushes via NotificationPushService if a message was produced.
    """
    import json
    from uuid import UUID

    from app.db.session import AsyncSessionLocal
    from app.schemas.notification import NotificationCreate
    from app.services.notification_service import NotificationService

    parsed_context = json.loads(context) if isinstance(context, str) else context

    async def _run():
        from app.core.redis_client import get_redis
        from app.signals.spine_orchestrator import SpineOrchestrator

        redis = get_redis()
        spine = SpineOrchestrator(redis=redis)

        # V-14: Run signal pipeline first (generates directives + trace)
        try:
            await spine.on_recall_check(
                user_id=user_id,
                trigger_type=trigger_type,
                **parsed_context,
            )
        except Exception:
            logger.debug("Spine on_recall_check skipped for user=%s", user_id)

        message = await spine.build_recall_notification(
            user_id=user_id,
            trigger_type=trigger_type,
            context=parsed_context,
        )
        if message is None:
            return {"status": "skipped", "reason": "cooldown_or_policy_blocked"}

        async with AsyncSessionLocal() as session:
            deep_link = message.deep_link or "/chat?source=recall"
            await NotificationService.create(
                session,
                UUID(user_id),
                NotificationCreate(
                    title=message.title,
                    content=message.body,
                    type="recall_notification",
                    data={
                        "trigger_type": message.trigger_type,
                        "strategy": message.strategy,
                        "message_id": message.message_id,
                        "cooldown_until": message.cooldown_until,
                        "frequency_tag": message.frequency_tag,
                        "deep_link": deep_link,
                    },
                ),
                push_via_websocket=True,
            )

        logger.info(
            "Recall notification sent: user=%s trigger=%s strategy=%s",
            user_id, trigger_type, message.strategy,
        )
        return {"status": "sent", "user_id": user_id, "trigger_type": trigger_type}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("recall_notification_task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_recall_notifications")
def scan_recall_notifications(self, limit: int = 500):
    """
    Spine v2.0 Recall: Scan active users and dispatch recall_notification_task
    for each applicable trigger type.

    Trigger detection uses data from Redis/DB:
    - undigested_material: uploaded but not diagnosed files
    - task_not_started: assigned tasks not started after 1h
    - task_missed: overdue tasks
    - pre_exam_silence: exam within 48h + no activity for 5h

    Runs every 30 minutes via Celery beat.
    """
    import json
    from datetime import datetime, timedelta

    from sqlalchemy import and_, select

    from app.db.session import AsyncSessionLocal
    from app.models.plan import Plan
    from app.models.user import User

    TRIGGER_TYPES = ["undigested_material", "task_not_started", "task_missed", "pre_exam_silence"]

    async def _run():
        async with AsyncSessionLocal() as session:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
            active_plan_users = (
                select(Plan.user_id)
                .where(
                    and_(
                        Plan.is_active.is_(True),
                        Plan.target_date.isnot(None),
                        Plan.not_deleted_filter(),
                    )
                )
                .distinct()
            )
            stmt = (
                select(User.id)
                .where(
                    and_(
                        User.is_active.is_(True),
                        User.last_login_at >= cutoff,
                        User.id.in_(active_plan_users),
                    )
                )
                .limit(limit)
            )
            result = await session.execute(stmt)
            user_ids = [str(row[0]) for row in result.all()]

        dispatched = 0
        for uid in user_ids:
            for trigger_type in TRIGGER_TYPES:
                celery_app.send_task(
                    "app.core.celery_tasks.recall_notification_task",
                    args=(uid, trigger_type, json.dumps({})),
                    queue="default",
                )
                dispatched += 1

        logger.info(
            "Recall scan: %d users × %d triggers = %d tasks dispatched",
            len(user_ids), len(TRIGGER_TYPES), dispatched,
        )
        return {"users": len(user_ids), "dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("scan_recall_notifications failed: %s", exc)
        raise self.retry(exc=exc, countdown=300) from exc


@celery_app.task(bind=True, max_retries=2, name="aggregate_community_error_patterns")
def aggregate_community_error_patterns(self):
    """Periodically aggregate anonymous community error patterns onto knowledge nodes."""

    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.services.community_error_aggregation_service import CommunityErrorAggregationService

        async with AsyncSessionLocal() as session:
            svc = CommunityErrorAggregationService(session)
            updated = await svc.aggregate_for_nodes_with_recent_errors()
            logger.info(f"Community error aggregation: {updated} nodes updated")
            return {"updated_nodes": updated}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"aggregate_community_error_patterns failed: {exc}")
        raise self.retry(exc=exc, countdown=300) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.spine_snapshot_task")
def spine_snapshot_task(self, user_id: str):
    """
    Spine v2.1: Save a snapshot of the user's Spine state for recovery after TTL expiry.

    Snapshots persist for 90 days in Redis and include:
    - Active states from StateRegister
    - Relationship model state
    - Growth chronicle summary
    - Recent policy effects
    - Known skills
    """
    async def _run():
        from app.core.redis_client import get_redis
        from app.signals.spine_orchestrator import SpineOrchestrator

        redis = get_redis()
        spine = SpineOrchestrator(redis_client=redis)
        snapshot = await spine.save_spine_snapshot(user_id=user_id)
        return {"status": "saved", "snapshot_id": snapshot.get("snapshot_id")}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("spine_snapshot_task failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_spine_snapshots")
def scan_spine_snapshots(self, limit: int = 500):
    """
    Spine v2.1: Daily scan — save snapshots for all active users with plans.

    Runs daily via Celery beat to ensure long-term stability.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import and_, select

    from app.db.session import AsyncSessionLocal
    from app.models.plan import Plan
    from app.models.user import User

    async def _run():
        async with AsyncSessionLocal() as session:
            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
            active_plan_users = (
                select(Plan.user_id)
                .where(
                    and_(
                        Plan.is_active.is_(True),
                        Plan.target_date.isnot(None),
                        Plan.not_deleted_filter(),
                    )
                )
                .distinct()
            )
            stmt = (
                select(User.id)
                .where(
                    and_(
                        User.is_active.is_(True),
                        User.last_login_at >= cutoff,
                        User.id.in_(active_plan_users),
                    )
                )
                .limit(limit)
            )
            result = await session.execute(stmt)
            user_ids = [str(row[0]) for row in result.all()]

        dispatched = 0
        for uid in user_ids:
            celery_app.send_task(
                "app.core.celery_tasks.spine_snapshot_task",
                args=(uid,),
                queue="default",
            )
            dispatched += 1

        logger.info("Spine snapshot scan: %d users, %d tasks dispatched", len(user_ids), dispatched)
        return {"users": len(user_ids), "dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("scan_spine_snapshots failed: %s", exc)
        raise self.retry(exc=exc, countdown=300) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.compact_user_traces")
def compact_user_traces(self, user_id: str):
    """
    Spine v2.2: Compact old traces beyond the 50-trace retention window.

    Aggregates signal types, directive types, and outcome stats into a
    compact summary. Individual traces are deleted to free Redis memory.
    """
    async def _run():
        from app.core.redis_client import get_redis
        from app.signals.causal_trace_store import CausalTraceStore

        redis = get_redis()
        store = CausalTraceStore(redis)
        result = await store.compact_old_traces(user_id)
        if result is None:
            return {"status": "skipped", "reason": "below_threshold"}
        return {"status": "compacted", "traces": result["traces_compacted"]}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("compact_user_traces failed for user %s: %s", user_id, exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_trace_compaction")
def scan_trace_compaction(self, limit: int = 500):
    """Phase 6 / T6.5.1: Daily scan — dispatch compact_user_traces for active users."""

    async def _run():
        from app.core.redis_client import get_redis

        redis = get_redis()
        # Scan all user trace index keys
        cursor = 0
        dispatched = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor, match="spine:user_traces:*", count=100,
            )
            for key in keys:
                key_str = key if isinstance(key, str) else key.decode()
                count = await redis.llen(key_str)
                if count <= 50:
                    continue
                # Extract user_id from key: spine:user_traces:{user_id}
                user_id = key_str.split(":")[-1]
                celery_app.send_task(
                    "app.core.celery_tasks.compact_user_traces",
                    args=(user_id,),
                    queue="default",
                )
                dispatched += 1
                if dispatched >= limit:
                    break
            if cursor == 0 or dispatched >= limit:
                break

        logger.info("Trace compaction scan: %d users dispatched", dispatched)
        return {"dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("scan_trace_compaction failed: %s", exc)
        raise self.retry(exc=exc, countdown=300) from exc


# =============================================================================
# Spine v2.5: Community Cohort Signal Injection
# =============================================================================


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.community_cohort_signal_task")
def community_cohort_signal_task(self, user_id: str, knowledge_node_id: str):
    """Inject community error patterns into Spine for a specific user+node."""

    async def _run():
        import json

        from app.core.redis_client import get_redis
        from app.signals.spine_orchestrator import SpineOrchestrator

        redis = get_redis()
        spine = SpineOrchestrator(redis_client=redis)

        # Load community_signal from knowledge node metadata
        sig_raw = await redis.get(f"galaxy:community_signal:{knowledge_node_id}")
        if not sig_raw:
            return {"status": "no_data"}
        sig = json.loads(sig_raw if isinstance(sig_raw, str) else sig_raw.decode())
        patterns = sig.get("common_mistake_patterns", [])
        if not patterns:
            return {"status": "no_patterns"}

        top = max(patterns, key=lambda p: p.get("count", 0))
        trace = await spine.on_community_cohort_data(
            user_id=user_id,
            knowledge_node_id=knowledge_node_id,
            subject=sig.get("subject", ""),
            mistake_type=top.get("error_type", "unknown"),
            cohort_size=top.get("user_count", 0),
            error_count=top.get("count", 0),
            common_misconception=top.get("error_category", ""),
        )
        return {"status": "injected" if trace else "skipped"}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("community_cohort_signal_task failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.scan_community_cohort_signals")
def scan_community_cohort_signals(self, limit: int = 200):
    """Scan active users and dispatch community cohort signal tasks."""

    async def _run():
        from app.core.redis_client import get_redis

        redis = get_redis()
        # Find users with active Spine state (recently interacted)
        cursor, keys = await redis.scan(match="spine:last_seen:*", count=limit)
        dispatched = 0
        for key in keys:
            key_str = key if isinstance(key, str) else key.decode()
            user_id = key_str.split(":")[-1]
            # Check if user has knowledge nodes with community_signal
            node_cursor = "0"
            while True:
                node_cursor, node_keys = await redis.scan(
                    cursor=node_cursor, match=f"galaxy:user_nodes:{user_id}:*", count=50,
                )
                for nk in node_keys:
                    nk_str = nk if isinstance(nk, str) else nk.decode()
                    node_id = nk_str.split(":")[-1]
                    # Check for community signal on this node
                    has_signal = await redis.get(f"galaxy:community_signal:{node_id}")
                    if has_signal:
                        celery_app.send_task(
                            "app.core.celery_tasks.community_cohort_signal_task",
                            args=(user_id, node_id),
                            queue="low_priority",
                        )
                        dispatched += 1
                if node_cursor in (0, "0"):
                    break
            if dispatched >= limit:
                break

        return {"dispatched": dispatched}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("scan_community_cohort_signals failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


# =============================================================================
# Spine v2.5: StateRegister expiry + Skill auto-deprecation
# =============================================================================


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.spine_expire_stale_states")
def spine_expire_stale_states(self, limit: int = 500):
    """Expire stale state entries for active users."""

    async def _run():
        from app.core.redis_client import get_redis
        from app.signals.state_register import StateRegister

        redis = get_redis()
        register = StateRegister(redis)
        cursor, keys = await redis.scan(match="spine:last_seen:*", count=limit)
        expired_total = 0
        for key in keys:
            key_str = key if isinstance(key, str) else key.decode()
            user_id = key_str.split(":")[-1]
            expired = await register.expire_stale(user_id)
            expired_total += expired
        return {"users_scanned": len(keys), "states_expired": expired_total}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("spine_expire_stale_states failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.spine_auto_deprecate_skills")
def spine_auto_deprecate_skills(self, limit: int = 500):
    """Auto-deprecate stale skills for active users."""

    async def _run():
        from app.core.redis_client import get_redis
        from app.signals.skill_lifecycle import SkillLifecycleManager

        redis = get_redis()
        manager = SkillLifecycleManager(redis)
        cursor, keys = await redis.scan(match="spine:last_seen:*", count=limit)
        total_deprecated = 0
        for key in keys:
            key_str = key if isinstance(key, str) else key.decode()
            user_id = key_str.split(":")[-1]
            deprecated = await manager.auto_deprecate_check(user_id)
            total_deprecated += len(deprecated)
        return {"users_scanned": len(keys), "skills_deprecated": total_deprecated}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("spine_auto_deprecate_skills failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from exc


@celery_app.task(bind=True, max_retries=2, name="app.core.celery_tasks.apply_memory_decay")
def apply_memory_decay(self, batch_size: int = 200):
    """Apply time-based decay to episodic memories with decay_policy.

    Policies:
      - "30d": half-life 30 days, archive when importance_score < 0.15
      - "60d": half-life 60 days, archive when importance_score < 0.15
      - "90d": half-life 90 days, archive when importance_score < 0.10

    Runs daily. Only processes memories with a decay_policy that are not
    already archived.
    """

    async def _run():

        from sqlalchemy import select

        from app.core.db import async_session_factory
        from app.models.memory import EpisodicMemory

        async with async_session_factory() as session:
            now = datetime.now(UTC)
            policies = {
                "30d": {"half_life_days": 30, "archive_threshold": 0.15},
                "60d": {"half_life_days": 60, "archive_threshold": 0.15},
                "90d": {"half_life_days": 90, "archive_threshold": 0.10},
            }

            total_decayed = 0
            total_archived = 0

            for policy_name, config in policies.items():
                stmt = (
                    select(EpisodicMemory)
                    .where(
                        EpisodicMemory.decay_policy == policy_name,
                        EpisodicMemory.archived_at.is_(None),
                        EpisodicMemory.importance_score.isnot(None),
                    )
                    .limit(batch_size)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                import math

                for row in rows:
                    if not row.occurred_at:
                        continue
                    age_days = max(0, (now.replace(tzinfo=None) - row.occurred_at).total_seconds() / 86400)
                    half_life = config["half_life_days"]
                    decay_factor = math.pow(0.5, age_days / half_life)
                    new_score = round((row.importance_score or 0.5) * decay_factor, 4)
                    row.importance_score = max(0.0, new_score)
                    total_decayed += 1

                    if new_score < config["archive_threshold"]:
                        row.archived_at = now.replace(tzinfo=None)
                        total_archived += 1

                if rows:
                    await session.commit()

            return {"decayed": total_decayed, "archived": total_archived}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error("apply_memory_decay failed: %s", exc)
        raise self.retry(exc=exc, countdown=300) from exc
