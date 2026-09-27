package outbox

// V3-FIX-469 regression tests: the processed_events durable idempotency gate
// must accept the event-key forms its only production caller (BaseWorker)
// actually sends — Redis stream message IDs in "ms-seq" form (e.g. "1758-0") —
// instead of rejecting every call at a uuid.Parse format assumption. The
// schema column processed_events.event_id is varchar(100) and the SQLC queries
// take a plain string: the gate died purely in the Go layer.
//
// Red→green without a live Postgres: the repository must forward the validated
// key to the idempotency SQL verbatim (byte-for-byte — the
// (event_id, consumer_group) PK match depends on it). A fake db.DBTX captures
// the forwarded arguments. The true end-to-end absorption round trip against
// Postgres is pinned by the TEST_DATABASE_URL-gated test below (same skip
// convention as internal/db/db_integration_test.go; no stack is started here).

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/db"
)

// --- fake db.DBTX capturing forwarded SQL arguments ------------------------

// fakeDBTX records the arguments the repository forwards to the SQL layer so
// tests can pin exactly which event key reaches processed_events.
type fakeDBTX struct {
	execSQL string
	execErr error
	// execArgs holds the args of the most recent Exec (MarkEventProcessed path).
	execArgs []any

	rowSQL string
	// rowArgs holds the args of the most recent QueryRow (IsEventProcessed path).
	rowArgs []any
	exists  bool
}

func (f *fakeDBTX) Exec(_ context.Context, sql string, args ...any) (pgconn.CommandTag, error) {
	f.execSQL, f.execArgs = sql, args
	if f.execErr != nil {
		return pgconn.CommandTag{}, f.execErr
	}
	return pgconn.NewCommandTag("INSERT 0 1"), nil
}

func (f *fakeDBTX) Query(context.Context, string, ...any) (pgx.Rows, error) {
	return nil, errors.New("fakeDBTX: Query not expected by processed-events tests")
}

func (f *fakeDBTX) QueryRow(_ context.Context, sql string, args ...any) pgx.Row {
	f.rowSQL, f.rowArgs = sql, args
	return fakeExistsRow{exists: f.exists}
}

type fakeExistsRow struct{ exists bool }

func (r fakeExistsRow) Scan(dest ...any) error {
	if len(dest) != 1 {
		return fmt.Errorf("fakeExistsRow: want 1 dest, got %d", len(dest))
	}
	b, ok := dest[0].(*bool)
	if !ok {
		return errors.New("fakeExistsRow: dest is not *bool")
	}
	*b = r.exists
	return nil
}

func newTestProcessedRepo(f *fakeDBTX) *ProcessedEventsRepository {
	return &ProcessedEventsRepository{queries: db.New(f)}
}

// --- contract tests (always run) -------------------------------------------

// TestProcessedEventsGateAcceptsRedisStreamID is the V3-FIX-469 red test:
// BaseWorker.isProcessed/markProcessed pass the XReadGroup message ID
// ("ms-seq" form). The gate must persist and match such keys verbatim
// instead of failing at a UUID format assumption.
func TestProcessedEventsGateAcceptsRedisStreamID(t *testing.T) {
	const (
		streamID = "1758-0" // redis stream "ms-seq" form, as XReadGroup delivers
		group    = "community_sync_v1"
	)
	f := &fakeDBTX{exists: true}
	repo := newTestProcessedRepo(f)
	ctx := context.Background()

	// MarkProcessed must persist the stream ID verbatim.
	require.NoError(t, repo.MarkProcessed(ctx, streamID, group))
	require.Contains(t, f.execSQL, "processed_events")
	require.Equal(t, []any{streamID, group}, f.execArgs,
		"MarkProcessed must forward the stream ID unchanged as event_id")

	// IsProcessed must query with the same verbatim key and absorb replays.
	f.rowArgs = nil
	got, err := repo.IsProcessed(ctx, streamID, group)
	require.NoError(t, err)
	require.True(t, got, "a stream ID marked processed must be absorbed on replay")
	require.Contains(t, f.rowSQL, "processed_events")
	require.Equal(t, []any{streamID, group}, f.rowArgs,
		"IsProcessed must forward the stream ID unchanged as event_id")
}

