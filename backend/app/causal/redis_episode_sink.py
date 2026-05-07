"""Redis-backed EpisodeSink for production persistence of evaluation episodes.

Wires into the module-level EpisodeLogger singleton so that decision
episodes survive process restarts and are available for counterfactual
analysis, research evaluation, and policy calibration.

Key prefix:  causal:episode:{trace_id}
"""

from __future__ import annotations

import json

from app.causal.episode_logger import EpisodeSink, EvaluationEpisode


class RedisEpisodeSink:
    """Persists EvaluationEpisodes to Redis."""

    def __init__(self, redis_client, *, ttl_seconds: int = 90 * 24 * 3600):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _episode_key(trace_id: str) -> str:
        return f"causal:episode:{trace_id}"

    @staticmethod
    def _user_index_key(user_id: str) -> str:
        return f"causal:episodes_user:{user_id}"

    async def write(self, episode: EvaluationEpisode) -> None:
        key = self._episode_key(episode.trace_id)
        payload = json.dumps(episode.to_dict(), ensure_ascii=False)
        await self.redis.setex(key, self.ttl_seconds, payload)
        # Index by user for listing
        user_key = self._user_index_key(episode.user_id)
        await self.redis.lpush(user_key, episode.trace_id)
        await self.redis.ltrim(user_key, 0, 199)  # keep most recent 200
        await self.redis.expire(user_key, self.ttl_seconds)

    async def update_outcome(self, trace_id: str, actual_outcome: float) -> None:
        key = self._episode_key(trace_id)
        raw = await self.redis.get(key)
        if raw is None:
            return
        data = json.loads(raw)
        from datetime import datetime, timezone
        data["actual_outcome"] = actual_outcome
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.redis.setex(key, self.ttl_seconds, json.dumps(data, ensure_ascii=False))

    async def by_trace_id(self, trace_id: str) -> EvaluationEpisode | None:
        key = self._episode_key(trace_id)
        raw = await self.redis.get(key)
        if raw is None:
            return None
        from dataclasses import fields
        data = json.loads(raw)
        # Reconstruct candidate policies
        from app.causal.episode_logger import CandidatePolicy
        candidates = [
            CandidatePolicy(**cp)
            for cp in data.get("candidate_policies", [])
        ]
        return EvaluationEpisode(
            trace_id=data["trace_id"],
            user_id=data["user_id"],
            context_signature=data["context_signature"],
            candidate_policies=candidates,
            selection_reason=data.get("selection_reason", ""),
            selected_policy_id=data.get("selected_policy_id"),
            expected_outcome=data.get("expected_outcome"),
            actual_outcome=data.get("actual_outcome"),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    async def list_for_user(
        self, user_id: str, limit: int = 20
    ) -> list[EvaluationEpisode]:
        user_key = self._user_index_key(user_id)
        trace_ids = await self.redis.lrange(user_key, 0, limit - 1)
        episodes = []
        for tid in trace_ids:
            tid_str = tid if isinstance(tid, str) else tid.decode()
            ep = await self.by_trace_id(tid_str)
            if ep is not None:
                episodes.append(ep)
        return episodes
