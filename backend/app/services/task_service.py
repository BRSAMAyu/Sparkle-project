"""
Task Service
Handle task business logic
"""
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from loguru import logger

from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.task import TaskListQuery
from app.core.cache import cache_service
from app.services.personalization import get_personalization_engine


class TaskService:
    @staticmethod
    async def get_by_id(
        db: AsyncSession, task_id: UUID, user_id: UUID
    ) -> Optional[Task]:
        """Get task by ID and verify user ownership"""
        query = select(Task).where(
            and_(Task.id == task_id, Task.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession, obj_in: TaskCreate, user_id: UUID
    ) -> Task:
        """Create new task"""
        estimated_minutes = obj_in.estimated_minutes
        difficulty = obj_in.difficulty

        if estimated_minutes is None or difficulty is None:
            try:
                engine = get_personalization_engine(db, cache_service.redis)
                profile = await engine.get_task_plan_profile(user_id)
                if estimated_minutes is None:
                    estimated_minutes = profile.preferred_task_duration
                if difficulty is None:
                    difficulty = TaskService._difficulty_from_gradient(profile.difficulty_gradient)
            except Exception:
                if estimated_minutes is None:
                    estimated_minutes = 25
                if difficulty is None:
                    difficulty = 1

        db_obj = Task(
            user_id=user_id,
            plan_id=obj_in.plan_id,
            title=obj_in.title,
            type=obj_in.type,
            tags=obj_in.tags,
            estimated_minutes=estimated_minutes,
            difficulty=difficulty,
            energy_cost=obj_in.energy_cost,
            guide_content=obj_in.guide_content,
            priority=obj_in.priority,
            due_date=obj_in.due_date,
            knowledge_node_id=obj_in.knowledge_node_id,
            tool_result_id=obj_in.tool_result_id,
            status=TaskStatus.PENDING,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def update(
        db: AsyncSession, db_obj: Task, obj_in: TaskUpdate
    ) -> Task:
        """Update task"""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def start(db: AsyncSession, db_obj: Task) -> Task:
        """Start task"""
        db_obj.status = TaskStatus.IN_PROGRESS
        db_obj.started_at = datetime.utcnow()
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def complete(
        db: AsyncSession, db_obj: Task, actual_minutes: int, note: Optional[str] = None
    ) -> Task:
        """Complete task and update plan progress if task belongs to a plan"""
        db_obj.status = TaskStatus.COMPLETED
        db_obj.completed_at = datetime.utcnow()
        db_obj.actual_minutes = actual_minutes
        if note:
            db_obj.user_note = note

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # P0.2: Auto-update plan progress when task is completed
        if db_obj.plan_id:
            from app.services.plan_service import PlanService
            await PlanService.update_progress(db, db_obj.plan_id, db_obj.user_id)

        if db_obj.knowledge_node_id:
            from app.services.galaxy_service import GalaxyService

            study_minutes = actual_minutes or db_obj.estimated_minutes or 15
            galaxy_service = GalaxyService(db)
            try:
                await galaxy_service.spark_node(
                    user_id=db_obj.user_id,
                    node_id=db_obj.knowledge_node_id,
                    study_minutes=study_minutes,
                    task_id=db_obj.id,
                    trigger_expansion=True,
                )
            except Exception as exc:
                logger.warning("Failed to spark node for task {}: {}", db_obj.id, exc)

        return db_obj

    @staticmethod
    def _difficulty_from_gradient(gradient: float) -> int:
        if gradient is None:
            return 1
        try:
            mapped = round(1 + max(0.0, min(1.0, gradient)) * 4)
        except Exception:
            return 1
        return max(1, min(5, int(mapped)))

    @staticmethod
    async def abandon(
        db: AsyncSession, db_obj: Task, reason: Optional[str] = None
    ) -> Task:
        """Abandon task"""
        db_obj.status = TaskStatus.ABANDONED
        db_obj.completed_at = datetime.utcnow() # using completed_at for end time
        if reason:
            db_obj.user_note = f"Abandoned: {reason}"
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def confirm_tasks_by_tool_result(
        db: AsyncSession, tool_result_id: str, user_id: UUID
    ) -> List[Task]:
        """
        Confirm all tasks associated with a specific tool_result_id.
        Changes status from PENDING to IN_PROGRESS.
        """
        query = select(Task).where(
            and_(
                Task.tool_result_id == tool_result_id,
                Task.user_id == user_id,
                Task.status == TaskStatus.PENDING
            )
        )
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        if not tasks:
            return []

        current_time = datetime.utcnow()
        for task in tasks:
            task.status = TaskStatus.IN_PROGRESS
            task.confirmed_at = current_time
            db.add(task)
            
        await db.commit()
        # Refresh all tasks to get updated fields
        for task in tasks:
            await db.refresh(task)
            
        return list(tasks)

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        user_id: UUID,
        query_params: TaskListQuery
    ) -> Tuple[List[Task], int]:
        """Get tasks with filtering and pagination"""
        query = select(Task).where(Task.user_id == user_id)
        
        # Apply filters
        if query_params.status:
            query = query.where(Task.status == query_params.status)
        if query_params.type:
            query = query.where(Task.type == query_params.type)
        if query_params.plan_id:
            query = query.where(Task.plan_id == query_params.plan_id)
        
        # Count total (before pagination)
        # Note: simplistic count
        # For better performance on large tables, consider separate count query
        
        # Apply sorting (default by created_at desc)
        query = query.order_by(desc(Task.created_at))
        
        # Apply pagination
        offset = (query_params.page - 1) * query_params.page_size
        query = query.offset(offset).limit(query_params.page_size)
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        return tasks, len(tasks) # This count is wrong for total pages, but for now simple return
