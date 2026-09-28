"""
Core: infra
Phase: none
Stage: N/A

FIX-559 回归钉：/docs 与 /redoc 页面资产引用与 CSP 头相容性。

缺陷（2026-09-28 V4-B04 旁路采集发现）：FastAPI 内置 docs/redoc 模板引用
jsdelivr CDN 资产并内联初始化脚本，被 SecurityHeadersMiddleware 的 CSP
（script-src/style-src 'self'）拦截，页面对任何访客不可渲染。

修复口径（本钉守住的不变量）：
1. 页面全部资产引用同源（/static/docs/* 与 /openapi.json），无第三方 http(s) 外链；
2. 页面无可执行内联脚本（初始化参数走 type="application/json" 数据块 +
   外置 swagger-init.js）——即页面不依赖 CSP 的 'unsafe-inline'；
3. 文档路由与自托管资产全部 200 可达；
4. swagger-ui / redoc 自托管资产与 B04 逐字节核验副本 sha256 一致
   （台账字节锚，防止无痕替换）；
5. CSP 头保持 'self' 严格口径：不因文档页引入 jsdelivr/第三方放行项。
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

# B04 字节锚（v4/evidence/V4-B04/ 旁路采集核验的 CDN 原件 sha256）
B04_SWAGGER_UI_CSS_SHA256 = "1ac324f7dcd27e4b9386b4bd6421271ec147e922a22c05ba24b11515e9aa6321"
B04_SWAGGER_UI_BUNDLE_SHA256 = "62df541529080464a7660adc793eab7128c6193ce3be24ddc1e0e0a4a63edc2f"
REDOC_STANDALONE_SHA256 = "dcaf76612bc4a3fbcc923a8966dee2f6146a5f32e5ce1b6f02dd60cbbf89500b"


class _AssetRefParser(HTMLParser):
    """收集页面全部 src/href 引用与 script 标签形态。"""

    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []
        self.scripts: list[dict[str, Optional[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attr_map = dict(attrs)
        if tag in ("script", "link", "img"):
            for key in ("src", "href"):
                if attr_map.get(key):
                    self.refs.append(attr_map[key])
        if tag == "script":
            self.scripts.append({"src": attr_map.get("src"), "type": attr_map.get("type")})


def _parse_page(html: str) -> _AssetRefParser:
    parser = _AssetRefParser()
    parser.feed(html)
    return parser


def _parse_csp_directives(csp: str) -> dict[str, list[str]]:
    directives: dict[str, list[str]] = {}
    for part in csp.split(";"):
        tokens = part.strip().split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestDocsCspCompatibility:
    """文档页资产引用 × CSP 头相容性（FIX-559 回归钉）。"""

    @pytest.mark.parametrize("page_path", ["/docs", "/redoc"])
    def test_page_renders_and_assets_same_origin(self, client: TestClient, page_path: str) -> None:
        resp = client.get(page_path)
        assert resp.status_code == 200, f"{page_path} 不可渲染即回归（FIX-559）"
        parsed = _parse_page(resp.text)
        assert parsed.refs, f"{page_path} 无资产引用，页面疑似空壳"
        for ref in parsed.refs:
            assert not ref.startswith(("http://", "https://")), (
                f"{page_path} 引用第三方资产 {ref}——将再次被 script-src/style-src " f"'self' 拦截（FIX-559 缺陷复发）"
            )

    @pytest.mark.parametrize("page_path", ["/docs", "/redoc"])
    def test_no_executable_inline_script(self, client: TestClient, page_path: str) -> None:
        """页面不得依赖内联可执行脚本（否则 script-src 'self' 拦截初始化逻辑）。"""
        resp = client.get(page_path)
        assert resp.status_code == 200
        parsed = _parse_page(resp.text)
        for script in parsed.scripts:
            if script["src"]:
                continue
            # 允许非执行型数据块（swagger-init 参数以 application/json 传入）
            assert script["type"] == "application/json", (
                f"{page_path} 存在可执行内联 <script>（type={script['type']}），"
                f"被 script-src 'self' 拦截即文档页白屏（FIX-559 缺陷复发）"
            )

    def test_csp_header_keeps_self_strict(self, client: TestClient) -> None:
        """CSP 头不得为文档页引入第三方放行面（jsdelivr 等），只许同源。"""
        csp = client.get("/docs").headers.get("Content-Security-Policy", "")
        assert csp, "CSP 头缺失——安全口径回归"
        script_src = _parse_csp_directives(csp).get("script-src", [])
        assert "'self'" in script_src, f"script-src 失去 'self'：{script_src}"
        for forbidden in ("cdn.jsdelivr.net", "'unsafe-eval'"):
            if forbidden == "'unsafe-eval'" and settings.DEBUG:
                continue  # DEBUG 分支既有口径，非本卡改动
            assert (
                forbidden not in script_src
            ), f"script-src 出现 {forbidden}——文档页改走第三方放行（超出 FIX-559 自托管口径）"

    @pytest.mark.parametrize(
        ("page_path", "expected_assets"),
        [
            (
                "/docs",
                [
                    "/static/docs/swagger-ui.css",
                    "/static/docs/swagger-ui-bundle.js",
                    "/static/docs/swagger-init.js",
                    "/static/docs/favicon.png",
                ],
            ),
            (
                "/redoc",
                [
                    "/static/docs/redoc.standalone.js",
                    "/static/docs/favicon.png",
                ],
            ),
        ],
    )
    def test_selfhosted_assets_reachable_200(
        self, client: TestClient, page_path: str, expected_assets: list[str]
    ) -> None:
        """页面引用的每个自托管资产必须 200 可达（离线访客视角）。"""
        resp = client.get(page_path)
        assert resp.status_code == 200
        parsed = _parse_page(resp.text)
        for asset in expected_assets:
            assert asset in parsed.refs, f"{page_path} 未引用自托管资产 {asset}（模板回退即回归）"
            asset_resp = client.get(asset)
            assert asset_resp.status_code == 200, f"自托管资产 {asset} 不可达（FIX-559 回归）"

    def test_openapi_json_reachable_for_docs_xhr(self, client: TestClient) -> None:
        """/openapi.json 是文档页唯一 connect-src 目标，必须同源 200 可达。"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert b"openapi" in resp.content[:64].lower()

    def test_oauth2_redirect_route_parity(self, client: TestClient) -> None:
        """/docs/oauth2-redirect 与上游默认一致保留。"""
        resp = client.get("/docs/oauth2-redirect")
        assert resp.status_code == 200


