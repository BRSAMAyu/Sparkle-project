package service

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupDedup(t *testing.T) (*MessageDedupService, *miniredis.Miniredis) {
	t.Helper()
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	return NewMessageDedupService(rdb), mr
}

func TestMessageDedup_FirstMessage(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	isDup, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup, "first message should not be a duplicate")
}

func TestMessageDedup_DuplicateMessage(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	_, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)

	isDup, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.True(t, isDup, "same requestID should be detected as duplicate")
}

func TestMessageDedup_DifferentUsersSameRequest(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	isDup1, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup1)

	isDup2, err := svc.CheckAndMark(ctx, "user2", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup2, "different users should have separate dedup keys")
}

func TestMessageDedup_DifferentRequestsSameUser(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	isDup1, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup1)

	isDup2, err := svc.CheckAndMark(ctx, "user1", "req-002")
	require.NoError(t, err)
	assert.False(t, isDup2, "different requestIDs should not be duplicates")
}

func TestMessageDedup_IsProcessed(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	exists, err := svc.IsProcessed(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, exists, "unprocessed message should not exist")

	_, err = svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)

	exists, err = svc.IsProcessed(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.True(t, exists, "processed message should exist")
}

func TestMessageDedup_MarkProcessed(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	err := svc.MarkProcessed(ctx, "user1", "req-001")
	require.NoError(t, err)

	isDup, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.True(t, isDup, "manually marked message should be detected as duplicate")
}

func TestMessageDedup_Clear(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	_, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)

	err = svc.Clear(ctx, "user1", "req-001")
	require.NoError(t, err)

	isDup, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup, "cleared message should not be a duplicate anymore")
}

func TestMessageDedup_ClearAllForUser(t *testing.T) {
	svc, _ := setupDedup(t)
	ctx := context.Background()

	_, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	_, err = svc.CheckAndMark(ctx, "user1", "req-002")
	require.NoError(t, err)

	err = svc.ClearAllForUser(ctx, "user1")
	require.NoError(t, err)

	isDup, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup)

	isDup, err = svc.CheckAndMark(ctx, "user1", "req-002")
	require.NoError(t, err)
	assert.False(t, isDup)
}

func TestMessageDedup_TTLExpiry(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewMessageDedupServiceWithTTL(rdb, 1*time.Second)
	ctx := context.Background()

	_, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)

	isDup, err := svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.True(t, isDup)

	mr.FastForward(2 * time.Second)

	isDup, err = svc.CheckAndMark(ctx, "user1", "req-001")
	require.NoError(t, err)
	assert.False(t, isDup, "expired dedup record should allow reprocessing")
}

func TestMessageDedup_RedisDown(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewMessageDedupService(rdb)
	ctx := context.Background()

	mr.Close() // simulate Redis down

	_, err := svc.CheckAndMark(ctx, "user1", "req-001")
	assert.Error(t, err, "should return error when Redis is down")

	_, err = svc.IsProcessed(ctx, "user1", "req-001")
	assert.Error(t, err)
}
