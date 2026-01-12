from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
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

    async def handle_nudge_triggered(self, event_data: Dict[str, Any]):
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
            
            # Retrieve user to pass to push_service (required by _send_push signature)
            # Or use a public method if available. 
            # Checking PushService._send_push, it takes (user, trigger_type, content, data)
            # But _send_push is "private".
            # PushService doesn't seem to have a simple "send_message" public method that takes ID.
            # It has process_user_push(user).
            
            # We might need to extend PushService or fetch user here.
            from app.models.user import User
            user = await self.db.get(User, uuid.UUID(user_id))
            if user:
                 # Reusing _send_push for now as it handles history/logging
                 await self.push_service._send_push(
                    user=user,
                    trigger_type="nudge",
                    content=content_dict,
                    data={
                        "type": "nudge",
                        "nudge_type": nudge_type,
                        "notification_id": str(notification.id),
                        **context
                    }
                )
        except Exception as e:
            # Log error but don't fail the transaction
            print(f"Failed to send push notification for nudge: {e}")

# Singleton Instance (if needed globally, but usually instantiated per request/worker)
# nudge_service = NudgeService(db_session)
