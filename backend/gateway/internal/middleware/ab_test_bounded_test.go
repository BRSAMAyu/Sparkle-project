package middleware

import (
	"testing"
	"time"
)

// TestABTestMetricBoundedDropsAtCapacity pins the R2-GW-7 fix: metric
// recording goroutines are capped. At capacity, new recordings are dropped
// (best-effort telemetry) instead of stacking unbounded goroutines; the
// in-flight ones release their slot when done.
func TestABTestMetricBoundedDropsAtCapacity(t *testing.T) {
	m := &ABTestMiddleware{metricSem: make(chan struct{}, 1)}

	ran := make(chan struct{}, 4)
	started := make(chan struct{})
	release := make(chan struct{})

	// First recording admits (slot free) and blocks, occupying the slot.
	m.recordMetricBounded(func() {
		close(started)
		<-release
		ran <- struct{}{}
	})
	<-started

	// At capacity: this recording must be dropped, not queued.
	m.recordMetricBounded(func() { ran <- struct{}{} })
	select {
	case <-ran:
		t.Fatal("recording must be dropped while at capacity")
	case <-time.After(50 * time.Millisecond):
	}

	// Release the slot: the in-flight recording completes and further
	// recordings are admitted again.
	close(release)
	<-ran
	m.recordMetricBounded(func() { ran <- struct{}{} })
	select {
	case <-ran:
	case <-time.After(2 * time.Second):
		t.Fatal("recording must run once a slot is free")
	}
}
