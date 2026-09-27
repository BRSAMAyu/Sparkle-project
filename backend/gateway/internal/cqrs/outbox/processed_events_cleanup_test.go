package outbox

// V3-FIX-487 row-level retention pins for ProcessedEventsRepository.Cleanup.
//
// The unit tests here pin the Go-side forwarding contract without a live
// Postgres (fakeDBTX, same convention as the 469 file); the true purge
// semantics — rows past the retention window deleted, rows inside kept, and
// the IsProcessed/MarkProcessed idempotency round trip unaffected by a purge —
// are pinned by the TEST_DATABASE_URL-gated test at the bottom (skipped when
// no schema-loaded test database is configured; no stack is started here).

import (
	"context"
	"fmt"
	"math"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/require"
)

// TestProcessedEventsCleanupForwardsRetentionDays: Cleanup must hand the
// retention window to the SQL layer verbatim (as int32) and touch the
// processed_events table; out-of-int32 retention fails fast in Go instead of
// reaching SQL.
func TestProcessedEventsCleanupForwardsRetentionDays(t *testing.T) {
	f := &fakeDBTX{}
	repo := newTestProcessedRepo(f)
	ctx := context.Background()

	deleted, err := repo.Cleanup(ctx, 7)
	require.NoError(t, err)
	require.Equal(t, int64(1), deleted, "fakeDBTX reports a 1-row command tag")
	require.Contains(t, f.execSQL, "DELETE FROM processed_events",
		"cleanup must purge processed_events rows")
	require.Contains(t, f.execSQL, "processed_at",
		"purge selection must be by processed age")
	require.Equal(t, []any{int32(7)}, f.execArgs,
		"retention days must be forwarded unchanged as the SQL cutoff argument")

	f.execArgs = nil
	_, err = repo.Cleanup(ctx, math.MaxInt32+1)
	require.Error(t, err, "out-of-int32 retention must fail fast in Go")
	require.Nil(t, f.execArgs, "a rejected retention value must never reach SQL")
}

// TestProcessedEventsRetentionPurgeAgainstPostgres pins the durable retention
// contract end to end:
//  1. a processed_events row older than the retention window is purged by
//     Cleanup (the unbounded-growth fix actually reclaims rows);
//  2. a row inside the window survives (recent absorption is intact);
//  3. after a purge, re-marking the purged key succeeds and IsProcessed sees
//     it again — the purge must not corrupt the idempotency round trip
//     (ON CONFLICT DO NOTHING semantics untouched);
//  4. the purge stays scoped per consumer group (a fresh row of another group
//     is never collateral).
func TestProcessedEventsRetentionPurgeAgainstPostgres(t *testing.T) {
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL not set; skipping DB-backed processed_events retention purge test")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Skipf("Could not connect to test database: %v", err)
	}
	defer pool.Close()
	if err := pool.Ping(ctx); err != nil {
		t.Skipf("Could not reach test database: %v", err)
	}

	repo := NewProcessedEventsRepository(pool)
	const group = "wt757_retention_purge_group"
	// Unique stream-ID-form keys per run so repeated runs on a shared test DB
	// never collide and cleanup only ever judges rows this test wrote.
	staleID := fmt.Sprintf("1758-stale-%d", time.Now().UnixNano())
	freshID := fmt.Sprintf("1758-fresh-%d", time.Now().UnixNano())
	otherGroupID := fmt.Sprintf("1758-other-%d", time.Now().UnixNano())

	cleanup := func() {
		_, _ = pool.Exec(ctx,
			`DELETE FROM processed_events WHERE (event_id, consumer_group) IN (($1, $2), ($3, $2), ($4, $5))`,
			staleID, group, freshID, otherGroupID, group+"_b")
	}
	cleanup()
	t.Cleanup(cleanup)

	// stale row: processed 8 days ago (outside a 7-day window)
	_, err = pool.Exec(ctx,
		`INSERT INTO processed_events (event_id, consumer_group, processed_at) VALUES ($1, $2, NOW() - INTERVAL '8 days')`,
		staleID, group)
	require.NoError(t, err)
	// fresh row: processed just now (inside the window)
	require.NoError(t, repo.MarkProcessed(ctx, freshID, group))
	// fresh row of ANOTHER group, same staleness profile as freshID
	require.NoError(t, repo.MarkProcessed(ctx, otherGroupID, group+"_b"))

	deleted, err := repo.Cleanup(ctx, 7)
	require.NoError(t, err)

	got, err := repo.IsProcessed(ctx, freshID, group)
	require.NoError(t, err)
	require.True(t, got, "a row inside the retention window must survive cleanup")

	stale, err := repo.IsProcessed(ctx, staleID, group)
	require.NoError(t, err)
	require.False(t, stale, "a row past the retention window must be purged")
	require.GreaterOrEqual(t, deleted, int64(1), "cleanup must report the stale row as deleted")

	other, err := repo.IsProcessed(ctx, otherGroupID, group+"_b")
	require.NoError(t, err)
	require.True(t, other, "a fresh row of another consumer group must survive cleanup")

	// Re-marking the purged key must succeed (ON CONFLICT DO NOTHING round
	// trip intact after a purge) and be visible to IsProcessed again.
	require.NoError(t, repo.MarkProcessed(ctx, staleID, group))
	regot, err := repo.IsProcessed(ctx, staleID, group)
	require.NoError(t, err)
	require.True(t, regot, "idempotency gate must accept a re-mark after the row was purged")
}
