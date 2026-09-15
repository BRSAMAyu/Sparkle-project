"""
Rate Limiting Middleware
Using slowapi to manage rate limits for API endpoints
"""
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    """
    获取真实 IP，支持代理透传 (X-Forwarded-For / X-Real-IP)。
    同时追加请求路径，确保不同端点的限流配额互相隔离——
    当所有流量经过同一个内网网关时（如 Docker 环境），
    若只用 IP 作为 key，所有端点会共享同一配额，极易误触发 429。
    """
    # SECURITY NOTE: X-Forwarded-For is trusted from all proxies. In production,
    # configure trusted proxy count via TRUSTED_PROXY_COUNT env var.
    forwarded = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif real_ip:
        ip = real_ip.strip()
    else:
        ip = get_remote_address(request)
    # Include path so per-endpoint limits don't share quota
    return f"{ip}:{request.url.path}"

limiter = Limiter(
    key_func=get_real_ip,
    default_limits=["600 per minute"]
)

def setup_rate_limiting(app: FastAPI):
    """
    Setup rate limiting for the FastAPI app
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
