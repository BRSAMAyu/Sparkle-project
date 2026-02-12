import time
from asyncio import iscoroutinefunction
from functools import wraps

from loguru import logger
from opentelemetry import trace
from prometheus_client import REGISTRY, Counter, Gauge, Histogram


def get_or_create_metric(metric_type, name, documentation, labelnames=(), **kwargs):
    """Safely get or create a prometheus metric."""
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_type(name, documentation, labelnames, **kwargs)

# 1. 基础请求指标
REQUEST_COUNT = get_or_create_metric(
    Counter,
    'sparkle_requests_total',
    'Total number of requests',
    ['module', 'method', 'status']
)

REQUEST_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_request_latency_seconds',
    'Request latency in seconds',
    ['module', 'method']
)

# 2. LLM 与 Token 指标
TOKEN_USAGE = get_or_create_metric(
    Counter,
    'sparkle_tokens_total',
    'Total number of tokens used',
    ['model', 'type']  # Removed user_id to prevent cardinality explosion
)

LLM_CALL_DURATION = get_or_create_metric(
    Histogram,
    'sparkle_llm_call_duration_seconds',
    'LLM call duration in seconds',
    ['model', 'provider']
)

# 3. 缓存指标
CACHE_HIT_COUNT = get_or_create_metric(
    Counter,
    'sparkle_cache_hits_total',
    'Total number of cache hits/misses',
    ['cache_name', 'result']  # result: hit, miss
)

SEMANTIC_CACHE_HIT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_semantic_cache_hit_total',
    'Total semantic cache hits'
)

SEMANTIC_CACHE_MISS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_semantic_cache_miss_total',
    'Total semantic cache misses'
)

SEMANTIC_CACHE_BYPASS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_semantic_cache_bypass_total',
    'Total semantic cache bypasses'
)

# 4. 工具执行指标
TOOL_EXECUTION_COUNT = get_or_create_metric(
    Counter,
    'sparkle_tool_executions_total',
    'Total number of tool executions',
    ['tool_name', 'status']
)

# 5. 系统指标
ACTIVE_SESSIONS = get_or_create_metric(
    Gauge,
    'sparkle_active_sessions_total',
    'Total number of active chat sessions'
)

KNOWLEDGE_NODE_UPDATES = get_or_create_metric(
    Counter,
    'sparkle_knowledge_node_updates_total',
    'Total number of knowledge node updates',
    ['reason']  # Removed user_id
)

RAG_RETRIEVAL_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_rag_retrieval_seconds',
    'RAG retrieval latency',
    ['source', 'stage'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

RETRIEVAL_TIMEOUT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_retrieval_timeout_total',
    'Total retrieval timeouts',
    ['source', 'stage']
)

RETRIEVAL_ERROR_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_retrieval_error_total',
    'Total retrieval errors',
    ['source', 'stage']
)

ACTIVE_WEBSOCKET_CONNECTIONS = get_or_create_metric(
    Gauge,
    'sparkle_websocket_connections',
    'Number of active WebSocket connections'
)

OUTBOX_PENDING_EVENTS = get_or_create_metric(
    Gauge,
    'sparkle_outbox_pending_events',
    'Number of pending events in the outbox table'
)

# 5b. Proto v2 Migration Metrics
PROTO_FIELD_READ_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_proto_field_read_total',
    'Total protocol field reads by source during v1/v2 migration',
    ['service', 'field', 'source']
)

PROTO_DUAL_WRITE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_proto_dual_write_total',
    'Total dual-write operations for legacy compatibility fields',
    ['service', 'field']
)

PROTO_ERROR_CODE_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_proto_error_code_fallback_total',
    'Total error code fallback operations during v1/v2 migration',
    ['service', 'direction']
)

# 6. Response Feedback & Bandit
RESPONSE_FEEDBACK_INGESTED = get_or_create_metric(
    Counter,
    'sparkle_response_feedback_ingested_total',
    'Total response feedback ingested',
    ['feedback_type']  # values: up, down
)

RESPONSE_FEEDBACK_DEDUPE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_response_feedback_dedup_total',
    'Total response feedback deduplicated'
)

PROMPT_BANDIT_UPDATES_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_prompt_bandit_updates_total',
    'Total prompt bandit updates',
    ['workflow_id']
)

PROMPT_BANDIT_STATE_MISSING_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_prompt_bandit_state_missing_total',
    'Total prompt bandit state misses',
    ['workflow_id']
)

FEEDBACK_TO_EFFECT_SECONDS = get_or_create_metric(
    Histogram,
    'sparkle_feedback_to_effect_seconds',
    'Time from feedback ingestion to prompt selection effect',
    ['workflow_id', 'prompt_version'],
    buckets=[60, 300, 900, 1800, 3600, 14400, 86400]
)

