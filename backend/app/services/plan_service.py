"""
Plan Service
Handle plan business logic
"""
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models.plan import Plan
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
