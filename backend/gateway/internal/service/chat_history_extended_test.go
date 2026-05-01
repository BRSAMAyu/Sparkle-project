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

func setupChatHistory(t *testing.T) (*ChatHistoryService, *miniredis.Miniredis) {
	t.Helper()
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(func() { svc.Stop() })
	return svc, mr
}

func TestChatHistory_StopIdempotent(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	svc.Stop()
	svc.Stop() // should not panic
}

func TestChatHistory_BreakerThreshold(t *testing.T) {
	svc, _ := setupChatHistory(t)

	assert.Equal(t, int64(DefaultMaxQueueSize), svc.GetBreakerThreshold())
	svc.SetBreakerThreshold(500)
	assert.Equal(t, int64(500), svc.GetBreakerThreshold())
}

func TestChatHistory_GetQueueLength(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	length, err := svc.GetQueueLength(ctx)
	require.NoError(t, err)
	assert.Equal(t, int64(0), length)

	require.NoError(t, svc.SaveMessage(ctx, "q-test", []byte(`{"session_id":"q-test","user_id":"u1","role":"user","content":"hi","timestamp":"1710000000"}`)))

	length, err = svc.GetQueueLength(ctx)
	require.NoError(t, err)
	assert.Equal(t, int64(1), length)
}

func TestChatHistory_PublishConnectionEvent(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	err := svc.PublishConnectionEvent(ctx, "user1", "connected")
	require.NoError(t, err)
}

func TestChatHistory_PublishConnectionEvent_NilRedis(t *testing.T) {
	svc := &ChatHistoryService{rdb: nil}
	ctx := context.Background()

	err := svc.PublishConnectionEvent(ctx, "user1", "connected")
	require.NoError(t, err)
}

func TestChatHistory_SaveMessage_InvalidJSON(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	// Invalid JSON still gets stored in the persist queue
	err := svc.SaveMessage(ctx, "bad-json", []byte(`not json at all`))
	require.NoError(t, err)
}

func TestChatHistory_GetMessages_Offset(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	for i := 0; i < 5; i++ {
		require.NoError(t, svc.SaveMessage(ctx, "offset-test", []byte(
			`{"session_id":"offset-test","user_id":"u1","role":"user","content":"msg`+string(rune('0'+i))+`","timestamp":"171000000`+string(rune('0'+i))+`"}`,
		)))
	}

	// Get with offset=2 should skip the first 2 oldest
	messages, err := svc.GetMessages(ctx, "u1", "offset-test", 10, 2)
	require.NoError(t, err)
	assert.Len(t, messages, 3)
}

func TestChatHistory_GetMessages_EmptySession(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	messages, err := svc.GetMessages(ctx, "u1", "nonexistent", 20, 0)
	require.NoError(t, err)
	assert.Empty(t, messages)
}

func TestChatHistory_GetMessages_DefaultLimit(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	// limit=0 should default to 20
	messages, err := svc.GetMessages(ctx, "u1", "test", 0, 0)
	require.NoError(t, err)
	assert.Empty(t, messages)
}

func TestChatHistory_GetRecentSessions_Empty(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	sessions, err := svc.GetRecentSessions(ctx, "nobody", 10)
	require.NoError(t, err)
	assert.Empty(t, sessions)
}

func TestChatHistory_GetRecentSessions_DefaultLimit(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	sessions, err := svc.GetRecentSessions(ctx, "u1", 0)
	require.NoError(t, err)
	assert.Empty(t, sessions)
}

func TestChatHistory_ConversationSettings_NotSet(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	_, ok, err := svc.GetConversationSettings(ctx, "u1", "no-settings")
	require.NoError(t, err)
	assert.False(t, ok)
}

func TestChatHistory_ConversationSettings_NilRedis(t *testing.T) {
	svc := &ChatHistoryService{rdb: nil}
	ctx := context.Background()

	settings, ok, err := svc.GetConversationSettings(ctx, "u1", "test")
	require.NoError(t, err)
	assert.False(t, ok)
	assert.Nil(t, settings)
}

func TestChatHistory_UpdateConversationSettings_NilRedis(t *testing.T) {
	svc := &ChatHistoryService{rdb: nil}
	ctx := context.Background()

	result, err := svc.UpdateConversationSettings(ctx, "u1", "test", ConversationSettings{
		UseDocumentContext: true,
		DocumentFilter:     []string{"a"},
	})
	require.NoError(t, err)
	assert.True(t, result.UseDocumentContext)
}

