"""V3-FIX-480 守卫：``forwarded_chain_trusted`` 判据与网关「追加 client IP」契约对齐。

历史判据（XFF 右起第 ``TRUSTED_PROXY_COUNT`` 段 == TCP 对端）与网关修后契约
**结构互斥**（wt748 独立审查登记，探针 v3-output/WT748-REVIEW/probe_proxy.py）：
Go 网关追加进 XFF 的是**本跳 client IP**（``setup_proxy_forwarded_test.go`` 钉测：
无注入→后端收 XFF=「clientIP」；带注入→「8.8.8.8, clientIP」），引擎视角对端=
网关自身 IP——真实流量末段==对端恒 False → 可信分支死路（428 XFH 分支在缺省
env 恒降级内网 ``http://sparkle_api:8000``）；而直连引擎的攻击者把「自身对端
地址」写进 XFF 最右段反而能过闸（fail-open）。

修正后判据（同 nginx real_ip / uvicorn forwarded-allow-ips / gin SetTrustedProxies
同型）：**TCP 对端 ∈ 引擎侧可信代理清单（``TRUSTED_PROXY_CIDRS``，缺省回环+
链路本地+RFC1918 私网+IPv6 ULA）且 XFF 链长 ≥ ``TRUSTED_PROXY_COUNT``**。本文件
请求形态一律以 Go 钉测的真实网关契约为准（追加段=client IP，对端=网关 IP）。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.core.rate_limiting import forwarded_chain_trusted

# 真实拓扑三要素（与 setup_proxy_forwarded_test.go 的世界一致）：
_GATEWAY_PEER = "172.20.0.5"  # 引擎 TCP 对端 = 网关容器 IP（docker 内网）
_CLIENT_IP = "203.0.113.7"  # 真实客户端公网 IP（网关追加进 XFF 的值）
_INJECTED = "8.8.8.8"  # 客户端自带伪造段（居左，右起解析弃用）
_EXTERNAL_PEER = "198.51.100.7"  # 直连引擎的外部对端（公网，不在可信清单）


def _request(headers: dict[str, str], client_host: str | None = _GATEWAY_PEER) -> Request:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/vocabulary/dictionary/packages",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "server": ("sparkle_api", 8000),
        "scheme": "http",
    }
    if client_host is not None:
        scope["client"] = (client_host, 40000)
    return Request(scope)


# ---------- 经网关真实形态：可信分支必须可达（修正前恒 False，红） ----------


def test_gateway_shape_no_client_injection_trusted() -> None:
    """Go 钉测 TestProxySetsXFFToClientIPWhenAbsent 形态：无注入时后端收
    XFF=「clientIP」，对端=网关 IP → 可信。修正前 parts[-1]==peer 恒 False。"""
    req = _request({"X-Forwarded-For": _CLIENT_IP, "X-Forwarded-Host": "api.sparkle.example"})
    assert forwarded_chain_trusted(req) is True


def test_gateway_shape_with_client_injection_trusted() -> None:
    """Go 钉测 TestProxyAppendsClientIPToXFFExactlyOnce 形态：入站链+追加段
    「8.8.8.8, clientIP」，对端=网关 IP → 可信。"""
    req = _request({"X-Forwarded-For": f"{_INJECTED}, {_CLIENT_IP}"})
    assert forwarded_chain_trusted(req) is True


# ---------- 引擎直连面：伪造链一律不可信（修正前 fail-open，红） ----------


def test_direct_peer_self_referential_chain_rejected() -> None:
    """直连引擎的攻击者把「自身对端地址」写进 XFF 最右段——修正前判据
    parts[-n]==peer 恰好过闸（fail-open，探针 test_c 实证同形）；修正后对端
    不在可信清单 → 一律不可信。"""
    req = _request(
        {"X-Forwarded-For": _EXTERNAL_PEER, "X-Forwarded-Host": "evil.example.com"},
        client_host=_EXTERNAL_PEER,
    )
    assert forwarded_chain_trusted(req) is False


def test_direct_peer_full_forgery_rejected() -> None:
    """直连面伪造任意链（含最右段==自身对端）：不可信。"""
    req = _request(
        {"X-Forwarded-For": f"6.6.6.6, {_EXTERNAL_PEER}", "X-Forwarded-Host": "evil.example.com"},
        client_host=_EXTERNAL_PEER,
    )
    assert forwarded_chain_trusted(req) is False


def test_direct_peer_any_chain_not_trusted() -> None:
    """直连面对端不在可信清单：无论链形如何（网关形态仿冒亦然）不可信。"""
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host=_EXTERNAL_PEER)
    assert forwarded_chain_trusted(req) is False


# ---------- 既有边界语义保持（426/428 既定口径，绿） ----------


def test_no_xff_untrusted_even_from_trusted_peer() -> None:
    """可信对端但无 XFF（链上有代理未追加）：不可信（fail-closed）。"""
    req = _request({"X-Forwarded-Host": "evil.example.com"})
    assert forwarded_chain_trusted(req) is False


def test_zero_trusted_proxies_never_trusts(monkeypatch: pytest.MonkeyPatch) -> None:
    """N=0：完全不信任转发头，与既定语义一致。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request({"X-Forwarded-For": _CLIENT_IP})
    assert forwarded_chain_trusted(req) is False