// TestProcessedEventsGateKeepsUUIDCanonicalization pins backward compatibility
// with the pre-fix write path: rows were stored through uuid.Parse's canonical
// form, so a non-canonical spelling of the same UUID must still canonicalize
// to the stored form (any hypothetical pre-existing rows keep being hit).
func TestProcessedEventsGateKeepsUUIDCanonicalization(t *testing.T) {
	const group = "galaxy_sync_v1"
	id := uuid.New()
	upper := strings.ToUpper(id.String()) // non-canonical spelling
	f := &fakeDBTX{exists: true}
	repo := newTestProcessedRepo(f)
	ctx := context.Background()

	require.NoError(t, repo.MarkProcessed(ctx, upper, group))
	require.Equal(t, []any{id.String(), group}, f.execArgs,
		"UUID-form keys must canonicalize exactly as the pre-fix gate stored them")

	got, err := repo.IsProcessed(ctx, upper, group)
	require.NoError(t, err)
	require.True(t, got)
	require.Equal(t, []any{id.String(), group}, f.rowArgs)
}

// TestProcessedEventsGateGuardsColumnWidth: any key up to the event_id column
// width (varchar(100)) must pass validation — including 100-char keys — while
// longer keys fail fast in Go (not at a DB value-too-long error) and empty
// keys are rejected.
func TestProcessedEventsGateGuardsColumnWidth(t *testing.T) {
	const group = "community_sync_v1"
	ctx := context.Background()

	ok100 := strings.Repeat("a", 100)
	mf := &fakeDBTX{}
	require.NoError(t, newTestProcessedRepo(mf).MarkProcessed(ctx, ok100, group),
		"a 100-char key exactly fits varchar(100) and must not be rejected")
	require.Equal(t, []any{ok100, group}, mf.execArgs)

	over := strings.Repeat("a", 101)
	err := newTestProcessedRepo(&fakeDBTX{}).MarkProcessed(ctx, over, group)
	require.Error(t, err)
	require.NotContains(t, err.Error(), "parse event ID",
		"rejection must be a width guard, not the removed UUID format gate")

	_, err = newTestProcessedRepo(&fakeDBTX{}).IsProcessed(ctx, "", group)
	require.Error(t, err, "empty event keys must be rejected")
}

// --- end-to-end absorption round trip (needs a real Postgres) --------------

// TestProcessedEventsRoundTripAgainstPostgres pins the true durable absorption
// contract: a stream-ID key marked processed by one consumer group is absorbed
// for that group and invisible to another; re-marking is idempotent. Skipped
// unless TEST_DATABASE_URL points at a schema-loaded test database (same
// convention as internal/db/db_integration_test.go).
func TestProcessedEventsRoundTripAgainstPostgres(t *testing.T) {
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL not set; skipping DB-backed processed_events round-trip test")
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
	const group = "wt749_gate_roundtrip_group"
	// Unique stream-ID-form key per run so repeated runs on a shared test DB
	// never collide and cleanup only ever touches rows this test wrote.
	streamID := fmt.Sprintf("1758-%d", time.Now().UnixNano())

	cleanup := func() {
		_, _ = pool.Exec(ctx,
			`DELETE FROM processed_events WHERE event_id = $1 AND consumer_group = $2`,
			streamID, group)
	}
	cleanup()
	t.Cleanup(cleanup)

	require.NoError(t, repo.MarkProcessed(ctx, streamID, group))

	got, err := repo.IsProcessed(ctx, streamID, group)
	require.NoError(t, err)
	require.True(t, got, "marked stream ID must be absorbed for its own group after a fresh process start")

	other, err := repo.IsProcessed(ctx, streamID, group+"_b")
	require.NoError(t, err)
	require.False(t, other, "absorption must stay scoped per consumer group")

	// Idempotent re-mark (ON CONFLICT DO NOTHING) must not error.
	require.NoError(t, repo.MarkProcessed(ctx, streamID, group))
}
