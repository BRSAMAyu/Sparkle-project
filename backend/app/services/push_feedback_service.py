"""
推送反馈服务 - 更新 consecutive_ignores
"""
from datetime import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import PushPreference
from app.models.notification import PushHistory
from app.services.personalization.preference_service import PreferenceService
from app.core.cache import cache_service


class PushFeedbackService:
    """推送反馈服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_push_interaction(
        self,
        user_id: UUID,
        push_id: UUID,
        interaction_type: str,  # "clicked" | "dismissed" | "ignored"
    ):
        """记录推送交互"""
        await self.db.execute(
            update(PushHistory).where(
                PushHistory.id == push_id
            ).values(
                interaction_type=interaction_type,
                status=self._map_status(interaction_type),
                interacted_at=datetime.utcnow(),
            )
        )

        result = await self.db.execute(
            select(PushPreference).where(PushPreference.user_id == user_id)
        )
        push_pref = result.scalar_one_or_none()

        if push_pref:
            if interaction_type == "clicked":
                new_value = 0
            elif interaction_type in ("dismissed", "ignored"):
                new_value = (push_pref.consecutive_ignores or 0) + 1
            else:
                new_value = push_pref.consecutive_ignores or 0

            push_pref.consecutive_ignores = new_value

            pref_service = PreferenceService(self.db, cache_service.redis)
            await pref_service.update_inferred(
                user_id,
                {"consecutive_ignores": new_value},
            )

            await self.db.commit()
            logger.info(
                "Updated consecutive_ignores for user {}: {}",
                user_id,
                new_value,
            )

    @staticmethod
    def _map_status(interaction_type: str) -> str:
        if interaction_type == "clicked":
            return "clicked"
        if interaction_type == "dismissed":
            return "dismissed"
        if interaction_type == "ignored":
            return "dismissed"
        return interaction_type
