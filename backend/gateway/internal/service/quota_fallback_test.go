package service

import (
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestQuotaLocalFallback_AllowUpToLimitThenReject(t *testing.T) {
	f := NewQuotaLocalFallback(2)
	now := time.Date(2026, 9, 18, 10, 0, 0, 0, time.UTC)

	count, admitted := f.Allow(now)
	require.True(t, admitted)
	require.Equal(t, int64(1), count)

	count, admitted = f.Allow(now)
	require.True(t, admitted)
	require.Equal(t, int64(2), count)

	count, admitted = f.Allow(now)
	require.False(t, admitted, "request over the cap must be rejected")
	require.Equal(t, int64(2), count, "rejected attempts must not consume budget")

	// The counter saturates: many rejected attempts never wrap or re-admit.
	for i := 0; i < 1000; i++ {
		if _, admitted = f.Allow(now); admitted {
			t.Fatal("rejected attempts must stay rejected within the same day")
		}
	}
}

func TestQuotaLocalFallback_ResetsOnUTCDayRollover(t *testing.T) {
	f := NewQuotaLocalFallback(1)
	day1 := time.Date(2026, 9, 18, 23, 59, 0, 0, time.UTC)
	day2 := day1.Add(2 * time.Hour) // next UTC day

	_, admitted := f.Allow(day1)
	require.True(t, admitted)
	_, admitted = f.Allow(day1)
	require.False(t, admitted)

	count, admitted := f.Allow(day2)
	require.True(t, admitted, "counter must reset on UTC day rollover")
	require.Equal(t, int64(1), count)
}

func TestQuotaLocalFallback_ConcurrentAllowNeverExceedsLimit(t *testing.T) {
	f := NewQuotaLocalFallback(50)
	now := time.Now()
	const workers, perWorker = 8, 100

	var mu sync.Mutex
	total := 0
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < perWorker; i++ {
				if _, ok := f.Allow(now); ok {
					mu.Lock()
					total++
					mu.Unlock()
				}
			}
		}()
	}
	wg.Wait()
	require.Equal(t, 50, total, "exactly limit admissions must succeed under concurrency")
}

func TestQuotaLocalFallback_EnvOverride(t *testing.T) {
	t.Setenv(QuotaLocalFallbackDailyLimitEnv, "7")
	f := NewQuotaLocalFallbackFromEnv()
	require.Equal(t, int64(7), f.Limit())

	t.Setenv(QuotaLocalFallbackDailyLimitEnv, "")
	f = NewQuotaLocalFallbackFromEnv()
	require.Equal(t, DefaultQuotaLocalFallbackDailyLimit, f.Limit(),
		"empty env must fall back to the documented default 50")

	t.Setenv(QuotaLocalFallbackDailyLimitEnv, "not-a-number")
	f = NewQuotaLocalFallbackFromEnv()
	require.Equal(t, DefaultQuotaLocalFallbackDailyLimit, f.Limit())

	t.Setenv(QuotaLocalFallbackDailyLimitEnv, "-3")
	f = NewQuotaLocalFallbackFromEnv()
	require.Equal(t, DefaultQuotaLocalFallbackDailyLimit, f.Limit())
}
