from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService

class UserScopeProvider:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.user_service = UserService(db, redis)

    async def get_scope(self, user_id: UUID) -> Dict[str, Any]:
        """Fetch user-level common context"""
        base_context = await self.user_service.get_context(user_id)
        if not base_context:
            return {}
            
        return {
            "profile": base_context.user_context.model_dump() if base_context.user_context else {},
            "preferences": base_context.preferences,
            "analytics_summary": base_context.analytics_summary,
        }
