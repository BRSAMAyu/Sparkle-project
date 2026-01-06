"""
Rate Limiting Middleware
Using slowapi to manage rate limits for API endpoints
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request

def get_real_ip(request: Request) -> str:
    """
    获取真实 IP，支持代理透传 (X-Forwarded-For)
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # 取第一个 IP (原始客户端)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_real_ip,
    default_limits=["200 per day", "50 per hour"]
)

def setup_rate_limiting(app: FastAPI):
    """
    Setup rate limiting for the FastAPI app
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
