import json
import asyncio
from typing import Dict, Optional
from loguru import logger
from app.learning.bayesian_learner import BayesianLearner, RouteStats

class PersistentBayesianLearner(BayesianLearner):
    """
    Bayesian Learner with Redis persistence.
    """
    def __init__(self, redis_client, user_id: str, ttl: int = 86400 * 7):
        super().__init__()
        self.redis = redis_client
        self.user_id = user_id
        self.ttl = ttl  # 7 days expiration
        self._loaded = False
    
    async def _load_from_redis(self):
        """Lazy load learning history from Redis."""
        if self._loaded:
            return
        
        try:
            data = await self.redis.get(f"learner:{self.user_id}")
            if data:
                loaded_stats = json.loads(data)
                for key, stats_data in loaded_stats.items():
                    self.stats[key] = RouteStats(
                        alpha=stats_data['alpha'],
                        beta=stats_data['beta']
                    )
                logger.info(f"Loaded {len(self.stats)} routes for user {self.user_id}")
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load learner state: {e}")
    
    async def _save_to_redis(self):
        """Persist to Redis."""
        if not self.stats:
            return
        
        try:
            serializable_stats = {
                key: {'alpha': stats.alpha, 'beta': stats.beta}
                for key, stats in self.stats.items()
            }
            
            await self.redis.setex(
                f"learner:{self.user_id}",
                self.ttl,
                json.dumps(serializable_stats)
            )
            logger.debug(f"Saved {len(self.stats)} routes for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save learner state: {e}")
    
    async def update(self, source: str, target: str, success: bool):
        """Override update to auto-persist."""
        await self._load_from_redis()
        await super().update(source, target, success)
        asyncio.create_task(self._save_to_redis())
    
    async def get_probability(self, source: str, target: str) -> float:
        """Get probability (ensuring loaded)."""
        await self._load_from_redis()
        return await super().get_probability(source, target)
    
    async def get_stats(self) -> Dict:
        """Get full stats."""
        await self._load_from_redis()
        return {
            key: {'alpha': stats.alpha, 'beta': stats.beta, 'mean': stats.mean}
            for key, stats in self.stats.items()
        }

async def create_learner(redis_client, user_id: str) -> PersistentBayesianLearner:
    """Factory to create and load learner."""
    learner = PersistentBayesianLearner(redis_client, user_id)
    await learner._load_from_redis()
    return learner
