from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import UserNodeStatus


@dataclass
class BKTParams:
    p_init: float = 0.2
    p_transit: float = 0.15
    p_slip: float = 0.1
    p_guess: float = 0.2


class BKTService:
    """
    Bayesian Knowledge Tracing updater.
    """

    def __init__(self, db: AsyncSession, params: Optional[BKTParams] = None):
        self.db = db
        self.params = params or BKTParams()

    def _update_prob(self, p_l: float, correct: bool) -> float:
        p_slip = self.params.p_slip
        p_guess = self.params.p_guess

        if correct:
            numerator = p_l * (1 - p_slip)
            denominator = numerator + (1 - p_l) * p_guess
        else:
            numerator = p_l * p_slip
            denominator = numerator + (1 - p_l) * (1 - p_guess)

        p_l_given_obs = numerator / denominator if denominator > 0 else p_l
        return p_l_given_obs + (1 - p_l_given_obs) * self.params.p_transit

    async def update_mastery(self, user_id: UUID, node_id: UUID, correct: bool) -> Optional[UserNodeStatus]:
        stmt = select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id == node_id
        )
        result = await self.db.execute(stmt)
        status = result.scalar_one_or_none()
        if not status:
            return None

        current = status.bkt_mastery_prob or self.params.p_init
        status.bkt_mastery_prob = self._update_prob(current, correct)
        status.bkt_last_updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(status)
        return status
