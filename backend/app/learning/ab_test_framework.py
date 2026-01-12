from typing import List, Dict, Optional
from datetime import datetime
import json
import asyncio
from loguru import logger
import time

class ABTestFramework:
    """A/B Testing Framework."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def create_experiment(
        self, 
        name: str, 
        variants: List[str], 
        traffic_split: Dict[str, float],
        metrics: List[str] = None
    ) -> str:
        """Create new experiment."""
        exp_id = f"exp:{name}:{datetime.now().strftime('%Y%m%d')}"
        
        config = {
            'name': name,
            'variants': variants,
            'traffic_split': traffic_split,
            'metrics': metrics or ['success_rate', 'latency'],
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'min_sample_size': 100,
            'confidence_level': 0.95
        }
        
        await self.redis.set(exp_id, json.dumps(config))
        logger.info(f"Created experiment {exp_id}")
        return exp_id
    
    async def assign_variant(self, user_id: str, exp_id: str) -> str:
        """Assign user to variant deterministically."""
        config = await self._get_config(exp_id)
        if not config:
            return 'control'
        
        # Deterministic hashing
        hash_val = hash(f"{user_id}:{exp_id}") % 10000
        total = 0
        
        for variant, weight in config['traffic_split'].items():
            total += weight * 100
            if hash_val < total:
                return variant
        
        return 'control'
    
    async def record_outcome(self, exp_id: str, variant: str, user_id: str, metrics: Dict):
        """Record experiment result."""
        config = await self._get_config(exp_id)
        if not config or config['status'] != 'running':
            return
        
        result_key = f"exp_result:{exp_id}:{variant}:{user_id}"
        result_data = {
            **metrics,
            'timestamp': datetime.now().isoformat(),
            'variant': variant
        }
        
        await self.redis.lpush(result_key, json.dumps(result_data))
        await self.redis.expire(result_key, 86400 * 7)
        
        # Update aggregate stats
        await self._update_aggregate_stats(exp_id, variant, metrics)
        
        logger.debug(f"Recorded outcome for {exp_id}:{variant}:{user_id}")
    
    async def get_stats(self, exp_id: str) -> Optional[Dict]:
        """Get experiment stats."""
        config = await self._get_config(exp_id)
        if not config:
            return None
        
        results = {}
        
        for variant in config['variants']:
            agg_key = f"exp_agg:{exp_id}:{variant}"
            data = await self.redis.hgetall(agg_key)
            
            if data:
                count = int(data.get('count', 0))
                if count == 0:
                    continue
                
                success_count = int(data.get('success_count', 0))
                total_latency = float(data.get('total_latency', 0))
                
                success_rate = success_count / count if count > 0 else 0
                avg_latency = total_latency / count if count > 0 else 0
                
                ci = self._calculate_confidence_interval(success_count, count, config['confidence_level'])
                
                results[variant] = {
                    'count': count,
                    'success_rate': success_rate,
                    'avg_latency': avg_latency,
                    'confidence_interval': ci
                }
        
        return results
    
    async def _update_aggregate_stats(self, exp_id: str, variant: str, metrics: Dict):
        """Update aggregate statistics atomically."""
        agg_key = f"exp_agg:{exp_id}:{variant}"
        
        # Simple increment without LUA for simplicity, or assume atomic enough
        success = 1 if metrics.get('success', False) else 0
        latency = metrics.get('latency', 0)
        
        await self.redis.hincrby(agg_key, 'count', 1)
        if success:
            await self.redis.hincrby(agg_key, 'success_count', 1)
        await self.redis.hincrbyfloat(agg_key, 'total_latency', latency)
    
    def _calculate_confidence_interval(self, successes: int, total: int, confidence: float):
        if total == 0:
            return [0, 0]
        
        p = successes / total
        z = 1.96 if confidence == 0.95 else 2.58
        
        se = (p * (1 - p) / total) ** 0.5
        lower = max(0, p - z * se)
        upper = min(1, p + z * se)
        
        return [round(lower, 3), round(upper, 3)]
    
    async def _get_config(self, exp_id: str):
        data = await self.redis.get(exp_id)
        return json.loads(data) if data else None

class ExperimentManager:
    """Manager for running experiments."""
    
    def __init__(self, redis_client):
        self.framework = ABTestFramework(redis_client)
        self.active_experiments = {}
    
    async def register_experiment(self, name: str, variants: List[str], metrics: List[str] = None):
        """Register/Create an experiment."""
        exp_id = await self.framework.create_experiment(name, variants, {'control': 0.5, 'treatment': 0.5}, metrics=metrics)
        self.active_experiments[name] = exp_id
        return exp_id
    
    async def run_experiment(self, exp_name: str, user_id: str, func, *args, **kwargs):
        """Run function under experiment variant."""
        if exp_name not in self.active_experiments:
            raise ValueError(f"Experiment {exp_name} not registered")
        
        exp_id = self.active_experiments[exp_name]
        variant = await self.framework.assign_variant(user_id, exp_id)
        
        start_time = time.time()
        success = False
        try:
            # Inject variant into func or just run different logic based on variant?
            # Here we assume func takes variant as first arg
            result = await func(variant, *args, **kwargs)
            success = True
            return result
        except Exception:
            success = False
            raise
        finally:
            latency = time.time() - start_time
            metrics = {
                'success': success,
                'latency': latency
            }
            await self.framework.record_outcome(exp_id, variant, user_id, metrics)
