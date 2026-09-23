package service

// HISTORY-TAIL regression tests (V13-RETEST Major residual).
//
// Incident: after an app kill the Redis cache held 10 messages while the
// engine had persisted 13 to PostgreSQL; the old cache-hit short-circuit in
// GetMessages served the truncated tail until the TTL healed it (~15min).
// These tests pin the watermark-based tail repair: a stale cache hit is
// repaired from the DB tail, a fresh hit never touches the DB, and the
// merge/paging primitives keep their pre-refactor semantics.

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func tailFixturePayload(role, content string, ts int64) []byte {
	return []byte(fmt.Sprintf(
		`{"id":"cache-%s-%d","session_id":"tail-sess","user_id":"u1","role":%q,"content":%q,"timestamp":"%d"}`,
		role, ts, role, content, ts,
	))
}

func tailFixtureDBRow(role, content string, ts int64) ChatHistoryMessage {
	return ChatHistoryMessage{
		ID:        fmt.Sprintf("db-%s-%d", role, ts),
		SessionID: "tail-sess",
		UserID:    "u1",
		Role:      role,
		Content:   content,
		Timestamp: fmt.Sprintf("%d", ts),
	}
}

// seedTailCache appends n alternating user/assistant messages via the normal
// SaveMessage write path (the gateway append whose gaps caused the incident).
func seedTailCache(t *testing.T, svc *ChatHistoryService, n int, baseTs int64) {
	t.Helper()
	for i := 0; i < n; i++ {
		role, content := "user", fmt.Sprintf("cached-msg-%02d", i)
		if i%2 == 1 {
			role, content = "assistant", fmt.Sprintf("cached-reply-%02d", i)
		}
		require.NoError(t, svc.SaveMessage(context.Background(), "tail-sess", tailFixturePayload(role, content, baseTs+int64(i))))
	}
}

// TestGetMessagesRepairsTruncatedTailFromDB is the red proof for the card:
// Redis holds 10 stale messages while the DB holds 13 — the read must return
// 13, rewrite the cache, and a follow-up read must be served from the repaired
// cache without probing the DB again.
func TestGetMessagesRepairsTruncatedTailFromDB(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(svc.Stop)
	ctx := context.Background()

	const cachedN = 10
	const totalN = 13
	const baseTs = int64(1710000000)
	seedTailCache(t, svc, cachedN, baseTs)

	// DB truth: the same 10 logical messages (engine-persisted under
	// different IDs, timestamps drifted by 1s) plus 3 tail messages whose
	// gateway append was lost.
	dbRows := make([]ChatHistoryMessage, 0, totalN)
	for i := 0; i < cachedN; i++ {
		role, content := "user", fmt.Sprintf("cached-msg-%02d", i)
		if i%2 == 1 {
			role, content = "assistant", fmt.Sprintf("cached-reply-%02d", i)
		}
		dbRows = append(dbRows, tailFixtureDBRow(role, content, baseTs+int64(i)+1))
	}
	for i := cachedN; i < totalN; i++ {
		role, content := "user", fmt.Sprintf("db-only-msg-%02d", i)
		if i%2 == 1 {
			role, content = "assistant", fmt.Sprintf("db-only-reply-%02d", i)
		}
		dbRows = append(dbRows, tailFixtureDBRow(role, content, baseTs+int64(i)+1))
	}

	probeCalls := 0
	svc.tailProbeFn = func(ctx context.Context, sessionID, userID string, since time.Time) ([]ChatHistoryMessage, error) {
		probeCalls++
		return dbRows, nil
	}

	messages, err := svc.GetMessages(ctx, "u1", "tail-sess", 20, 0)
	require.NoError(t, err)
	require.Len(t, messages, totalN, "truncated cache tail must be repaired from the DB")
	require.Equal(t, 1, probeCalls)
	require.Equal(t, "cached-msg-00", messages[0].Content)
	require.Equal(t, "db-only-msg-12", messages[totalN-1].Content)
	require.Equal(t, "user", messages[totalN-1].Role, "index 12 is even → user turn")

	// The repair rewrote the cache asynchronously; once it lands, the next
	// read is served from the repaired cache without touching the DB.
	svc.backfillWg.Wait()
	messages, err = svc.GetMessages(ctx, "u1", "tail-sess", 20, 0)
	require.NoError(t, err)
	require.Len(t, messages, totalN, "repaired cache must serve the full tail")
	require.Equal(t, 1, probeCalls, "fresh watermark must not re-probe")

	cached, err := rdb.LRange(ctx, "chat:history:tail-sess", 0, -1).Result()
	require.NoError(t, err)
	require.Len(t, cached, totalN, "cache rewrite must contain the merged window")

	// Session metadata follows the repaired tail (dual-metadata contradiction).
	lastMessageAt, err := rdb.HGet(ctx, "chat:session_meta:tail-sess", "last_message_at").Result()
	require.NoError(t, err)
	expected := time.Unix(baseTs+totalN, 0).UTC().Format(time.RFC3339)
	require.Equal(t, expected, lastMessageAt)
}

