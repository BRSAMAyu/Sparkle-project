from __future__ import annotations

from app.consumers.journey_consumer_base import JourneyEventConsumerBase, JourneyPayloadSecurityError
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService


class UserProfileBootstrapConsumer(JourneyEventConsumerBase):
    GROUP_NAME = "user_profile_bootstrap_consumer"
    EVENT_TYPE = "user.registered"
    CONSUMER_NAME_PREFIX = "profile-bootstrap"
    CONSUMER_LABEL = "UserProfileBootstrapConsumer"

    async def _process_event(self, event: dict, user_id) -> None:
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if user is None:
                raise JourneyPayloadSecurityError("user_not_found")

            await PreferenceService(db, self.redis).get_preferences(user_id)
            await ProfileContextService(db, self.redis).get_profile_context(user_id)
