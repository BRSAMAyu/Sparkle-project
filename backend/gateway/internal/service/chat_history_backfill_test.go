package service

import (
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

// TestStartBackfillBoundedAndTracked pins the R2-GW-7 fix on the chat
// history cache backfill: work runs off the request path, concurrency is
// capped (excess backfills are dropped — the cache self-heals on the next
// read), and Stop() waits for in-flight backfills instead of abandoning them.
func TestStartBackfillBoundedAndTracked(t *testing.T) {
	s := &ChatHistoryService{backfillSem: make(chan struct{}, 1)}

	// With a free slot the work runs and Stop() (backfillWg.Wait) waits for it.
	ran := make(chan struct{})
	s.startBackfill(func() { close(ran) })
	select {
	case <-ran:
	case <-time.After(2 * time.Second):
		t.Fatal("backfill work must run when a slot is available")
	}

	// At capacity the work is dropped, never queued or blocked.
	s.backfillSem <- struct{}{} // occupy the only slot
	dropped := false
	s.startBackfill(func() { dropped = true })
	require.False(t, dropped, "backfill must be dropped while at capacity")
	released := false
	s.startBackfill(func() { released = true }) // also dropped (slot busy)
	require.False(t, released)

	// Release and confirm capacity is restored.
	<-s.backfillSem
	s.startBackfill(func() {})
	s.backfillWg.Wait() // must not hang: goroutines release their slots
}

// TestChatHistoryStopWaitsForBackfill pins the Stop() contract addition.
func TestChatHistoryStopWaitsForBackfill(t *testing.T) {
	s := &ChatHistoryService{
		retryStopCh: make(chan struct{}),
		backfillSem: make(chan struct{}, chatHistoryBackfillMaxConcurrent),
	}
	started := make(chan struct{})
	release := make(chan struct{})
	s.startBackfill(func() {
		close(started)
		<-release
	})
	<-started

	stopped := make(chan struct{})
	go func() {
		s.Stop()
		close(stopped)
	}()

	select {
	case <-stopped:
		t.Fatal("Stop must wait for in-flight backfills")
	case <-time.After(50 * time.Millisecond):
	}
	close(release)
	select {
	case <-stopped:
	case <-time.After(2 * time.Second):
		t.Fatal("Stop must return once in-flight backfills finish")
	}
}