// TestGetMessagesFreshWatermarkSkipsProbe pins the performance contract: a
// cache hit inside the probe window is served from Redis only — no DB probe,
// no re-source, no latency regression. Once the watermark expires the next
// hit re-checks exactly once.
func TestGetMessagesFreshWatermarkSkipsProbe(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(svc.Stop)
	ctx := context.Background()

	seedTailCache(t, svc, 3, 1710000000)

	probeCalls := 0
	svc.tailProbeFn = func(ctx context.Context, sessionID, userID string, since time.Time) ([]ChatHistoryMessage, error) {
		probeCalls++
		return nil, nil
	}

	// Fresh watermark: the hit must not re-source.
	require.NoError(t, rdb.HSet(ctx, "chat:session_meta:tail-sess", chatHistoryTailCheckedAtField, time.Now().UTC().Format(time.RFC3339)).Err())
	messages, err := svc.GetMessages(ctx, "u1", "tail-sess", 20, 0)
	require.NoError(t, err)
	require.Len(t, messages, 3)
	require.Equal(t, 0, probeCalls, "fresh hit must not probe the DB")

	// Expired watermark: exactly one re-check.
	require.NoError(t, rdb.HSet(ctx, "chat:session_meta:tail-sess", chatHistoryTailCheckedAtField, time.Now().UTC().Add(-chatHistoryTailProbeInterval-time.Second).Format(time.RFC3339)).Err())
	_, err = svc.GetMessages(ctx, "u1", "tail-sess", 20, 0)
	require.NoError(t, err)
	require.Equal(t, 1, probeCalls)
}

