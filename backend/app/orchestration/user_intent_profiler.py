from __future__ import annotations
"""
User Intent Profiler for Personalized Intent Recognition

Phase 2.2: Learn user's intent patterns for personalized classification.
Target: Up to 30% boost for frequently used intents.

This module provides:
- Track user's historical intent distribution
- Calculate intent weights based on frequency
- Adjust intent scores based on user patterns
- Redis-backed caching with 1-hour TTL
- Automatic profile updates
"""

import json
from datetime import timezone, datetime

from loguru import logger


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserIntentProfiler:
    """User intent profiling for personalized classification

    Tracks each user's intent usage patterns and boosts confidence
    for frequently used intents.

    Algorithm:
        1. Track intent counts in Redis (hash: user:intent:patterns:{user_id})
        2. Calculate weights: weight = count / total_count
        3. Apply boost: adjusted_score = base_score * (1 + weight * 0.3)
        4. Max boost: 30% for most frequently used intent

    Example:
        User "alice" frequently uses "create" (50% of time)
        -> "create" intent gets 15% boost (0.5 * 0.3)
        -> base_score 0.7 becomes 0.805
    """

    # Redis key patterns
    USER_PATTERN_PREFIX = "user:intent:patterns:"

    # Cache TTL (1 hour)
    CACHE_TTL = 3600

    # Intent categories
    INTENT_CATEGORIES = [
        "chat", "create", "update", "delete", "query",
        "learn", "review", "translation", "prism", "sprint"
    ]

    def __init__(self, redis_client):
        """Initialize user intent profiler

        Args:
            redis_client: aioredis Redis client
        """
        self.redis = redis_client

        if not redis_client:
            logger.warning("UserIntentProfiler initialized without Redis (profiling disabled)")

    async def get_user_profile(self, user_id: str) -> dict:
        """Get user's intent profile

        Returns intent distribution and calculated weights.

        Args:
            user_id: User ID

        Returns:
            {
                "user_id": "...",
                "total_count": 150,
                "intents": {
                    "create": {"count": 45, "weight": 0.30, "boost": 1.09},
                    "learn": {"count": 30, "weight": 0.20, "boost": 1.06},
                    ...
                },
                "recent_intents": ["create", "create", "learn", ...],
                "last_updated": "2025-01-27T10:30:00"
            }
        """
        if not self.redis:
            return self._get_default_profile(user_id)

        try:
            key = f"{self.USER_PATTERN_PREFIX}{user_id}"
            raw = await self.redis.get(key)

            if raw:
                profile = json.loads(raw)
                profile = self._calculate_weights(profile)
                return profile
            else:
                # New user: return default profile
                return self._get_default_profile(user_id)

        except Exception as e:
            logger.warning(f"Failed to get user profile: {e}")
            return self._get_default_profile(user_id)

    async def update_profile(
        self,
        user_id: str,
        intent: str,
        metadata: dict = None
    ):
        """Update user's intent profile after classification

        Increments intent count and adds to recent intents list.

        Args:
            user_id: User ID
            intent: Classified intent
            metadata: Optional metadata (timestamp, confidence, etc.)
        """
        if not self.redis:
            return

        try:
            key = f"{self.USER_PATTERN_PREFIX}{user_id}"

            # Get existing profile
            raw = await self.redis.get(key)
            profile = json.loads(raw) if raw else self._get_default_profile(user_id)

            # Update intent count
            if intent in profile["intents"]:
                profile["intents"][intent]["count"] += 1
            else:
                profile["intents"][intent] = {"count": 1}

            profile["total_count"] = profile.get("total_count", 0) + 1

            # Update recent intents (keep last 50)
            recent = profile.get("recent_intents", [])
            recent.insert(0, {
                "intent": intent,
                "timestamp": _utcnow().isoformat(),
                "metadata": metadata or {}
            })

            # Keep only last 50
            profile["recent_intents"] = recent[:50]

            # Update timestamp
            profile["last_updated"] = _utcnow().isoformat()

            # Recalculate weights
            profile = self._calculate_weights(profile)

            # Save to Redis
            await self.redis.setex(
                key,
                self.CACHE_TTL,
                json.dumps(profile)
            )

            logger.debug(f"Updated user profile: {user_id} -> {intent}")

        except Exception as e:
            logger.warning(f"Failed to update user profile: {e}")

    def adjust_intent_scores(
        self,
        scores: dict[str, float],
        user_profile: dict,
        max_boost: float = 0.3
    ) -> dict[str, float]:
        """Adjust intent scores based on user profile

        Boosts frequently used intents by up to 30%.

        Args:
            scores: Base intent scores from classifier
            user_profile: User's intent profile
            max_boost: Maximum boost to apply (0.3 = 30%)

        Returns:
            Adjusted scores with user personalization
        """
        adjusted = scores.copy()
        intent_weights = user_profile.get("intents", {})

        for intent, base_score in scores.items():
            if intent in intent_weights:
                weight_info = intent_weights[intent]
                weight = weight_info.get("weight", 0.0)

                # Calculate boost: up to max_boost
                boost = 1 + (weight * max_boost)

                # Apply boost
                adjusted[intent] = base_score * boost

                logger.debug(f"Profile boost: {intent} {base_score:.2f} -> {adjusted[intent]:.2f} (x{boost:.2f})")

        return adjusted

    def get_top_intents(
        self,
        user_profile: dict,
        top_n: int = 3
    ) -> list[str]:
        """Get user's most frequently used intents

        Args:
            user_profile: User's intent profile
            top_n: Number of top intents to return

        Returns:
            List of intent names (sorted by frequency)
        """
        intents = user_profile.get("intents", {})

        # Sort by count
        sorted_intents = sorted(
            intents.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )

        return [intent for intent, _ in sorted_intents[:top_n]]

    def get_recent_intents(
        self,
        user_profile: dict,
        last_n: int = 5
    ) -> list[str]:
        """Get user's recent intents

        Args:
            user_profile: User's intent profile
            last_n: Number of recent intents to return

        Returns:
            List of recent intent names
        """
        recent = user_profile.get("recent_intents", [])

        # Extract intent names from recent list
        return [item["intent"] for item in recent[:last_n]]

    async def get_user_stats(self, user_id: str) -> dict:
        """Get user's intent statistics

        Args:
            user_id: User ID

        Returns:
            {
                "total_classifications": 150,
                "most_used_intent": "create",
                "intent_diversity": 0.6,
                "last_active": "2025-01-27T10:30:00"
            }
        """
        profile = await self.get_user_profile(user_id)

        total = profile.get("total_count", 0)
        intents = profile.get("intents", {})

        # Calculate diversity (entropy-like measure)
        if total > 0:
            diversity = len([i for i in intents.values() if i.get("count", 0) > 0]) / len(self.INTENT_CATEGORIES)
        else:
            diversity = 0.0

        # Get most used intent
        most_used = max(intents.items(), key=lambda x: x[1].get("count", 0))[0] if intents else "none"

        return {
            "total_classifications": total,
            "most_used_intent": most_used,
            "intent_diversity": diversity,
            "last_active": profile.get("last_updated")
        }

    async def reset_user_profile(self, user_id: str):
        """Reset user's profile (for testing/debugging)

        Args:
            user_id: User ID to reset
        """
        if not self.redis:
            return

        try:
            key = f"{self.USER_PATTERN_PREFIX}{user_id}"
            await self.redis.delete(key)
            logger.info(f"Reset user profile: {user_id}")

        except Exception as e:
            logger.warning(f"Failed to reset user profile: {e}")

    async def get_global_stats(self) -> dict:
        """Get global statistics across all users

        Returns:
            {
                "total_users": 100,
                "total_classifications": 15000,
                "avg_per_user": 150,
                "most_popular_intent": "create"
            }
        """
        if not self.redis:
            return {"enabled": False}

        try:
            # Scan all user pattern keys
            pattern = f"{self.USER_PATTERN_PREFIX}*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if not keys:
                return {
                    "total_users": 0,
                    "total_classifications": 0,
                    "avg_per_user": 0,
                    "most_popular_intent": "none"
                }

            # Aggregate stats
            total_classifications = 0
            intent_counts = dict.fromkeys(self.INTENT_CATEGORIES, 0)

            for key in keys:
                raw = await self.redis.get(key)
                if raw:
                    profile = json.loads(raw)
                    total_classifications += profile.get("total_count", 0)

                    for intent, data in profile.get("intents", {}).items():
                        if intent in intent_counts:
                            intent_counts[intent] += data.get("count", 0)

            # Calculate stats
            total_users = len(keys)
            avg_per_user = total_classifications / total_users if total_users > 0 else 0
            most_popular = max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else "none"

            return {
                "total_users": total_users,
                "total_classifications": total_classifications,
                "avg_per_user": round(avg_per_user, 1),
                "most_popular_intent": most_popular,
                "intent_distribution": intent_counts
            }

        except Exception as e:
            logger.warning(f"Failed to get global stats: {e}")
            return {"error": str(e)}

    def _calculate_weights(self, profile: dict) -> dict:
        """Calculate intent weights and boost factors

        Args:
            profile: User profile (will be modified in-place)

        Returns:
            Updated profile with weights and boosts
        """
        total = profile.get("total_count", 0)

        if total == 0:
            return profile

        intents = profile.get("intents", {})

        for _intent, data in intents.items():
            count = data.get("count", 0)
            weight = count / total

            # Calculate boost factor (max 30%)
            boost = 1 + min(weight * 0.3, 0.3)

            data["weight"] = round(weight, 3)
            data["boost"] = round(boost, 3)

        return profile

    def _get_default_profile(self, user_id: str) -> dict:
        """Get default profile for new user

        Args:
            user_id: User ID

        Returns:
            Default profile structure
        """
        return {
            "user_id": user_id,
            "total_count": 0,
            "intents": {intent: {"count": 0, "weight": 0.0, "boost": 1.0} for intent in self.INTENT_CATEGORIES},
            "recent_intents": [],
            "last_updated": _utcnow().isoformat()
        }


# Singleton instance
_user_profiler = None


def get_user_profiler(redis_client) -> UserIntentProfiler | None:
    """Get singleton user profiler instance

    Args:
        redis_client: Redis client

    Returns:
        UserIntentProfiler instance or None if no Redis
    """
    global _user_profiler

    if redis_client and _user_profiler is None:
        _user_profiler = UserIntentProfiler(redis_client)

    return _user_profiler


async def update_user_intent(
    user_id: str,
    intent: str,
    confidence: float,
    redis_client
):
    """Convenience function to update user intent profile

    Args:
        user_id: User ID
        intent: Classified intent
        confidence: Confidence score
        redis_client: Redis client
    """
    profiler = get_user_profiler(redis_client)
    if profiler:
        await profiler.update_profile(
            user_id,
            intent,
            metadata={"confidence": confidence}
        )
