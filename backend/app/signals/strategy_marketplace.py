"""
Core: execution
Phase: adapt
Stage: Signal-to-Action Spine P3-4 Strategy Marketplace

Lightweight strategy sharing — effective strategies from one user's learning
can be recommended to others with similar profiles. Rule-based matching only.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

_STRATEGY_KEY = "spine:marketplace:strategy:{strategy_key}"
_INDEX_KEY = "spine:marketplace:index"
_RECOMMENDATIONS_KEY = "spine:marketplace:recs:{user_id}"


class StrategyMarketplace:
    """Share and discover effective strategies across users."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def publish_strategy(
        self,
        strategy_key: str,
        *,
        source_user_id: str,
        effectiveness: float,
        evidence_count: int,
        goal_type: str = "",
        subject: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Publish a proven-effective strategy to the marketplace."""
        entry = {
            "strategy_key": strategy_key,
            "source_user_id": _anonymize_id(source_user_id),
            "effectiveness": round(effectiveness, 3),
            "evidence_count": evidence_count,
            "goal_type": goal_type,
            "subject": subject,
            "metadata": metadata or {},
        }

        key = _STRATEGY_KEY.format(strategy_key=strategy_key)
        await self.redis.set(key, json.dumps(entry), ex=30 * 24 * 3600)

        # Add to index for discovery
        await self.redis.sadd(_INDEX_KEY, strategy_key)
        await self.redis.expire(_INDEX_KEY, 30 * 24 * 3600)

        logger.info(
            "StrategyMarketplace: published key={} eff={:.2f} evidence={}",
            strategy_key, effectiveness, evidence_count,
        )
        return entry

    async def get_strategy(self, strategy_key: str) -> dict[str, Any] | None:
        """Get a specific strategy entry."""
        raw = await self.redis.get(_STRATEGY_KEY.format(strategy_key=strategy_key))
        if not raw:
            return None
        return json.loads(raw)

    async def find_recommendations(
        self,
        *,
        goal_type: str = "",
        subject: str = "",
        min_effectiveness: float = 0.7,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find effective strategies matching given criteria."""
        all_keys = await self.redis.smembers(_INDEX_KEY)
        if not all_keys:
            return []

        decoded_keys = [
            k if isinstance(k, str) else k.decode() for k in all_keys
        ]

        candidates = []
        for sk in decoded_keys:
            entry = await self.get_strategy(sk)
            if not entry:
                continue
            if entry.get("effectiveness", 0) < min_effectiveness:
                continue
            if goal_type and entry.get("goal_type") and entry["goal_type"] != goal_type:
                continue
            if subject and entry.get("subject") and entry["subject"] != subject:
                continue
            candidates.append(entry)

        candidates.sort(key=lambda e: (-e.get("effectiveness", 0), -e.get("evidence_count", 0)))
        return candidates[:limit]

    async def store_recommendations(
        self,
        user_id: str,
        recommendations: list[dict[str, Any]],
    ) -> None:
        """Cache recommendations for a user."""
        await self.redis.set(
            _RECOMMENDATIONS_KEY.format(user_id=user_id),
            json.dumps(recommendations),
            ex=24 * 3600,
        )

    async def get_cached_recommendations(self, user_id: str) -> list[dict[str, Any]]:
        """Get cached recommendations for a user."""
        raw = await self.redis.get(_RECOMMENDATIONS_KEY.format(user_id=user_id))
        if not raw:
            return []
        return json.loads(raw)


def _anonymize_id(user_id: str) -> str:
    """One-way hash for user privacy in marketplace entries."""
    import hashlib
    return hashlib.sha256(user_id.encode()).hexdigest()[:12]
