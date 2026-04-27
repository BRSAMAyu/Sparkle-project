"""
Core: execution
Phase: adapt
Stage: Signal-to-Action Spine P3-3 L4 Async Deep Learning

Triggers background deep analysis when sufficient signals accumulate.
Uses a simple Redis-based task queue (not Celery) for lightweight async work.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


_QUEUE_KEY = "spine:deep_learning_queue"
_SIGNAL_ACCUMULATION_KEY = "spine:deep_learning_accumulation:{user_id}"
_RESULT_KEY = "spine:deep_learning_result:{user_id}"
_MIN_SIGNALS_FOR_TRIGGER = 10
_ACCUMULATION_TTL = 48 * 3600  # 48 hours


class AsyncDeepLearner:
    """Queue and process L4 async deep learning analysis."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def accumulate_signal(
        self,
        user_id: str,
        signal_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Accumulate a signal for potential deep learning analysis.

        Returns {"triggered": bool, "accumulated_count": int}
        """
        key = _SIGNAL_ACCUMULATION_KEY.format(user_id=user_id)
        raw = await self.redis.get(key)
        signals: list[dict] = json.loads(raw) if raw else []

        signals.append(signal_data)
        # Keep only last 50 signals
        signals = signals[-50:]

        await self.redis.set(key, json.dumps(signals), ex=_ACCUMULATION_TTL)

        count = len(signals)
        triggered = False

        if count >= _MIN_SIGNALS_FOR_TRIGGER:
            triggered = await self._check_and_trigger(user_id, signals)

        return {"triggered": triggered, "accumulated_count": count}

    async def _check_and_trigger(
        self,
        user_id: str,
        signals: list[dict],
    ) -> bool:
        """Check if conditions warrant a deep learning analysis trigger."""
        # Don't trigger if there's a pending analysis
        existing = await self.redis.get(_RESULT_KEY.format(user_id=user_id))
        if existing:
            return False

        # Analyze signal patterns
        state_keys = [s.get("state_key", "") for s in signals]
        unique_keys = set(state_keys)

        # Trigger if we have diverse signals (>= 5 unique state keys)
        # or if any single key appears >= 5 times (persistent issue)
        should_trigger = len(unique_keys) >= 5
        if not should_trigger:
            from collections import Counter
            counts = Counter(state_keys)
            if counts and counts.most_common(1)[0][1] >= 5:
                should_trigger = True

        if should_trigger:
            task = {
                "user_id": user_id,
                "signal_count": len(signals),
                "unique_state_keys": list(unique_keys),
                "triggered_at": _utcnow(),
            }
            try:
                await self.redis.rpush(_QUEUE_KEY, json.dumps(task))
            except AttributeError:
                # Fallback for FakeRedis — store as single task
                await self.redis.set(_QUEUE_KEY + ":latest", json.dumps(task))
            logger.info(
                "DeepLearning: triggered for user={} signals={} keys={}",
                user_id, len(signals), len(unique_keys),
            )
            return True

        return False

    async def pop_task(self) -> dict[str, Any] | None:
        """Pop a task from the deep learning queue for processing."""
        try:
            raw = await self.redis.lpop(_QUEUE_KEY)
        except AttributeError:
            # Fallback for FakeRedis
            raw = await self.redis.get(_QUEUE_KEY + ":latest")
            if raw:
                await self.redis.delete(_QUEUE_KEY + ":latest")
        if not raw:
            return None
        return json.loads(raw)

    async def store_result(
        self,
        user_id: str,
        result: dict[str, Any],
    ) -> None:
        """Store a deep learning analysis result."""
        await self.redis.set(
            _RESULT_KEY.format(user_id=user_id),
            json.dumps(result),
            ex=7 * 24 * 3600,  # 7-day retention
        )

    async def get_result(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve the latest deep learning result for a user."""
        raw = await self.redis.get(_RESULT_KEY.format(user_id=user_id))
        if not raw:
            return None
        return json.loads(raw)

    def analyze_signal_patterns(self, signals: list[dict]) -> dict[str, Any]:
        """Pure computation: analyze accumulated signals for patterns.

        This is the core L4 analysis logic — runs synchronously after pop.
        """
        if not signals:
            return {"patterns": [], "recommendations": []}

        state_keys = [s.get("state_key", "") for s in signals]
        from collections import Counter
        key_counts = Counter(state_keys)

        patterns: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []

        # Pattern 1: Persistent issue
        for key, count in key_counts.most_common(5):
            if count >= 5:
                patterns.append({
                    "type": "persistent_issue",
                    "state_key": key,
                    "occurrences": count,
                })
                recommendations.append({
                    "action": "strategy_reassess",
                    "target": key,
                    "reason": f"appeared {count} times without resolution",
                })

        # Pattern 2: Related issues cluster
        related_groups = {
            "execution": {"task_granularity_fit", "execution_consistency", "deadline_pressure"},
            "knowledge": {"knowledge_bottleneck", "knowledge_transfer", "retrieval_risk"},
            "affective": {"affective_pressure", "cognitive_load", "growth_momentum"},
        }
        for group_name, group_keys in related_groups.items():
            group_count = sum(key_counts.get(k, 0) for k in group_keys)
            if group_count >= 3:
                patterns.append({
                    "type": "cluster",
                    "group": group_name,
                    "related_keys": [k for k in group_keys if key_counts.get(k, 0) > 0],
                })

        return {
            "patterns": patterns,
            "recommendations": recommendations,
            "total_signals": len(signals),
            "unique_keys": len(set(state_keys)),
        }


def _utcnow() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
