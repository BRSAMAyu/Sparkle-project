"""
Rate Limiting Middleware
Using slowapi to manage rate limits for API endpoints
"""
import os

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _trusted_proxy_count() -> int:
    """
    可信代理层数（环境变量 ``TRUSTED_PROXY_COUNT``，默认 1）。

    - **1（默认）**：匹配本仓部署拓扑——Go 网关（httputil.ReverseProxy /
      websocket_proxy）在 X-Forwarded-For 尾部追加真实 client IP，取最右 1 段。
    - **0**：完全不信任 XFF / X-Real-IP（引擎直连暴露、前面没有可信代理时使用）。
    - **N**：链路上有 N 层会追加 XFF 的可信代理，取右起第 N 段。
    """
    raw = os.getenv("TRUSTED_PROXY_COUNT", "1")
    try:
        return max(0, int(raw.strip()))
    except (ValueError, AttributeError):
        return 0


def get_real_ip(request: Request) -> str:
    """
    获取真实客户端 IP（按可信代理数从 X-Forwarded-For 右起解析，EI-09）。

    历史实现无条件信任 XFF 首段——客户端可伪造该头绕过按 IP 限流（auth 登录
    端点的爆破防护）。现按 ``TRUSTED_PROXY_COUNT`` 取 XFF **右起**第 N 段：
    可信代理追加的段在右侧，客户端注入的伪造段在左侧天然被弃用。链条短于 N
    （说明有代理未追加，右段可能是客户端注入）或 N=0 时，退回 TCP 对端地址——
    宁可退化为共享桶也不可被伪造。

    同时追加请求路径，确保不同端点的限流配额互相隔离——
    当所有流量经过同一个内网网关时（如 Docker 环境），
    若只用 IP 作为 key，所有端点会共享同一配额，极易误触发 429。

    NOTE（R2 复核加注，EI-09 遗留边界）：
    - ``default_limits=["600 per minute"]`` 未挂 SlowAPIMiddleware，**并不生效**，
      仅 ``@limiter.limit`` 装饰的端点（auth/community/suggestions）有限流；
    - 按 IP 限流只是纵深防御的一层，登录爆破防护以 DB 侧账号级锁
      （login_attempt 机制）为准，不依赖本限流。
    """
    peer = get_remote_address(request)
    forwarded = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")
    n = _trusted_proxy_count()

    ip = peer
    if n > 0:
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if len(parts) >= n:
                ip = parts[-n]
        elif real_ip:
            ip = real_ip
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
