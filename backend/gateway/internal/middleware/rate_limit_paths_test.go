package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
	"golang.org/x/time/rate"
)

func serveWithMiddleware(mw gin.HandlerFunc, path string, userID string) *httptest.ResponseRecorder {
	router := gin.New()
	router.Use(func(c *gin.Context) {
		if userID != "" {
			c.Set("user_id", userID)
		}
		c.Next()
	})
	router.Use(mw)
	router.Any(path, func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"ok":              true,
			"rate_limit_info": c.GetStringMap("rate_limit_info"),
		})
	})
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, path, nil)
	req.RemoteAddr = "127.0.0.1:12345"
	router.ServeHTTP(w, req)
	return w
}

func TestRateLimiterEvictsOldestVisitor(t *testing.T) {
	rl := NewRateLimiterWithMax(rate.Limit(1), 1, 2)
	defer rl.Stop()

	_ = rl.getVisitor("old")
	_ = rl.getVisitor("new")
	rl.mu.Lock()
	rl.visitors["old"].lastSeen = time.Now().Add(-time.Hour)
	rl.mu.Unlock()

	_ = rl.getVisitor("newest")

	rl.mu.RLock()
	defer rl.mu.RUnlock()
	require.Len(t, rl.visitors, 2)
	require.NotContains(t, rl.visitors, "old")
	require.Contains(t, rl.visitors, "new")
	require.Contains(t, rl.visitors, "newest")
}

func TestRateLimitMiddlewareAllowsThenRejects(t *testing.T) {
	rl := NewRateLimiter(rate.Limit(0), 1)
	defer rl.Stop()
	mw := RateLimitMiddleware(rl)

	first := serveWithMiddleware(mw, "/limited", "")
	require.Equal(t, http.StatusOK, first.Code)
	require.Equal(t, "1", first.Header().Get("X-RateLimit-Limit"))

	second := serveWithMiddleware(mw, "/limited", "")
	require.Equal(t, http.StatusTooManyRequests, second.Code)
}

func TestUserAndEndpointSpecificRateLimits(t *testing.T) {
	userMW := UserBasedRateLimit(100, 1)
	first := serveWithMiddleware(userMW, "/user", "user-1")
	require.Equal(t, http.StatusOK, first.Code)

	fallback := serveWithMiddleware(UserBasedRateLimit(100, 1), "/user-ip", "")
	require.Equal(t, http.StatusOK, fallback.Code)

	endpointMW := EndpointSpecificRateLimit("/api/v1/chat", 0, 1)
	require.Equal(t, http.StatusOK, serveWithMiddleware(endpointMW, "/endpoint", "").Code)
	require.Equal(t, http.StatusTooManyRequests, serveWithMiddleware(endpointMW, "/endpoint", "").Code)
}

func TestAdaptiveAndWebSocketRateLimitBranches(t *testing.T) {
	adaptive := AdaptiveRateLimitMiddleware(100, 10)

	for _, tc := range []struct {
		method string
		path   string
	}{
		{method: http.MethodGet, path: "/api/v1/tasks"},
		{method: http.MethodPost, path: "/api/v1/tasks"},
		{method: http.MethodPost, path: "/api/v1/auth/login"},
	} {
		router := gin.New()
		router.Use(adaptive)
		router.Handle(tc.method, tc.path, func(c *gin.Context) {
			_, exists := c.Get("rate_limit_info")
			require.True(t, exists)
			c.Status(http.StatusOK)
		})
		w := httptest.NewRecorder()
		req := httptest.NewRequest(tc.method, tc.path, nil)
		req.RemoteAddr = "127.0.0.1:22222"
		router.ServeHTTP(w, req)
		require.Equal(t, http.StatusOK, w.Code)
	}

	previousRate := GlobalRateLimitConfig.WebSocketConnectionsPerMinute
	previousBurst := GlobalRateLimitConfig.WebSocketBurst
	GlobalRateLimitConfig.WebSocketConnectionsPerMinute = 0
	GlobalRateLimitConfig.WebSocketBurst = 1
	defer func() {
		GlobalRateLimitConfig.WebSocketConnectionsPerMinute = previousRate
		GlobalRateLimitConfig.WebSocketBurst = previousBurst
	}()

	wsMW := WebSocketRateLimitMiddleware()
	require.Equal(t, http.StatusOK, serveWithMiddleware(wsMW, "/ws", "").Code)
	require.Equal(t, http.StatusTooManyRequests, serveWithMiddleware(wsMW, "/ws", "").Code)
}

func TestSlidingWindowMiddlewareRedisAndFallback(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	mw := SlidingWindowRateLimitMiddleware(rdb, time.Minute, 1)
	require.Equal(t, http.StatusOK, serveWithMiddleware(mw, "/sliding", "user-1").Code)
	require.Equal(t, http.StatusTooManyRequests, serveWithMiddleware(mw, "/sliding", "user-1").Code)

	mr.Close()
	fallback := SlidingWindowRateLimitMiddleware(rdb, time.Minute, 1)
	require.Equal(t, http.StatusOK, serveWithMiddleware(fallback, "/fallback", "user-2").Code)
	require.Equal(t, http.StatusTooManyRequests, serveWithMiddleware(fallback, "/fallback", "user-2").Code)
}

func TestDistributedRateLimiterParsingEdges(t *testing.T) {
	gotFloat, err := parseScriptFloat([]byte("1.25"))
	require.NoError(t, err)
	require.Equal(t, 1.25, gotFloat)

	gotFloat, err = parseScriptFloat(int64(2))
	require.NoError(t, err)
	require.Equal(t, 2.0, gotFloat)

	_, err = parseScriptFloat(struct{}{})
	require.Error(t, err)

	gotInt, err := parseScriptInt("3.9")
	require.NoError(t, err)
	require.Equal(t, int64(3), gotInt)

	gotInt, err = parseScriptInt([]byte("4"))
	require.NoError(t, err)
	require.Equal(t, int64(4), gotInt)

	_, err = parseScriptInt(struct{}{})
	require.Error(t, err)
}
