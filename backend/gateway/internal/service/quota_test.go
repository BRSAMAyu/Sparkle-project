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

func TestQuotaService_ReserveRequest(t *testing.T) {
	// Setup miniredis
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{
		Addr: s.Addr(),
	})
	defer rdb.Close()

	svc := NewQuotaService(rdb)
	ctx := context.Background()
	uid := "user_123"

	t.Run("Reserve with sufficient quota", func(t *testing.T) {
		// Set initial quota
		s.Set(fmt.Sprintf("user:quota:%s", uid), "10")

		reqID := "req_1"
		remaining, err := svc.ReserveRequest(ctx, uid, reqID, time.Minute)
		assert.NoError(t, err)
		assert.Equal(t, int64(9), remaining)

		// Verify quota decremented
		val, _ := s.Get(fmt.Sprintf("user:quota:%s", uid))
		assert.Equal(t, "9", val)

		// Verify request key created
		exists := s.Exists(fmt.Sprintf("quota:request:%s:%s", uid, reqID))
		assert.True(t, exists)

		// Verify sync queue
		l, err := s.List("queue:sync:quota")
		assert.NoError(t, err)
		assert.Len(t, l, 1)
	})

	t.Run("Reserve with insufficient quota", func(t *testing.T) {
		s.Set(fmt.Sprintf("user:quota:%s", uid), "0")

		reqID := "req_2"
		remaining, err := svc.ReserveRequest(ctx, uid, reqID, time.Minute)
		assert.ErrorIs(t, err, ErrQuotaInsufficient)
		assert.Equal(t, int64(0), remaining)
	})

	t.Run("Idempotency", func(t *testing.T) {
		s.Set(fmt.Sprintf("user:quota:%s", uid), "10")
		reqID := "req_duplicate"

		// First call
		_, err := svc.ReserveRequest(ctx, uid, reqID, time.Minute)
		assert.NoError(t, err)

		// Second call with same ID should not decrement
		remaining, err := svc.ReserveRequest(ctx, uid, reqID, time.Minute)
		assert.NoError(t, err)
		assert.Equal(t, int64(9), remaining) // Should still be 9, not 8
	})
}

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

		// Verify tokens added
		val, _ := s.Get(dayKey)
		assert.Equal(t, "100", val)
	})

	t.Run("Record usage idempotency", func(t *testing.T) {
		reqID := "req_usage_dup"
		dayKey := fmt.Sprintf("llm_tokens:%s:%s", uid, time.Now().Format("2006-01-02"))

		// First call
		svc.RecordUsage(ctx, uid, reqID, 50, time.Minute)

		// Verify key exists
		key := fmt.Sprintf("usage:request:%s:%s", uid, reqID)
		assert.True(t, s.Exists(key), "Request key should exist after first call")

		// Second call
		ok, err := svc.RecordUsage(ctx, uid, reqID, 50, time.Minute)
		assert.NoError(t, err)
		assert.False(t, ok) // Should return false as it was already recorded

		// Verify tokens are 100 + 50 = 150 (from prev test + this test's first call)
		// Wait, miniredis is shared? No, different keys or I need to flush.
		// Actually I reused 's' but different keys/reqIDs.
		// Previous test used user_456 but distinct reqID.
		// dayKey is same. 100 (prev) + 50 (this) = 150.
		val, _ := s.Get(dayKey)
		assert.Equal(t, "150", val)
	})
}