class TestSelfHostedAssetByteAnchors:
    """自托管资产字节锚：与 B04 逐字节核验副本 sha256 一致。"""

    def test_swagger_ui_css_matches_b04_copy(self, client: TestClient) -> None:
        body = client.get("/static/docs/swagger-ui.css").content
        assert hashlib.sha256(body).hexdigest() == B04_SWAGGER_UI_CSS_SHA256

    def test_swagger_ui_bundle_matches_b04_copy(self, client: TestClient) -> None:
        body = client.get("/static/docs/swagger-ui-bundle.js").content
        assert hashlib.sha256(body).hexdigest() == B04_SWAGGER_UI_BUNDLE_SHA256

    def test_redoc_standalone_pinned(self, client: TestClient) -> None:
        body = client.get("/static/docs/redoc.standalone.js").content
        assert hashlib.sha256(body).hexdigest() == REDOC_STANDALONE_SHA256


class TestSwaggerInitScript:
    """外置初始化脚本契约（替代上游内联模板，FIX-559）。"""

    def test_init_script_reads_json_config_block(self, client: TestClient) -> None:
        init_js = client.get("/static/docs/swagger-init.js").text
        assert "swagger-init-config" in init_js
        assert "SwaggerUIBundle" in init_js

    def test_json_config_block_carries_spec_url(self, client: TestClient) -> None:
        html = client.get("/docs").text
        match = re.search(
            r'<script id="swagger-init-config" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        assert match, "swagger-init-config 数据块缺失"
        assert "/openapi.json" in match.group(1)
