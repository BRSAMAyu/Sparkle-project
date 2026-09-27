package service

// V3-FIX-427 regression tests: ChatHistoryPersister graceful shutdown used to
// drop the in-flight batch (≤ PersisterBatchSize messages per deploy).
//
// Failure chain (wt716 登记, wt735 复核 CONFIRMED): main.go bgCancel() fires
// before the drain phases finish, so Run's ctx.Done branch called
// flushWithRetry on an already-cancelled context — pool.Acquire failed on the
// first attempt, the retry-backoff select returned ctx.Err() with the batch
// already swapped out of p.batch (neither written nor re-queued), and the
// last-resort requeue discarded every LPush error. The tests below pin the
// durability contract: a shutdown flush must end with the batch in
// PostgreSQL or back in the Redis queue — never silently dropped — and
// requeue push failures must be observable.
//
// The hermetic tests use a bad-DSN pgxpool (port 1 refuses immediately) plus
// miniredis, mirroring the wt735 verification experiment: with no reachable
// database, "not lost" can only mean "back in the queue". The DB-gated test
// (TEST_DATABASE_URL, same convention as internal/db/db_integration_test.go)
// pins the write half end-to-end against a real schema.

import (
	"context"
	"errors"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

// badDSN points at a port that refuses connections immediately, so write
// attempts fail fast without needing a real PostgreSQL.
const badDSN = "postgres://persister_test:persister_test@127.0.0.1:1/persister_test"

func newShutdownTestPersister(t *testing.T) (*ChatHistoryPersister, *miniredis.Miniredis) {
	t.Helper()
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })
	pool, err := pgxpool.New(context.Background(), badDSN)
	if err != nil {
		t.Fatalf("bad-DSN pool must parse: %v", err)
	}
	t.Cleanup(pool.Close)
	return NewChatHistoryPersister(rdb, pool), mr
}

func queuedShutdownMessage() ChatHistoryMessage {
	return ChatHistoryMessage{
		ID:        uuid.NewString(),
		UserID:    uuid.NewString(),
		SessionID: uuid.NewString(),
		Role:      "user",
		Content:   "V3-FIX-427 shutdown flush regression",
		Timestamp: fmt.Sprintf("%d", time.Now().Unix()),
	}
}

func persistQueueLength(t *testing.T, rdb *redis.Client) int64 {
	t.Helper()
	n, err := rdb.LLen(context.Background(), "queue:persist:history").Result()
	if err != nil {
		t.Fatalf("queue length: %v", err)
	}
	return n
}

// TestFlushWithRetryCancelledContextDoesNotDropBatch pins the flushWithRetry
// invariant directly: even when handed an already-cancelled context (as
// Run's shutdown branches did before the fix), the swapped-out batch must
// never vanish — the retry-backoff cancellation path has to hand it back to
// the queue on a context that is not the cancelled one. Pre-fix this failed
// with queue length 0: the batch was neither written nor re-queued.
func TestFlushWithRetryCancelledContextDoesNotDropBatch(t *testing.T) {
	p, _ := newShutdownTestPersister(t)
	p.batch = []ChatHistoryMessage{queuedShutdownMessage()}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	_ = p.flushWithRetry(ctx)

	if got := persistQueueLength(t, p.rdb); got != 1 {
		t.Fatalf("cancelled-context flush must not drop the batch: queue length = %d, want 1 (re-queued)", got)
	}
}

// TestRunShutdownFlushSurvivesContextCancel pins the Run wiring: the final
// flush on ctx.Done must run on a context detached from the cancelled
// shutdown context (detachedPersistCtx precedent in
// handler/chat_orchestrator_chatflow.go) so it can actually reach the
// database or requeue, while Run still reports context.Canceled so
// LogRunnerStopped keeps grading the exit as INFO. Pre-fix this failed with
// queue length 0 — every retry died on the cancelled context and the
// requeue swallowed the LPush errors.
func TestRunShutdownFlushSurvivesContextCancel(t *testing.T) {
	p, _ := newShutdownTestPersister(t)
	p.batch = []ChatHistoryMessage{queuedShutdownMessage()}

	ctx, cancel := context.WithCancel(context.Background())
	errCh := make(chan error, 1)
	go func() { errCh <- p.Run(ctx) }()
	cancel()

	select {
	case err := <-errCh:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("Run must still report context.Canceled on shutdown, got %v", err)
		}
	case <-time.After(20 * time.Second):
		t.Fatal("Run did not exit after context cancel")
	}

	if got := persistQueueLength(t, p.rdb); got != 1 {
		t.Fatalf("shutdown final flush must not drop the batch: queue length = %d, want 1 (re-queued)", got)
	}
}

