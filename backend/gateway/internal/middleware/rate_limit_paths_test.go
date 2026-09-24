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

func TestEndpointSpecificRateLimit(t *testing.T) {
	endpointMW := EndpointSpecificRateLimit("/api/v1/chat", 0, 1)
	require.Equal(t, http.StatusOK, serveWithMiddleware(endpointMW, "/endpoint", "").Code)
	require.Equal(t, http.StatusTooManyRequests, serveWithMiddleware(endpointMW, "/endpoint", "").Code)
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
