import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.irt import IRTItemParameter, UserIRTAbility


class IRTService:
    """
    轻量 IRT 更新器 (在线估计)
    """

    def __init__(self, db: AsyncSession, lr: float = 0.05):
        self.db = db
        self.lr = lr

    @staticmethod
    def _prob(theta: float, a: float, b: float, c: float) -> float:
        return c + (1 - c) / (1 + math.exp(-a * (theta - b)))

    async def update_theta(
        self,
        user_id: UUID,
        question_id: UUID,
        correct: bool,
        subject_id: Optional[str] = None
    ) -> Optional[UserIRTAbility]:
        item = await self._get_item_params(question_id, subject_id)
        ability = await self._get_or_create_ability(user_id, subject_id)

        p = self._prob(ability.theta, item.a, item.b, item.c)
        gradient = (1.0 if correct else 0.0) - p
        ability.theta += self.lr * gradient
        ability.last_updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(ability)
        return ability

    async def _get_item_params(self, question_id: UUID, subject_id: Optional[str]) -> IRTItemParameter:
        stmt = select(IRTItemParameter).where(IRTItemParameter.question_id == question_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            return item

        item = IRTItemParameter(
            question_id=question_id,
            subject_id=subject_id,
            a=1.0,
            b=0.0,
            c=0.2
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def _get_or_create_ability(self, user_id: UUID, subject_id: Optional[str]) -> UserIRTAbility:
        stmt = select(UserIRTAbility).where(
            UserIRTAbility.user_id == user_id,
            UserIRTAbility.subject_id == subject_id
        )
        result = await self.db.execute(stmt)
        ability = result.scalar_one_or_none()
        if ability:
            return ability

        ability = UserIRTAbility(
            user_id=user_id,
            subject_id=subject_id,
            theta=0.0
        )
        self.db.add(ability)
        await self.db.commit()
        await self.db.refresh(ability)
        return ability
