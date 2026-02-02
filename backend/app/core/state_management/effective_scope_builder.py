from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .merge_strategy import MergeStrategy
from .plan_scope_provider import PlanScopeProvider
from .user_scope_provider import UserScopeProvider


class EffectiveScopeBuilder:
    """
    Unified builder for constructing the effective execution scope (context).
    """

    def __init__(self, db: AsyncSession, redis=None):
        self.user_provider = UserScopeProvider(db, redis)
        self.plan_provider = PlanScopeProvider(db, redis)

    async def build(
        self,
        user_id: UUID,
        plan_id: UUID | None = None
    ) -> dict[str, Any]:
        """
        Build the effective scope.
        """
        # Parallel fetch could be optimized here
        user_scope = await self.user_provider.get_scope(user_id)

        plan_scope = {}
        if plan_id:
            plan_scope = await self.plan_provider.get_scope(user_id, plan_id)

        return MergeStrategy.merge(user_scope, plan_scope)
