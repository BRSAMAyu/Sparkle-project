"""EI-09 守卫（P3 清扫）：get_real_ip 按可信代理数解析真实客户端 IP。

历史行为：无条件信任 ``X-Forwarded-For`` 首段——客户端可伪造该头绕过按 IP
限流（auth 登录端点的爆破防护，R2 §5 EI-09 复核加注项）。

本仓部署拓扑：Go 网关（httputil.ReverseProxy）在 XFF 尾部追加真实 client IP，
因此正确做法是取 XFF 右起第 N 位（N = ``TRUSTED_PROXY_COUNT``）；N=0 时
完全不信任该头，退回 TCP 对端地址。链条短于 N（说明有代理未追加，最右段
可能是客户端注入的）时同样退回对端地址，宁可退化为共享桶也不可被伪造。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.core.rate_limiting import _trusted_proxy_count, get_real_ip

_PEER = "203.0.113.9"


def _request(headers: dict[str, str], client_host: str = _PEER, path: str = "/api/v1/auth/login") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "client": (client_host, 12345),
        "server": ("server", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_spoofed_xff_ignored_when_no_trusted_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request({"X-Forwarded-For": "1.2.3.4"})
    assert get_real_ip(req) == f"{_PEER}:/api/v1/auth/login"


def test_rightmost_entry_trusted_with_single_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "1.2.3.4, 198.51.100.7"})
    # 最右段由可信网关追加；客户端伪造的首段无效
    assert get_real_ip(req).startswith("198.51.100.7:")


def test_shorter_chain_than_trusted_count_falls_back_to_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "3")
    req = _request({"X-Forwarded-For": "1.2.3.4, 198.51.100.7"})
    assert get_real_ip(req).startswith(f"{_PEER}:")


def test_x_real_ip_trusted_only_behind_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request({"X-Real-IP": "5.6.7.8"})
    assert get_real_ip(req).startswith(f"{_PEER}:")
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req2 = _request({"X-Real-IP": "5.6.7.8"})
    assert get_real_ip(req2).startswith("5.6.7.8:")


def test_direct_peer_used_without_proxy_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({})
    assert get_real_ip(req).startswith(f"{_PEER}:")


def test_invalid_env_value_falls_back_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "bogus")
    assert _trusted_proxy_count() == 0