// TestRequeuePushFailureIsObservable pins the requeue observability fix:
// LPush errors used to be discarded entirely, so a shutdown flush against an
// unreachable Redis lost the batch with zero signal. Push failures must now
// be counted per message and surfaced via GetStats.
func TestRequeuePushFailureIsObservable(t *testing.T) {
	p, mr := newShutdownTestPersister(t)
	p.batch = []ChatHistoryMessage{
		queuedShutdownMessage(),
		queuedShutdownMessage(),
		queuedShutdownMessage(),
	}

	mr.Close() // Redis writes now fail: the requeue path must say so.

	_ = p.flushWithRetry(context.Background())

	if got := p.GetStats()["requeue_failed"]; got != int64(3) {
		t.Fatalf("re-queue push failures must be observable: requeue_failed = %v (%T), want int64(3)", got, got)
	}
}

// TestShutdownFlushWritesBatchToDB pins the write half of the contract
// against a real schema: after a shutdown cancel, the final flush must land
// the batch row in chat_messages. Gated on TEST_DATABASE_URL so the
// hermetic suite stays green without a database.
func TestShutdownFlushWritesBatchToDB(t *testing.T) {
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL not set; skipping DB-backed shutdown flush test")
	}

	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })
	pool, err := pgxpool.New(context.Background(), dsn)
	if err != nil {
		t.Fatalf("test pool: %v", err)
	}
	t.Cleanup(pool.Close)

	ctx := context.Background()

	// The chat_messages FK needs an attributable user; seed one synthetic row
	// and clean it up again (db_integration_test.go writes to the same test DB).
	userID := uuid.New()
	sessionID := uuid.New()
	messageID := uuid.New()
	_, err = pool.Exec(ctx, `
		INSERT INTO users (id, username, email, hashed_password, avatar_status,
			flame_level, flame_brightness, depth_preference, curiosity_preference,
			is_active, is_superuser, status, registration_source, age_verified,
			photon_balance, created_at, updated_at)
		VALUES ($1, $2, $3, 'test-hash', 'PENDING',
			1, 0.5, 0.5, 0.5,
			true, false, 'OFFLINE', 'test', false,
			0, NOW(), NOW())`,
		userID, "wt739-"+userID.String()[:8], "wt739-"+userID.String()+"@example.invalid")
	if err != nil {
		t.Fatalf("seed user: %v", err)
	}
	t.Cleanup(func() {
		// Child rows first, then the user.
		_, _ = pool.Exec(context.Background(), `DELETE FROM chat_messages WHERE user_id = $1`, userID)
		_, _ = pool.Exec(context.Background(), `DELETE FROM chat_sessions WHERE user_id = $1`, userID)
		_, _ = pool.Exec(context.Background(), `DELETE FROM users WHERE id = $1`, userID)
	})

	p := NewChatHistoryPersister(rdb, pool)
	p.batch = []ChatHistoryMessage{{
		ID:        messageID.String(),
		UserID:    userID.String(),
		SessionID: sessionID.String(),
		Role:      "user",
		Content:   "V3-FIX-427 DB write regression",
		Timestamp: fmt.Sprintf("%d", time.Now().Unix()),
	}}

	runCtx, cancel := context.WithCancel(context.Background())
	errCh := make(chan error, 1)
	go func() { errCh <- p.Run(runCtx) }()
	cancel()
	select {
	case err := <-errCh:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("Run must still report context.Canceled on shutdown, got %v", err)
		}
	case <-time.After(20 * time.Second):
		t.Fatal("Run did not exit after context cancel")
	}

	var rows int
	if err := pool.QueryRow(ctx,
		`SELECT count(*) FROM chat_messages WHERE id = $1 AND session_id = $2`,
		messageID, sessionID).Scan(&rows); err != nil {
		t.Fatalf("readback: %v", err)
	}
	if rows != 1 {
		t.Fatalf("shutdown final flush must write the batch to the DB: rows = %d, want 1", rows)
	}
}
