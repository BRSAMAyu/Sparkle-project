"""
Galaxy 事件消费者 - 处理错题创建事件
"""
import asyncio
from datetime import timezone, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.galaxy import UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.task_resources import TaskKnowledgeLink
from app.orchestration.dual_core_router import AdaptationRecord
from app.services.galaxy_service import GalaxyService
from app.services.galaxy.graph_evolution_service import GraphEvolutionService
from app.services.plan_state_service import PlanStateService
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GalaxyEventConsumer:
    """消费 error.created 事件，更新知识节点掌握度"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "galaxy_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        """启动事件消费循环"""
        await self.event_bus.connect()
        self._running = True

        logger.info(f"GalaxyEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                # 使用 event_bus 的订阅机制
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"galaxy-{_utcnow().timestamp()}",
                    callback=self.handle_event
                )
                break  # subscribe 内部是循环，成功后跳出
            except Exception as e:
                logger.error(f"GalaxyEventConsumer error: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        """处理单个事件"""
        event_type = event.get("event_type")

        if event_type == "error_created":
            await self._handle_error_created(event)
        elif event_type == "galaxy.node.updated":
            await self._handle_node_updated(event)
        elif event_type == "task.completed":
            await self._handle_task_completed(event)
        elif event_type == "node_mastery_updated":
            await self._handle_mastery_updated(event)

    async def _handle_error_created(self, event: dict):
        """处理错题创建事件 - 降低关联节点掌握度"""
        try:
            user_id = event.get("user_id")
            linked_node_ids = event.get("linked_node_ids", [])

            if not user_id or not linked_node_ids:
                return

            async with AsyncSessionLocal() as db:
                galaxy_service = GalaxyService(db)
                await galaxy_service.handle_error_created(event)
                evolution = GraphEvolutionService(db)
                await evolution.handle_error_created(event)

            logger.info(f"Processed error_created for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to handle error_created: {e}")

    async def _handle_node_updated(self, event: dict):
        try:
            user_id = event.get("user_id")
            node_id = event.get("node_id")
            if not user_id or not node_id:
                return

            user_uuid = UUID(str(user_id))
            node_uuid = UUID(str(node_id))
            old_mastery = float(event.get("old_mastery") or 0.0)
            new_mastery = float(event.get("new_mastery") or 0.0)

            async with AsyncSessionLocal() as db:
                plans_result = await db.execute(
                    select(Plan)
                    .join(Task, Task.plan_id == Plan.id)
                    .join(
                        TaskKnowledgeLink,
                        (TaskKnowledgeLink.task_id == Task.id)
                        & (TaskKnowledgeLink.relation_type == "prerequisite")
                        & (TaskKnowledgeLink.is_primary.is_(True)),
                    )
                    .where(
                        Plan.user_id == user_uuid,
                        Plan.is_active.is_(True),
                        Task.status != TaskStatus.COMPLETED,
                        TaskKnowledgeLink.knowledge_node_id == node_uuid,
                    )
                    .distinct()
                )
                active_plans = list(plans_result.scalars().all())
                if not active_plans:
                    return

                state_service = PlanStateService(db)
                for plan in active_plans:
                    readiness_rows = await db.execute(
                        select(TaskKnowledgeLink.knowledge_node_id, Task.title)
                        .join(
                            TaskKnowledgeLink,
                            (TaskKnowledgeLink.task_id == Task.id)
                            & (TaskKnowledgeLink.relation_type == "prerequisite")
                            & (TaskKnowledgeLink.is_primary.is_(True)),
                        )
                        .where(
                            Task.plan_id == plan.id,
                            Task.status != TaskStatus.COMPLETED,
                        )
                    )
                    task_links = readiness_rows.all()
                    if not task_links:
                        continue

                    prerequisite_node_ids = list({row.knowledge_node_id for row in task_links})
                    blocking_titles: list[str] = []
                    readiness_map: dict[str, str] = {}
                    for linked_node_id, task_title in task_links:
                        readiness_map[str(linked_node_id)] = task_title

                    mastery_rows = await db.execute(
                        select(UserNodeStatus.node_id, UserNodeStatus.mastery_score)
                        .where(
                            UserNodeStatus.user_id == user_uuid,
                            UserNodeStatus.node_id.in_(prerequisite_node_ids),
                        )
                    )
                    mastery_map = {str(node): float(score or 0.0) for node, score in mastery_rows.all()}
                    if not mastery_map:
                        continue

                    scores = []
                    for prerequisite_node_id in prerequisite_node_ids:
                        score = mastery_map.get(str(prerequisite_node_id), 0.0)
                        scores.append(score / 100.0)
                        if score < 30.0 and str(prerequisite_node_id) in readiness_map:
                            blocking_titles.append(readiness_map[str(prerequisite_node_id)])
                    readiness_score = round(sum(scores) / len(scores), 2) if scores else 0.0

                    state = await state_service.get_or_create_plan_state(user_uuid, plan.id, for_write=True)
                    facts = dict(state.facts or {})
                    previous = facts.get("knowledge_readiness") or {}
                    previous_score = float(previous.get("score") or 0.0)
                    facts["knowledge_readiness"] = {
                        "score": readiness_score,
                        "updated_at": _utcnow().isoformat(),
                        "blocking_tasks": blocking_titles[:3],
                        "last_updated_node_id": str(node_uuid),
                    }
                    state.facts = facts
                    await db.commit()

                    if previous_score < 0.3 and readiness_score >= 0.5 and blocking_titles:
                        record = AdaptationRecord(
                            what_changed=f"计划「{plan.name}」的知识就绪度从 {previous_score:.2f} 提升到 {readiness_score:.2f}",
                            why=f"你在相关前置知识点上的掌握度提升了（节点 {node_id} 从 {old_mastery:.1f} 到 {new_mastery:.1f}）。",
                            expected_effect=f"现在可以开始「{blocking_titles[0]}」这类原先被知识前置阻塞的任务。",
                            user_facing_message=f"你在相关知识点上的掌握度提升了，现在可以开始「{blocking_titles[0]}」了。",
                            source="galaxy_event_consumer",
                        )
                        await SystemUpdateService().enqueue(
                            user_uuid,
                            build_system_update(
                                update_type="knowledge_readiness_improved",
                                category="evolution",
                                title="知识就绪度提升",
                                description=record.user_facing_message,
                                priority="low",
                                metadata={
                                    "evolution_kind": "adaptation_record",
                                    "adaptation_record": record.to_dict(),
                                },
                            ),
                        )

            logger.info(f"Processed galaxy.node.updated for user {user_id}, node {node_id}")
        except Exception as e:
            logger.error(f"Failed to handle galaxy.node.updated: {e}")

    async def _handle_task_completed(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                evolution = GraphEvolutionService(db)
                await evolution.handle_task_completed(event)
            logger.info("Processed task.completed graph evolution for task {}", event.get("task_id"))
        except Exception as e:
            logger.error(f"Failed to handle task.completed: {e}")

    async def _handle_mastery_updated(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                evolution = GraphEvolutionService(db)
                await evolution.handle_mastery_updated(event)
            logger.info("Processed node_mastery_updated graph evolution for node {}", event.get("node_id"))
        except Exception as e:
            logger.error(f"Failed to handle node_mastery_updated: {e}")

    def stop(self):
        """停止消费者"""
        self._running = False
