package middleware

import (
	"context"
	"math"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
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
