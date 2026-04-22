from __future__ import annotations

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.system_update_service import SystemUpdateService, build_system_update

from app.consumers.journey_consumer_base import JourneyEventConsumerBase, JourneyPayloadSecurityError


class WelcomeOnboardingConsumer(JourneyEventConsumerBase):
    GROUP_NAME = "welcome_onboarding_consumer"
    EVENT_TYPE = "user.registered"
    CONSUMER_NAME_PREFIX = "welcome"
    CONSUMER_LABEL = "WelcomeOnboardingConsumer"

    async def _process_event(self, event: dict, user_id) -> None:
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if user is None:
                raise JourneyPayloadSecurityError("user_not_found")

        nickname = str((event.get("metadata") or {}).get("nickname") or event.get("username") or "同学").strip()
        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type="welcome_onboarding",
                category="system",
                title="欢迎来到 Sparkle",
                description=f"{nickname}，你的学习旅程已经启动。我会从第一条计划和第一段进展开始持续帮你补齐画像。",
                priority="normal",
                metadata={
                    "consumer": self.CONSUMER_LABEL,
                    "event_type": self.EVENT_TYPE,
                },
            ),
        )
