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

	// V3-FIX-553（CI 负载敏感测试族，同 FIX-544 形态）：select 等的是后台
	// goroutine 首次被调度，等待成立即返回——预算放宽不影响健康路径时长。
	// 2s 是全清单最紧的固定预算（wt805 候选表），CPU 饱和 runner 上 goroutine
	// 调度延迟可超 2s，放宽只消假阴性：2s → 10s。
	select {
	case <-started:
	case <-time.After(10 * time.Second):
		t.Fatal("detached rebuild never started")
	}

	// Memory visibility between the goroutine and the test is established by
	// the channel close above.
	require.NoError(t, errWhileRunning,
		"rebuild context must be alive while the work runs (handler frame already returned)")

	// (2) bounded by projectionRebuildTimeout.
	// 下界余量 1min ≫ 本测试全部等待预算（10s 级），预算放宽不触及该断言。
	require.True(t, hasDeadline, "rebuild context must carry a deadline")
	require.Greater(t, time.Until(deadline), projectionRebuildTimeout-time.Minute,
		"deadline should be roughly projectionRebuildTimeout away")
	require.LessOrEqual(t, time.Until(deadline), projectionRebuildTimeout)

	// (3) released after the work returns.
	// V3-FIX-553：Eventually 本就是相对等待（成立即返回），窗口 2s → 10s
	// 只消负载假阴性；轮询间隔 5ms 不变（远小于窗口，匹配）。
	require.Eventually(t, func() bool {
		return inner.Err() == context.Canceled
	}, 10*time.Second, 5*time.Millisecond,
		"rebuild context must be canceled after the work function returns")
}
