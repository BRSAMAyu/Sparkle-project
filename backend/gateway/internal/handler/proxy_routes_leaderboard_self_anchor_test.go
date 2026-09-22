/*
Core: <cognitive|execution|bridge|infra>
Phase: none
Stage: regression

D-COMM-1: 自我 7 日锚视图（GET /api/v1/leaderboards/self-anchor）网关可达性。

裁决（v3-output/D-COMMUNITY/DESIGN.md §3.2 + KNOWN_CODE_DEBT_LEDGER P1 #3）：
leaderboards 组保持 wildcard-only 代理（registerREST "/*path"，gamification-eval
P1-2 先例）。gin 1.9.1 在 catch-all 同级注册静态路由会 panic
（"conflicts with existing wildcard"），故自我锚视图不加显式路由行——引擎侧
新端点经 wildcard 自动可达且过组级 authMiddleware。本测试固化：
  1. /api/v1/leaderboards/self-anchor 经 wildcard 代理到引擎（200，路径原样）；
  2. 该路径受组级 authMiddleware 保护，未认证请求不会到达引擎；
  3. 既有榜面路径（bare collection 与子路径）不回归。
*/
package handler

import (
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/middleware"
)

// proxySetupWithAuth mirrors proxy_routes_trailing_slash_test.go's
// newProxyTestSetup but lets the test inject the auth middleware behavior.
func proxySetupWithAuth(t *testing.T, auth func(*gin.Context)) (*gin.Engine, *pathRecorder) {
	t.Helper()
	gin.SetMode(gin.TestMode)

	rec := &pathRecorder{}
	upstream := httptest.NewServer(rec.handler())
	t.Cleanup(upstream.Close)

	target, err := url.Parse(upstream.URL)
	if err != nil {
		t.Fatalf("parse upstream url: %v", err)
	}
	proxy := httputil.NewSingleHostReverseProxy(target)

	abTest := middleware.NewABTestMiddleware(&middleware.ABTestConfig{
		BackendURL: upstream.URL,
		Timeout:    3 * time.Second,
		Enabled:    false,
	})

	h := NewProxyRoutesHandler(proxy, abTest, zap.NewNop())

	router := gin.New()
	api := router.Group("/api/v1")
	h.RegisterProxyRoutes(api, auth)
	return router, rec
}

func TestLeaderboardSelfAnchorProxiedThroughWildcard(t *testing.T) {
	passAuth := func(c *gin.Context) {
		c.Set("user_id", "test-user-123")
		c.Set("auth_token", "test-token-abc")
		c.Next()
	}
	router, rec := proxySetupWithAuth(t, passAuth)

	if code := doGET(t, router, "/api/v1/leaderboards/self-anchor"); code != http.StatusOK {
		t.Fatalf("GET /api/v1/leaderboards/self-anchor = %d, want 200", code)
	}
	if got := rec.last(); got != "/api/v1/leaderboards/self-anchor" {
		t.Fatalf("upstream path = %q, want /api/v1/leaderboards/self-anchor", got)
	}
}

func TestLeaderboardSelfAnchorRequiresAuth(t *testing.T) {
	denyAuth := func(c *gin.Context) {
		c.AbortWithStatus(http.StatusUnauthorized)
	}
	router, rec := proxySetupWithAuth(t, denyAuth)

	if code := doGET(t, router, "/api/v1/leaderboards/self-anchor"); code != http.StatusUnauthorized {
		t.Fatalf("unauthenticated GET /api/v1/leaderboards/self-anchor = %d, want 401", code)
	}
	if got := rec.last(); got == "/api/v1/leaderboards/self-anchor" {
		t.Fatalf("unauthenticated request reached upstream: %q", got)
	}
}

func TestLeaderboardExistingFacesNotRegressed(t *testing.T) {
	passAuth := func(c *gin.Context) {
		c.Set("user_id", "test-user-123")
		c.Next()
	}
	router, rec := proxySetupWithAuth(t, passAuth)

	for _, path := range []string{"/api/v1/leaderboards", "/api/v1/leaderboards/summary", "/api/v1/leaderboards/my-rank"} {
		if code := doGET(t, router, path); code != http.StatusOK {
			t.Fatalf("GET %s = %d, want 200 (wildcard proxy regression)", path, code)
		}
	}
	if got := rec.last(); got != "/api/v1/leaderboards/my-rank" {
		t.Fatalf("upstream path = %q, want /api/v1/leaderboards/my-rank", got)
	}
}
