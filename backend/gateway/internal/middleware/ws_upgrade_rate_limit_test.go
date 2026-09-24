package middleware

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func wsUpgradeTestRouter(rps float64, burst int, routes ...string) *gin.Engine {
	router := gin.New()
	mw := WSUpgradeRateLimitMiddleware(nil, rps, burst)
	for _, route := range routes {
		router.GET(route, mw, func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"ok": true})
		})
	}
	return router
}

func performWSUpgradeRequest(router *gin.Engine, target, remoteAddr string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, target, nil)
	req.RemoteAddr = remoteAddr
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, req)
	return recorder
}

// 阈值内放行：burst 之内的握手全部到达 handler（WS-TICKET-DESIGN §6.2-S4 正常重连不误杀口径）。
func TestWSUpgradeRateLimit_AllowsWithinBurst(t *testing.T) {
	t.Parallel()

	router := gin.New()
	router.GET("/ws/chat", WSUpgradeRateLimitMiddleware(nil, 1, 5), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	for i := 0; i < 5; i++ {
		recorder := performWSUpgradeRequest(router, "/ws/chat", "10.0.0.1:12345")
		require.Equal(t, http.StatusOK, recorder.Code, "handshake %d within burst must pass", i+1)
	}
}

// 超阈 429 + Retry-After：bucket 耗尽后的握手被钳，响应带 Retry-After 头与结构化错误体。
func TestWSUpgradeRateLimit_RejectsOverBurstWithRetryAfter(t *testing.T) {
	t.Parallel()

	router := gin.New()
	router.GET("/ws/chat", WSUpgradeRateLimitMiddleware(nil, 1, 3), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	for i := 0; i < 3; i++ {
		recorder := performWSUpgradeRequest(router, "/ws/chat", "10.0.0.2:12345")
		require.Equal(t, http.StatusOK, recorder.Code)
	}

	recorder := performWSUpgradeRequest(router, "/ws/chat", "10.0.0.2:12345")
	require.Equal(t, http.StatusTooManyRequests, recorder.Code)

	retryAfter := recorder.Header().Get("Retry-After")
	require.NotEmpty(t, recorder.Header(), "429 must carry Retry-After header")
	seconds, err := strconv.Atoi(retryAfter)
	require.NoError(t, err, "Retry-After must be delay-seconds format, got %q", retryAfter)
	require.GreaterOrEqual(t, seconds, 1, "Retry-After must be positive")

	var body map[string]any
	require.NoError(t, json.Unmarshal(recorder.Body.Bytes(), &body))
	assert.Equal(t, "rate_limit_exceeded", body["error"])
	assert.Equal(t, float64(seconds), body["retry_after"], "body retry_after must match header")
}

// 5 路由共享预算：一个限流器实例 = 单一 per-IP 预算，换入口不能绕过（§3.3）。
func TestWSUpgradeRateLimit_SharedBudgetAcrossFiveRoutes(t *testing.T) {
	t.Parallel()

	router := wsUpgradeTestRouter(1, 2,
		"/ws/chat",
		"/ws/files",
		"/ws/stt",
		"/api/v1/community/groups/:group_id/ws",
		"/api/v1/community/ws/connect",
	)

	require.Equal(t, http.StatusOK, performWSUpgradeRequest(router, "/ws/chat", "10.0.0.3:12345").Code)
	require.Equal(t, http.StatusOK, performWSUpgradeRequest(router, "/ws/files", "10.0.0.3:12345").Code)

	// 预算耗尽后，未打过的路由同样 429。
	recorder := performWSUpgradeRequest(router, "/api/v1/community/ws/connect", "10.0.0.3:12345")
	assert.Equal(t, http.StatusTooManyRequests, recorder.Code)
}

// per-IP 隔离：不同 IP 各自独立预算。
func TestWSUpgradeRateLimit_PerIPBudgetIsolation(t *testing.T) {
	t.Parallel()

	router := gin.New()
	router.GET("/ws/chat", WSUpgradeRateLimitMiddleware(nil, 1, 1), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	require.Equal(t, http.StatusOK, performWSUpgradeRequest(router, "/ws/chat", "10.0.1.1:12345").Code)
	require.Equal(t, http.StatusTooManyRequests, performWSUpgradeRequest(router, "/ws/chat", "10.0.1.1:12345").Code)
	require.Equal(t, http.StatusOK, performWSUpgradeRequest(router, "/ws/chat", "10.0.1.2:12345").Code)
}

// 钉位在认证之前：预算外请求 429（不触 WsAuth）；预算内请求照常走到 WsAuth 得 401。
func TestWSUpgradeRateLimit_RejectsBeforeAuthWhenExhausted(t *testing.T) {
	t.Parallel()

	cfg := testAuthConfig()
	router := gin.New()
	router.GET("/ws/chat",
		WSUpgradeRateLimitMiddleware(nil, 1, 1),
		WsAuthMiddleware(cfg, nil),
		func(c *gin.Context) { c.JSON(http.StatusOK, gin.H{"ok": true}) },
	)

	// 预算内：无凭据 → 穿过钉层，被 WsAuth 以 401 拒（missing_credentials 路径）。
	recorder := performWSUpgradeRequest(router, "/ws/chat", "10.0.2.1:12345")
	require.Equal(t, http.StatusUnauthorized, recorder.Code)
	assert.Contains(t, recorder.Body.String(), "authorization_token_required")

	// 预算外：钉层先挡，无论凭据如何都是 429。
	recorder = performWSUpgradeRequest(router, "/ws/chat", "10.0.2.1:12345")
	require.Equal(t, http.StatusTooManyRequests, recorder.Code)
}

// 已认证正常握手不受影响：有效 JWT 依次穿过钉层与 WsAuthMiddleware 到达 handler（§6.1 回归）。
func TestWSUpgradeRateLimit_AuthenticatedHandshakeUnaffected(t *testing.T) {
	t.Parallel()

	cfg := testAuthConfig()
	token := makeTestJWT(cfg, nil)
	router := gin.New()
	router.GET("/ws/chat",
		WSUpgradeRateLimitMiddleware(nil, 30, 60),
		WsAuthMiddleware(cfg, nil),
		func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"user_id":        c.GetString("user_id"),
				"ws_auth_method": c.GetString("ws_auth_method"),
			})
		},
	)

	for i := 0; i < 3; i++ {
		req := httptest.NewRequest(http.MethodGet, "/ws/chat", nil)
		req.RemoteAddr = "10.0.3.1:12345"
		req.Header.Set("Authorization", "Bearer "+token)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)
		require.Equal(t, http.StatusOK, recorder.Code, "authenticated handshake %d must pass the pin", i+1)
		assert.Contains(t, recorder.Body.String(), `"user_id":"user-123"`)
		assert.Contains(t, recorder.Body.String(), `"ws_auth_method":"jwt_header"`)
	}
}

// Retry-After 估算函数：至少 1 秒，且随缺口/rate 收敛。
func TestWSUpgradeRetryAfterSeconds(t *testing.T) {
	t.Parallel()

	assert.Equal(t, 1, wsUpgradeRetryAfterSeconds(30, 0), "full deficit at 30rps should round up to 1s")
	assert.Equal(t, 1, wsUpgradeRetryAfterSeconds(30, -5), "negative remaining floors at 1s")
	assert.Equal(t, 2, wsUpgradeRetryAfterSeconds(1, -1), "1.5 token deficit at 1rps rounds up to 2s")
	assert.Equal(t, 1, wsUpgradeRetryAfterSeconds(0, 0), "zero rate guard returns 1s")
}
