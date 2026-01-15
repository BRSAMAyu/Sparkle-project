from prometheus_client import Counter, Histogram, Gauge, Summary, REGISTRY
from functools import wraps
import time

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
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
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

# 6. 文档质量门禁指标
DOC_QUALITY_CHECK_COUNT = get_or_create_metric(
    Counter,
    'sparkle_doc_quality_checks_total',
    'Total number of document quality checks',
    ['doc_type', 'result']  # result: passed, failed
)

DOC_QUALITY_SCORE = get_or_create_metric(
    Histogram,
    'sparkle_doc_quality_score',
    'Distribution of document quality scores',
    ['doc_type'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

DOC_GARBLED_RATIO = get_or_create_metric(
    Histogram,
    'sparkle_doc_garbled_ratio',
    'Distribution of garbled character ratios',
    ['doc_type'],
    buckets=[0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
)

DOC_OCR_CONFIDENCE = get_or_create_metric(
    Histogram,
    'sparkle_doc_ocr_confidence',
    'Distribution of OCR confidence scores',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
)

DOC_QUALITY_ISSUES = get_or_create_metric(
    Counter,
    'sparkle_doc_quality_issues_total',
    'Count of specific quality issues detected',
    ['issue_type']  # garbled, too_short, low_chinese_ratio, repeated_headers, etc.
)

# 装饰器：用于测量函数执行时间并记录指标
def track_latency(module, method):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from opentelemetry import trace
            start_time = time.time()
            span = trace.get_current_span()
            trace_id = format(span.get_span_context().trace_id, '032x') if span else "n/a"
            
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(module=module, method=method, status='success').inc()
                return result
            except Exception as e:
                # Log with TraceID for correlation
                from loguru import logger
                logger.error(f"[TraceID: {trace_id}] Error in {module}.{method}: {e}")
                REQUEST_COUNT.labels(module=module, method=method, status='error').inc()
                raise
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module=module, method=method).observe(latency)