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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.services.plan_state_service import PlanStateService


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
            await self._plan_state_service.on_task_completed(
                user_id=task.user_id,
                plan_id=task.plan_id,
                task_id=task.id,
                task_type=task.type.value if task.type else "UNKNOWN",
                actual_minutes=actual_minutes or task.actual_minutes,
            )
            # Also sync task summaries after completion
            await self.sync_task_summaries(task.user_id, task.plan_id)
            logger.info(
                f"Synced task completion: task_id={task.id}, plan_id={task.plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to sync task completion: {e}")

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

        return {
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
