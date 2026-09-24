package outbox

// PROD-FIX-2 defect #6 regression pins: the outbox publisher must back off
// exponentially under a persistent downstream outage instead of erroring at
// the fixed poll cadence (production evidence: 8,494 "Failed to publish
// batch" logs — 10/s — during a 16h DB outage), rate-limit the same-cause
// error log, and reset to the normal cadence with a recovery log line on
// first success.

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"go.uber.org/zap/zaptest/observer"

	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
)

// --- fakes -----------------------------------------------------------------

// fakeRepo is safe for concurrent use: Run's poll goroutine calls
// GetUnpublished while the test goroutine flips the outage to healed
// (CI -race, run 35962100809 — the fields used to be written raw).
type fakeRepo struct {
	mu                sync.Mutex
	getUnpublishedErr error
	entries           []*event.OutboxEntry
	getCalls          int
}

func (f *fakeRepo) InsertWithTx(context.Context, pgx.Tx, *event.OutboxEntry) error { return nil }
func (f *fakeRepo) Insert(context.Context, *event.OutboxEntry) error               { return nil }
func (f *fakeRepo) GetUnpublished(context.Context, int) ([]*event.OutboxEntry, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.getCalls++
	// Snapshot under the lock; heal replaces the slice header instead of
	// mutating entries in place, so iterating the snapshot is race-free.
	return f.entries, f.getUnpublishedErr
}

// heal ends the simulated outage: clears the GetUnpublished error and queues
// the given pending entries as one atomic state transition observable by the
// polling Run goroutine.
func (f *fakeRepo) heal(entries ...*event.OutboxEntry) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.getUnpublishedErr = nil
	f.entries = entries
}
func (f *fakeRepo) MarkPublished(context.Context, []uuid.UUID) error { return nil }
func (f *fakeRepo) DeleteOld(context.Context, int) (int64, error)    { return 0, nil }
func (f *fakeRepo) GetPendingCount(context.Context) (int64, error)   { return 0, nil }

type fakeBus struct {
	publishErr error
	publishes  int
}

func (f *fakeBus) Publish(context.Context, event.DomainEvent) error {
	f.publishes++
	return f.publishErr
}
func (f *fakeBus) PublishBatch(ctx context.Context, events []event.DomainEvent) error {
	for range events {
		if err := f.Publish(ctx, event.DomainEvent{}); err != nil {
			return err
		}
	}
	return nil
}
func (f *fakeBus) Close() error { return nil }

// testMetrics is shared across tests: NewCQRSMetrics registers on the
// default prometheus registerer via promauto, which panics on duplicates.
var testMetrics = metrics.NewCQRSMetrics("sparkle_test_outbox")

func newTestPublisher(repo Repository, bus event.EventBus) (*Publisher, *observer.ObservedLogs) {
	core, logs := observer.New(zapcore.DebugLevel)
	logger := zap.New(core)
	p := NewPublisher(repo, bus, testMetrics, logger, PublisherConfig{
		BatchSize:    10,
		PollInterval: 10 * time.Millisecond,
		MaxBackoff:   80 * time.Millisecond,
	})
	return p, logs
}

// --- unit pins: backoff curve ----------------------------------------------

func TestBackoffDelay_DoublesPerFailureAndCaps(t *testing.T) {
	p, _ := newTestPublisher(&fakeRepo{}, &fakeBus{})
	require.Equal(t, 80*time.Millisecond, p.maxBackoff)

	want := []time.Duration{20 * time.Millisecond, 40 * time.Millisecond, 80 * time.Millisecond}
	for i, w := range want {
		p.consecutiveFailures = i + 1
		require.Equal(t, w, p.backoffDelay(), "failure #%d", i+1)
	}
	// Saturated outage: stays pinned at the cap.
	p.consecutiveFailures = 50
	require.Equal(t, p.maxBackoff, p.backoffDelay())
}

// --- unit pins: log rate limiting and metrics ------------------------------

func TestNoteFailure_LogsFirstAndEveryTenthOnly(t *testing.T) {
	p, logs := newTestPublisher(&fakeRepo{getUnpublishedErr: errors.New("dial tcp: connection refused")}, &fakeBus{})

	for i := 0; i < 25; i++ {
		p.noteFailure(errors.New("dial tcp: connection refused"))
	}

	errLogs := logs.FilterMessage("Failed to publish batch").All()
	require.Len(t, errLogs, 3, "only failure #1, #10, #20 may log Error at Error level")
	require.Equal(t, zapcore.ErrorLevel, errLogs[0].Level)
	require.Equal(t, 25, p.consecutiveFailures)
}

func TestNoteSuccess_ResetsCadenceAndLogsRecovery(t *testing.T) {
	p, logs := newTestPublisher(&fakeRepo{}, &fakeBus{})

	p.noteFailure(errors.New("boom"))
	p.noteFailure(errors.New("boom"))
	require.Equal(t, 2, p.consecutiveFailures)

	p.noteSuccess()

	require.Equal(t, 0, p.consecutiveFailures)
	require.True(t, p.firstFailureAt.IsZero())
	recoveries := logs.FilterMessage("Outbox publish recovered").All()
	require.Len(t, recoveries, 1)
	require.Equal(t, zapcore.InfoLevel, recoveries[0].Level)

	// Clean baseline: no spurious recovery log when nothing failed.
	p.noteSuccess()
	require.Len(t, logs.FilterMessage("Outbox publish recovered").All(), 1)
}

// --- loop behavior: outage cadence + recovery + clean shutdown -------------

func TestRun_BacksoffDuringOutageAndKeepsContextCancellationResponsive(t *testing.T) {
	repo := &fakeRepo{getUnpublishedErr: errors.New("dial tcp: connection refused")}
	p, logs := newTestPublisher(repo, &fakeBus{})

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- p.Run(ctx) }()

	// Naive cadence (no backoff, 10ms poll) would attempt ~24 times in 150ms.
	time.Sleep(150 * time.Millisecond)
	cancel()
	require.ErrorIs(t, <-done, context.Canceled)

	attempts := repo.getCalls
	require.GreaterOrEqual(t, attempts, 3, "must still retry during outage")
	require.LessOrEqual(t, attempts, 10,
		"persistent outage must back off, not poll at the fixed cadence (got %d attempts in 150ms)", attempts)

	errLogs := logs.FilterMessage("Failed to publish batch").All()
	require.LessOrEqual(t, len(errLogs), attempts/5+1, "same-cause error log must be rate-limited")
}

func TestRun_RecoversToNormalCadenceAfterOutage(t *testing.T) {
	repo := &fakeRepo{getUnpublishedErr: errors.New("connection refused")}
	bus := &fakeBus{}
	p, logs := newTestPublisher(repo, bus)

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- p.Run(ctx) }()

	// Let it fail a few times, then heal the downstream with a pending entry.
	time.Sleep(40 * time.Millisecond)
	repo.heal(&event.OutboxEntry{
		ID:        uuid.New(),
		EventType: event.EventTaskCreated,
		Payload:   []byte("{}"),
		CreatedAt: time.Now(),
	})
	time.Sleep(60 * time.Millisecond)
	cancel()
	require.ErrorIs(t, <-done, context.Canceled)

	require.Len(t, logs.FilterMessage("Outbox publish recovered").All(), 1,
		"first success after the failure streak must log recovery")

	// Post-recovery cadence is the normal pollInterval: enough attempts to
	// prove liveness, none of them failing.
	require.Greater(t, bus.publishes, 0)
	require.Empty(t, logs.FilterMessage("Failed to publish event").All())
}
