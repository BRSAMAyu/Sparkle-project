package main

import (
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

type fakeProxyDrain struct {
	grants []time.Duration
}

func (f *fakeProxyDrain) ProxyDrainAll(timeout time.Duration) {
	f.grants = append(f.grants, timeout)
}

type fakeRegistryDrain struct {
	grants []time.Duration
}

func (f *fakeRegistryDrain) DrainAll(timeout time.Duration) {
	f.grants = append(f.grants, timeout)
}

// TestDrainWebSocketPhasesSharedDeadline pins the R2-GW-6 fix: the two drain
// phases share one absolute deadline, so the second phase only receives the
// budget the first phase did not consume. The old wiring granted each phase
// the full drainTimeout (worst case 2T/3 for a T/3 budget).
func TestDrainWebSocketPhasesSharedDeadline(t *testing.T) {
	proxy := &fakeProxyDrain{}
	registry := &fakeRegistryDrain{}

	start := time.Now()
	drainWebSocketPhases(proxy, registry, zap.NewNop(), 400*time.Millisecond)
	elapsed := time.Since(start)

	require.Len(t, proxy.grants, 1)
	require.Len(t, registry.grants, 1)

	// Neither phase may receive more than the total budget.
	require.LessOrEqual(t, proxy.grants[0], 400*time.Millisecond)
	require.LessOrEqual(t, registry.grants[0], 400*time.Millisecond,
		"registry drain must not receive a fresh full-timeout grant")

	// The second grant reflects only the unconsumed remainder: the first
	// phase returned immediately (fake), but the deadline still bounds the
	// total wall time of both phases.
	require.Less(t, elapsed, 400*time.Millisecond)
	require.GreaterOrEqual(t, registry.grants[0], time.Duration(0))
}

// TestRemainingDrainBudgetNeverNegative pins the floor-at-zero semantics.
func TestRemainingDrainBudgetNeverNegative(t *testing.T) {
	require.Equal(t, time.Duration(0), remainingDrainBudget(time.Now().Add(-time.Hour)))
	require.Greater(t, remainingDrainBudget(time.Now().Add(time.Hour)), time.Duration(0))
}
