from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.services.galaxy.graph_structure_service import GraphStructureEvolutionService


class GraphEvolutionService:
    """Applies lightweight learning-behavior signals back into Galaxy."""

    WEAK_SIGNAL_TAG = "signal:weak_at"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.structure = GraphStructureEvolutionService(db)

    async def handle_task_completed(self, event: dict) -> None:
        task_id = event.get("task_id")
        user_id = event.get("user_id")
        if not task_id or not user_id:
            return

        task = await self.db.get(Task, UUID(str(task_id)))
        if not task or not task.knowledge_node_id:
            return

        minutes = int(event.get("actual_minutes") or task.actual_minutes or task.estimated_minutes or 0)
        await self.structure.record_engagement(user_id=UUID(str(user_id)), node_id=task.knowledge_node_id, minutes=minutes)
        await self.structure.adjust_neighbor_relation_strengths(task.knowledge_node_id, delta=0.03)
        await self.structure.tag_node_signal(task.knowledge_node_id, self.WEAK_SIGNAL_TAG, active=False)
        logger.info("Graph evolution reinforced node {} from task {}", task.knowledge_node_id, task_id)

    async def handle_error_created(self, event: dict) -> None:
        linked_node_ids = list(event.get("linked_node_ids") or [])
        for node_id in linked_node_ids:
            try:
                node_uuid = UUID(str(node_id))
            except Exception:
                continue
            await self.structure.adjust_neighbor_relation_strengths(node_uuid, delta=-0.04)
            await self.structure.tag_node_signal(node_uuid, self.WEAK_SIGNAL_TAG, active=True)
        if linked_node_ids:
            logger.info("Graph evolution marked {} linked nodes as weak", len(linked_node_ids))

    async def handle_mastery_updated(self, event: dict) -> None:
        node_id = event.get("node_id")
        if not node_id:
            return
        try:
            node_uuid = UUID(str(node_id))
        except Exception:
            return

        old_mastery = float(event.get("old_mastery") or 0.0)
        new_mastery = float(event.get("new_mastery") or 0.0)
        delta = 0.02 if new_mastery >= old_mastery else -0.02
        await self.structure.adjust_neighbor_relation_strengths(node_uuid, delta=delta)
        if new_mastery >= 60:
            await self.structure.tag_node_signal(node_uuid, self.WEAK_SIGNAL_TAG, active=False)
