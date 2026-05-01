from __future__ import annotations

from app.consumers.journey_consumer_base import JourneyEventConsumerBase, JourneyPayloadSecurityError
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.memory_service import MemoryService


class UserMemorySeedConsumer(JourneyEventConsumerBase):
    GROUP_NAME = "user_memory_seed_consumer"
    EVENT_TYPE = "user.registered"
    CONSUMER_NAME_PREFIX = "memory-seed"
    CONSUMER_LABEL = "UserMemorySeedConsumer"

    async def _process_event(self, event: dict, user_id) -> None:
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if user is None:
                raise JourneyPayloadSecurityError("user_not_found")

            summary = f"用户 {user.nickname or user.username or '新同学'} 完成注册，旅程初始化开始。"
            await MemoryService(db).create_episodic_memory(
                user_id=user_id,
                summary=summary,
                source_type="user_registered",
                source_id=str(event.get("event_type") or self.EVENT_TYPE),
                occurred_at=user.created_at,
                importance_score=0.55,
                tags=["journey", "signup", "stage38"],
                evidence_refs=[
                    {
                        "type": "event",
                        "id": f"user.registered:{user_id}",
                        "schema_version": "event.v1",
                    }
                ],
                embedding=None,
                confidence=0.7,
                emit_system_update=False,
            )
