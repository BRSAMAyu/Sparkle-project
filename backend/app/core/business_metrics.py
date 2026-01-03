from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from functools import wraps
import time
from typing import List, Dict, Optional, Any

def get_or_create_metric(metric_type, name, documentation, labelnames=(), **kwargs):
    """Safely get or create a prometheus metric."""
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_type(name, documentation, labelnames, **kwargs)

# ========== Routing Metrics ==========
ROUTING_DECISIONS = get_or_create_metric(
    Counter,
    'sparkle_routing_decisions_total',
    'Total routing decisions by method',
    ['source', 'target', 'method']
)

ROUTING_SUCCESS = get_or_create_metric(
    Counter,
    'sparkle_routing_success_total',
    'Successful routing executions',
    ['source', 'target']
)

ROUTING_FAILURE = get_or_create_metric(
    Counter,
    'sparkle_routing_failure_total',
    'Failed routing executions',
    ['source', 'target', 'reason']
)

ROUTING_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_routing_latency_seconds',
    'Routing decision latency',
    ['method']
)

ROUTING_CONFIDENCE = get_or_create_metric(
    Histogram,
    'sparkle_routing_confidence',
    'Routing confidence distribution',
    ['method']
)

# ========== Learning Metrics ==========
LEARNING_UPDATES = get_or_create_metric(
    Counter,
    'sparkle_learning_updates_total',
    'Bayesian learning updates',
    ['source', 'target', 'outcome']
)

PROBABILITY_DISTRIBUTION = get_or_create_metric(
    Gauge,
    'sparkle_route_probability',
    'Current probability of route',
    ['source', 'target']
)

LEARNER_STATE_SIZE = get_or_create_metric(
    Gauge,
    'sparkle_learner_state_size',
    'Number of routes in learner',
    ['user_id']
)

# ========== Collaboration Metrics ==========
COLLABORATION_SUCCESS = get_or_create_metric(
    Counter,
    'sparkle_collaboration_success_total',
    'Successful multi-agent collaborations',
    ['workflow_type', 'agents_used', 'outcome']
)

COLLABORATION_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_collaboration_latency_seconds',
    'Full collaboration workflow latency',
    ['workflow_type']
)

AGENT_INTERACTION_COUNT = get_or_create_metric(
    Counter,
    'sparkle_agent_interactions_total',
    'Number of agent-to-agent interactions',
    ['from_agent', 'to_agent', 'type']
)

# ========== System Health Metrics ==========
ACTIVE_LEARNERS = get_or_create_metric(
    Gauge,
    'sparkle_active_learners_total',
    'Number of active Bayesian learners'
)

ACTIVE_SESSIONS = get_or_create_metric(
    Gauge,
    'sparkle_active_sessions_total',
    'Number of active chat sessions'
)

CACHE_EFFECTIVENESS = get_or_create_metric(
    Counter,
    'sparkle_cache_effectiveness',
    'Cache hit/miss for routing',
    ['cache_type', 'result']
)

GRAPH_COMPLEXITY = get_or_create_metric(
    Gauge,
    'sparkle_graph_complexity',
    'Graph complexity (nodes + edges)',
    ['graph_name']
)

STATE_SIZE = get_or_create_metric(
    Gauge,
    'sparkle_state_size_bytes',
    'Size of the workflow state in bytes',
    ['session_id']
)

# ========== Decorators and Tools ==========
def track_routing_decision(method: str):
    """Routing decision tracking decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            # Try to extract source/target from args or kwargs if possible
            # This is a best-effort extraction depending on signature
            source = kwargs.get('current', 'unknown')
            
            try:
                result = await func(*args, **kwargs)
                latency = time.time() - start_time
                
                target = result if isinstance(result, str) else 'unknown'
                
                # Confidence tracking if available in kwargs
                confidence = kwargs.get('confidence', 0.5)
                
                if result:
                    ROUTING_SUCCESS.labels(source=source, target=target).inc()
                    ROUTING_CONFIDENCE.labels(method=method).observe(confidence)
                
                ROUTING_LATENCY.labels(method=method).observe(latency)
                ROUTING_DECISIONS.labels(source=source, target=target, method=method).inc()
                
                return result
                
            except Exception as e:
                ROUTING_FAILURE.labels(source=source, target='error', reason=str(e)).inc()
                raise
        
        return wrapper
    return decorator

def track_collaboration(workflow_type: str, agents: List[str]):
    """Collaboration process tracking"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                latency = time.time() - start_time
                
                agents_used = ",".join(sorted(agents))
                outcome = "success" if result else "failure"
                
                COLLABORATION_SUCCESS.labels(
                    workflow_type=workflow_type,
                    agents_used=agents_used,
                    outcome=outcome
                ).inc()
                
                COLLABORATION_LATENCY.labels(workflow_type=workflow_type).observe(latency)
                
                return result
                
            except Exception as e:
                COLLABORATION_SUCCESS.labels(
                    workflow_type=workflow_type,
                    agents_used=",".join(sorted(agents)),
                    outcome="error"
                ).inc()
                raise
        
        return wrapper
    return decorator

# ========== Metrics Collector ==========
class BusinessMetricsCollector:
    """Business metrics collector"""
    
    def __init__(self):
        self._cache = {}
    
    def update_route_probability(self, source: str, target: str, probability: float):
        """Update route probability"""
        PROBABILITY_DISTRIBUTION.labels(source=source, target=target).set(probability)
    
    def update_learner_state_size(self, user_id: str, size: int):
        """Update learner state size"""
        LEARNER_STATE_SIZE.labels(user_id=user_id).set(size)
    
    def record_cache_hit(self, cache_type: str, hit: bool):
        """Record cache hit"""
        result = "hit" if hit else "miss"
        CACHE_EFFECTIVENESS.labels(cache_type=cache_type, result=result).inc()
    
    def update_graph_complexity(self, graph_name: str, nodes: int, edges: int):
        """Update graph complexity"""
        GRAPH_COMPLEXITY.labels(graph_name=graph_name).set(nodes + edges)
    
    def record_agent_interaction(self, from_agent: str, to_agent: str, interaction_type: str):
        """Record agent interaction"""
        AGENT_INTERACTION_COUNT.labels(
            from_agent=from_agent,
            to_agent=to_agent,
            type=interaction_type
        ).inc()
    
    def update_state_size(self, session_id: str, state: Any):
        """Update state size"""
        import sys
        # Rough estimation
        size = sys.getsizeof(state.messages) + sys.getsizeof(state.context_data)
        STATE_SIZE.labels(session_id=session_id).set(size)

# Global Instance
metrics_collector = BusinessMetricsCollector()
