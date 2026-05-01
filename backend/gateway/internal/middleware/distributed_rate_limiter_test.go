package middleware

import (
	"context"
	"math"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"golang.org/x/time/rate"
)

func newDistributedRateLimiterForTest(t *testing.T, rate float64, burst, initialTokens int) (*DistributedRateLimiter, *miniredis.Miniredis) {
	t.Helper()

	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() {
		_ = rdb.Close()
	})

	return NewDistributedRateLimiterWithInitialTokens(rdb, rate, burst, initialTokens, "ratelimit-test"), mr
}

func TestRateLimiter_DimensionalCorrectness(t *testing.T) {
	t.Parallel()

	if got := tokensAddedForElapsed(1000, 10); math.Abs(got-10) > 0.01 {
		t.Fatalf("tokensAddedForElapsed(1000ms, 10/s) = %.4f, want 10.00", got)
	}

	limiter, _ := newDistributedRateLimiterForTest(t, 10, 20, 0)
	ctx := context.Background()

	if allowed, _, err := limiter.allowAtMillis(ctx, "dimensional", 0); err != nil {
		t.Fatalf("prime empty bucket: %v", err)
	} else if allowed {
		t.Fatalf("prime empty bucket unexpectedly allowed request")
	}

	allowed, remaining, err := limiter.allowAtMillis(ctx, "dimensional", 1000)
	if err != nil {
		t.Fatalf("allowAtMillis(1000ms): %v", err)
	}
	if !allowed {
		t.Fatalf("expected request to be allowed after 1000ms refill")
	}
	if got := remaining + 1; math.Abs(got-10) > 0.01 {
		t.Fatalf("refilled tokens = %.4f, want 10.00", got)
	}
}

func TestRateLimiter_SteadyState(t *testing.T) {
	t.Parallel()

	limiter, _ := newDistributedRateLimiterForTest(t, 10, 10, 0)
	ctx := context.Background()

	if _, _, err := limiter.allowAtMillis(ctx, "steady", 0); err != nil {
		t.Fatalf("prime empty bucket: %v", err)
	}

	allowedCount := 0
	for request := 1; request <= 30; request++ {
		allowed, _, err := limiter.allowAtMillis(ctx, "steady", int64(request*100))
		if err != nil {
			t.Fatalf("steady-state request %d: %v", request, err)
		}
		if allowed {
			allowedCount++
		}
	}

	if allowedCount < 28 {
		t.Fatalf("steady-state allowed %d requests, want at least 28", allowedCount)
	}
}

func TestRateLimiter_BurstExhaustion(t *testing.T) {
	t.Parallel()

	limiter, _ := newDistributedRateLimiterForTest(t, 2, 5, 5)
	ctx := context.Background()

	for request := 0; request < 5; request++ {
		allowed, _, err := limiter.allowAtMillis(ctx, "burst", 0)
		if err != nil {
			t.Fatalf("initial burst request %d: %v", request, err)
		}
		if !allowed {
			t.Fatalf("initial burst request %d unexpectedly rejected", request)
		}
	}

	refillPasses := 0
	for request := 1; request <= 10; request++ {
		allowed, _, err := limiter.allowAtMillis(ctx, "burst", int64(request*200))
		if err != nil {
			t.Fatalf("post-burst request %d: %v", request, err)
		}
		if allowed {
			refillPasses++
		}
	}

	if refillPasses < 3 || refillPasses > 4 {
		t.Fatalf("post-burst refill allowed %d requests, want about 2/s over 2s (3-4)", refillPasses)
	}
}

