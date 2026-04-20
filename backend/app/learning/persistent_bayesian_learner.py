import asyncio
import json

from loguru import logger

from app.learning.bayesian_learner import BayesianLearner, RouteStats

PERSISTENT_BAYESIAN_TTL_SECONDS = 86400 * 7
PERSISTENT_BAYESIAN_KEY_PREFIX = "learner:"
LEGACY_PERSISTENT_BAYESIAN_KEY_PREFIX = "bayesian_learner:"


def build_persistent_bayesian_key(user_id: str) -> str:
    return f"{PERSISTENT_BAYESIAN_KEY_PREFIX}{user_id}"


def build_legacy_persistent_bayesian_key(user_id: str) -> str:
    return f"{LEGACY_PERSISTENT_BAYESIAN_KEY_PREFIX}{user_id}"


class PersistentBayesianLearner(BayesianLearner):
    """
    Bayesian Learner with Redis persistence.
    """
    def __init__(self, redis_client, user_id: str, ttl: int = PERSISTENT_BAYESIAN_TTL_SECONDS):
        super().__init__()
        self.redis = redis_client
        self.user_id = user_id
        self.ttl = ttl  # 7 days expiration
        self._loaded = False
        self._pending_saves: set[asyncio.Task] = set()

    def _key(self) -> str:
        return build_persistent_bayesian_key(self.user_id)

    def _legacy_key(self) -> str:
        return build_legacy_persistent_bayesian_key(self.user_id)

    def _serialize_stats(self) -> dict[str, dict[str, float]]:
        return {
            key: {"alpha": stats.alpha, "beta": stats.beta}
            for key, stats in self.stats.items()
        }

    def _load_serialized_stats(self, payload: dict) -> None:
        for key, stats_data in payload.items():
            self.stats[key] = RouteStats(
                alpha=stats_data["alpha"],
                beta=stats_data["beta"],
            )

    async def _load_from_redis(self):
        """Lazy load learning history from Redis."""
        if self._loaded:
            return
        if not self.redis:
            self._loaded = True
            return

        try:
            data = await self.redis.get(self._key())
            loaded_from_legacy = False
            if not data:
                data = await self.redis.get(self._legacy_key())
                loaded_from_legacy = bool(data)
            if data:
                loaded_stats = json.loads(data)
                self._load_serialized_stats(loaded_stats)
                if loaded_from_legacy:
                    await self.redis.setex(
                        self._key(),
                        self.ttl,
                        json.dumps(self._serialize_stats()),
                    )
                logger.info(f"Loaded {len(self.stats)} routes for user {self.user_id}")
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load learner state: {e}")
            self._loaded = True

    async def _save_to_redis(self):
        """Persist to Redis."""
        if not self.stats or not self.redis:
            return

        try:
            await self.redis.setex(
                self._key(),
                self.ttl,
                json.dumps(self._serialize_stats())
            )
            logger.debug(f"Saved {len(self.stats)} routes for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save learner state: {e}")

    async def update(self, source: str, target: str, success: bool):
        """Override update to auto-persist."""
        await self._load_from_redis()
        await super().update(source, target, success)
        self._schedule_save()

    async def get_probability(self, source: str, target: str) -> float:
        """Get probability (ensuring loaded)."""
        await self._load_from_redis()
        return await super().get_probability(source, target)

    async def get_stats(self) -> dict:
        """Get full stats."""
        await self._load_from_redis()
        return {
            key: {'alpha': stats.alpha, 'beta': stats.beta, 'mean': stats.mean}
            for key, stats in self.stats.items()
        }

    def _schedule_save(self):
        """Track async persistence tasks to avoid fire-and-forget leakage."""
        task = asyncio.create_task(self._save_to_redis())
        self._pending_saves.add(task)
        task.add_done_callback(self._on_save_done)

    def _on_save_done(self, task: asyncio.Task):
        self._pending_saves.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug(f"Learner save task cancelled for user {self.user_id}")
        except Exception as e:
            logger.error(f"Learner save task failed for user {self.user_id}: {e}")

    async def drain_pending_saves(self):
        """Flush all outstanding save tasks before shutdown."""
        if not self._pending_saves:
            return
        pending = list(self._pending_saves)
        await asyncio.gather(*pending, return_exceptions=True)

async def create_learner(redis_client, user_id: str) -> PersistentBayesianLearner:
    """Factory to create and load learner."""
    learner = PersistentBayesianLearner(redis_client, user_id)
    await learner._load_from_redis()
    return learner
