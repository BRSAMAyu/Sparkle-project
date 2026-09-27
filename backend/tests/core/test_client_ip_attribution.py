"""V3-FIX-426 守卫：审计/会话/知情同意三消费方 IP 归因按可信代理数右起解析。

历史行为：三处 ``_client_ip`` 无条件取 ``X-Forwarded-For`` **首段**——客户端
可注入该头让审计取证（auth_audit_log.ip_address）、设备会话基线
（user_sessions.ip_address）、知情同意合规存证（含 sha256 后的 grant/
revoke_ip_hash）记录攻击者选定值，而同链限流面已按 EI-09 修为右起解析
（tests/core/test_rate_limit_real_ip.py）——同头两套口径并存。

修复后：三消费方统一走 ``app.core.rate_limiting.get_client_ip`` 单一出口，
右起第 ``TRUSTED_PROXY_COUNT`` 段（缺省 1，与本仓 Go 网关部署拓扑匹配）；
链条短于 N 或 N=0 退回 TCP 对端；伪造段居左天然弃用，右起解析既定语义不变。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.v1.research_consent import _client_ip as consent_client_ip
from app.core.auth_audit_service import _client_ip as audit_client_ip
from app.services.auth_session_service import _client_ip as session_client_ip

_PEER = "203.0.113.9"

ALL_THREE = pytest.mark.parametrize(
    "client_ip_fn",
    [audit_client_ip, session_client_ip, consent_client_ip],
    ids=["auth_audit", "auth_session", "research_consent"],
)


def _request(headers: dict[str, str], client_host: str | None = _PEER) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "server": ("server", 80),
        "scheme": "http",
    }
    if client_host is not None:
        scope["client"] = (client_host, 12345)
    return Request(scope)


@ALL_THREE
def test_forged_xff_first_segment_not_attributed(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    """部署实态链：客户端自带伪造 XFF「8.8.8.8」，网关追加真实 IP 在最右——
    修复前取首段落库 8.8.8.8（可投毒），修复后取右起第 1 段（网关追加段）。
    单段 XFF（无网关追加）按 EI-09 既定边界视为可信最右段，与限流面一致。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    assert client_ip_fn(_request({"X-Forwarded-For": f"8.8.8.8, {_PEER}"})) == _PEER


@ALL_THREE
def test_rightmost_segment_trusted_single_proxy(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "1.2.3.4, 198.51.100.7, 8.8.8.8"})
    assert client_ip_fn(req) == "8.8.8.8"


@ALL_THREE
def test_right_nth_segment_with_multi_proxy_count(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
    req = _request({"X-Forwarded-For": "1.2.3.4, 198.51.100.7, 8.8.8.8"})
    assert client_ip_fn(req) == "198.51.100.7"


@ALL_THREE
def test_shorter_chain_than_trusted_count_falls_back_to_peer(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "3")
    req = _request({"X-Forwarded-For": "1.2.3.4, 8.8.8.8"})
    assert client_ip_fn(req) == _PEER


@ALL_THREE
def test_zero_trusted_proxies_ignores_xff(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request({"X-Forwarded-For": "1.2.3.4"})
    assert client_ip_fn(req) == _PEER


@ALL_THREE
def test_direct_peer_used_without_xff(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    assert client_ip_fn(_request({})) == _PEER


@ALL_THREE
def test_whitespace_segments_stripped(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": " 8.8.8.8 ,  198.51.100.7  "})
    assert client_ip_fn(req) == "198.51.100.7"


@ALL_THREE
def test_missing_client_scope_returns_none(client_ip_fn, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    assert client_ip_fn(_request({}, client_host=None)) is None


def test_none_request_returns_none_for_optional_signatures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    assert audit_client_ip(None) is None
    assert session_client_ip(None) is None
