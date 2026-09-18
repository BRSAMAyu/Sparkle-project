package main

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

// Regression test for GW-P1-4: background projection rebuilds used to run on
// c.Request.Context(), which net/http cancels the moment the handler returns
// — every rebuild was aborted right after "rebuild_started" was answered.
// startDetachedRebuild must give the work a context that (1) survives the
// caller returning, (2) carries the projectionRebuildTimeout deadline, and
// (3) is released once the work completes.
func TestStartDetachedRebuildContextSurvivesCallerReturn(t *testing.T) {
	started := make(chan struct{})
	var (
		inner           context.Context
		deadline        time.Time
		hasDeadline     bool
		errWhileRunning error
	)

	startDetachedRebuild(func(ctx context.Context) {
		// (1) checked from inside the work function: the context is released
		// as soon as the work returns (by design), so the caller frame has
		// long returned by the time the test goroutine observes anything.
		errWhileRunning = ctx.Err()
		deadline, hasDeadline = ctx.Deadline()
		inner = ctx
		close(started)
	})

	select {
	case <-started:
	case <-time.After(2 * time.Second):
		t.Fatal("detached rebuild never started")
	}

	// Memory visibility between the goroutine and the test is established by
	// the channel close above.
	require.NoError(t, errWhileRunning,
		"rebuild context must be alive while the work runs (handler frame already returned)")

	// (2) bounded by projectionRebuildTimeout.
	require.True(t, hasDeadline, "rebuild context must carry a deadline")
	require.Greater(t, time.Until(deadline), projectionRebuildTimeout-time.Minute,
		"deadline should be roughly projectionRebuildTimeout away")
	require.LessOrEqual(t, time.Until(deadline), projectionRebuildTimeout)

	// (3) released after the work returns.
	require.Eventually(t, func() bool {
		return inner.Err() == context.Canceled
	}, 2*time.Second, 5*time.Millisecond,
		"rebuild context must be canceled after the work function returns")
}
