import json
import re

from loguru import logger


class SuggestionService:
    """
    智能建议服务 (Vision Item 3: Real-time Intent Prediction)

    Responsibilities:
    1. Provide real-time auto-completion/next-step suggestions based on user input.
    2. Combine rule-based heuristics (fast) with AI-based prediction (smart).

    P1 Fix #7: Improved word boundary matching to avoid false positives.
    P2 Fix #11-12: Added caching and personalized suggestions.
    """

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    def __init__(self, redis_client=None):
        self.redis = redis_client

        # Basic heuristic rules
        self.rules = {
            "create": ["Create a new task", "Create a study plan", "Create a new habit"],
            "plan": ["Plan my week", "Plan for exam", "Sprint planning"],
            "review": ["Review today's tasks", "Review weekly progress", "Start flashcard review"],
            "analy": ["Analyze my behavior (Prism)", "Analyze study time"],
            "trans": ["Translate this text", "Translate to Chinese"],
            "spr": ["Start Sprint Mode", "Enter Focus Mode"],
            "b": ["Behavior Report", "Back to Home"]
        }

    async def predict_intent(self, query: str, user_id: str) -> list[dict[str, str]]:
        """
        Predict user intent based on partial input.

        P1 Fix #7: Uses word boundary matching instead of substring matching.
        P2 Fix #11: Results are cached in Redis.
        P2 Fix #12: Includes personalized suggestions based on user history.
        """
        query_lower = query.lower()
        suggestions = []

        # P2 Fix #11: Check cache first
        if self.redis:
            cache_key = f"suggestions:{user_id}:{query_lower}"
            cached = await self.redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except (json.JSONDecodeError, TypeError):
                    pass  # Fall through to generate suggestions

        # 1. Exact/Prefix Match from Rules with word boundary matching
        for key, templates in self.rules.items():
            # P1 Fix #7: Use word boundary matching instead of substring
            # Match whole word or prefix
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, query_lower) or query_lower.startswith(key):
                for t in templates:
                    suggestions.append({
                        "text": t,
                        "type": "command",
                        "confidence": 0.9 if query_lower == key else 0.7
                    })

        # 2. P2 Fix #12: Get personalized suggestions based on user history
        if self.redis:
            personalized = await self._get_personalized_suggestions(user_id, query)
            suggestions.extend(personalized)

        # 3. Context-Aware Suggestions (Placeholder for AI/History)
        # TODO: Fetch recent user context or use a small language model
        if len(query) > 5 and not suggestions:
             suggestions.append({
                 "text": f"Ask about '{query}'",
                 "type": "chat",
                 "confidence": 0.5
             })

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        result = suggestions[:5]

        # P2 Fix #11: Cache results
        if self.redis and result:
            cache_key = f"suggestions:{user_id}:{query_lower}"
            try:
                await self.redis.setex(
                    cache_key,
                    self.CACHE_TTL,
                    json.dumps(result)
                )
            except Exception as e:
                logger.warning(f"Failed to cache suggestions: {e}")

        return result

    async def _get_personalized_suggestions(
        self, user_id: str, query: str
    ) -> list[dict[str, str]]:
        """
        Get personalized suggestions based on user history.

        P2 Fix #12: Returns suggestions from recent query history.
        """
        if not self.redis:
            return []

        try:
            # Get recent queries
            history_key = f"user:{user_id}:recent_queries"
            recent = await self.redis.lrange(history_key, 0, 4)

            suggestions = []
            query_lower = query.lower()
            for past_query in recent:
                if isinstance(past_query, bytes):
                    past_query = past_query.decode('utf-8')
                if past_query and query_lower in past_query.lower():
                    suggestions.append({
                        "text": past_query,
                        "type": "history",
                        "confidence": 0.8
                    })

            # Add current query to history
            await self.redis.lpush(history_key, query)
            await self.redis.ltrim(history_key, 0, 9)

            return suggestions
        except Exception as e:
            logger.warning(f"Failed to get personalized suggestions: {e}")
            return []

suggestion_service = SuggestionService()
