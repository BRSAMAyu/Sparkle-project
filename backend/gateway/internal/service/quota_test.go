package service

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
)

// The reserve/refund/decr quota family (ReserveRequest / RefundReservation /
// DecrQuota + decr_quota.lua / reserve_quota.lua / refund_quota.lua) was
// deleted as dead code — zero production callers, and no initializer ever
// wrote its user:quota:* keys (R2-05 §4.1 option 1). The tests below pin the
// live quota chain: usage metering on date-suffixed keys with request-scoped
// idempotency, plus the daily-usage read that gates admission.

func TestQuotaService_RecordUsage(t *testing.T) {
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{
		Addr: s.Addr(),
	})
	defer rdb.Close()

	svc := NewQuotaService(rdb)
	ctx := context.Background()
	uid := "user_456"

	t.Run("Record usage", func(t *testing.T) {
		reqID := "req_usage_1"
		dayKey := fmt.Sprintf("llm_tokens:%s:%s", uid, time.Now().Format("2006-01-02"))

		ok, err := svc.RecordUsage(ctx, uid, reqID, 100, time.Minute)
		assert.NoError(t, err)
		assert.True(t, ok)

		val, _ := s.Get(dayKey)
		assert.Equal(t, "100", val)
	})

	t.Run("Record usage idempotency", func(t *testing.T) {
		reqID := "req_usage_dup"
		dayKey := fmt.Sprintf("llm_tokens:%s:%s", uid, time.Now().Format("2006-01-02"))

		svc.RecordUsage(ctx, uid, reqID, 50, time.Minute)

		key := fmt.Sprintf("usage:request:%s:%s", uid, reqID)
		assert.True(t, s.Exists(key), "Request key should exist after first call")

		ok, err := svc.RecordUsage(ctx, uid, reqID, 50, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)

		val, _ := s.Get(dayKey)
		assert.Equal(t, "150", val)
	})

	t.Run("Empty requestID returns false without error", func(t *testing.T) {
		ok, err := svc.RecordUsage(ctx, uid, "", 100, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)
	})
}

func TestQuotaService_RecordUsageSegment(t *testing.T) {
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	defer rdb.Close()

	svc := NewQuotaService(rdb)
	ctx := context.Background()
	uid := "user_segment"
	dayKey := fmt.Sprintf("llm_tokens:%s:%s", uid, time.Now().Format("2006-01-02"))
	year, week := time.Now().ISOWeek()
	weekKey := fmt.Sprintf("llm_tokens:%s:week:%d:%02d", uid, year, week)

	t.Run("Records first segment", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_1", 1, 200, time.Minute)
		assert.NoError(t, err)
		assert.True(t, ok)

		val, _ := s.Get(dayKey)
		assert.Equal(t, "200", val)

		wVal, _ := s.Get(weekKey)
		assert.Equal(t, "200", wVal)

		segKey := fmt.Sprintf("usage:segment:%s:req_seg_1:1", uid)
		assert.True(t, s.Exists(segKey))
	})

	t.Run("Same segment is idempotent", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_1", 1, 200, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)

		val, _ := s.Get(dayKey)
		assert.Equal(t, "200", val)
	})

	t.Run("Different segment of same request is recorded", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_1", 2, 150, time.Minute)
		assert.NoError(t, err)
		assert.True(t, ok)

		val, _ := s.Get(dayKey)
		assert.Equal(t, "350", val)
	})

	t.Run("Empty requestID returns false", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "", 1, 100, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)
	})

	t.Run("Zero segment returns false", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_2", 0, 100, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)
	})

	t.Run("Negative segment returns false", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_2", -1, 100, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)
	})

	t.Run("Zero tokens returns false", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_3", 1, 0, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)
	})

	t.Run("Negative tokens returns false", func(t *testing.T) {
		ok, err := svc.RecordUsageSegment(ctx, uid, "req_seg_3", 1, -50, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok)
	})
}

func TestQuotaService_GetDailyUsage(t *testing.T) {
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	defer rdb.Close()

	svc := NewQuotaService(rdb)
	ctx := context.Background()
	uid := "user_daily"

	t.Run("Returns zero when no usage", func(t *testing.T) {
		usage, err := svc.GetDailyUsage(ctx, uid)
		assert.NoError(t, err)
		assert.Equal(t, int64(0), usage)
	})

	t.Run("Returns recorded daily usage", func(t *testing.T) {
		dayKey := fmt.Sprintf("llm_tokens:%s:%s", uid, time.Now().Format("2006-01-02"))
		s.Set(dayKey, "350")

		usage, err := svc.GetDailyUsage(ctx, uid)
		assert.NoError(t, err)
		assert.Equal(t, int64(350), usage)
	})
}
