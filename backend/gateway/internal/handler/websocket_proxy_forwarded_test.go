package handler

// V3-FIX-482：community/personal WS 代理握手头与 HTTP 代理 Rewrite 契约
// （cmd/server/setup.go / setup_proxy_forwarded_test.go / stdlib
// ProxyRequest.SetXForwarded）对齐的钉测。
//
// 修复前实证（wt748 独立审查 CONFIRMED，台账 V3-FIX-482）：
// buildBackendWebSocketHeaders 对入站 X-Forwarded-For / X-Real-IP 原样 Set
// 透传、不追加本跳 client IP——与 backend/app/core/rate_limiting.py 契约声明
// （「Go 网关（httputil.ReverseProxy / websocket_proxy）在 X-Forwarded-For
// 尾部追加真实 client IP」）相悖：引擎侧对 WS 握手请求按 TRUSTED_PROXY_COUNT
// 右起解析会取到客户端任写的最右段（归因可投毒）。
//
// 修复后契约（与 HTTP 路径 setup_proxy_forwarded_test.go 同一世界）：
//   - XFF：入站链保留 + 恰好追加一次 SplitHostPort(RemoteAddr) host（stdlib
//     SetXForwarded 同型）；RemoteAddr 无端口形（SplitHostPort 失败）时整头
//     不转发（stdlib 同款 fail-closed，宁缺勿假）；
//   - X-Real-IP：不透传——引擎 IP 归因单一出口 get_client_ip 不读该头（426
//     既定口径），透传只会制造第二归因信道。

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/require"
)

func wsBackendHeaders(t *testing.T, remoteAddr string, setHeaders map[string]string) http.Header {
	t.Helper()

	req := httptest.NewRequest(http.MethodGet, "http://gateway.local/api/v1/community/ws/connect", nil)
	req.RemoteAddr = remoteAddr
	for k, v := range setHeaders {
		req.Header.Set(k, v)
	}
	return buildBackendWebSocketHeaders(req, "token-123")
}

// 入站链保留 + 恰好追加一次本跳 client IP（与 HTTP 钉测
// TestProxyAppendsClientIPToXFFExactlyOnce 同形态）。修复前透传不追加，红。
func TestWSProxyAppendsClientIPToXFFExactlyOnce(t *testing.T) {
	headers := wsBackendHeaders(t, "203.0.113.7:12345", map[string]string{"X-Forwarded-For": "8.8.8.8"})

	require.Equal(t, "8.8.8.8, 203.0.113.7", headers.Get("X-Forwarded-For"))
}

// 无客户端 XFF 时后端收到恰为单个真实 client IP（与
// TestProxySetsXFFToClientIPWhenAbsent 同形态）。修复前整头缺席，红。
func TestWSProxySetsXFFToClientIPWhenAbsent(t *testing.T) {
	headers := wsBackendHeaders(t, "203.0.113.7:12345", nil)

	require.Equal(t, "203.0.113.7", headers.Get("X-Forwarded-For"))
}

// 追加的是 SplitHostPort(RemoteAddr) 的 host，端口不入链（stdlib 同型）。
func TestWSProxyAppendUsesHostPartOnly(t *testing.T) {
	headers := wsBackendHeaders(t, "[2001:db8::1]:2049", nil)

	require.Equal(t, "2001:db8::1", headers.Get("X-Forwarded-For"))
}

// X-Real-IP 不透传。修复前原样透传（第二归因信道），红。
func TestWSProxyDropsClientXRealIP(t *testing.T) {
	headers := wsBackendHeaders(t, "203.0.113.7:12345", map[string]string{
		"X-Real-IP":       "10.0.0.8",
		"X-Forwarded-For": "8.8.8.8",
	})

	require.Empty(t, headers.Get("X-Real-IP"))
}

// RemoteAddr 无端口（SplitHostPort 失败）：XFF 整头不转发（stdlib
// SetXForwarded 同款 fail-closed），不透传无法追加归因的入站链。
func TestWSProxyUnparsableRemoteAddrDropsXFF(t *testing.T) {
	headers := wsBackendHeaders(t, "203.0.113.7", map[string]string{"X-Forwarded-For": "8.8.8.8"})

	require.Empty(t, headers.Get("X-Forwarded-For"))
}
