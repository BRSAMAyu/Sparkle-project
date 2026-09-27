"""V3-FIX-428 守卫（拓扑按 V3-FIX-480 重模）：``vocabulary._external_base_url``
对 X-Forwarded-Host 做可信判断。

历史行为：XFH 无条件参与绝对 URL 拼接——①网关 Director 覆写 ``req.Host``
后才读 ``req.Host`` 兜底，XFH 恒为内网主机（``sparkle_api:8000``），返回给
客户端的词典包下载地址为不可达坏链+内部拓扑外泄；②客户端自带伪造 XFH
原样透传且被采信。

修复后：XFH/XFP 仅在请求确证经过可信代理链时采信。判据语义按 V3-FIX-480
修正：**TCP 对端 ∈ 可信代理清单（``TRUSTED_PROXY_CIDRS`` 缺省私网/回环）且
XFF 链长 ≥ ``TRUSTED_PROXY_COUNT``**——与本仓 Go 网关契约同一世界（追加段=
本跳 client IP，对端=网关自身 IP，见 gateway ``setup_proxy_forwarded_test.go``
钉测；初版守卫建模「追加段==对端」拓扑与该钉测互斥，wt748 审查登记 480 行
指出后按真实拓扑重模）。不可信时降级 ``request.base_url``。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.v1.vocabulary import _external_base_url
from app.config.settings import settings

_GATEWAY_PEER = "172.20.0.5"  # 引擎 TCP 对端 = 网关容器 IP（docker 内网，缺省可信清单内）
_CLIENT_IP = "203.0.113.7"  # 真实客户端 IP（网关追加进 XFF 的最右段）
_INJECTED = "8.8.8.8"  # 客户端自带伪造段
_EXTERNAL_PEER = "198.51.100.7"  # 直连引擎的外部对端（公网，不在可信清单）
_FORGED_XFH = "evil.example.com"


def _request(
    headers: dict[str, str],
    client_host: str = _GATEWAY_PEER,
    server: tuple[str, int] = ("sparkle_api", 8000),
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/vocabulary/dictionary/packages",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "server": server,
        "client": (client_host, 12345),
        "scheme": "http",
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _default_env_paths(monkeypatch: pytest.MonkeyPatch):
    """XFH fallback 是缺省活路径（两 env 缺省均为空串）。"""
    monkeypatch.setattr(settings, "DICTIONARY_PACKAGE_BASE_URL", "")
    monkeypatch.setattr(settings, "GATEWAY_INTERNAL_URL", "")


def test_gateway_shape_uses_client_original_host() -> None:
    """真实网关形态（Go 钉测契约：无注入时后端收 XFF=「clientIP」，对端=
    网关 IP）：XFH 可信，拼出客户端原始 Host 的可达 URL。修正前判据
    parts[-n]==peer 对该形态恒 False → 恒降级内网 sparkle_api:8000（480 行
    死路缺陷）；伪造 XFH 亦被网关剥除（钉测），此处 XFH 即客户端原始 Host。"""
    req = _request(
        {
            "X-Forwarded-For": _CLIENT_IP,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "api.sparkle.example",
        }
    )
    assert _external_base_url(req) == "https://api.sparkle.example"


def test_gateway_shape_with_injection_uses_client_original_host() -> None:
    """带客户端注入段的网关形态（「8.8.8.8, clientIP」，注入居左）：仍可信，
    XFH 取客户端原始 Host。"""
    req = _request(
        {
            "X-Forwarded-For": f"{_INJECTED}, {_CLIENT_IP}",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "api.sparkle.example",
        }
    )
    assert _external_base_url(req) == "https://api.sparkle.example"


def test_direct_forged_chain_not_used_for_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """直连引擎的外部对端伪造 XFF 最右段==自身对端（修正前判据恰好过闸的
    fail-open 形）：XFH 不可信，降级 request.base_url，伪造 XFH 不得出现在
    结果里。"""
    req = _request(
        {
            "X-Forwarded-For": _EXTERNAL_PEER,
            "X-Forwarded-Host": _FORGED_XFH,
            "X-Forwarded-Proto": "https",
        },
        client_host=_EXTERNAL_PEER,
    )
    result = _external_base_url(req)
    assert _FORGED_XFH not in result
    assert result == "http://sparkle_api:8000"


def test_untrusted_xff_not_used_for_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """直连引擎（对端不在可信清单）任意链：XFH 不可信，降级 request.base_url。"""
    req = _request(
        {
            "X-Forwarded-For": "8.8.8.8",
            "X-Forwarded-Host": _FORGED_XFH,
            "X-Forwarded-Proto": "https",
        },
        client_host=_EXTERNAL_PEER,
    )
    result = _external_base_url(req)
    assert _FORGED_XFH not in result
    assert result == "http://sparkle_api:8000"


def test_forged_xfh_without_xff_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """直连引擎仅带伪造 XFH（无 XFF）：不可信，降级 request.base_url。"""
    req = _request({"X-Forwarded-Host": _FORGED_XFH}, client_host=_EXTERNAL_PEER)
    result = _external_base_url(req)
    assert _FORGED_XFH not in result
    assert result == "http://sparkle_api:8000"


def test_zero_trusted_proxies_never_trusts_xfh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request(
        {
            "X-Forwarded-For": _CLIENT_IP,
            "X-Forwarded-Host": _FORGED_XFH,
        }
    )
    assert _FORGED_XFH not in _external_base_url(req)


def test_trusted_chain_shorter_than_count_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """链条短于 N（有可信代理未追加，右段可能客户端注入）：对端可信亦不开闸。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "3")
    req = _request(
        {
            "X-Forwarded-For": f"{_INJECTED}, {_CLIENT_IP}",
            "X-Forwarded-Host": _FORGED_XFH,
        }
    )
    assert _FORGED_XFH not in _external_base_url(req)


def test_explicit_base_url_env_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DICTIONARY_PACKAGE_BASE_URL", "https://dl.sparkle.example/pkg/")
    req = _request({"X-Forwarded-Host": _FORGED_XFH}, client_host=_EXTERNAL_PEER)
    assert _external_base_url(req) == "https://dl.sparkle.example/pkg"


def test_gateway_internal_url_env_second(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GATEWAY_INTERNAL_URL", "https://gw.sparkle.example")
    req = _request({"X-Forwarded-Host": _FORGED_XFH}, client_host=_EXTERNAL_PEER)
    assert _external_base_url(req) == "https://gw.sparkle.example"


def test_forwarded_prefix_appended_when_trusted() -> None:
    req = _request(
        {
            "X-Forwarded-For": _CLIENT_IP,
            "X-Forwarded-Host": "api.sparkle.example",
            "X-Forwarded-Prefix": "/api/v1",
        }
    )
    assert _external_base_url(req) == "http://api.sparkle.example/api/v1"
