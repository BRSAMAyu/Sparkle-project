package main

// V3-FIX-426 / V3-FIX-428 代理转发头守卫（过真实 setupProxy，非复刻逻辑）。
//
// 修复前实证（wt735 复核探针同形态 + 本文件修前红实录）：
//   - Director 手工追加 XFF 与 stdlib ReverseProxy（Director 模式）默认追加
//     叠加，后端实收 "8.8.8.8, 203.0.113.7, 203.0.113.7"（真实 IP 出现两次）；
//   - req.Host 先被覆写为内网 target host，XFH 兜底读到覆写后的值，客户端
//     原始 Host 完全丢失；客户端自带伪造 XFH 原样透传（可伪造面）。
//
// 修复后契约（Rewrite 单一出口）：
//   - XFF：入站链保留 + 恰好追加一次真实 client IP（右起第 N 段解析语义
//     不变，EI-09；伪造段居左由 Python 侧解析弃用）；
//   - XFH：恒为客户端原始 Host（stdlib SetXForwarded 取 In.Host），伪造 XFH
//     不再透传；engine 侧消费方仍须自行做可信判断（见
//     backend/tests/api/test_vocabulary_external_base_url.py）；
//   - XFP：入站值保留（上游 TLS 终止方语义），缺省 http。
//
// Python 侧右起解析由 backend/tests/core/test_rate_limit_real_ip.py 与
// backend/tests/core/test_client_ip_attribution.py 分别守卫。

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/sparkle/gateway/internal/config"
	"go.uber.org/zap"
)

// backendCapture 记录后端实际收到的请求头与 Host。
type backendCapture struct {
	host    string
	headers http.Header
}

func setupProxyWithBackend(t *testing.T) (*proxyBundle, *backendCapture) {
	t.Helper()

	capture := &backendCapture{}
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capture.host = r.Host
		capture.headers = r.Header.Clone()
		w.WriteHeader(http.StatusOK)
		_, _ = io.WriteString(w, "ok")
	}))
	t.Cleanup(backend.Close)

	proxy, err := setupProxy(&config.Config{BackendURL: backend.URL}, zap.NewNop())
	if err != nil {
		t.Fatalf("setupProxy: %v", err)
	}
	return proxy, capture
}

func serveThroughProxy(t *testing.T, proxy *proxyBundle, headers map[string]string, remoteAddr, host string) {
	t.Helper()

	req := httptest.NewRequest(http.MethodGet, "http://client.example/api/v1/health", nil)
	req.RemoteAddr = remoteAddr
	req.Host = host
	for k, v := range headers {
		req.Header.Set(k, v)
	}

	rec := httptest.NewRecorder()
	proxy.proxy.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("proxy round-trip status = %d, want 200", rec.Code)
	}
}

// V3-FIX-426：XFF 恰好追加一次真实 client IP（Director 手工追加 × stdlib
// 默认追加的冗余双写收拢后）。伪造段保持居首段不变——安全性由 Python 侧
// 右起第 N 段解析保证（EI-09），网关契约只承诺「入站链完整、真实 IP 在最右
// 且只出现一次」。
func TestProxyAppendsClientIPToXFFExactlyOnce(t *testing.T) {
	proxy, capture := setupProxyWithBackend(t)

	serveThroughProxy(t, proxy, map[string]string{"X-Forwarded-For": "8.8.8.8"}, "203.0.113.7:12345", "client.example")

	got := capture.headers.Get("X-Forwarded-For")
	want := "8.8.8.8, 203.0.113.7"
	if got != want {
		t.Fatalf("backend X-Forwarded-For = %q, want %q (double append = stdlib + manual both fired)", got, want)
	}
}

// V3-FIX-426 连带：无客户端 XFF 时后端收到的 XFF 恰为单个真实 client IP。
func TestProxySetsXFFToClientIPWhenAbsent(t *testing.T) {
	proxy, capture := setupProxyWithBackend(t)

	serveThroughProxy(t, proxy, nil, "203.0.113.7:12345", "client.example")

	got := capture.headers.Get("X-Forwarded-For")
	if got != "203.0.113.7" {
		t.Fatalf("backend X-Forwarded-For = %q, want %q", got, "203.0.113.7")
	}
}

// V3-FIX-428：不带 XFH 的请求，后端收到的 XFH 必须是客户端原始 Host，
// 而非覆写后的内网 target host（修复前恒为后端 host，原始 Host 完全丢失）。
func TestProxyPreservesOriginalHostInXForwardedHost(t *testing.T) {
	proxy, capture := setupProxyWithBackend(t)

	serveThroughProxy(t, proxy, nil, "203.0.113.7:12345", "api.sparkle.example")

	got := capture.headers.Get("X-Forwarded-Host")
	if got != "api.sparkle.example" {
		t.Fatalf("backend X-Forwarded-Host = %q, want original client host %q (leaked internal host %q)", got, "api.sparkle.example", capture.host)
	}
}

// V3-FIX-428：客户端自带伪造 XFH 不得透传——SetXForwarded 无条件取 In.Host
// （客户端原始 Host）。修复前伪造值原样透传（可伪造面）。
func TestProxyStripsForgedClientXFH(t *testing.T) {
	proxy, capture := setupProxyWithBackend(t)

	serveThroughProxy(t, proxy, map[string]string{
		"X-Forwarded-Host": "evil.example.com",
		"X-Forwarded-For":  "203.0.113.7",
	}, "203.0.113.7:12345", "api.sparkle.example")

	if got := capture.headers.Get("X-Forwarded-Host"); got != "api.sparkle.example" {
		t.Fatalf("backend X-Forwarded-Host = %q, want original client host %q (forged value leaked)", got, "api.sparkle.example")
	}
}

// 钉测：上游 TLS 终止方（nginx/ingress）写入的 XFP 保留，不被网关内网明文段
// 覆盖为 http（修复前 Director 亦保留入站 XFP，语义不变）。
func TestProxyPreservesUpstreamXForwardedProto(t *testing.T) {
	proxy, capture := setupProxyWithBackend(t)

	serveThroughProxy(t, proxy, map[string]string{"X-Forwarded-Proto": "https"}, "203.0.113.7:12345", "client.example")

	if got := capture.headers.Get("X-Forwarded-Proto"); got != "https" {
		t.Fatalf("backend X-Forwarded-Proto = %q, want upstream %q preserved", got, "https")
	}
}

// V3-FIX-428 连带：X-Forwarded-Proto 缺省仍为 http（网关内为明文段）。
func TestProxySetsXForwardedProtoDefault(t *testing.T) {
	proxy, capture := setupProxyWithBackend(t)

	serveThroughProxy(t, proxy, nil, "203.0.113.7:12345", "client.example")

	if got := capture.headers.Get("X-Forwarded-Proto"); got != "http" {
		t.Fatalf("backend X-Forwarded-Proto = %q, want %q", got, "http")
	}
}
