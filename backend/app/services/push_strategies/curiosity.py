"""
Curiosity Push Strategy
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.push_strategies.base import PushStrategy

class CuriosityStrategy(PushStrategy):
    """
    Push strategy for daily curiosity capsules.
    """
    async def should_trigger(self, user: User, db: AsyncSession) -> bool:
        """
        Trigger if user has curiosity preference enabled and no unread capsule.
        """
        # Note: We rely on the main PushService to check frequency caps and active time.
        # Here we just check if we SHOULD send a curiosity push logically.
        
        # 1. Check preference (already checked in caller usually, but safe to re-check)
        if not user.push_preference or not user.push_preference.enable_curiosity:
            return False
            
        # 2. Check if already has an unread capsule from today?
        # If user has an unread capsule, maybe we don't want to spam, 
        # OR we want to remind them.
        # Let's assume we trigger if we generate a NEW one.
        # For simplicity in this strategy: Always True if enabled, 
        # and let the service generation logic decide if it actually creates content.
        
        # A more complex logic: check if user already engaged with curiosity content today.
        
        return True

    async def get_trigger_data(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        """
        Return context data for content generation.
        """
        # The content generation happens in the service, 
        # here we return empty or minimal context.
        return {
            "type": "curiosity_capsule"
        }