def test_invalid_count_falls_back_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "bogus")
    req = _request({"X-Forwarded-For": _CLIENT_IP})
    assert forwarded_chain_trusted(req) is False


def test_chain_shorter_than_count_untrusted(monkeypatch: pytest.MonkeyPatch) -> None:
    """链长 < N（有可信代理未追加）：不可信，对端可信亦不开闸。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
    req = _request({"X-Forwarded-For": _CLIENT_IP})
    assert forwarded_chain_trusted(req) is False


def test_two_trusted_proxies_long_enough_chain_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    """N=2、链长 ≥ 2、对端可信：可信。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
    req = _request({"X-Forwarded-For": f"{_CLIENT_IP}, 10.0.0.2"})
    assert forwarded_chain_trusted(req) is True


def test_missing_client_scope_untrusted() -> None:
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host=None)
    assert forwarded_chain_trusted(req) is False


# ---------- TRUSTED_PROXY_CIDRS 语义 ----------


def test_default_covers_loopback_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    """缺省可信清单覆盖回环：本机反代拓扑（nginx→uvicorn 同机）可信分支可达。"""
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host="127.0.0.1")
    assert forwarded_chain_trusted(req) is True


def test_custom_cidrs_narrows_trust(monkeypatch: pytest.MonkeyPatch) -> None:
    """收窄到网关精确地址：网关对端可信。"""
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", f"{_GATEWAY_PEER}/32")
    req = _request({"X-Forwarded-For": _CLIENT_IP})
    assert forwarded_chain_trusted(req) is True


def test_custom_cidrs_excludes_other_private_peers(monkeypatch: pytest.MonkeyPatch) -> None:
    """收窄后其余私网对端不可信（需更严隔离的部署口径）。"""
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", f"{_GATEWAY_PEER}/32")
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host="192.168.1.10")
    assert forwarded_chain_trusted(req) is False


def test_empty_cidrs_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式置空=不信任任何对端（fail-closed）；修正前同形请求过闸（fail-open）。"""
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "")
    req = _request({"X-Forwarded-For": _GATEWAY_PEER}, client_host=_GATEWAY_PEER)
    assert forwarded_chain_trusted(req) is False


def test_invalid_cidr_entries_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """无法解析的段跳过；合法段仍生效。"""
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "not-a-cidr, 10.1.2.0/24")
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host="10.1.2.3")
    assert forwarded_chain_trusted(req) is True


def test_all_invalid_cidrs_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "not-a-cidr, 300.1.2.3/24")
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host=_GATEWAY_PEER)
    assert forwarded_chain_trusted(req) is False


def test_ipv4_mapped_peer_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    """双栈 socket 下对端呈 IPv4-mapped 形：归一后命中私网段，不因形差
    误判不可信（修正前判据同形 false-negative，484 登记族）。"""
    req = _request({"X-Forwarded-For": _CLIENT_IP}, client_host="::ffff:172.20.0.5")
    assert forwarded_chain_trusted(req) is True
