from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


class ToolPreferenceShadowRecorder:
    """L2-side recorder for bounded Stage 14 learner-vs-fallback shadow observations."""

    KEY_PREFIX = "inference_cache:tool_preference_shadow:"
    TTL_SECONDS = 86400 * 7
    MAX_RECORDS = 100

    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    def _key(self, user_id: str) -> str:
        return f"{self.KEY_PREFIX}{user_id}"

    async def record_decision(
        self,
        *,
        user_id: str,
        source_state: str,
        fallback_choice: str | None,
        learner_choice: str | None,
        eventual_outcome: str | None = None,
        timestamp: str | None = None,
        fallback_probability: float | None = None,
        learner_probability: float | None = None,
    ) -> None:
        if not self.redis or not user_id:
            return

        record = {
            "timestamp": timestamp or _utcnow_iso(),
            "user_id": user_id,
            "source_state": source_state,
            "fallback_choice": fallback_choice,
            "learner_choice": learner_choice,
            "eventual_outcome": eventual_outcome,
            "diverged": fallback_choice != learner_choice,
            "fallback_probability": fallback_probability,
            "learner_probability": learner_probability,
        }

        records = await self.get_recent_records(user_id=user_id, limit=self.MAX_RECORDS)
        records.append(record)
        trimmed = records[-self.MAX_RECORDS :]
        await self.redis.setex(self._key(user_id), self.TTL_SECONDS, json.dumps(trimmed))

    async def get_recent_records(self, *, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.redis or not user_id:
            return []

        raw = await self.redis.get(self._key(user_id))
        if not raw:
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if not isinstance(payload, list):
            return []
        return [dict(item) for item in payload[-limit:] if isinstance(item, dict)]

    async def get_divergence_summary(self, *, user_id: str, limit: int = 50) -> dict[str, Any]:
        records = await self.get_recent_records(user_id=user_id, limit=limit)
        total = len(records)
        diverged = sum(1 for record in records if record.get("diverged"))
        return {
            "user_id": user_id,
            "total_records": total,
            "diverged_records": diverged,
            "divergence_rate": (diverged / total) if total else 0.0,
            "latest_record": records[-1] if records else None,
        }