func TestSlidingWindowRateLimiter_AllowRejectAndRecover(t *testing.T) {
	t.Parallel()

	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() {
		_ = rdb.Close()
	})

	limiter := NewSlidingWindowRateLimiter(rdb, 20*time.Millisecond, 2, "ratelimit-test")
	ctx := context.Background()

	tests := []struct {
		name              string
		waitBeforeRequest time.Duration
		wantAllowed       bool
		wantRemaining     int
	}{
		{name: "first request allowed", wantAllowed: true, wantRemaining: 1},
		{name: "second request allowed", wantAllowed: true, wantRemaining: 0},
		{name: "third request rejected", wantAllowed: false, wantRemaining: 0},
		{name: "request after window allowed", waitBeforeRequest: 30 * time.Millisecond, wantAllowed: true, wantRemaining: 1},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.waitBeforeRequest > 0 {
				time.Sleep(tt.waitBeforeRequest)
			}

			allowed, remaining, err := limiter.Allow(ctx, "sliding")
			if err != nil {
				t.Fatalf("Allow(): %v", err)
			}
			if allowed != tt.wantAllowed {
				t.Fatalf("allowed = %v, want %v", allowed, tt.wantAllowed)
			}
			if remaining != tt.wantRemaining {
				t.Fatalf("remaining = %d, want %d", remaining, tt.wantRemaining)
			}
		})
	}
}

func TestHybridRateLimitMiddleware_RedisAllowAndReject(t *testing.T) {
	limiter, _ := newDistributedRateLimiterForTest(t, 1, 1, 1)
	localRL := NewRateLimiterWithCleanup(rate.Limit(100), 100, time.Minute)
	t.Cleanup(localRL.Stop)

	router := gin.New()
	router.Use(HybridRateLimitMiddleware(limiter.rdb, localRL, HybridRateLimiterConfig{
		Backend:         "redis",
		Rate:            1,
		Burst:           1,
		CleanupInterval: time.Minute,
	}))
	router.GET("/limited", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	first := httptest.NewRecorder()
	firstReq := httptest.NewRequest(http.MethodGet, "/limited", nil)
	firstReq.RemoteAddr = "127.0.0.1:34567"
	router.ServeHTTP(first, firstReq)
	if first.Code != http.StatusOK {
		t.Fatalf("first redis-backed request got %d, want %d", first.Code, http.StatusOK)
	}
	if first.Header().Get("X-RateLimit-Remaining") != "0" {
		t.Fatalf("first request remaining header = %q, want 0", first.Header().Get("X-RateLimit-Remaining"))
	}

	second := httptest.NewRecorder()
	secondReq := httptest.NewRequest(http.MethodGet, "/limited", nil)
	secondReq.RemoteAddr = "127.0.0.1:34567"
	router.ServeHTTP(second, secondReq)
	if second.Code != http.StatusTooManyRequests {
		t.Fatalf("second redis-backed request got %d, want %d", second.Code, http.StatusTooManyRequests)
	}
}

func TestHybridRateLimitMiddleware_RedisFailureFallsBackToLocalLimiter(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{
		Addr:         mr.Addr(),
		MaxRetries:   0,
		DialTimeout:  5 * time.Millisecond,
		ReadTimeout:  5 * time.Millisecond,
		WriteTimeout: 5 * time.Millisecond,
	})
	t.Cleanup(func() {
		_ = rdb.Close()
	})
	mr.Close()

	localRL := NewRateLimiterWithCleanup(rate.Limit(0), 1, time.Minute)
	t.Cleanup(localRL.Stop)

	router := gin.New()
	router.Use(HybridRateLimitMiddleware(rdb, localRL, HybridRateLimiterConfig{
		Backend:         "redis",
		Rate:            1,
		Burst:           1,
		CleanupInterval: time.Minute,
	}))
	router.GET("/fallback", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	first := httptest.NewRecorder()
	firstReq := httptest.NewRequest(http.MethodGet, "/fallback", nil)
	firstReq.RemoteAddr = "127.0.0.1:34567"
	router.ServeHTTP(first, firstReq)
	if first.Code != http.StatusOK {
		t.Fatalf("first local fallback request got %d, want %d", first.Code, http.StatusOK)
	}

	second := httptest.NewRecorder()
	secondReq := httptest.NewRequest(http.MethodGet, "/fallback", nil)
	secondReq.RemoteAddr = "127.0.0.1:34567"
	router.ServeHTTP(second, secondReq)
	if second.Code != http.StatusTooManyRequests {
		t.Fatalf("second local fallback request got %d, want %d", second.Code, http.StatusTooManyRequests)
	}
}
