from typing import Dict, List, Any
import asyncio
from loguru import logger
import json
from datetime import datetime
import time
# numpy might not be available, use standard math or implement simple stats
try:
    import numpy as np
except ImportError:
    np = None

class AutoOptimizer:
    """Auto-optimization engine for routing parameters."""
    
    def __init__(self, graph_router, learner, redis_client):
        self.graph = graph_router
        self.learner = learner
        self.redis = redis_client
        self.optimization_history = []
    
    async def optimize(self):
        """Execute optimization cycle."""
        logger.info("Starting auto-optimization...")
        
        # 1. Collect metrics
        metrics = await self._collect_metrics()
        
        # 2. Identify opportunities
        opportunities = await self._identify_opportunities(metrics)
        
        # 3. Apply optimizations
        changes = await self._apply_optimizations(opportunities)
        
        # 4. Validate (Mocked for now)
        validation = await self._validate_improvement()
        
        # 5. Record history
        await self._record_optimization(opportunities, changes, validation)
        
        logger.info(f"Auto-optimization complete: {len(changes)} changes applied")
        return {
            'opportunities': opportunities,
            'changes': changes,
            'validation': validation
        }
    
    async def _collect_metrics(self) -> Dict:
        """Collect system metrics."""
        metrics = {
            'routes': {},
            'performance': {},
            'graph': {}
        }
        
        # Route stats
        if hasattr(self.learner, 'get_stats'):
            stats = await self.learner.get_stats()
            # Convert to dict format if needed
            metrics['routes'] = stats
        
        # Graph stats
        if hasattr(self.graph, 'graph'):
            metrics['graph']['node_count'] = self.graph.graph.number_of_nodes()
            metrics['graph']['edge_count'] = self.graph.graph.number_of_edges()
            
        return metrics
    
    async def _identify_opportunities(self, metrics: Dict) -> List[Dict]:
        """Identify optimization opportunities."""
        opportunities = []
        
        # 1. Low probability routes with high attempts (Dead ends?)
        for route, stats in metrics.get('routes', {}).items():
            # PersistentBayesianLearner stats format: {'alpha': x, 'beta': y, 'mean': z}
            attempts = stats.get('alpha', 1) + stats.get('beta', 1) - 2
            mean = stats.get('mean', 0.5)
            
            if attempts > 10 and mean < 0.2:
                opportunities.append({
                    'type': 'route_pruning_candidate',
                    'route': route,
                    'reason': f"Low probability ({mean:.2f}) with {attempts} attempts",
                    'priority': 'medium'
                })
        
        # 2. Unexplored paths (if we could detect them)
        # This requires knowing all potential paths vs explored paths
        
        return opportunities
    
    async def _apply_optimizations(self, opportunities: List[Dict]) -> List[Dict]:
        """Apply optimizations."""
        changes = []
        for opp in opportunities:
            # For now, just log. Real implementation would adjust graph weights or learner params.
            changes.append({
                'action': 'log',
                'target': opp['route'],
                'status': 'simulated'
            })
        return changes
    
    async def _validate_improvement(self) -> Dict:
        return {'status': 'skipped', 'reason': 'not implemented'}
    
    async def _record_optimization(self, opportunities, changes, validation):
        """Record history to Redis."""
        record = {
            'timestamp': datetime.now().isoformat(),
            'opportunities_count': len(opportunities),
            'changes_count': len(changes),
            'changes': changes,
            'validation': validation
        }
        
        self.optimization_history.append(record)
        
        # Persist simple history
        await self.redis.lpush(
            "auto_optimization_history",
            json.dumps(record)
        )
        await self.redis.ltrim("auto_optimization_history", 0, 99)
        
    async def get_optimization_history(self, limit: int = 10):
        """Get history."""
        history = await self.redis.lrange("auto_optimization_history", 0, limit - 1)
        return [json.loads(h) for h in history]

class ScheduledOptimizer:
    """Scheduled Optimizer."""
    
    def __init__(self, optimizer: AutoOptimizer, interval: int = 3600):
        self.optimizer = optimizer
        self.interval = interval
        self.running = False
        self._task = None
    
    async def start(self):
        """Start scheduler."""
        if self.running:
            return
        self.running = True
        logger.info(f"Scheduled optimizer started (interval: {self.interval}s)")
        self._task = asyncio.create_task(self._run_loop())
        
    async def _run_loop(self):
        while self.running:
            try:
                await asyncio.sleep(self.interval)
                if self.running:
                    await self.optimizer.optimize()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled optimization error: {e}")
                await asyncio.sleep(60) # Retry delay
    
    def stop(self):
        """Stop scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("Scheduled optimizer stopped")

class OptimizationService:
    """Service wrapper for optimization."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.optimizer = None
        self.scheduler = None
    
    async def initialize(self, graph_router, learner):
        """Initialize with dependencies."""
        self.optimizer = AutoOptimizer(graph_router, learner, self.redis)
        self.scheduler = ScheduledOptimizer(self.optimizer, interval=3600) # 1 hour
        await self.scheduler.start()
        logger.info("Optimization service initialized")
    
    async def manual_optimize(self):
        if not self.optimizer:
            raise ValueError("Optimizer not initialized")
        return await self.optimizer.optimize()
    
    async def stop(self):
        if self.scheduler:
            self.scheduler.stop()
