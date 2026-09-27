package outbox

// V3-FIX-487 contract tests: the processed_events retention cleaner must be a
// standalone periodic maintenance runner (startup sweep + ticker), not dead
// code. Before this card, ProcessedEventsRepository.Cleanup had zero callers
// repo-wide: since V3-FIX-469 every processed event really INSERTs a row, so
// the DB-side authoritative duplicate gate grew monotonically with no purge
// (the DB mirror of V3-FIX-481's in-process unbounded cache).
//
// Red→green without a live Postgres: a recording fake stands in for the
// repository so the loop's contract (sweep at startup, then once per tick;
// configured retention forwarded verbatim; keeps sweeping through injected
// errors; stops on context cancel) is pinned. The true row-level retention
// semantics (rows past the window purged, rows inside kept, IsProcessed
// idempotency unaffected) are pinned by the TEST_DATABASE_URL-gated test in
// processed_events_cleanup_test.go (same skip convention as the 469 file).

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"go.uber.org/zap"
)

// recordingCleanupRepo records every Cleanup call and can be told to fail the
// first N calls to prove the loop survives transient DB outages.
type recordingCleanupRepo struct {
	mu         sync.Mutex
	retentions []int
	failFirst  int
}

func (r *recordingCleanupRepo) Cleanup(_ context.Context, retentionDays int) (int64, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.retentions = append(r.retentions, retentionDays)
	if len(r.retentions) <= r.failFirst {
		return 0, errors.New("injected cleanup outage")
	}
	return 1, nil
}

func (r *recordingCleanupRepo) calls() []int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]int(nil), r.retentions...)
}

// TestProcessedEventsCleanerSweepsAtStartupThenPerTick pins the loop cadence:
// one sweep immediately at startup (so the first deployment of this fix
// reclaims any legacy accumulation without waiting a full interval) plus at
// least one more on the ticker, each carrying the configured retention days.
func TestProcessedEventsCleanerSweepsAtStartupThenPerTick(t *testing.T) {
	repo := &recordingCleanupRepo{}
	cleaner := NewProcessedEventsCleaner(repo, zap.NewNop(), ProcessedEventsCleanerConfig{
		RetentionDays: 7,
		CleanInterval: 5 * time.Millisecond,
	})

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- cleaner.Run(ctx) }()

	deadline := time.Now().Add(2 * time.Second)
	for len(repo.calls()) < 2 && time.Now().Before(deadline) {
		time.Sleep(2 * time.Millisecond)
	}
	cancel()
	<-done

	calls := repo.calls()
	if len(calls) < 2 {
		t.Fatalf("cleaner swept %d times before cancel, want >= 2 (startup + ticker): no periodic maintenance wired (V3-FIX-487)", len(calls))
	}
	for i, got := range calls {
		if got != 7 {
			t.Fatalf("sweep %d forwarded retention %d, want 7 (configured value must reach the SQL verbatim)", i, got)
		}
	}
}

// TestProcessedEventsCleanerKeepsSweepingAfterErrors pins outage tolerance:
// injected Cleanup failures must not kill the loop — the next tick retries
// (matching the outbox Cleaner / DLQCleaner error posture: log and continue).
func TestProcessedEventsCleanerKeepsSweepingAfterErrors(t *testing.T) {
	repo := &recordingCleanupRepo{failFirst: 3}
	cleaner := NewProcessedEventsCleaner(repo, zap.NewNop(), ProcessedEventsCleanerConfig{
		RetentionDays: 7,
		CleanInterval: 2 * time.Millisecond,
	})

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- cleaner.Run(ctx) }()

	deadline := time.Now().Add(2 * time.Second)
	for len(repo.calls()) <= 3 && time.Now().Before(deadline) {
		time.Sleep(2 * time.Millisecond)
	}
	cancel()
	<-done

	if got := len(repo.calls()); got <= 3 {
		t.Fatalf("cleaner stopped after %d calls while the first 3 errored: loop must keep sweeping through transient failures", got)
	}
}

// TestProcessedEventsCleanerStopsOnContextCancel pins graceful shutdown: after
// ctx is cancelled Run returns and no further sweeps are issued.
func TestProcessedEventsCleanerStopsOnContextCancel(t *testing.T) {
	repo := &recordingCleanupRepo{}
	cleaner := NewProcessedEventsCleaner(repo, zap.NewNop(), ProcessedEventsCleanerConfig{
		RetentionDays: 7,
		CleanInterval: 2 * time.Millisecond,
	})

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- cleaner.Run(ctx) }()

	deadline := time.Now().Add(2 * time.Second)
	for len(repo.calls()) < 1 && time.Now().Before(deadline) {
		time.Sleep(2 * time.Millisecond)
	}
	cancel()
	if err := <-done; err == nil {
		t.Fatalf("Run returned nil after ctx cancel, want context error like sibling runners")
	}
	stable := len(repo.calls())
	deadline = time.Now().Add(100 * time.Millisecond)
	for time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
		if got := len(repo.calls()); got != stable {
			t.Fatalf("cleaner kept sweeping after cancel: %d -> %d calls", stable, got)
		}
	}
}

// TestProcessedEventsCleanerGuardsMisconfiguration pins the zero/negative
// config guard: retention <= 0 would make the SQL cutoff land in the future
// and purge the WHOLE table, and a non-positive interval panics NewTicker.
// Both must fall back to the documented defaults instead.
func TestProcessedEventsCleanerGuardsMisconfiguration(t *testing.T) {
	repo := &recordingCleanupRepo{}
	cleaner := NewProcessedEventsCleaner(repo, zap.NewNop(), ProcessedEventsCleanerConfig{
		RetentionDays: 0, // misconfigured: must default, not purge-all
		CleanInterval: time.Millisecond,
	})

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- cleaner.Run(ctx) }()

	deadline := time.Now().Add(2 * time.Second)
	for len(repo.calls()) < 1 && time.Now().Before(deadline) {
		time.Sleep(2 * time.Millisecond)
	}
	cancel()
	<-done

	calls := repo.calls()
	if len(calls) == 0 {
		t.Fatalf("cleaner never swept")
	}
	for i, got := range calls {
		if got != DefaultProcessedEventsRetentionDays {
			t.Fatalf("sweep %d forwarded retention %d with zero-config input, want default %d (retention <= 0 must not purge the whole table)", i, got, DefaultProcessedEventsRetentionDays)
		}
	}

	if func() (panicked bool) {
		defer func() { panicked = recover() != nil }()
		NewProcessedEventsCleaner(repo, zap.NewNop(), ProcessedEventsCleanerConfig{RetentionDays: 7, CleanInterval: 0})
		NewProcessedEventsCleaner(repo, zap.NewNop(), ProcessedEventsCleanerConfig{RetentionDays: 7, CleanInterval: -time.Second})
		return
	}() {
		t.Fatalf("non-positive clean interval must be defaulted, NewTicker would panic")
	}
}
