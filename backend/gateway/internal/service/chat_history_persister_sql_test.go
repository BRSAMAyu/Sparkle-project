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
	"strings"
	"testing"
	"time"

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
