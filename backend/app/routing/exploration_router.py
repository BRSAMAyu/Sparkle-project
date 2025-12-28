import random
from typing import List, Dict, Optional
from loguru import logger
import math

class ExplorationRouter:
    """Exploration-Exploitation Strategy Base"""
    
    def __init__(self, learner, epsilon: float = 0.1, adaptive: bool = True):
        self.learner = learner
        self.epsilon = epsilon
        self.adaptive = adaptive
        self.attempts = {}
    
    async def select_route(self, source: str, targets: List[str], user_id: str = None) -> Optional[str]:
        """Epsilon-Greedy Selection"""
        if not targets:
            return None
        
        current_epsilon = self._get_adaptive_epsilon(user_id) if self.adaptive else self.epsilon
        
        if random.random() < current_epsilon:
            # Exploration
            selected = random.choice(targets)
            logger.debug(f"🔍 Exploration: randomly selected {selected} (ε={current_epsilon:.2f})")
            return selected
        else:
            # Exploitation
            scores = {}
            for target in targets:
                prob = await self.learner.get_probability(source, target)
                scores[target] = prob
            
            selected = max(scores, key=scores.get)
            logger.debug(f"🎯 Exploitation: selected {selected} (score={scores[selected]:.2f})")
            return selected
    
    def _get_adaptive_epsilon(self, user_id: str) -> float:
        """Adaptive epsilon based on user attempts"""
        if not user_id:
            return self.epsilon
        
        attempts = self.attempts.get(user_id, 0)
        self.attempts[user_id] = attempts + 1
        
        decay_rate = 0.99
        base_epsilon = 0.3
        
        epsilon = base_epsilon * (decay_rate ** attempts)
        return max(0.05, epsilon)

class ThompsonSamplingRouter:
    """Thompson Sampling Strategy"""
    
    def __init__(self, learner):
        self.learner = learner
    
    async def select_route(self, source: str, targets: List[str]) -> Optional[str]:
        """Sample from Beta distribution"""
        if not targets:
            return None
        
        samples = {}
        for target in targets:
            # Access stats directly or via method if possible
            # Here we assume learner has stats dict loaded
            # If not, we might need a method on learner to get alpha/beta
            # PersistentBayesianLearner loads stats on demand
            
            # Using get_stats() might be heavy if it returns everything
            # Let's assume we can get it via key
            key = f"{source}->{target}"
            if hasattr(self.learner, 'stats') and key in self.learner.stats:
                stats = self.learner.stats[key]
                sample = random.betavariate(stats.alpha, stats.beta)
                samples[target] = sample
            else:
                # Prior
                samples[target] = random.betavariate(1, 1)
        
        selected = max(samples, key=samples.get)
        logger.debug(f"🎲 Thompson Sampling: selected {selected}")
        return selected

class UCBRouter:
    """Upper Confidence Bound (UCB1) Strategy"""
    
    def __init__(self, learner):
        self.learner = learner
        self.total_attempts = 0
    
    async def select_route(self, source: str, targets: List[str]) -> Optional[str]:
        """UCB1 Selection"""
        if not targets:
            return None
        
        self.total_attempts += 1
        
        scores = {}
        for target in targets:
            key = f"{source}->{target}"
            if hasattr(self.learner, 'stats') and key in self.learner.stats:
                stats = self.learner.stats[key]
                attempts = stats.alpha + stats.beta - 2
                if attempts > 0:
                    mean = stats.mean
                    exploration = math.sqrt(2 * math.log(self.total_attempts) / attempts)
                    scores[target] = mean + exploration
                else:
                    scores[target] = float('inf')
            else:
                scores[target] = float('inf')
        
        selected = max(scores, key=scores.get)
        logger.debug(f"📊 UCB: selected {selected}")
        return selected

class HybridExplorationRouter:
    """Hybrid Strategy Router"""
    
    def __init__(self, learner, user_id: str = None):
        self.learner = learner
        self.user_id = user_id
        
        self.epsilon_greedy = ExplorationRouter(learner, epsilon=0.1, adaptive=True)
        self.thompson = ThompsonSamplingRouter(learner)
        self.ucb = UCBRouter(learner)
    
    async def select_route(self, source: str, targets: List[str], context: Dict = None) -> Optional[str]:
        """Smart strategy selection"""
        if not targets:
            return None
        
        attempts = 0
        if self.user_id:
            # Estimate total attempts for user
            if hasattr(self.learner, 'stats'):
                # This is rough, as stats might be global or per user depending on learner implementation
                # PersistentBayesianLearner is per user_id, so self.learner.stats is relevant
                total = sum(s.alpha + s.beta - 2 for s in self.learner.stats.values())
                attempts = int(total)
        
        if attempts < 10:
            return await self.thompson.select_route(source, targets)
        elif attempts < 50:
            return await self.ucb.select_route(source, targets)
        else:
            return await self.epsilon_greedy.select_route(source, targets, self.user_id)
