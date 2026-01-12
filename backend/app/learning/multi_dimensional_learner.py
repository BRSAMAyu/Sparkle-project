from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import json
import asyncio
from loguru import logger

from app.learning.bayesian_learner import BayesianLearner, RouteStats

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
    
    async def update(self, source: str, target: str, metrics: Dict):
        """Update learners based on metrics."""
        await self._load()
        normalized = self._normalize_metrics(metrics)
        
        for dim, value in normalized.items():
            if dim in self.dimensions:
                await self.dimensions[dim].update(source, target, value)
        
        asyncio.create_task(self._save())
        logger.debug(f"Multi-dimension update: {source}->{target}, metrics={metrics}")
    
    async def get_combined_score(self, source: str, target: str, user_pref: Dict = None) -> float:
        """Get weighted score."""
        await self._load()
        weights = user_pref.get('weights', asdict(self.weights)) if user_pref else asdict(self.weights)
        
        score = 0
        for dim, learner in self.dimensions.items():
            prob = await learner.get_probability(source, target)
            weight = weights.get(dim, 0.25)
            score += prob * weight
        
        return score
    
    async def get_dimension_breakdown(self, source: str, target: str) -> Dict:
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
    
    def _normalize_metrics(self, metrics: Dict) -> Dict[str, bool]:
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
            data = {}
            for dim, learner in self.dimensions.items():
                dim_stats = {}
                for key, stats in learner.stats.items():
                    dim_stats[key] = {'alpha': stats.alpha, 'beta': stats.beta}
                data[dim] = {'stats': dim_stats}
            
            # Also save current weights preference
            data['config'] = {'weights': asdict(self.weights)}
            
            await self.redis.setex(
                f"multi_learner:{self.user_id}",
                86400 * 7,
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Failed to save multi-dimensional learner: {e}")
    
    async def _load(self):
        """Load from Redis."""
        if self._loaded:
            return
        
        try:
            data_str = await self.redis.get(f"multi_learner:{self.user_id}")
            if not data_str:
                self._loaded = True
                return
            
            loaded = json.loads(data_str)
            
            for dim, dim_data in loaded.items():
                if dim == 'config':
                    if 'weights' in dim_data:
                        self.weights = DimensionWeights(**dim_data['weights'])
                    continue
                
                if dim in self.dimensions:
                    learner = self.dimensions[dim]
                    stats_data = dim_data.get('stats', {})
                    for key, s in stats_data.items():
                        learner.stats[key] = RouteStats(alpha=s['alpha'], beta=s['beta'])
            
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load multi-dimensional learner: {e}")