# 装饰器：用于测量函数执行时间并记录指标
def track_latency(module, method):
    """Decorator to track function execution latency and record metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            span = trace.get_current_span()
            trace_id = format(span.get_span_context().trace_id, '032x') if span else "n/a"

            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(module=module, method=method, status='success').inc()
                return result
            except Exception as e:
                # Log with TraceID for correlation
                logger.error(f"[TraceID: {trace_id}] Error in {module}.{method}: {e}")
                REQUEST_COUNT.labels(module=module, method=method, status='error').inc()
                raise
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module=module, method=method).observe(latency)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                REQUEST_COUNT.labels(module=module, method=method, status='success').inc()
                return result
            except Exception as e:
                logger.error(f"Error in {module}.{method}: {e}")
                REQUEST_COUNT.labels(module=module, method=method, status='error').inc()
                raise
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module=module, method=method).observe(latency)

        # Return async wrapper if func is async, else sync wrapper
        if iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


# ============ Phase 3: Circuit Breaker & Collaboration Metrics ============

LANGGRAPH_PLANNING_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_langgraph_planning_total',
    'Total number of LangGraph planning operations',
    ['collaboration_mode', 'agents_count']
)

LANGGRAPH_PLANNING_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_langgraph_planning_latency_seconds',
    'LangGraph planning latency in seconds',
    ['collaboration_mode'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

CIRCUIT_BREAKER_TRIPS = get_or_create_metric(
    Counter,
    'sparkle_circuit_breaker_trips_total',
    'Total number of circuit breaker trips',
    ['circuit_name']
)

CIRCUIT_BREAKER_RESETS = get_or_create_metric(
    Counter,
    'sparkle_circuit_breaker_resets_total',
    'Total number of circuit breaker resets',
    ['circuit_name']
)

COLLABORATION_SUCCESS = get_or_create_metric(
    Counter,
    'sparkle_collaboration_total',
    'Total number of collaboration operations',
    ['workflow_type', 'agents_used', 'outcome']
)

COLLABORATION_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_collaboration_latency_seconds',
    'Collaboration latency in seconds',
    ['workflow_type'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

EXPERT_SELECTED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_expert_selected_total',
    'Total expert selections by strategy and source',
    ['expert_id', 'strategy', 'entry_source']
)

EXPERT_INVOKED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_expert_invoked_total',
    'Total expert invocations',
    ['expert_id', 'workflow_id']
)

EXPERT_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_expert_fallback_total',
    'Total expert fallbacks',
    ['reason', 'from_mode']
)

EXPERT_OVERRIDDEN_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_expert_overridden_total',
    'Total explicit expert overrides',
    ['requested_expert', 'used_expert']
)

USER_FEEDBACK_BOUND_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_user_feedback_bound_total',
    'Total feedback events bound to expert routing context',
    ['workflow_id']
)

# ============ Strategy Optimization Metrics ============

ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_adaptive_routing_adjustments_total',
    'Adaptive routing adjustments by trigger and mode change',
    ['action', 'trigger', 'from_mode', 'to_mode']
)

ROUTING_SUMMARY_CONTEXT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_routing_summary_context_total',
    'Summary context usage in routing',
    ['phase']
)

RESPONSE_FALLBACK_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_response_fallback_generated_total',
    'Fallback responses generated to avoid empty output',
    ['source']
)

# ============ Phase 4: Preference Inference Metrics ============

PREFERENCE_INFERENCE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_preference_inference_total',
    'Total number of preference inferences from feedback',
    ['preference_key', 'direction', 'source']  # source: feedback, behavior
)

PREFERENCE_INFERENCE_CONFIDENCE = get_or_create_metric(
    Gauge,
    'sparkle_preference_inference_confidence',
    'Current confidence level for inferred preferences',
    ['preference_key']
)

PREFERENCE_DECAY_APPLIED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_preference_decay_applied_total',
    'Total number of preference decay operations',
    ['preference_key', 'action']  # action: decay, reset
)

# ============ Phase 4: Preference Event Latency Metrics ============

PREFERENCE_EVENT_E2E_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_preference_event_e2e_latency_seconds',
    'End-to-end latency from preference update to cache invalidation',
    ['event_type', 'source'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

PREFERENCE_EVENT_CONSUME_LAG = get_or_create_metric(
    Gauge,
    'sparkle_preference_event_consume_lag_seconds',
    'Time lag between event publish and consumer processing',
    ['consumer_group']
)

PREFERENCE_EVENT_STREAM_LENGTH = get_or_create_metric(
    Gauge,
    'sparkle_preference_event_stream_length',
    'Number of pending events in Redis Stream',
    ['stream_key']
)

CACHE_INVALIDATION_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_cache_invalidation_latency_seconds',
    'Time from cache invalidation call to completion',
    ['cache_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

PREFERENCE_EVENT_ERRORS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_preference_event_errors_total',
    'Total preference event processing errors',
    ['error_type', 'consumer_group']
)
