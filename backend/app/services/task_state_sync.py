"""
TaskStateSync - 任务状态同步服务

Synchronizes task events with PlanState's task_index.
Listens to task create/update/complete events and updates the plan's state.

Usage:
    from app.services.task_state_sync import TaskStateSyncService

    sync_service = TaskStateSyncService(db, redis)
    await sync_service.on_task_created(task)
    await sync_service.on_task_completed(task, actual_minutes)
    await sync_service.on_task_updated(task)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.task_resources import TaskResourceLink, TaskKnowledgeLink
from app.services.plan_state_service import PlanStateService
from app.services.milestone_handler import MilestoneHandler


class TaskStateSyncService:
    """
    Synchronizes task events with PlanState.

    Responsibilities:
    1. Update task_index on task create/update/complete
    2. Maintain lightweight task summaries in plan state
    3. Trigger milestone checks on significant events
    """

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
    ) -> None:
        self.db = db
        self.redis = redis
        self._plan_state_service = PlanStateService(db, redis)
        self._milestone_handler = MilestoneHandler(db)

    async def on_task_created(
        self,
        task: Task,
    ) -> None:
        """
        Handle task creation event.

        Updates plan state's task_index with new task count.

        Args:
            task: The newly created task
        """
        if not task.plan_id:
            logger.debug(f"Task {task.id} has no plan_id, skipping sync")
            return

        try:
            await self._plan_state_service.on_task_created(
                user_id=task.user_id,
                plan_id=task.plan_id,
                task_type=task.type.value if task.type else "UNKNOWN",
            )
            # Also sync task summaries after creation
            await self.sync_task_summaries(task.user_id, task.plan_id)
            logger.info(
                f"Synced task creation: task_id={task.id}, plan_id={task.plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to sync task creation: {e}")

    async def on_task_completed(
        self,
        task: Task,
        actual_minutes: Optional[int] = None,
    ) -> None:
        """
        Handle task completion event.

        Updates plan state's task_index with completion stats.

        Args:
            task: The completed task
            actual_minutes: Actual time spent on task
        """
        if not task.plan_id:
            logger.debug(f"Task {task.id} has no plan_id, skipping sync")
            return

        try:
            state, new_milestones = await self._plan_state_service.on_task_completed(
                user_id=task.user_id,
                plan_id=task.plan_id,
                task_id=task.id,
                task_type=task.type.value if task.type else "UNKNOWN",
                actual_minutes=actual_minutes or task.actual_minutes,
            )
            # Also sync task summaries after completion
            await self.sync_task_summaries(task.user_id, task.plan_id)

            # Handle milestones if any
            if new_milestones and state:
                pending_count = await self._count_pending_tasks(task.plan_id)
                plan_context = state.to_dict()
                
                for milestone in new_milestones:
                    await self._milestone_handler.on_milestone_achieved(
                        user_id=task.user_id,
                        plan_id=task.plan_id,
                        milestone=milestone,
                        pending_task_count=pending_count,
                        current_plan_context=plan_context
                    )

            logger.info(
                f"Synced task completion: task_id={task.id}, plan_id={task.plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to sync task completion: {e}")

    async def _count_pending_tasks(self, plan_id: UUID) -> int:
        """Count pending and in-progress tasks for a plan."""
        result = await self.db.execute(
            select(func.count()).select_from(Task).where(
                Task.plan_id == plan_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
            )
        )
        return result.scalar() or 0

    async def on_task_updated(
        self,
        task: Task,
        old_status: Optional[TaskStatus] = None,
    ) -> None:
        """
        Handle task update event.

        Currently handles status changes that affect task_index.

        Args:
            task: The updated task
            old_status: Previous status before update
        """
        if not task.plan_id:
            return

        # If task was completed and is now being re-opened, we might need to adjust
        # For now, we only track completion events
        if task.status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            await self.on_task_completed(task)
        else:
            await self.sync_task_summaries(task.user_id, task.plan_id)

    async def sync_task_summaries(
        self,
        user_id: UUID,
        plan_id: UUID,
        limit: int = 10,
    ) -> None:
        """
        Store recent N task summaries in PlanState.task_summaries.

        This provides a hybrid approach: recent tasks are cached in PlanState
        for quick access, while full task details are still available via DB queries.

        Args:
            user_id: User ID
            plan_id: Plan ID
            limit: Maximum number of recent tasks to store
        """
        try:
            summaries = await self.get_task_summaries(user_id, plan_id, limit)
            await self._plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"task_summaries": summaries},
                bump_version=False,  # Don't bump version for cache update
            )
            logger.debug(
                f"Synced task summaries: plan_id={plan_id}, count={len(summaries)}"
            )
        except Exception as e:
            logger.warning(f"Failed to sync task summaries: {e}")

    async def rebuild_task_index(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> Dict[str, Any]:
        """
        Rebuild task_index from database.

        Useful for data recovery or fixing inconsistencies.

        Args:
            user_id: User ID
            plan_id: Plan ID to rebuild index for

        Returns:
            Rebuilt task_index dictionary
        """
        # Query all tasks for this plan
        result = await self.db.execute(
            select(Task).where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
            )
        )
        tasks = list(result.scalars().all())

        # Build index
        task_index: Dict[str, Any] = {
            "total": len(tasks),
            "completed": 0,
            "by_type": {},
        }

        for task in tasks:
            task_type = task.type.value if task.type else "UNKNOWN"

            # Initialize type stats if needed
            if task_type not in task_index["by_type"]:
                task_index["by_type"][task_type] = {"total": 0, "completed": 0}

            task_index["by_type"][task_type]["total"] += 1

            if task.status == TaskStatus.COMPLETED:
                task_index["completed"] += 1
                task_index["by_type"][task_type]["completed"] += 1

        # Calculate completion rate
        if task_index["total"] > 0:
            task_index["avg_completion_rate"] = round(
                task_index["completed"] / task_index["total"], 3
            )

        # Update plan state with rebuilt index
        await self._plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"task_index": task_index},
            bump_version=True,
        )

        logger.info(
            f"Rebuilt task_index: plan_id={plan_id}, "
            f"total={task_index['total']}, completed={task_index['completed']}"
        )
        return task_index

    async def get_task_summaries(
        self,
        user_id: UUID,
        plan_id: UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get lightweight task summaries for a plan.

        Args:
            user_id: User ID
            plan_id: Plan ID
            limit: Maximum tasks to return

        Returns:
            List of task summary dictionaries
        """
        result = await self.db.execute(
            select(Task)
            .where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        tasks = list(result.scalars().all())

        return [
            {
                "task_id": str(task.id),
                "title": task.title,
                "status": task.status.value if task.status else None,
                "type": task.type.value if task.type else None,
                "priority": task.priority,
                "estimated_minutes": task.estimated_minutes,
                "actual_minutes": task.actual_minutes,
                "difficulty": task.difficulty,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
            for task in tasks
        ]

    async def get_task_detail(
        self,
        user_id: UUID,
        task_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get full task details for LLM consumption.

        Args:
            user_id: User ID
            task_id: Task ID

        Returns:
            Task detail dictionary or None if not found
        """
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.user_id == user_id,
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        detail = {
            "task_id": str(task.id),
            "plan_id": str(task.plan_id) if task.plan_id else None,
            "title": task.title,
            "status": task.status.value if task.status else None,
            "type": task.type.value if task.type else None,
            "tags": task.tags or [],
            "priority": task.priority,
            "difficulty": task.difficulty,
            "energy_cost": task.energy_cost,
            "estimated_minutes": task.estimated_minutes,
            "actual_minutes": task.actual_minutes,
            "guide_content": task.guide_content,
            "user_note": task.user_note,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }

        try:
            from app.models.galaxy import KnowledgeNode
            link_result = await self.db.execute(
                select(TaskKnowledgeLink, KnowledgeNode)
                .join(KnowledgeNode, TaskKnowledgeLink.knowledge_node_id == KnowledgeNode.id)
                .where(TaskKnowledgeLink.task_id == task_id)
                .order_by(TaskKnowledgeLink.order_index.asc())
            )
            link_rows = link_result.all()
            related_nodes = []
            for link, node in link_rows:
                related_nodes.append(
                    {
                        "node_id": str(node.id),
                        "title": node.name,
                        "summary": node.description[:200] if node.description else None,
                        "relation_type": link.relation_type,
                        "strength": link.strength,
                        "is_primary": link.is_primary,
                    }
                )
            detail["related_knowledge_nodes"] = related_nodes
        except Exception:
            detail["related_knowledge_nodes"] = []

        try:
            resource_result = await self.db.execute(
                select(TaskResourceLink)
                .where(TaskResourceLink.task_id == task_id)
                .order_by(TaskResourceLink.order_index.asc())
            )
            resource_links = resource_result.scalars().all()
            detail["learning_resources"] = [
                {
                    "id": str(link.id),
                    "resource_type": link.resource_type,
                    "resource_id": str(link.resource_id) if link.resource_id else None,
                    "title": link.title,
                    "summary": link.summary,
                    "url": link.url,
                    "metadata": link.resource_metadata,
                    "order_index": link.order_index,
                    "is_primary": link.is_primary,
                }
                for link in resource_links
            ]
        except Exception:
            detail["learning_resources"] = []

        return detail
