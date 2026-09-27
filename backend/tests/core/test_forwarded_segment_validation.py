"""V3-FIX-484 守卫：XFF 分段 IP 形态校验（fail-closed）与 X-Real-IP 残留分支删除。

wt748 独立审查 CONFIRMED（探针 probe_proxy.py::test_d/test_e）的两组残余：

① ``get_real_ip`` 在 XFF 缺席时回退采信 ``X-Real-IP``——直连 :8000 面客户端
   可选头 → 限流键可轮转；与 426 单一出口 :func:`get_client_ip`「不读
   X-Real-IP」既定口径相悖。修后与 get_client_ip 对齐：XFF 缺席/不可归因一律
   退回 TCP 对端（宁共桶不伪造）。

② ``_forwarded_for_parts`` 纯文本切分不校验 IP 形态——括号形
   ``[2001:db8::1]``、带端口 ``203.0.113.7:8080``、IPv4-mapped
   ``::ffff:a.b.c.d`` 以原样串参与归因与比较。修后逐段 :func:`ipaddress`
   解析 + 归一（括号剥离/剥端口/mapped 归裸 IPv4）；右起 N 段归因窗口内出现
   非 IP 形态段 → fail-closed 退回 TCP 对端/不可信，不以杂质串归因。
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.core.rate_limiting import (
    _normalize_forwarded_segment,
    forwarded_chain_trusted,
    get_client_ip,
    get_real_ip,
)

_PEER = "203.0.113.9"  # 直连面对端（公网，不在可信清单）
_GATEWAY_PEER = "172.20.0.5"  # 经网关面对端（docker 内网，缺省可信清单内）
_CLIENT_IP = "203.0.113.7"


def _request(
    headers: dict[str, str],
    client_host: str | None = _PEER,
    path: str = "/api/v1/auth/login",
) -> Request:
    scope: dict = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "server": ("server", 80),
        "scheme": "http",
    }
    if client_host is not None:
        scope["client"] = (client_host, 12345)
    return Request(scope)


# ---------- ① X-Real-IP 残留分支删除（修复前采信，红） ----------


def test_real_ip_ignores_x_real_ip_when_xff_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """XFF 缺席 + 仅 X-Real-IP：不采信，退回 TCP 对端（与 get_client_ip 同口径）。
    修复前 N=1 时返回 X-Real-IP 值（限流键可轮转，探针 test_d 同形）。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Real-IP": "5.6.7.8"})
    assert get_real_ip(req) == f"{_PEER}:/api/v1/auth/login"


def test_real_ip_ignores_x_real_ip_with_zero_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "0")
    req = _request({"X-Real-IP": "5.6.7.8"})
    assert get_real_ip(req) == f"{_PEER}:/api/v1/auth/login"


def test_xff_still_wins_over_x_real_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """XFF 在场时按右起解析（既有语义，不因 484 改变）。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": f"8.8.8.8, {_CLIENT_IP}", "X-Real-IP": "5.6.7.8"})
    assert get_real_ip(req) == f"{_CLIENT_IP}:/api/v1/auth/login"


def test_get_client_ip_never_reads_x_real_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """单一出口本就不读 X-Real-IP（426 口径，钉住不回退）。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Real-IP": "5.6.7.8"})
    assert get_client_ip(req) == _PEER


# ---------- ② 分段 IP 形态校验与归一（修复前原样串归因，红） ----------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("2001:db8::1", "2001:db8::1"),
        ("[2001:db8::1]", "2001:db8::1"),  # 括号形归一
        ("[2001:db8::1]:443", "2001:db8::1"),  # 括号+端口
        ("203.0.113.7:8080", "203.0.113.7"),  # IPv4 带端口
        ("::ffff:203.0.113.7", "203.0.113.7"),  # IPv4-mapped 归裸 IPv4
        ("unknown", None),  # 非 IP 形态 fail-closed
        ("1.2.3", None),  # 截断形
        ("[2001:db8::1", None),  # 括号未闭合
        ("[not-an-ip]:80", None),
    ],
)
def test_segment_normalization_matrix(raw: str, want: str | None) -> None:
    assert _normalize_forwarded_segment(raw) == want


def test_bracketed_ipv6_segment_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    """修复前归因串为原样「[2001:db8::1]」（探针 test_e 同形），红。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "8.8.8.8, [2001:db8::1]"})
    assert get_client_ip(req) == "2001:db8::1"


def test_port_form_segment_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "8.8.8.8, 203.0.113.7:8080"})
    assert get_client_ip(req) == "203.0.113.7"


def test_ipv4_mapped_segment_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "::ffff:203.0.113.7"})
    assert get_client_ip(req) == "203.0.113.7"


# ---------- 右起 N 段窗口内杂质 → fail-closed（修复前原样串归因，红） ----------


def test_garbage_rightmost_segment_falls_back_to_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    """最右段（网关应追加位）非 IP 形：尾段不是代理追加的 IP → 退回对端。
    修复前归因串为「unknown」。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "8.8.8.8, unknown"})
    assert get_client_ip(req) == _PEER


def test_solo_garbage_segment_falls_back_to_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "unknown"})
    assert get_client_ip(req) == _PEER


def test_garbage_window_segment_with_count_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """N=2 右起窗口 [valid, garbage] 含杂质 → 对端；窗口全合法 → 归因右起
    第 2 段（代理追加位，非最右段）。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
    req = _request({"X-Forwarded-For": "8.8.8.8, 10.0.0.2, unknown"})
    assert get_client_ip(req) == _PEER
    req2 = _request({"X-Forwarded-For": f"unknown, 10.0.0.2, {_CLIENT_IP}"})
    assert get_client_ip(req2) == "10.0.0.2"


def test_garbage_left_of_window_does_not_matter(monkeypatch: pytest.MonkeyPatch) -> None:
    """杂质居左（客户端注入区）不影响右起归因（426 既定语义）。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": f"unknown, garbage[0], {_CLIENT_IP}"})
    assert get_client_ip(req) == _CLIENT_IP


def test_real_ip_garbage_rightmost_falls_back_to_peer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "1.2.3.4, unknown"})
    assert get_real_ip(req) == f"{_PEER}:/api/v1/auth/login"


def test_trusted_chain_with_garbage_tail_not_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    """forwarded_chain_trusted：可信对端但最右段非 IP 形——链尾不是代理追加段，
    XFH 等转发头不可信（480 判据 + 484 形态闸）。修复前仅数链长恒 True，红。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request(
        {"X-Forwarded-For": f"{_CLIENT_IP}, unknown", "X-Forwarded-Host": "evil.example.com"},
        client_host=_GATEWAY_PEER,
    )
    assert forwarded_chain_trusted(req) is False


def test_trusted_chain_valid_tail_leftover_garbage_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    """杂质居左、最右段合法（真实网关形态）：可信分支不受 484 影响。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request(
        {"X-Forwarded-For": f"unknown, {_CLIENT_IP}", "X-Forwarded-Host": "api.sparkle.example"},
        client_host=_GATEWAY_PEER,
    )
    assert forwarded_chain_trusted(req) is True


def test_real_gateway_shape_with_bracketed_client_unaffected(monkeypatch: pytest.MonkeyPatch) -> None:
    """客户端本身是 IPv6 时网关追加裸压缩形；即便上游呈括号形也归一后归因。"""
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    req = _request({"X-Forwarded-For": "8.8.8.8, [2001:db8::1]:443"}, client_host=_GATEWAY_PEER)
    assert get_client_ip(req) == "2001:db8::1"
