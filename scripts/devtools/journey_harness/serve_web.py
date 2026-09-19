#!/usr/bin/env python3
"""Flutter Web SPA 静态服务器 + 同源反向代理（journey harness web backend 用）。

用法： python3 serve_web.py [port] [web_dir] [api_target]
  api_target 默认 http://localhost:8080。

为什么需要反向代理（2026-09-19 B-03 实测发现）：
  Flutter Web 客户端对 /auth/register 等请求携带 `X-Idempotency-Key` 头，
  而网关 CORS Allow-Headers 白名单不含该头 → 跨源 preflight 失败 → 浏览器
  静默拦截全部 API（UI 无任何错误提示）。把静态资源与 API 收敛到同一
  origin（经本代理转发到网关）即消除 preflight，等价生产 nginx 拓扑，
  不属于绕过体验层（App 仍是真实 UI 驱动）。

路由：
  /api/...  → 反代 {api_target}/api/...   （GET/POST/PUT/PATCH/DELETE）
  /ws/...   → 反代 WebSocket 升级与双向转发
  其余      → 静态文件；未知路径回退 index.html（GoRouter 刷新支持）
"""

from __future__ import annotations

import http.client
import http.server
import os
import socket
import socketserver
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
}


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    api_target: str = "http://localhost:8080"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB_DIR), **kw)

    # ---------- 反代 ----------
    def _is_api(self) -> bool:
        return self.path.startswith("/api/") or self.path == "/api"

    @staticmethod
    def _trace_enabled() -> bool:
        return os.environ.get("SPARKLE_PROXY_TRACE") == "1"

    def _trace(self, kind: str, payload: bytes) -> None:
        """SPARKLE_PROXY_TRACE=1 时把 auth 流量落盘（journey 取证用，默认关闭）。"""
        if not self._trace_enabled() or "/auth/" not in self.path:
            return
        trace_path = Path(os.environ.get("SPARKLE_PROXY_TRACE_FILE") or "/tmp/proxy_traffic.log")
        with trace_path.open("a", encoding="utf-8") as fh:
            fh.write(f"== {kind} {self.path}\n{payload.decode('utf-8', 'replace')[:4000]}\n")

    def _is_ws(self) -> bool:
        return self.path.startswith("/ws/")

    def _proxy(self, method: str) -> None:
        parts = urlsplit(self.api_target)
        host, port = parts.hostname, parts.port or 80
        target_path = self.path
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP}
        if body:
            self._trace("REQ", body)
        try:
            conn = http.client.HTTPConnection(host, port, timeout=60)
            conn.request(method, target_path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self._trace(f"RESP({resp.status})", data)
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(data)
            conn.close()
        except Exception as exc:  # 网关不可达 => 明确 502，不留悬挂连接
            self.send_response(502)
            msg = f"[serve_web] proxy error: {exc}".encode()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _proxy_ws(self) -> None:
        """最小 WebSocket 双向转发：读完 upgrade 请求后原样转发并裸转发字节流。"""
        parts = urlsplit(self.api_target)
        upstream = socket.create_connection((parts.hostname, parts.port or 80), timeout=30)
        # 原样重放请求行与头（Host 头改为上游）
        req_lines = [f"{self.command} {self.path} HTTP/1.1"]
        for k, v in self.headers.items():
            if k.lower() == "host":
                v = self.headers["Host"].split(":", 1)[0] + (f":{port_part}" if (port_part := str(parts.port or "")) else "")
            req_lines.append(f"{k}: {v}")
        payload = ("\r\n".join(req_lines) + "\r\n\r\n").encode()
        upstream.sendall(payload)
        client_conn = self.connection
        client_conn.sendall(b"")  # noqa: 占位；等待上游响应后开始转发

        def pump(src: socket.socket, dst: socket.socket) -> None:
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

        t = threading.Thread(target=pump, args=(client_conn, upstream), daemon=True)
        t.start()
        try:
            while True:
                data = upstream.recv(65536)
                if not data:
                    break
                client_conn.sendall(data)
        except OSError:
            pass
        finally:
            try:
                upstream.close()
            except OSError:
                pass

    def do_GET(self):  # noqa: N802
        if self._is_ws():
            self._proxy_ws()
        elif self._is_api():
            self._proxy("GET")
        else:
            super().do_GET()

    def do_POST(self):  # noqa: N802
        self._proxy("POST")

    def do_PUT(self):  # noqa: N802
        self._proxy("PUT")

    def do_PATCH(self):  # noqa: N802
        self._proxy("PATCH")

    def do_DELETE(self):  # noqa: N802
        self._proxy("DELETE")

    def do_HEAD(self):  # noqa: N802
        if self._is_api():
            self._proxy("HEAD")
        else:
            super().do_HEAD()

    # ---------- 静态 SPA 回退 ----------
    def send_head(self):
        if self._is_api() or self._is_ws():
            return super().send_head()
        path = self.translate_path(self.path)
        if not os.path.exists(path) or (
            os.path.isdir(path) and not os.path.exists(os.path.join(path, "index.html"))
        ):
            self.path = "/index.html"
        return super().send_head()

    def log_message(self, fmt, *args):
        pass


class ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8437
    web_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("mobile/build/web")
    if len(sys.argv) > 3:
        ProxyHandler.api_target = sys.argv[3]
    WEB_DIR = web_dir.resolve()
    if not (WEB_DIR / "index.html").exists():
        print(f"[serve_web] {WEB_DIR}/index.html 不存在——先 flutter build web")
        sys.exit(2)
    with ThreadingTCPServer(("127.0.0.1", port), ProxyHandler) as httpd:
        print(
            f"serving {WEB_DIR} at http://127.0.0.1:{port}/ (api-> {ProxyHandler.api_target})",
            flush=True,
        )
        httpd.serve_forever()
