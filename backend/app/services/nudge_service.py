import uuid
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.services.push_service import PushService


class NudgeService:
    """
    Nudge Service (Cognitive Nexus Phase 3)

    Delivers "Just-in-Time" interventions based on behavioral patterns.
    Respects per-channel delivery strategy from Spine NotificationDirective:
    - push:  in-app notification + mobile push (default)
    - in_app: in-app notification only, no mobile push
    - silent: database record only, no user-visible delivery

    Subscribes to: 'nudge.triggered'
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.push_service = PushService(db)

    async def handle_nudge_triggered(self, event_data: dict[str, Any]):
        user_id = event_data.get("user_id")
        nudge_type = event_data.get("type")
        message = event_data.get("message")
        context = event_data.get("context", {})

        if not user_id or not message:
            return

        # Resolve delivery channel from Spine directive (default: push)
        channel = await self._resolve_channel(user_id)

        # 1. Always create in-app notification (unless fully silent)
        notification = await self._create_in_app_notification(
            user_id, nudge_type, message, context, channel,
        )

        # 2. Mobile push — only when channel == "push"
        if channel == "push" and notification:
            await self._send_mobile_push(
                user_id, nudge_type, message, context, notification,
            )

        logger.info(
            "NudgeService: user={} nudge_type={} channel={} notification_id={}",
            user_id, nudge_type, channel,
            str(notification.id) if notification else "suppressed",
        )

    async def _resolve_channel(self, user_id: str) -> str:
        """Check Spine NotificationDirective for channel policy."""
        try:
            from app.core.cache import cache_service
            if not cache_service.redis:
                return "push"
            from app.signals.spine_orchestrator import SpineOrchestrator
            spine = SpineOrchestrator(cache_service.redis)
            directive = await spine.get_notification_directive(user_id)
            if directive and directive.channel in ("push", "in_app", "silent"):
                return directive.channel
        except Exception:
            logger.debug("Spine channel resolution failed, defaulting to push", exc_info=True)
        return "push"

    async def _create_in_app_notification(
        self,
        user_id: str,
        nudge_type: str | None,
        message: str,
        context: dict,
        channel: str,
    ) -> Notification | None:
        """Create in-app notification. Returns None if channel is silent."""
        if channel == "silent":
            return None

        notification = Notification(
            user_id=uuid.UUID(user_id),
            title="Sparkle Insight",
            content=message,
            type="system",
            data={
                "nudge_type": nudge_type,
                "context": context,
                "priority": "high",
                "delivery_channel": channel,
            },
            is_read=False,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def _send_mobile_push(
        self,
        user_id: str,
        nudge_type: str | None,
        message: str,
        context: dict,
        notification: Notification,
    ):
        """Send mobile push notification via PushService."""
        try:
            spine_directive = None
            try:
                from app.core.cache import cache_service
                if cache_service.redis:
                    from app.signals.spine_orchestrator import SpineOrchestrator
                    spine = SpineOrchestrator(cache_service.redis)
                    spine_directive = await spine.get_notification_directive(user_id)
            except Exception:
                logger.debug("Spine directive fetch for push failed (non-fatal)", exc_info=True)

            if spine_directive:
                content_dict = {
                    "title": "Sparkle",
                    "body": message,
                }
                extra_data = {
                    "spine_trigger": spine_directive.trigger,
                    "message_strategy": spine_directive.message_strategy,
                    "value_reason": context.get("value_reason", ""),
                }
            else:
                content_dict = {
                    "title": "Sparkle Insight",
                    "body": message,
                }
                extra_data = {}

            from app.models.user import User
            from app.services.personalization import get_personalization_engine

            user = await self.db.get(User, uuid.UUID(user_id))
            if user:
                engine = get_personalization_engine(self.db, None)
                policy = await engine.get_push_policy_profile(user.id)

                await self.push_service._send_push(
                    user=user,
                    trigger_type=spine_directive.trigger if spine_directive else "nudge",
                    content=content_dict,
                    data={
                        "type": "nudge",
                        "nudge_type": nudge_type,
                        "notification_id": str(notification.id),
                        **extra_data,
                        **context,
                    },
                    policy=policy,
                )
        except Exception:
            logger.error("Failed to send push notification for nudge", exc_info=True)
