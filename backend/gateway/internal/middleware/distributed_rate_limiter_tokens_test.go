package middleware

import (
	"context"
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	dto "github.com/prometheus/client_model/go"
	"github.com/stretchr/testify/require"
)

// TestRateLimiter_TokensRemainingHistogram pins the GW-P3-6 fix: per-request
// remaining tokens are recorded into a histogram (rate_limiter_tokens_remaining)
// instead of a single gauge whose value was whichever key requested last.
func TestRateLimiter_TokensRemainingHistogram(t *testing.T) {
	d, _ := newDistributedRateLimiterForTest(t, 1.0, 5, 5)

	// Observe the histogram count before and after real limiter traffic.
	countBefore := rateLimiterTokensRemainingObservations(t)

	for i := 0; i < 3; i++ {
		allowed, remaining, err := d.Allow(context.Background(), "histogram-probe")
		require.NoError(t, err)
		require.True(t, allowed)
		require.GreaterOrEqual(t, remaining, int64(0))
	}

	countAfter := rateLimiterTokensRemainingObservations(t)
	require.Greater(t, countAfter, countBefore,
		"limiter requests must observe into the remaining-tokens histogram")
}

func rateLimiterTokensRemainingObservations(t *testing.T) uint64 {
	t.Helper()
	mch := make(chan prometheus.Metric, 16)
	rateLimiterTokensRemaining.Collect(mch)
	close(mch)
	for m := range mch {
		var dtoM dto.Metric
		require.NoError(t, m.Write(&dtoM))
		return dtoM.GetHistogram().GetSampleCount()
	}
	return 0
}
