from prometheus_client import Counter, Histogram, Gauge, Summary
from functools import wraps
import time

# 1. 基础请求指标
REQUEST_COUNT = Counter(
    'sparkle_requests_total',
    'Total number of requests',
    ['module', 'method', 'status']
)

REQUEST_LATENCY = Histogram(
    'sparkle_request_latency_seconds',
    'Request latency in seconds',
    ['module', 'method']
)

# 2. LLM 与 Token 指标
TOKEN_USAGE = Counter(
    'sparkle_tokens_total',
    'Total number of tokens used',
    ['model', 'type']  # type: prompt, completion
)

LLM_CALL_DURATION = Histogram(
    'sparkle_llm_call_duration_seconds',
    'LLM call duration in seconds',
    ['model', 'provider']
)

# 3. 缓存指标
CACHE_HIT_COUNT = Counter(
    'sparkle_cache_hits_total',
    'Total number of cache hits/misses',
    ['cache_name', 'result']  # result: hit, miss
)

# 4. 工具执行指标
TOOL_EXECUTION_COUNT = Counter(
    'sparkle_tool_executions_total',
    'Total number of tool executions',
    ['tool_name', 'status']
)

# 5. 系统指标
ACTIVE_SESSIONS = Gauge(
    'sparkle_active_sessions_total',
    'Total number of active chat sessions'
)

# 装饰器：用于测量函数执行时间并记录指标
def track_latency(module, method):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(module=module, method=method, status='success').inc()
                return result
            except Exception as e:
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
                REQUEST_COUNT.labels(module=module, method=method, status='error').inc()
                raise
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module=module, method=method).observe(latency)
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator