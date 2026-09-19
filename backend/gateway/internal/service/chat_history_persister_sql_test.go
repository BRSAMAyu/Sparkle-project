package service

// Regression tests for daily-flow DF-2 (gateway side).
//
// The durable chat pipeline was dead on arrival: ChatHistoryPersister was
// never started, and even if started, its SQL referenced the dropped
// `metadata` column, divided second-based timestamps by 1000 (→ 1970),
// crashed on non-UUID session labels ("df-d2-s1"), and used an ON CONFLICT
// target that matches no unique index (chat_messages PK is (id, created_at)).
// Assistant replies therefore never reached PostgreSQL via the queue path.

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/google/uuid"
)

func TestChatMessageInsertSQLHasNoDroppedMetadataColumn(t *testing.T) {
	if strings.Contains(chatMessageInsertSQL, "metadata") {
		t.Fatalf("chat_messages.metadata was dropped by migration gfix03; insert SQL must not reference it:\n%s", chatMessageInsertSQL)
	}
}

func TestChatMessageInsertSQLTreatsTimestampsAsSeconds(t *testing.T) {
	// Producers (saveMessage, chat_history.go) write Unix *seconds*.
	// The old SQL did to_timestamp($7::bigint / 1000.0) → 1970 rows.
	if strings.Contains(chatMessageInsertSQL, "/ 1000.0") {
		t.Fatalf("insert SQL must not divide seconds timestamps by 1000:\n%s", chatMessageInsertSQL)
	}
	if !strings.Contains(chatMessageInsertSQL, "to_timestamp($6::double precision)") {
		t.Fatalf("insert SQL must interpret $7 as epoch seconds:\n%s", chatMessageInsertSQL)
	}
}

func TestChatMessageInsertSQLConflictTargetMatchesPK(t *testing.T) {
	// chat_messages PK is (id, created_at); bare ON CONFLICT (id) fails with
	// 42P10 ("no unique or exclusion constraint matches").
	if !strings.Contains(chatMessageInsertSQL, "ON CONFLICT (id, created_at) DO NOTHING") {
		t.Fatalf("insert SQL must target the (id, created_at) PK:\n%s", chatMessageInsertSQL)
	}
}

func TestChatMessageInsertSQLDedupesEnginePersistedRows(t *testing.T) {
	// The engine already persists user+assistant rows for streamed chats;
	// the gateway persister must not create duplicate history rows.
	if !strings.Contains(chatMessageInsertSQL, "NOT EXISTS") {
		t.Fatalf("insert SQL must skip rows the engine already persisted:\n%s", chatMessageInsertSQL)
	}
}

func TestResolveSessionUUIDPassthroughAndDeterministicLabel(t *testing.T) {
	raw := "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
	if got := resolveSessionUUID(raw); got.String() != raw {
		t.Fatalf("valid UUID must pass through unchanged, got %s", got)
	}

	label := "df-d2-s1"
	first := resolveSessionUUID(label)
	second := resolveSessionUUID(label)
	if first == (uuid.UUID{}) {
		t.Fatal("label session must not resolve to zero UUID")
	}
	if first != second {
		t.Fatalf("label session must resolve deterministically, got %s vs %s", first, second)
	}
	if first.String() == label {
		t.Fatal("derived UUID must differ from the raw label")
	}
}

// TestResolveSessionUUIDMatchesEngineDerivation pins P2-D (daily-flow R2):
// the gateway must derive the SAME pseudo UUID as the engine's
// `_coerce_session_uuid` (app/orchestration/orchestrator.py), i.e.
// uuid5(NAMESPACE_URL, "sparkle-session:{label}") — SHA-1 based. The pre-fix
// MD5/"sparkle:chat-session:" variant hashed the same label to a different
// UUID, so the NOT EXISTS dedup never matched engine rows and every streamed
// chat turn landed twice (4 rows per turn, R2 eval). The expected value below
// was computed independently with Python's uuid.uuid5.
func TestResolveSessionUUIDMatchesEngineDerivation(t *testing.T) {
	// python: uuid.uuid5(uuid.NAMESPACE_URL, "sparkle-session:df2-d1-s1")
	const want = "fefd227a-b4d1-5c8a-8a15-672c5151c647"
	if got := resolveSessionUUID("df2-d1-s1").String(); got != want {
		t.Fatalf("label derivation diverges from the engine's uuid5: got %s want %s", got, want)
	}
	// Trimming must not change the derivation (engine strips too).
	if got := resolveSessionUUID("  df2-d1-s1\t").String(); got != want {
		t.Fatalf("whitespace-padded label must resolve identically, got %s", got)
	}
}

