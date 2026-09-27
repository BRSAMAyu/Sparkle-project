package main

// V3-FIX-483 守卫：dev/test 缺省不再落入 gin v1.9.1 缺省 trust-all。
//
// 修复前实证（wt748 独立审查 CONFIRMED，台账 V3-FIX-483）：gin v1.9.1 缺省
// trustedProxies=0.0.0.0/0,::/0 且 RemoteIPHeaders 含 X-Real-IP（gin.go New()
// 缺省），validateHeader 右起扫描 trust-all 下返回 XFF 最左段——直连 :8080 的
// 对端任写 X-Forwarded-For/X-Real-IP 即任控 c.ClientIP()，per-IP 限流键与 WS
// 升级预鉴权桶可轮转绕过、审计 client_ip 可投毒；setupRouter 原逻辑仅 prod 缺
// TRUSTED_PROXIES 时 Fatal，dev 分支不设任何信任面（落入库缺省 trust-all）。
//
// 修后契约（applyTrustedProxies 单一出口）：
//   - 显式 TRUSTED_PROXIES：一律按清单（生产唯一合法形态，路径不变）；
//   - 生产缺 TRUSTED_PROXIES：Fatal 闸不变；
//   - dev/test 缺省：SetTrustedProxies(nil)——gin 文档语义 = ClientIP() 恒取
//     TCP 对端地址，X-Forwarded-For/X-Real-IP 不参与解析：伪造轮转从根上失效。
//     本地反代拓扑（nginx→gateway dev）需要按真实客户端归因时显式设
//     TRUSTED_PROXIES（迁移注记见 v3-output/WT758-PROXY/notes.md）。

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
)

func newIPProbeRouter(t *testing.T, cfg *config.Config) *gin.Engine {
	t.Helper()

	gin.SetMode(gin.TestMode)
	r := gin.New()
	applyTrustedProxies(r, cfg, zap.NewNop())
	r.GET("/echo-ip", func(c *gin.Context) {
		c.String(http.StatusOK, c.ClientIP())
	})
	return r
}

func probeClientIP(t *testing.T, r *gin.Engine, remoteAddr string, headers map[string]string) string {
	t.Helper()

	req := httptest.NewRequest(http.MethodGet, "/echo-ip", nil)
	req.RemoteAddr = remoteAddr
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	return rec.Body.String()
}

// dev 缺省（不设 TRUSTED_PROXIES）：伪造 X-Forwarded-For / X-Real-IP 不得控制
// ClientIP()——限流/WS 预鉴权桶键与审计字段恒取 TCP 对端。修复前 trust-all 下
// 返回 XFF 最左段 8.8.8.8，红。
func TestDevDefaultIgnoresSpoofedForwardedHeaders(t *testing.T) {
	r := newIPProbeRouter(t, &config.Config{})

	got := probeClientIP(t, r, "203.0.113.7:12345", map[string]string{
		"X-Forwarded-For": "8.8.8.8, 9.9.9.9",
		"X-Real-IP":       "10.10.10.10",
	})
	require.Equal(t, "203.0.113.7", got, "dev default ClientIP controlled by spoofed forwarded headers (V3-FIX-483)")
}

// 显式 TRUSTED_PROXIES 一律生效（生产/LB 路径不回退）：可信对端 10.0.0.5 转发的
// XFF 右起第一个非可信段归因。修复前即有行为，钉住不回退。
func TestExplicitTrustedProxiesStillHonored(t *testing.T) {
	r := newIPProbeRouter(t, &config.Config{TrustedProxies: []string{"10.0.0.0/8"}})

	got := probeClientIP(t, r, "10.0.0.5:443", map[string]string{"X-Forwarded-For": "8.8.8.8, 203.0.113.7"})
	require.Equal(t, "203.0.113.7", got)

	// 不可信对端直连：即便带了 XFF 也按 TCP 对端归因（gin 既定语义）。
	got = probeClientIP(t, r, "203.0.113.9:8080", map[string]string{"X-Forwarded-For": "8.8.8.8"})
	require.Equal(t, "203.0.113.9", got)
}
