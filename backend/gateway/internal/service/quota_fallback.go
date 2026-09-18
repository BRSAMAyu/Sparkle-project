package service

import (
	"os"
	"strconv"
	"sync/atomic"
	"time"
)

// QuotaLocalFallbackDailyLimitEnv overrides the per-instance daily hard cap
// used when Redis-backed daily usage accounting is unavailable.
const QuotaLocalFallbackDailyLimitEnv = "QUOTA_LOCAL_FALLBACK_DAILY_LIMIT"

// DefaultQuotaLocalFallbackDailyLimit is the per-instance approximate daily
// request cap while quota enforcement runs in local fallback mode. The value
// is deliberately much lower than the normal DAILY_QUOTA token budget: it is
// an emergency bounded-degradation ceiling (GW-P2-4 product decision,
// 2026-09-18), not a feature.
const DefaultQuotaLocalFallbackDailyLimit = int64(50)

const quotaFallbackDayShift = 32

// QuotaLocalFallback is an instance-level approximate daily request counter
// used as a bounded fallback when the Redis-backed daily usage snapshot cannot
// be loaded. It keeps the gateway available during a Redis outage while
// guaranteeing a hard per-instance ceiling instead of unbounded fail-open.
//
// Semantics:
//   - instance-local: across N gateway replicas the effective ceiling is
//     N * limit (documented approximation, mitigated by alerting on
//     sparkle_quota_local_fallback_active);
//   - counts admitted requests, not tokens (Redis is down, so token metering
//     is unavailable by definition);
//   - resets on UTC day rollover (approximate "daily"), implemented as one
//     atomic CAS word: high 32 bits = UTC day, low 32 bits = today's count.
type QuotaLocalFallback struct {
	limit int64
	state atomic.Int64
}

// NewQuotaLocalFallbackFromEnv builds the fallback with the limit from
// QUOTA_LOCAL_FALLBACK_DAILY_LIMIT, or DefaultQuotaLocalFallbackDailyLimit
// when unset or invalid.
func NewQuotaLocalFallbackFromEnv() *QuotaLocalFallback {
	limit := DefaultQuotaLocalFallbackDailyLimit
	if raw := os.Getenv(QuotaLocalFallbackDailyLimitEnv); raw != "" {
		if parsed, err := strconv.ParseInt(raw, 10, 64); err == nil && parsed > 0 {
			limit = parsed
		}
	}
	return &QuotaLocalFallback{limit: limit}
}

// NewQuotaLocalFallback builds the fallback with an explicit limit (tests).
func NewQuotaLocalFallback(limit int64) *QuotaLocalFallback {
	if limit <= 0 {
		limit = DefaultQuotaLocalFallbackDailyLimit
	}
	return &QuotaLocalFallback{limit: limit}
}

// Limit returns the configured per-instance daily cap.
func (f *QuotaLocalFallback) Limit() int64 { return f.limit }

func packQuotaFallbackState(day, count int64) int64 {
	return day<<quotaFallbackDayShift | count
}

// Allow atomically admits one request against the per-instance daily cap,
// resetting the counter when the UTC day rolls over. It returns the number of
// requests admitted today (including this one) and whether the request is
// admitted. Once the cap is reached the counter saturates: further attempts
// are rejected without mutating state.
func (f *QuotaLocalFallback) Allow(now time.Time) (count int64, admitted bool) {
	day := now.UTC().Unix() / 86400
	for {
		cur := f.state.Load()
		if cur>>quotaFallbackDayShift != day {
			// Day rolled over (or first use): try to start today's window.
			if f.state.CompareAndSwap(cur, packQuotaFallbackState(day, 1)) {
				return 1, 1 <= f.limit
			}
			continue
		}
		count = cur & ((1 << quotaFallbackDayShift) - 1)
		if count >= f.limit {
			return count, false
		}
		if f.state.CompareAndSwap(cur, cur+1) {
			return count + 1, true
		}
	}
}