func TestChatHistory_RedisDown(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(func() { svc.Stop() })
	ctx := context.Background()

	// Save a message while Redis is up
	require.NoError(t, svc.SaveMessage(ctx, "down-test", []byte(`{"session_id":"down-test","user_id":"u1","role":"user","content":"before down","timestamp":"1710000000"}`)))

	// Kill Redis
	mr.Close()

	// With nil pool, GetMessages falls through and returns empty (no DB to fallback to)
	// This is by design: graceful degradation
	messages, err := svc.GetMessages(ctx, "u1", "down-test", 20, 0)
	// Either error or empty result is acceptable
	if err == nil {
		assert.Empty(t, messages)
	}
}

func TestParseUnixString(t *testing.T) {
	assert.Equal(t, int64(1710000000), parseUnixString("1710000000").Unix())
	assert.WithinDuration(t, time.Now().UTC(), parseUnixString(""), time.Second)
	assert.WithinDuration(t, time.Now().UTC(), parseUnixString("not-a-number"), time.Second)
}

func TestNormalizeDocumentFilter(t *testing.T) {
	assert.Empty(t, normalizeDocumentFilter(nil))
	assert.Empty(t, normalizeDocumentFilter([]string{}))
	assert.Equal(t, []string{"a", "b"}, normalizeDocumentFilter([]string{"a", "a", " b ", "b", ""}))
}

func TestChatHistory_RetryBufferFlush(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(func() { svc.Stop() })
	ctx := context.Background()

	// Set threshold to 0 so messages go to retry buffer
	svc.SetBreakerThreshold(0)

	require.NoError(t, svc.SaveMessage(ctx, "retry-test", []byte(`{"session_id":"retry-test","user_id":"u1","role":"user","content":"retry me","timestamp":"1710000000"}`)))

	// Message should be in retry buffer
	svc.retryMu.Lock()
	assert.Len(t, svc.retryBuf, 1)
	svc.retryMu.Unlock()

	// Raise threshold and flush
	svc.SetBreakerThreshold(10000)
	svc.flushRetryBuf()

	// Buffer should be empty now
	svc.retryMu.Lock()
	assert.Empty(t, svc.retryBuf)
	svc.retryMu.Unlock()

	// Message should be in the persist queue
	length, err := svc.GetQueueLength(ctx)
	require.NoError(t, err)
	assert.Equal(t, int64(1), length)
}

func TestChatHistory_RetryBufferExpired(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(func() { svc.Stop() })
	ctx := context.Background()

	svc.SetBreakerThreshold(0)

	require.NoError(t, svc.SaveMessage(ctx, "expire-test", []byte(`{"session_id":"expire-test","user_id":"u1","role":"user","content":"old","timestamp":"1710000000"}`)))

	// Manually age the entry
	svc.retryMu.Lock()
	svc.retryBuf[0] = retryEntry{msg: svc.retryBuf[0].msg, enqueuedAt: time.Now().Add(-3 * time.Minute)}
	svc.retryMu.Unlock()

	svc.SetBreakerThreshold(10000)
	svc.flushRetryBuf()

	// Old entry should have been dropped, not re-queued
	svc.retryMu.Lock()
	assert.Empty(t, svc.retryBuf)
	svc.retryMu.Unlock()

	// Queue should be empty (entry was too old)
	length, err := svc.GetQueueLength(ctx)
	require.NoError(t, err)
	assert.Equal(t, int64(0), length)
}

func TestChatHistory_ChatHistoryMessageFields(t *testing.T) {
	svc, _ := setupChatHistory(t)
	ctx := context.Background()

	msg := `{"session_id":"field-test","user_id":"u1","role":"assistant","content":"response","timestamp":"1710000000","widgets":[{"type":"card"}],"tool_results":[{"name":"search"}],"has_errors":true,"errors":[{"code":"E1"}],"requires_confirmation":true,"confirmation_data":{"action":"approve"},"reasoning_steps":[{"step":1}],"reasoning_summary":"thinking","is_reasoning_complete":true,"meta":{"version":"2"},"agentCollaboration":{"mode":"roundtable"}}`
	require.NoError(t, svc.SaveMessage(ctx, "field-test", []byte(msg)))

	messages, err := svc.GetMessages(ctx, "u1", "field-test", 20, 0)
	require.NoError(t, err)
	require.Len(t, messages, 1)

	m := messages[0]
	assert.Equal(t, "assistant", m.Role)
	assert.Equal(t, "response", m.Content)
	assert.True(t, m.HasErrors)
	assert.True(t, m.RequiresConfirmation)
	assert.True(t, m.IsReasoningComplete)
	assert.Equal(t, "thinking", m.ReasoningSummary)
	assert.NotEmpty(t, m.Widgets)
	assert.NotEmpty(t, m.ToolResults)
	assert.NotEmpty(t, m.Errors)
	assert.NotEmpty(t, m.ConfirmationData)
	assert.NotEmpty(t, m.ReasoningSteps)
	assert.NotEmpty(t, m.Meta)
	assert.NotEmpty(t, m.AgentCollaboration)
}
