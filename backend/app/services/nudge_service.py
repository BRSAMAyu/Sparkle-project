import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from app.models.notification import Notification
from app.services.push_service import PushService


class NudgeService:
    """
    Nudge Service (Cognitive Nexus Phase 3)

    Responsible for delivering "Just-in-Time" interventions (Nudges) based on
    behavioral patterns detected by the BehaviorPatternService.

    Subscribes to: 'nudge.triggered'
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.push_service = PushService(db)

    async def handle_nudge_triggered(self, event_data: dict[str, Any]):
        """
        Handle 'nudge.triggered' event.
        - Create Notification record
        - Push to mobile (via PushService)
        """
        user_id = event_data.get("user_id")
        nudge_type = event_data.get("type")
        message = event_data.get("message")
        context = event_data.get("context", {})

        if not user_id or not message:
            return

        # 1. Create In-App Notification
        # Using correct column names from Notification model
        notification = Notification(
            user_id=uuid.UUID(user_id),
            title="Sparkle Insight",
            content=message,
            type="system", # Mapped to 'type' column
            data={
                "nudge_type": nudge_type,
                "context": context,
                "priority": "high"
            },
            is_read=False
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # 2. Send Push Notification (Real-time)
        try:
            # Generate push content dict
            content_dict = {
                "title": "Sparkle Insight",
                "body": message
            }

            from app.models.user import User
            from app.services.personalization import get_personalization_engine
            
            user = await self.db.get(User, uuid.UUID(user_id))
            if user:
                 # Get user policy profile
                 engine = get_personalization_engine(self.db, None)
                 policy = await engine.get_push_policy_profile(user.id)
                 
                 # Calling the private _send_push method with the correct signature
                 await self.push_service._send_push(
                    user=user,
                    trigger_type="nudge",
                    content=content_dict,
                    data={
                        "type": "nudge",
                        "nudge_type": nudge_type,
                        "notification_id": str(notification.id),
                        **context
                    },
                    policy=policy
                 )

        except Exception as e:
            logger.error(f"Failed to send push notification for nudge: {e}")

# Singleton Instance (if needed globally, but usually instantiated per request/worker)
# nudge_service = NudgeService(db_session)
