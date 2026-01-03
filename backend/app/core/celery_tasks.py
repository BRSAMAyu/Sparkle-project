"""
Celery 任务模块 - 任务包装器

提供与应用服务的集成,确保任务可以访问应用上下文

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

from app.core.celery_app import celery_app
from loguru import logger


@celery_app.task(bind=True, name="health_check_task")
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
    from app.services.embedding_service import embedding_service
    from app.models.galaxy import KnowledgeNode
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
    from app.core.cache import redis_client
    from loguru import logger
    import json

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
        except Exception as e:
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
    from app.db.session import AsyncSessionLocal
    from app.models.pending_actions import PendingAction
    from loguru import logger

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
        async with AsyncSessionLocal() as session:
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
    from app.db.session import AsyncSessionLocal
    from app.services.galaxy.expansion_service import ExpansionService
    from loguru import logger

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


# =============================================================================
# 任务监控装饰器
# =============================================================================

def monitor_task_execution(task_func):
    """
    任务执行监控装饰器

    自动记录任务执行时间、成功率等指标
    """
    from functools import wraps
    import time

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
