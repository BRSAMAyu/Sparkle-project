import asyncio
import json
from dataclasses import asdict, dataclass
from typing import Any

from loguru import logger

from app.learning.bayesian_learner import BayesianLearner, RouteStats

MULTI_DIMENSIONAL_LEARNER_TTL_SECONDS = 86400 * 7


def build_multi_dimensional_learner_key(user_id: str) -> str:
    return f"multi_learner:{user_id}"


@dataclass
class DimensionWeights:
    """Weights for different dimensions."""
    success: float = 0.4
    latency: float = 0.3
    cost: float = 0.1
    user_satisfaction: float = 0.2

    def validate(self):
        total = sum([self.success, self.latency, self.cost, self.user_satisfaction])
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

class MultiDimensionalLearner:
    """
    Multi-dimensional Bayesian Learner.
    Tracks success, latency, cost, and satisfaction separately.
    """

    def __init__(self, redis_client, user_id: str, weights: DimensionWeights = None):
        self.redis = redis_client
        self.user_id = user_id
        self.weights = weights or DimensionWeights()
        self.weights.validate()

        self.dimensions = {
            'success': BayesianLearner(),
            'latency': BayesianLearner(),
            'cost': BayesianLearner(),
            'user_satisfaction': BayesianLearner()
        }
        self._loaded = False
        self._pending_saves: set[asyncio.Task] = set()

    def _key(self) -> str:
        return build_multi_dimensional_learner_key(self.user_id)

    async def update(self, source: str, target: str, metrics: dict):
        """Update learners based on metrics."""
        await self._load()
        normalized = self._normalize_metrics(metrics)

        for dim, value in normalized.items():
            if dim in self.dimensions:
                await self.dimensions[dim].update(source, target, value)

        self._schedule_save()
        logger.debug(f"Multi-dimension update: {source}->{target}, metrics={metrics}")

    async def get_combined_score(self, source: str, target: str, user_pref: dict = None) -> float:
        """Get weighted score."""
        await self._load()
        weights = user_pref.get('weights', asdict(self.weights)) if user_pref else asdict(self.weights)

        score = 0
        for dim, learner in self.dimensions.items():
            prob = await learner.get_probability(source, target)
            weight = weights.get(dim, 0.25)
            score += prob * weight

        return score

    async def get_dimension_breakdown(self, source: str, target: str) -> dict:
        """Get stats for each dimension."""
        await self._load()
        breakdown = {}
        for dim, learner in self.dimensions.items():
            key = learner._get_key(source, target)
            stats = learner.stats.get(key)
            if stats:
                breakdown[dim] = {
                    'probability': stats.mean,
                    'alpha': stats.alpha,
                    'beta': stats.beta,
                    'attempts': stats.alpha + stats.beta - 2
                }
            else:
                breakdown[dim] = {
                    'probability': 0.5,
                    'alpha': 1,
                    'beta': 1,
                    'attempts': 0
                }
        return breakdown

    def export_state(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for dim, learner in self.dimensions.items():
            dim_stats = {}
            for key, stats in learner.stats.items():
                dim_stats[key] = {"alpha": stats.alpha, "beta": stats.beta}
            data[dim] = {"stats": dim_stats}
        data["config"] = {"weights": asdict(self.weights)}
        return data

    def _normalize_persisted_state(self, state_data: dict[str, Any]) -> dict[str, Any]:
        config = dict(state_data.get("config") or {})
        weights_payload = dict(config.get("weights") or asdict(self.weights))
        normalized_weights = DimensionWeights(**weights_payload)
        normalized_weights.validate()

        normalized: dict[str, Any] = {"config": {"weights": asdict(normalized_weights)}}
        for dim in self.dimensions:
            raw_dim = state_data.get(dim) or {}
            raw_stats = raw_dim.get("stats") if isinstance(raw_dim, dict) else {}
            normalized_stats: dict[str, dict[str, float]] = {}
            for key, stats in (raw_stats or {}).items():
                if not isinstance(stats, dict):
                    continue
                normalized_stats[key] = {
                    "alpha": float(stats.get("alpha", 1.0)),
                    "beta": float(stats.get("beta", 1.0)),
                }
            normalized[dim] = {"stats": normalized_stats}
        return normalized

    def _apply_persisted_state(self, state_data: dict[str, Any]) -> None:
        weights = DimensionWeights(**dict(state_data.get("config", {}).get("weights", {})))
        weights.validate()
        self.weights = weights
        for learner in self.dimensions.values():
            learner.stats.clear()
        for dim in self.dimensions:
            stats_data = dict(state_data.get(dim, {}).get("stats", {}))
            learner = self.dimensions[dim]
            for key, stats in stats_data.items():
                learner.stats[key] = RouteStats(
                    alpha=float(stats["alpha"]),
                    beta=float(stats["beta"]),
                )

    async def save_state(self, state_data: dict[str, Any]) -> None:
        """Persist an explicit payload for background or recovery paths."""
        if not self.redis:
            return
        normalized = self._normalize_persisted_state(state_data)
        await self.redis.setex(
            self._key(),
            MULTI_DIMENSIONAL_LEARNER_TTL_SECONDS,
            json.dumps(normalized),
        )
        self._apply_persisted_state(normalized)
        self._loaded = True

    def _normalize_metrics(self, metrics: dict) -> dict[str, bool]:
        """Normalize metrics to boolean success/fail for Beta distribution."""
        normalized = {}

        if 'success' in metrics:
            normalized['success'] = bool(metrics['success'])

        if 'latency' in metrics:
            # Latency < 1.0s is 'success' (arbitrary threshold, should be configurable)
            latency = metrics['latency']
            normalized['latency'] = latency < 1.0

        if 'cost' in metrics:
            # Low cost is 'success'
            cost = metrics['cost']
            normalized['cost'] = cost < 0.05

        if 'user_satisfaction' in metrics:
            # 5-star scale, >= 4 is 'success'
            satisfaction = metrics.get('user_satisfaction', 0)
            normalized['user_satisfaction'] = satisfaction >= 4

        return normalized

    async def _save(self):
        """Save to Redis."""
        try:
            await self.save_state(self.export_state())
        except Exception as e:
            logger.error(f"Failed to save multi-dimensional learner: {e}")

    async def _load(self):
        """Load from Redis."""
        if self._loaded:
            return

        try:
            if not self.redis:
                self._loaded = True
                return
            data_str = await self.redis.get(self._key())
            if not data_str:
                self._loaded = True
                return

            loaded = self._normalize_persisted_state(json.loads(data_str))
            self._apply_persisted_state(loaded)
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load multi-dimensional learner: {e}")
            self._loaded = True

    def _schedule_save(self):
        """Track async persistence tasks to avoid fire-and-forget leakage."""
        task = asyncio.create_task(self._save())
        self._pending_saves.add(task)
        task.add_done_callback(self._on_save_done)

    def _on_save_done(self, task: asyncio.Task):
        self._pending_saves.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug(f"Multi-dimensional save task cancelled for user {self.user_id}")
        except Exception as e:
            logger.error(f"Multi-dimensional save task failed for user {self.user_id}: {e}")

    async def drain_pending_saves(self):
        """Flush all outstanding save tasks before shutdown."""
        if not self._pending_saves:
            return
        pending = list(self._pending_saves)
        await asyncio.gather(*pending, return_exceptions=True)
