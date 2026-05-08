"""
TaskEventListener - 任务事件监听器

监听任务相关事件并触发知识星图更新
"""
import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import or_, select

from app.core.event_bus import EventBus
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.task import Task
from app.services.galaxy.feedback_service import GalaxyFeedbackService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TaskEventListener:
    """
    任务事件监听器

    监听任务完成、任务放弃等事件，并触发知识星图的自动更新：
    1. 任务完成 → 更新关联知识节点的掌握度
    2. 错题创建 → 降低关联知识节点的掌握度
    3. 触发知识拓展（如果满足条件）
    """

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "galaxy_listeners"

    def __init__(
        self,
        session_factory: Any,
        event_bus: EventBus,
    ):
        self.session_factory = session_factory
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        """启动事件监听"""
        await self.event_bus.connect()
        self._running = True

        logger.info(f"TaskEventListener started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"task_event_listener-{_utcnow().timestamp()}",
                    callback=self._on_event,
                )
                break
            except Exception as e:
                logger.error(f"TaskEventListener subscribe error: {e}")
                await asyncio.sleep(1)

        logger.info("TaskEventListener subscription established")

    async def _on_event(self, event_data: dict):
        """处理接收到的事件"""
        event_type = event_data.get("event_type")

        try:
            if event_type == "task.completed":
                await self.on_task_completed(event_data)
            elif event_type == "task.abandoned":
                await self.on_task_abandoned(event_data)
            elif event_type == "error_created":
                await self.on_error_created(event_data)

        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}", exc_info=True)

    async def on_task_completed(self, event: dict):
        """
        任务完成事件处理

        流程：
        1. 获取任务关联的知识节点
        2. 使用 GalaxyStatsService.spark_node 正式更新掌握度
        3. 记录反馈
        """
        try:
            task_id = event.get("task_id")
            user_id = event.get("user_id")

            if not task_id or not user_id:
                logger.warning(f"Missing task_id or user_id in task.completed event: {event}")
                return

            task_id = UUID(task_id)
            user_id = UUID(user_id)

            async with self.session_factory() as db:
                related_nodes = await self._get_task_related_nodes(db, task_id)

                if not related_nodes:
                    logger.debug(f"No related nodes found for task {task_id}")
                    return

                logger.info(f"Task {task_id} completed, found {len(related_nodes)} related nodes")

                actual_minutes = event.get("actual_minutes", event.get("estimated_minutes", 15))

                from app.services.galaxy.stats_service import GalaxyStatsService
                stats_service = GalaxyStatsService(db)

                for node_id in related_nodes:
                    try:
                        result = await stats_service.spark_node(
                            user_id=user_id,
                            node_id=node_id,
                            study_minutes=actual_minutes,
                            task_id=task_id,
                            trigger_expansion=True,
                        )

                        logger.debug(
                            f"Updated node {node_id} mastery: "
                            f"{result.spark_event.old_mastery} → {result.spark_event.new_mastery}"
                        )

                    except Exception as e:
                        logger.error(f"Failed to update node {node_id} after task completion: {e}")

                logger.info(
                    f"Processed task.completed for task {task_id}, "
                    f"updated {len(related_nodes)} nodes for user {user_id}"
                )

        except Exception as e:
            logger.error(f"Failed to handle task.completed: {e}", exc_info=True)

    async def on_task_abandoned(self, event: dict):
        """
        任务放弃事件处理

        任务放弃会轻微降低关联节点的掌握度
        """
        try:
            task_id = event.get("task_id")
            user_id = event.get("user_id")
            time_spent = event.get("time_spent", 0)

            if not task_id or not user_id:
                return

            task_id = UUID(task_id)
            user_id = UUID(user_id)

            async with self.session_factory() as db:
                related_nodes = await self._get_task_related_nodes(db, task_id)

                if not related_nodes:
                    return

                feedback_service = GalaxyFeedbackService(db)

                for node_id in related_nodes:
                    if time_spent and time_spent >= 10:
                        await feedback_service.collect_implicit_feedback({
                            "type": "task_abandoned",
                            "user_id": user_id,
                            "node_id": node_id,
                            "task_id": task_id,
                            "time_spent": time_spent,
                        })

                logger.info(
                    f"Processed task.abandoned for task {task_id}, "
                    f"updated {len(related_nodes)} nodes"
                )

        except Exception as e:
            logger.error(f"Failed to handle task.abandoned: {e}")

    async def on_error_created(self, event: dict):
        """
        错题创建事件处理

        流程：
        1. 获取错题关联的知识节点
        2. 收集负向反馈
        3. 更新掌握度
        """
        try:
            error_id = event.get("error_id")
            user_id = event.get("user_id")
            linked_node_ids = event.get("linked_node_ids", [])

            if not error_id or not user_id:
                return

            user_id = UUID(user_id)

            async with self.session_factory() as db:
                if not linked_node_ids:
                    linked_node_ids = await self._get_error_related_nodes(db, UUID(error_id))

                if not linked_node_ids:
                    logger.debug(f"No related nodes found for error {error_id}")
                    return

                feedback_service = GalaxyFeedbackService(db)

                for node_id_str in linked_node_ids:
                    try:
                        node_id = UUID(node_id_str)
                        await feedback_service.collect_implicit_feedback({
                            "type": "error_created",
                            "user_id": user_id,
                            "node_id": node_id,
                            "error_id": error_id,
                        })

                        logger.debug(f"Applied negative feedback to node {node_id} due to error {error_id}")

                    except Exception as e:
                        logger.error(f"Failed to apply feedback for node {node_id_str}: {e}")

                logger.info(
                    f"Processed error.created for error {error_id}, "
                    f"updated {len(linked_node_ids)} nodes"
                )

        except Exception as e:
            logger.error(f"Failed to handle error_created: {e}")

    async def _get_task_related_nodes(self, db, task_id: UUID) -> list[UUID]:
        """
        获取任务关联的知识节点

        优先级：
        1. 任务直接关联的节点 (knowledge_node_id)
        2. 根据任务标题/描述查找相关节点（关键词匹配）
        """
        related_nodes = []

        try:
            task = await db.get(Task, task_id)
            if task and task.knowledge_node_id:
                related_nodes.append(task.knowledge_node_id)
                return related_nodes

            if task:
                nodes = await self._find_nodes_by_keywords(
                    db, f"{task.title} {task.description or ''}", limit=5
                )
                related_nodes.extend(nodes)

            related_nodes = list(set(related_nodes))

        except Exception as e:
            logger.error(f"Error getting task related nodes: {e}")

        return related_nodes

    async def _get_error_related_nodes(self, db, error_id: UUID) -> list[str]:
        """
        获取错误关联的知识节点

        优先级：
        1. 错误直接关联的节点 (linked_node_ids)
        2. 根据题目内容查找相关节点
        """
        linked_node_ids = []

        try:
            error = await db.get(ErrorRecord, error_id)
            if not error:
                return linked_node_ids

            if hasattr(error, 'linked_node_ids') and error.linked_node_ids:
                if isinstance(error.linked_node_ids, list):
                    linked_node_ids = error.linked_node_ids
                return linked_node_ids

            nodes = await self._find_nodes_by_keywords(
                db,
                f"{error.question_content or ''} {error.subject or ''}",
                limit=3,
            )
            linked_node_ids = [str(n) for n in nodes]

        except Exception as e:
            logger.error(f"Error getting error related nodes: {e}")

        return linked_node_ids

    async def _find_nodes_by_keywords(
        self,
        db,
        text: str,
        limit: int = 5,
    ) -> list[UUID]:
        """
        根据关键词查找知识节点

        使用简单的关键词匹配，完整实现可以使用向量相似度搜索
        """
        if not text or not text.strip():
            return []

        node_ids = []

        try:
            words = [w for w in text.split() if len(w) >= 2]

            if not words:
                return []

            conditions = []
            for word in words[:10]:
                conditions.append(KnowledgeNode.name.ilike(f"%{word}%"))

            if not conditions:
                return []

            query = select(KnowledgeNode.id).where(
                or_(*conditions)
            ).limit(limit)

            result = await db.execute(query)
            node_ids = [row[0] for row in result.all()]

        except Exception as e:
            logger.error(f"Error finding nodes by keywords: {e}")

        return node_ids

    def stop(self):
        """停止监听器"""
        self._running = False
        close_method = getattr(self.event_bus, "close", None)
        if close_method and asyncio.iscoroutinefunction(close_method):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(close_method())
            except RuntimeError:
                pass
        logger.info("TaskEventListener stopped")

    async def shutdown(self):
        """停止监听器并等待事件总线释放资源。"""
        self._running = False
        close_method = getattr(self.event_bus, "close", None)
        if close_method and asyncio.iscoroutinefunction(close_method):
            await close_method()
        logger.info("TaskEventListener shutdown complete")
