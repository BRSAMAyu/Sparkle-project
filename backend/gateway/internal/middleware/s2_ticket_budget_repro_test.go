package middleware

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

// WSQ-6 S2 red-flag follow-up (wt323): the load test reported 309 tickets
// issued out of 1500 requests @50rps×30s against a "theoretical budget" of
// 160 (burst10 + 5rps×30s) — a supposed 1.93× over-issue.
//
// Root cause: the 160 model assumed the viper DEFAULTS (WS_TICKET_RATE_RPS=5,
// config.go), but the gateway under test loads backend/gateway/.env which sets
// WS_TICKET_RATE_RPS=10. The runtime bucket is rate=10/burst=10, whose budget
// over the same window is 10 + 10×30 = 310 — the observed 309 is 99.7% of it,
// i.e. a fully converged token bucket, not an over-issue.
//
// These tests pin the budget semantics with a deterministic virtual clock
// (same arrival process as the S2 scenario: 1500 requests spaced 20ms apart):
//   - rate=5/burst=10  → ≈160 dispensed (design-default model holds; a real
//     1.93× implementation leak would fail this subtest)
//   - rate=10/burst=10 → ≈310 dispensed (reproduces the observed 309;
//     conforms to the runtime budget instead of exceeding it)
func TestS2TicketBudgetTracksRuntimeParams(t *testing.T) {
	t.Parallel()

	const totalRequests = 1500 // 50 rps × 30 s
	const spacingMs = 20

	cases := []struct {
		name        string
		rate        float64
		burst       int
		wantMin     int // budget conformance lower bound (bucket drains no faster than refill)
		wantMax     int // budget conformance upper bound (burst + rate×window, +1 boundary)
		redFlagCond bool // when true, assert the count exceeds the legacy 160-model budget — reproducing WSQ-6's observation
	}{
		{
			name:        "design_default_5rps_burst10_budget_160",
			rate:        5.0,
			burst:       10,
			wantMin:     155,
			wantMax:     162, // 10 + 5×29.98 = 159.9, +boundary
			redFlagCond: false,
		},
		{
			name:        "dev_env_10rps_burst10_reproduces_observed_309",
			rate:        10.0,
			burst:       10,
			wantMin:     305,
			wantMax:     311, // 10 + 10×29.98 = 309.8, +boundary
			redFlagCond: true,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			mr := miniredis.RunT(t)
			rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
			t.Cleanup(func() { _ = rdb.Close() })

			// Mirror HybridRateLimitMiddlewareSimple's wiring: NewDistributedRateLimiter
			// starts the bucket full (initialTokens = burst).
			limiter := NewDistributedRateLimiter(rdb, tc.rate, tc.burst, "ratelimit")
			ctx := context.Background()

			allowed := 0
			for i := 0; i < totalRequests; i++ {
				ok, _, err := limiter.allowAtMillis(ctx, "s2_flood_user:POST:/api/v1/ws/ticket", int64(i*spacingMs))
				if err != nil {
					t.Fatalf("request %d: %v", i, err)
				}
				if ok {
					allowed++
				}
			}

			if allowed < tc.wantMin || allowed > tc.wantMax {
				t.Fatalf("dispensed %d tickets with rate=%.1f/burst=%d over 30s, want within [%d,%d] (burst+rate×window model)",
					allowed, tc.rate, tc.burst, tc.wantMin, tc.wantMax)
			}

			const legacyModelBudget = 160 // what the original S2 script assumed
			const legacyRedFlagLine = int(float64(legacyModelBudget) * 1.15)
			if tc.redFlagCond {
				if allowed <= legacyRedFlagLine {
					t.Fatalf("expected reproduction of the WSQ-6 observation (issued > %d under runtime params), got %d", legacyRedFlagLine, allowed)
				}
				t.Logf("reproduced WSQ-6 S2 observation: %d issued > legacy 160-model line %d, while ≤ runtime budget %d (no over-issue)",
					allowed, legacyRedFlagLine, tc.wantMax-1)
			}
		})
	}
}
