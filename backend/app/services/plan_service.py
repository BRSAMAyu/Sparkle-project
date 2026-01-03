"""
Plan Service
Handle plan business logic
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.schemas.plan import PlanCreate, PlanUpdate


class PlanService:
    @staticmethod
    async def get_by_id(
        db: AsyncSession, plan_id: UUID, user_id: UUID
    ) -> Optional[Plan]:
        query = select(Plan).where(
            and_(Plan.id == plan_id, Plan.user_id == user_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession, obj_in: PlanCreate, user_id: UUID
    ) -> Plan:
        db_obj = Plan(
            user_id=user_id,
            name=obj_in.name,
            type=obj_in.type,
            description=obj_in.description,
            subject=obj_in.subject,
            target_date=obj_in.target_date,
            daily_available_minutes=obj_in.daily_available_minutes,
            total_estimated_hours=obj_in.total_estimated_hours,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def update(
        db: AsyncSession, db_obj: Plan, obj_in: PlanUpdate
    ) -> Plan:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def list_active(
        db: AsyncSession, user_id: UUID, limit: int = 5
    ) -> List[Plan]:
        query = (
            select(Plan)
            .where(and_(Plan.user_id == user_id, Plan.is_active == True))
            .order_by(desc(Plan.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_progress(
        db: AsyncSession, plan_id: UUID, user_id: UUID
    ) -> Optional[float]:
        """
        Calculate and update plan progress based on task completion ratio.

        P0.2: Plan Progress Auto-Update
        Called automatically when tasks are completed to keep progress in sync.

        Returns:
            Updated progress value (0.0-1.0), or None if plan not found
        """
        # Verify plan exists and belongs to user
        plan = await PlanService.get_by_id(db, plan_id, user_id)
        if not plan:
            return None

        # Count total tasks for this plan
        total_query = select(func.count(Task.id)).where(Task.plan_id == plan_id)
        total_result = await db.execute(total_query)
        total_tasks = total_result.scalar_one()

        # Count completed tasks
        completed_query = select(func.count(Task.id)).where(
            and_(Task.plan_id == plan_id, Task.status == TaskStatus.COMPLETED)
        )
        completed_result = await db.execute(completed_query)
        completed_tasks = completed_result.scalar_one()

        # Calculate progress ratio
        if total_tasks > 0:
            new_progress = completed_tasks / total_tasks
        else:
            new_progress = 0.0

        # Update plan progress
        plan.progress = new_progress
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        return new_progress
