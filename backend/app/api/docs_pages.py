"""
API 文档页面（/docs、/redoc）——自托管资产 + 外置初始化脚本（FIX-559）。

背景（FIX-559，2026-09-28 V4-B04 发现）：FastAPI 内置 docs/redoc 模板引用
jsdelivr CDN 资产并内联 <script> 初始化，而本应用的 SecurityHeadersMiddleware
对全部响应施加 CSP（script-src/style-src 'self'），页面自身引用的资产与内联
脚本均被拦截，对任何访客不可渲染。

本模块的处理：
1. 资产全部自托管在 ``backend/app/static/docs/``（swagger-ui-dist@5.33.0 与
   redoc@2.5.4，sha256 见同目录 LICENSES.md，其中 swagger-ui 两件资产与
   V4-B04 逐字节核验副本一致）；
2. Swagger UI 初始化脚本外置为同源静态文件（swagger-init.js），页面内不放
   内联脚本，动态参数经 ``type="application/json"`` 数据块传入（CSP
   script-src 不约束非执行型 script 数据块）——CSP 保持 'self' 严格口径，
   中间件无需对文档路由做任何放宽；
3. ReDoc 页面放弃默认模板里的 Google Fonts 外链（同样被 style-src 'self'
   拦截），回退系统字体——纯外观差异，换取 CSP 不放行第三方字体源。

oauth2-redirect 页保留与上游一致的路由（其内联脚本在本 CSP 下同样受限，
与上游默认行为一致；本 API 文档鉴权为 HTTPBearer/apiKey，不触发 OAuth2
弹窗跳转流程，故不额外处理）。
"""

from __future__ import annotations

import json

from fastapi import Request
from fastapi.responses import HTMLResponse

_SWAGGER_JS = "/static/docs/swagger-ui-bundle.js"
_SWAGGER_CSS = "/static/docs/swagger-ui.css"
_REDOC_JS = "/static/docs/redoc.standalone.js"
_FAVICON = "/static/docs/favicon.png"
_SWAGGER_INIT_JS = "/static/docs/swagger-init.js"
_OAUTH2_REDIRECT = "/docs/oauth2-redirect"


def _root_path(request: Request) -> str:
    """与 FastAPI 内置 docs 处理一致：反代挂载时拼接 root_path 前缀。"""
    return request.scope.get("root_path", "").rstrip("/")


def swagger_ui_page(request: Request) -> HTMLResponse:
    """Swagger UI 文档页（自托管资产、外置初始化脚本，FIX-559）。"""
    prefix = _root_path(request)
    init_config = {
        "url": f"{prefix}/openapi.json",
        "dom_id": "#swagger-ui",
        "layout": "BaseLayout",
        "deepLinking": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "oauth2RedirectPath": f"{prefix}{_OAUTH2_REDIRECT}",
    }
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link type="text/css" rel="stylesheet" href="{_SWAGGER_CSS}">
    <link rel="shortcut icon" href="{_FAVICON}">
    <title>Sparkle - Swagger UI</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="{_SWAGGER_JS}"></script>
    <!-- FIX-559: 初始化参数经 JSON 数据块传入，执行逻辑在外置 swagger-init.js -->
    <script id="swagger-init-config" type="application/json">{json.dumps(init_config)}</script>
    <script src="{_SWAGGER_INIT_JS}"></script>
    </body>
    </html>
    """
    return HTMLResponse(html)


def redoc_page(request: Request) -> HTMLResponse:
    """ReDoc 文档页（自托管资产、无第三方字体外链，FIX-559）。"""
    prefix = _root_path(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>Sparkle - ReDoc</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="shortcut icon" href="{_FAVICON}">
    <!-- FIX-559: 上游模板的 fonts.googleapis.com 外链被 style-src 'self' 拦截，回退系统字体 -->
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
    </style>
    </head>
    <body>
    <noscript>
        ReDoc requires Javascript to function. Please enable it to browse the documentation.
    </noscript>
    <redoc spec-url="{prefix}/openapi.json"></redoc>
    <script src="{_REDOC_JS}"> </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


def swagger_ui_oauth2_redirect_page() -> HTMLResponse:
    """Swagger UI OAuth2 redirect 页（与上游 fastapi.openapi.docs 一致）。"""
    from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html

    return get_swagger_ui_oauth2_redirect_html()