// TestMergeCacheAndDBTail pins the merge semantics: content-based pairing of
// gateway-appended and engine-persisted copies (unrelated IDs, drifted
// timestamps), nearest-first pairing for legitimate identical retries, and
// zero-match signalling for incompatible sources.
func TestMergeCacheAndDBTail(t *testing.T) {
	// Full overlap with drifted timestamps: nothing to add.
	cached := []ChatHistoryMessage{
		tailFixtureDBRow("user", "hi", 100),
		tailFixtureDBRow("assistant", "hello", 110),
	}
	dbRows := []ChatHistoryMessage{
		tailFixtureDBRow("user", "hi", 101),
		tailFixtureDBRow("assistant", "hello", 112),
	}
	merged, dbOnly, matched := mergeCacheAndDBTail(cached, dbRows)
	assert.Equal(t, 2, matched)
	assert.Empty(t, dbOnly)
	assert.Equal(t, cached, merged)

	// Legitimate identical retry (V13 B-02): pairs nearest-first, no dup.
	cached = []ChatHistoryMessage{
		tailFixtureDBRow("user", "hi", 100),
		tailFixtureDBRow("user", "hi", 200),
	}
	dbRows = []ChatHistoryMessage{
		tailFixtureDBRow("user", "hi", 101),
		tailFixtureDBRow("user", "hi", 201),
	}
	_, dbOnly, matched = mergeCacheAndDBTail(cached, dbRows)
	assert.Equal(t, 2, matched)
	assert.Empty(t, dbOnly)

	// Mid-history gap: the DB-only row is merged in timestamp order.
	cached = []ChatHistoryMessage{
		tailFixtureDBRow("user", "a", 100),
		tailFixtureDBRow("assistant", "b", 120),
	}
	dbRows = []ChatHistoryMessage{tailFixtureDBRow("assistant", "gap", 110)}
	merged, dbOnly, matched = mergeCacheAndDBTail(cached, dbRows)
	assert.Equal(t, 0, matched)
	require.Len(t, dbOnly, 1)
	require.Len(t, merged, 3)
	assert.Equal(t, "a", merged[0].Content)
	assert.Equal(t, "gap", merged[1].Content)
	assert.Equal(t, "b", merged[2].Content)

	// Zero matches: the divergence signal (drives the DB-authoritative path).
	cached = []ChatHistoryMessage{tailFixtureDBRow("user", "shape-a", 100)}
	dbRows = []ChatHistoryMessage{tailFixtureDBRow("user", "shape-b", 101)}
	_, dbOnly, matched = mergeCacheAndDBTail(cached, dbRows)
	assert.Equal(t, 0, matched)
	assert.Len(t, dbOnly, 1)

	// Match tolerance boundary: within matches, beyond does not.
	cached = []ChatHistoryMessage{tailFixtureDBRow("user", "hi", 1000)}
	dbRows = []ChatHistoryMessage{tailFixtureDBRow("user", "hi", 1000+int64(chatHistoryTailMatchTolerance/time.Second))}
	_, dbOnly, matched = mergeCacheAndDBTail(cached, dbRows)
	assert.Equal(t, 1, matched)
	assert.Empty(t, dbOnly)

	dbRows = []ChatHistoryMessage{tailFixtureDBRow("user", "hi", 1000+int64(chatHistoryTailMatchTolerance/time.Second)+1)}
	_, dbOnly, matched = mergeCacheAndDBTail(cached, dbRows)
	assert.Equal(t, 0, matched)
	assert.Len(t, dbOnly, 1)
}

// TestSliceMessagesPage pins the paging window semantics extracted verbatim
// from the old getMessagesFromRedis slicing (13-message view = the incident
// shape).
func TestSliceMessagesPage(t *testing.T) {
	view := make([]ChatHistoryMessage, 13)
	for i := range view {
		view[i] = tailFixtureDBRow("user", fmt.Sprintf("m%02d", i), int64(1710000000+i))
	}

	assert.Len(t, sliceMessagesPage(view, 20, 0), 13)
	assert.Empty(t, sliceMessagesPage(view, 0, 0), "limit normalization happens in GetMessages")
	got := sliceMessagesPage(view, 5, 0)
	require.Len(t, got, 5)
	assert.Equal(t, "m12", got[4].Content, "newest-first window")
	got = sliceMessagesPage(view, 5, 5)
	require.Len(t, got, 5)
	assert.Equal(t, "m03", got[0].Content, "offset skips the newest pages")
	assert.Equal(t, "m07", got[4].Content)
	assert.Equal(t, []ChatHistoryMessage{}, sliceMessagesPage(view, 20, 13), "offset at end is empty")
	assert.Equal(t, []ChatHistoryMessage{}, sliceMessagesPage(view, 20, 99), "offset beyond end is empty")
	assert.Equal(t, "m00", sliceMessagesPage(view, 3, 12)[0].Content, "partial window at the oldest edge")
}

// TestReplaceRedisMessagesRewritesInsteadOfAppending pins the repair write
// primitive: the cache is replaced atomically, never appended onto.
func TestReplaceRedisMessagesRewritesInsteadOfAppending(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryService(rdb)
	t.Cleanup(svc.Stop)
	ctx := context.Background()

	seedTailCache(t, svc, 3, 1710000000)

	svc.replaceRedisMessages("tail-sess", []ChatHistoryMessage{
		tailFixtureDBRow("user", "auth-0", 1710000100),
		tailFixtureDBRow("assistant", "auth-1", 1710000101),
	})

	raw, err := rdb.LRange(ctx, "chat:history:tail-sess", 0, -1).Result()
	require.NoError(t, err)
	require.Len(t, raw, 2, "rewrite must not keep stale entries")
	var msg ChatHistoryMessage
	require.NoError(t, json.Unmarshal([]byte(raw[0]), &msg))
	assert.Equal(t, "auth-0", msg.Content)
}
