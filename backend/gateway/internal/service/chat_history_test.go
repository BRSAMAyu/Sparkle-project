package service

import (
	"context"
	"errors"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
)

func TestChatHistoryServiceStoresSessionMetadataAndHistory(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	ctx := context.Background()

	require.NoError(t, svc.SaveMessage(ctx, "agent_test", []byte(`{"session_id":"agent_test","user_id":"u1","role":"user","content":"帮我制定高数复习计划","timestamp":"1710000000"}`)))
	require.NoError(t, svc.SaveMessage(ctx, "agent_test", []byte(`{"session_id":"agent_test","user_id":"u1","role":"assistant","content":"先确认考试时间","timestamp":"1710000001"}`)))

	sessions, err := svc.GetRecentSessions(ctx, "u1", 10)
	require.NoError(t, err)
	require.Len(t, sessions, 1)
	require.Equal(t, "agent_test", sessions[0].ID)
	require.Equal(t, "帮我制定高数复习计划", sessions[0].Title)

	messages, err := svc.GetMessages(ctx, "u1", "agent_test", 20, 0)
	require.NoError(t, err)
	require.Len(t, messages, 2)
	require.Equal(t, "user", messages[0].Role)
	require.Equal(t, "assistant", messages[1].Role)
}

func TestChatHistoryServiceRejectsForeignSession(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	ctx := context.Background()

	require.NoError(t, svc.SaveMessage(ctx, "agent_test", []byte(`{"session_id":"agent_test","user_id":"owner","role":"user","content":"hello","timestamp":"1710000000"}`)))

	_, err := svc.GetMessages(ctx, "other", "agent_test", 20, 0)
	require.Error(t, err)
	require.True(t, errors.Is(err, ErrChatHistoryForbidden()))
}

func TestChatHistoryServiceReportsRetryBufferOverflow(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	ctx := context.Background()

	svc.breakerThreshold.Store(0)
	svc.retryMu.Lock()
	svc.retryBuf = make([]retryEntry, breakerRetryBufMax)
	svc.retryMu.Unlock()

	err := svc.SaveMessage(ctx, "agent_test", []byte(`{"session_id":"agent_test","user_id":"u1","role":"user","content":"overflow","timestamp":"1710000002"}`))
	require.Error(t, err)
	require.True(t, errors.Is(err, errRetryBufferOverflow))

	history, historyErr := svc.GetMessages(ctx, "u1", "agent_test", 20, 0)
	require.NoError(t, historyErr)
	require.Len(t, history, 1)
	require.Equal(t, "overflow", history[0].Content)
}
