"""
Curiosity Push Strategy
"""
from typing import Dict, Any
import random

from app.models.user import User
from app.services.personalization import PushPolicyProfile
from app.services.push_strategies.strategy import PushStrategy

class CuriosityStrategy(PushStrategy):
    """
    Push strategy for daily curiosity capsules.
    """
    async def should_trigger(self, user: User, policy: PushPolicyProfile) -> bool:
        if policy.curiosity_frequency == "low":
            return False

        frequency_map = {"low": 0.0, "medium": 0.3, "high": 0.6}
        trigger_probability = frequency_map.get(policy.curiosity_frequency, 0.3)

        return random.random() < trigger_probability

    async def get_context_data(self, user: User) -> Dict[str, Any]:
        """
        Return context data for content generation.
        """
        return {"capsule_type": "curiosity"}