// TestPersistQueueProducerDisabledSkipsQueue pins the P2-D producer gate:
// with the persister disabled (the new default), SaveMessage must keep the
// Redis read-cache writes but stop enqueueing into queue:persist:history,
// which otherwise grows unbounded with no consumer draining it.
func TestPersistQueueProducerDisabledSkipsQueue(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	svc := NewChatHistoryServiceWithTTL(rdb, time.Minute)
	svc.SetPersistQueueProducerEnabled(false)

	payload := []byte(`{"id":"m1","user_id":"u1","session_id":"s1","role":"user","content":"hi","timestamp":"1789758149"}`)
	if err := svc.SaveMessage(context.Background(), "s1", payload); err != nil {
		t.Fatalf("SaveMessage should succeed with the producer disabled: %v", err)
	}
	if got, _ := rdb.LLen(context.Background(), "queue:persist:history").Result(); got != 0 {
		t.Fatalf("disabled producer must not enqueue, queue length = %d", got)
	}
	if got, _ := rdb.LLen(context.Background(), "chat:history:s1").Result(); got != 1 {
		t.Fatalf("cache writes must be unaffected, cache length = %d", got)
	}

	// The retry buffer must drain (not replay) once the producer is off —
	// buffered entries would never be consumed.
	svc.retryMu.Lock()
	svc.retryBuf = []retryEntry{{msg: payload, enqueuedAt: time.Now()}}
	svc.retryMu.Unlock()
	svc.flushRetryBuf()
	svc.retryMu.Lock()
	left := len(svc.retryBuf)
	svc.retryMu.Unlock()
	if left != 0 {
		t.Fatalf("flushRetryBuf must clear the buffer when the producer is disabled, left = %d", left)
	}
	if got, _ := rdb.LLen(context.Background(), "queue:persist:history").Result(); got != 0 {
		t.Fatalf("disabled producer must not requeue buffered entries, queue length = %d", got)
	}
}

func TestParseMessageTimestampSeconds(t *testing.T) {
	// 1789758149 is a real stranded queue sample (2026-09-18, seconds).
	got := parseMessageTimestampSeconds("1789758149")
	want := time.Unix(1789758149, 0)
	if !got.Equal(want) {
		t.Fatalf("seconds timestamp misparsed: got %v want %v", got, want)
	}

	if got := parseMessageTimestampSeconds(""); got.Before(time.Now().Add(-time.Minute)) {
		t.Fatalf("empty timestamp should fall back to now, got %v", got)
	}

	// Legacy 13-digit ms payloads must not become year-59652 dates.
	ms := parseMessageTimestampSeconds("1789758149123")
	if diff := ms.Sub(time.Unix(1789758149, 123*int64(time.Millisecond))); diff > time.Second || diff < -time.Second {
		t.Fatalf("millisecond timestamp misparsed: got %v", ms)
	}
}

func TestNormalizeChatRole(t *testing.T) {
	// messagerole enum stores SQLAlchemy member NAMES (USER/ASSISTANT/SYSTEM);
	// producers enqueue lowercase roles. The old code inserted "assistant"
	// verbatim → 22P02 invalid enum input, aborting the whole batch.
	if got := normalizeChatRole("assistant"); got != "ASSISTANT" {
		t.Fatalf("assistant must normalize to ASSISTANT, got %q", got)
	}
	if got := normalizeChatRole("user"); got != "USER" {
		t.Fatalf("user must normalize to USER, got %q", got)
	}
	if got := normalizeChatRole(""); got != "USER" {
		t.Fatalf("empty role must default to USER, got %q", got)
	}
	if got := normalizeChatRole("tool"); got != "" {
		t.Fatalf("unknown roles must be rejected, got %q", got)
	}
}

func TestChatSessionUpsertSQLTreatsTimestampsAsSeconds(t *testing.T) {
	if strings.Contains(chatSessionUpsertSQL, "/ 1000.0") {
		t.Fatalf("session upsert SQL must not divide seconds timestamps by 1000:\n%s", chatSessionUpsertSQL)
	}
	if !strings.Contains(chatSessionUpsertSQL, "to_timestamp($4::double precision)") {
		t.Fatalf("session upsert SQL must interpret $4 as epoch seconds:\n%s", chatSessionUpsertSQL)
	}
}
