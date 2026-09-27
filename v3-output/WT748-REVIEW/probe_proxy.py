"""WT748 review probe — proxy/转发头族残余（engine 侧 Python 面）.

焦点2: 以"真实网关修后形态"构造请求（Go 侧契约由仓库自身
setup_proxy_forwarded_test.go 钉死：追加段=本跳 client IP，非网关自身地址），
验证 rate_limiting.forwarded_chain_trusted / get_client_ip / get_real_ip 语义。
"""

import os
import sys

BACKEND = "/Users/brsama/code/GitHub/Sparkle-project/backend"
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "app"))
sys.path.insert(0, os.path.join(BACKEND, "app", "gen"))

os.environ.setdefault("SECRET_KEY", "v")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from starlette.requests import Request

from app.config.settings import settings
from app.core.rate_limiting import (
    forwarded_chain_trusted,
    get_client_ip,
    get_real_ip,
)
from app.api.v1.vocabulary import _external_base_url

GATEWAY_IP = "172.20.0.5"  # engine 的 TCP 对端（docker 内网网关容器）
CLIENT_IP = "203.0.113.7"  # 真实客户端公网/LAN IP（网关追加进 XFF 的值）


def _request(headers: dict, client=(GATEWAY_IP, 40000), path="/api/v1/vocabulary/dictionary/packages") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "server": ("sparkle_api", 8000),
        "client": client,
        "scheme": "http",
    }
    return Request(scope)


def test_a_gateway_shape_request_trust_gate_never_opens(monkeypatch):
    """真实网关修后形态（Go 钉测契约：无注入客户端 → 引擎收 XFF=「clientIP」，
    TCP 对端=网关 IP）：forwarded_chain_trusted 恒 False → _external_base_url
    恒降级 http://sparkle_api:8000 —— V3-FIX-428 要修的「坏链+内网拓扑外泄」
    症状在缺省 env（两 URL 配置缺省空串）下依旧。"""
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    monkeypatch.setattr(settings, "DICTIONARY_PACKAGE_BASE_URL", "")
    monkeypatch.setattr(settings, "GATEWAY_INTERNAL_URL", "")
    # 完全诚实、无任何客户端注入的链条（网关恰一次追加真实 client IP）
    req = _request({"X-Forwarded-For": CLIENT_IP, "X-Forwarded-Host": "api.sparkle.example"})
    assert not forwarded_chain_trusted(req)
    # 带客户端注入段的链条（注入段居左，网关追加 clientIP 居右）
    req2 = _request(
        {
            "X-Forwarded-For": f"8.8.8.8, {CLIENT_IP}",
            "X-Forwarded-Host": "api.sparkle.example",
            "X-Forwarded-Proto": "https",
        }
    )
    assert not forwarded_chain_trusted(req2)
    url = _external_base_url(req2)
    assert url == "http://sparkle_api:8000", f"实际返回 {url}"
    # 而 428 的 Python 守卫测试建模的是「追加段==网关自身IP」——与 Go 侧契约互斥


def test_b_attribute_and_ratelimit_key_still_correct_via_gateway(monkeypatch):
    """对照面（非缺陷）：HTTP 经网关路径 get_client_ip/get_real_ip 右起解析
    仍取真实 client IP——426 修复本体不受影响。"""
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    req = _request({"X-Forwarded-For": f"8.8.8.8, {CLIENT_IP}"}, path="/api/v1/auth/guest")
    assert get_client_ip(req) == CLIENT_IP
    assert get_real_ip(req) == f"{CLIENT_IP}:/api/v1/auth/guest"


def test_c_ws_path_no_append_forged_rightmost_is_attributed(monkeypatch):
    """WS 升级路径形态（websocket_proxy.go buildBackendWebSocketHeaders 原样
    透传、不追加本跳 client IP）：客户端伪造 XFF 最右段被 get_client_ip 如实
    采信为「真实客户端 IP」；且伪造最右段=网关自身 IP 时 forwarded_chain_trusted
    直接转 True——信任闸在未追加路径上可被完全伪造的链条打开。"""
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    # WS 客户端直连网关，伪造 XFF（网关原样转发）
    req = _request({"X-Forwarded-For": "1.2.3.4"}, path="/ws/chat")
    assert get_client_ip(req) == "1.2.3.4", "伪造最右段未被视为归因 IP"
    # 伪造最右段恰为网关自身 IP → 信任闸为伪造链开门
    req2 = _request({"X-Forwarded-For": GATEWAY_IP, "X-Forwarded-Host": "evil.example.com"}, path="/ws/chat")
    assert forwarded_chain_trusted(req2), "伪造链未过信任闸（与 HTTP 路径恒 False 形成偏差）"


def test_d_x_real_ip_residual_branch_in_get_real_ip(monkeypatch):
    """get_real_ip 在 XFF 缺席时仍采信 X-Real-IP（直连 :8000 面=客户端可选头）：
    限流键=攻击者轮转值。与 426 单一出口 get_client_ip「不读 X-Real-IP」口径相悖。"""
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    req = _request({"X-Real-IP": "9.9.9.9"}, path="/api/v1/auth/login")
    assert get_real_ip(req) == "9.9.9.9:/api/v1/auth/login"
    # 同请求 get_client_ip（426 出口）正确回退 TCP 对端
    assert get_client_ip(req) == GATEWAY_IP


def test_e_ipv6_and_bracketed_forms_fail_closed(monkeypatch):
    """IPv6/带端口/括号形鲁棒性：_forwarded_for_parts 纯文本切分不校验形态——
    括号形/带端口形以原样字符串参与归因与 == 比较；偏差方向为 fail-closed
    （信任闸 false-negative）+归因串带杂质，无 false-positive 安全面。"""
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    # 括号形 IPv6 原样归因
    req = _request({"X-Forwarded-For": "[2001:db8::1]"}, path="/api/v1/auth/guest")
    assert get_client_ip(req) == "[2001:db8::1]"
    # 带端口形原样归因
    req2 = _request({"X-Forwarded-For": "2001:db8::1:40000"}, path="/api/v1/auth/guest")
    assert get_client_ip(req2) == "2001:db8::1:40000"
    # IPv4-mapped 与裸形不等价 → 信任闸 fail-closed
    req3 = _request(
        {"X-Forwarded-For": "::ffff:172.20.0.5", "X-Forwarded-Host": "api.sparkle.example"},
        client=("172.20.0.5", 40000),
    )
    assert not forwarded_chain_trusted(req3)
