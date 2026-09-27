package main

// V3-FIX-487 structural wiring guard.
//
// ProcessedEventsRepository.Cleanup sat at zero callers repo-wide: the
// processed_events durable idempotency gate (authoritative since V3-FIX-469)
// grew monotonically with no purge. The fix wires a dedicated periodic
// cleaner into the gateway's background maintenance set — the same posture as
// the outbox Cleaner and DLQCleaner (own goroutine, started by
// startCQRSWorkers, shutdown-graded by LogRunnerStopped).
//
// This guard pins the wiring at the three structural points so the purge can
// not silently detach again (e.g. the goroutine start dropped in a refactor):
// bundle field, construction in initCQRS, and the go statement in
// startCQRSWorkers. Removing any of them requires deleting a literal here —
// a deliberate, reviewable adjudication.

import (
	"os"
	"strings"
	"testing"
)

func TestProcessedEventsCleanupWiredIntoPeriodicMaintenance(t *testing.T) {
	src, err := os.ReadFile("setup.go")
	if err != nil {
		t.Fatalf("read setup.go: %v", err)
	}
	body := string(src)

	required := []string{
		// bundle field alongside the other runner closures
		"processedEventsCleanerRun func()",
		// construction: the cleaner must be built on the real processed_events repo
		"NewProcessedEventsCleaner(",
		// runner closure bound with shutdown-grade logging like its siblings
		"processedEventsCleanerRun: func()",
		// and actually started with the other periodic workers
		"go cqrs.processedEventsCleanerRun()",
	}
	for _, want := range required {
		if !strings.Contains(body, want) {
			t.Fatalf("setup.go missing %q: processed_events retention cleanup is not wired into periodic maintenance (V3-FIX-487)", want)
		}
	}
}
