"""V3-FIX-428 守卫：``vocabulary._external_base_url`` 对 X-Forwarded-Host 做可信判断。

历史行为：XFH 无条件参与绝对 URL 拼接——①网关 Director 覆写 ``req.Host``
后才读 ``req.Host`` 兜底，XFH 恒为内网主机（``sparkle_api:8000``），返回给
客户端的词典包下载地址为不可达坏链+内部拓扑外泄；②客户端自带伪造 XFH
原样透传且被采信。

修复后：XFH/XFP 仅在请求确证经过可信代理链时采信——判据与 EI-09 同源
（XFF 右起第 ``TRUSTED_PROXY_COUNT`` 段 == TCP 对端地址，即可信网关追加的
段）；不可信时降级 ``request.base_url``。Go 侧原语见 gateway
``setup_proxy_forwarded_test.go``（XFH 缺省取客户端原始 Host；自带 XFH
透传为钉测契约——正因为透传，engine 侧必须自行判断）。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.v1.vocabulary import _external_base_url
from app.config.settings import settings

_PEER = "203.0.113.9"
_FORGED_XFH = "evil.example.com"


def _request(
    headers: dict[str, str],
    client_host: str = _PEER,
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


def test_trusted_proxy_chain_uses_forwarded_host() -> None:
    """过可信网关的请求：XFF 最右段 == 对端 → XFH/XFP 可信，拼出客户端可达 URL。"""
    req = _request(
        {
            "X-Forwarded-For": "198.51.100.7, " + _PEER,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "api.sparkle.example",
        }
    )
    assert _external_base_url(req) == "https://api.sparkle.example"


def test_untrusted_xff_not_used_for_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """XFF 链不一致（最右段 != 对端，缺省 N=1 含直连无 XFF 场）：XFH 不可信，
    降级 request.base_url，伪造 XFH 不得出现在结果里。"""
    req = _request(
        {
            "X-Forwarded-For": "8.8.8.8",
            "X-Forwarded-Host": _FORGED_XFH,
            "X-Forwarded-Proto": "https",
        }
    )
    result = _external_base_url(req)
    assert _FORGED_XFH not in result
    assert result == "http://sparkle_api:8000"


def test_forged_xfh_without_xff_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """直连引擎仅带伪造 XFH（无 XFF）：不可信，降级 request.base_url。"""
    req = _request({"X-Forwarded-Host": _FORGED_XFH})
    result = _external_base_url(req)
    assert _FORGED_XFH not in result
    assert result == "http://sparkle_api:8000"


def test_zero_trusted_proxies_never_trusts_xfh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request(
        {
            "X-Forwarded-For": _PEER,
            "X-Forwarded-Host": _FORGED_XFH,
        }
    )
    assert _FORGED_XFH not in _external_base_url(req)


def test_trusted_chain_shorter_than_count_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """链条短于 N（有可信代理未追加，右段可能客户端注入）：不可信。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "3")
    req = _request(
        {
            "X-Forwarded-For": "198.51.100.7, " + _PEER,
            "X-Forwarded-Host": _FORGED_XFH,
        }
    )
    assert _FORGED_XFH not in _external_base_url(req)


def test_explicit_base_url_env_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DICTIONARY_PACKAGE_BASE_URL", "https://dl.sparkle.example/pkg/")
    req = _request({"X-Forwarded-Host": _FORGED_XFH})
    assert _external_base_url(req) == "https://dl.sparkle.example/pkg"


def test_gateway_internal_url_env_second(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GATEWAY_INTERNAL_URL", "https://gw.sparkle.example")
    req = _request({"X-Forwarded-Host": _FORGED_XFH})
    assert _external_base_url(req) == "https://gw.sparkle.example"


def test_forwarded_prefix_appended_when_trusted() -> None:
    req = _request(
        {
            "X-Forwarded-For": _PEER,
            "X-Forwarded-Host": "api.sparkle.example",
            "X-Forwarded-Prefix": "/api/v1",
        }
    )
    assert _external_base_url(req) == "http://api.sparkle.example/api/v1"
