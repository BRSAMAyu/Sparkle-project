"""
Rate Limiting Middleware
Using slowapi to manage rate limits for API endpoints
"""
import ipaddress
import os

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# V3-FIX-480：引擎侧可信代理清单缺省值——回环 + 链路本地 + RFC1918 私网 +
# IPv6 ULA。本仓部署（docker compose，引擎端口仅内网可达）中网关对端落在
# 该集合内；需要更严隔离的部署用 ``TRUSTED_PROXY_CIDRS`` 收窄到网关精确地址。
_DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8",  # IPv4 回环
    "::1/128",  # IPv6 回环
    "10.0.0.0/8",  # RFC1918 私网
    "172.16.0.0/12",  # RFC1918 私网（Docker 默认地址池）
    "192.168.0.0/16",  # RFC1918 私网
    "169.254.0.0/16",  # IPv4 链路本地
    "fe80::/10",  # IPv6 链路本地
    "fc00::/7",  # IPv6 ULA
)


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


def _trusted_proxy_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """
    引擎侧可信代理清单（环境变量 ``TRUSTED_PROXY_CIDRS``，逗号分隔 CIDR，
    缺省 :data:`_DEFAULT_TRUSTED_PROXY_CIDRS`——回环+链路本地+私网，覆盖本仓
    docker/内网部署拓扑中网关对端所在网段）。

    无法解析的段跳过；显式置空串或全部无法解析 → 空表=任何对端都不可信
    （fail-closed）。语义同 nginx ``real_ip``/uvicorn ``--forwarded-allow-ips``/
    gin ``SetTrustedProxies`` 的引擎侧对位物。
    """
    raw = os.getenv("TRUSTED_PROXY_CIDRS", ",".join(_DEFAULT_TRUSTED_PROXY_CIDRS))
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for entry in raw.split(","):
        candidate = entry.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            continue
    return networks


def _peer_is_trusted_proxy(peer: str | None) -> bool:
    """TCP 对端是否属于可信代理清单；IPv4-mapped 对端归一后比对。"""
    if not peer:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return any(addr in network for network in _trusted_proxy_networks())


def _forwarded_for_parts(request: Request) -> list[str] | None:
    """X-Forwarded-For 规范化：按逗号切分、去空白、剔空段；头缺席返回 None。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return None
    return [p.strip() for p in forwarded.split(",") if p.strip()]


def get_client_ip(request: Request) -> str | None:
    """
    真实客户端 IP 归因单一出口（V3-FIX-426；右起解析同 EI-09）。

    审计（auth_audit_log.ip_address）、设备会话（user_sessions.ip_address）、
    知情同意合规存证等 IP 归因面统一走本函数，禁再散抄 XFF 首段：按
    ``TRUSTED_PROXY_COUNT`` 取 XFF **右起**第 N 段——可信网关追加的段在右，
    客户端注入的伪造段居左天然弃用；链条短于 N（有代理未追加，右段可能是
    客户端注入）或 N=0 时退回 TCP 对端地址。与 :func:`get_real_ip` 的差异：
    不带路径后缀，且不读 ``X-Real-IP``（历史归因面未采信该头，不引入新信任面）。
    """
    n = _trusted_proxy_count()
    peer = request.client.host if request.client else None
    if n > 0:
        parts = _forwarded_for_parts(request)
        if parts is not None:
            if len(parts) >= n:
                return parts[-n]
            return peer
    return peer


def forwarded_chain_trusted(request: Request) -> bool:
    """
    X-Forwarded-Host/Proto 等转发头是否可信（V3-FIX-428 引擎侧判据；判据
    语义按 V3-FIX-480 修正）。

    判据（与 nginx ``real_ip``/uvicorn ``--forwarded-allow-ips``/gin
    ``SetTrustedProxies`` 同型的引擎侧对位物）：

    1. **TCP 对端 ∈ 引擎侧可信代理清单**（``TRUSTED_PROXY_CIDRS``，缺省
       回环+链路本地+私网，见 :func:`_trusted_proxy_networks`）——对端不可信
       时 XFF/XFH/XFP 全是客户端可选值，一律不可信；
    2. ``TRUSTED_PROXY_COUNT`` > 0 且 XFF 链长 ≥ N——确证链上有 N 层会追加
       的代理。

    历史判据（XFF 右起第 N 段 == TCP 对端）与本仓网关契约**结构互斥**：
    Go 网关（``setup_proxy_forwarded_test.go`` 钉测）在 XFF 尾部追加的是
    **本跳 client IP** 而非网关自身地址，真实流量末段==对端恒 False → 可信
    分支死路（428 的 XFH 分支在缺省 env 恒降级内网 ``sparkle_api:8000``）；
    而直连引擎的攻击者把自身对端地址写进 XFF 最右段反而能过闸（fail-open）。
    修正后：

    - 经网关真实流量（对端=网关 ∈ 缺省私网集）可信分支可达——XFH 为客户端
      原始 Host（Go 钉测契约），``vocabulary._external_base_url`` 拼出客户端
      可达绝对 URL；
    - 引擎直连面（对端 ∉ 可信清单）伪造任何链（含最右段==自身对端）均不可信
      （fail-closed）；
    - ``TRUSTED_PROXY_COUNT=0`` 语义不变（完全不信任转发头）。

    采信转发头的消费方（如 ``vocabulary._external_base_url`` 拼客户端可达绝
    对 URL）必须先过本判断，不可信时降级 ``request.base_url`` 等自证值。
    """
    peer = request.client.host if request.client else None
    if not _peer_is_trusted_proxy(peer):
        return False
    n = _trusted_proxy_count()
    if n <= 0:
        return False
    parts = _forwarded_for_parts(request)
    if parts is None or len(parts) < n:
        return False
    return True


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
    real_ip = request.headers.get("X-Real-IP")
    n = _trusted_proxy_count()

    ip = peer
    if n > 0:
        parts = _forwarded_for_parts(request)
        if parts is not None:
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
