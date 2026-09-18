package handler

import (
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
)

// TestWebSocketProxyReconnectCheckAndRecordAtomic pins GW-P3-5: the reconnect
// admission decision and the attempt recording must happen in one atomic
// step. With the old split (check under one lock, record under another), two
// concurrent reconnects could both observe "allowed" before either recorded —
// deterministically reproducible at the last budget slot: both checks return
// true and attemptCount overshoots to max+1. The merged decision removes the
// interleaving window entirely.
func TestWebSocketProxyReconnectCheckAndRecordAtomic(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{}, nil)
	userID := "user-reconnect-atomic"

	const workers = 32
	start := make(chan struct{})
	var wg sync.WaitGroup
	var mu sync.Mutex
	admitted := 0
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start // release all workers at once to maximize contention
			for i := 0; i < reconnectMaxAttemptsDefault; i++ {
				if proxy.checkAndRecordReconnect(userID) {
					mu.Lock()
					admitted++
					mu.Unlock()
				}
			}
		}()
	}
	close(start)
	wg.Wait()

	require.LessOrEqual(t, admitted, reconnectMaxAttemptsDefault,
		"atomic check-and-record must never admit more than maxAttempts")
	require.Equal(t, reconnectMaxAttemptsDefault, admitted,
		"exactly maxAttempts reconnects must be admitted")

	// Window reset semantics survive the merge: after the sliding window
	// expires (and any block is lifted) admission reopens.
	proxy.mu.Lock()
	reopened := time.Now().Add(-2 * time.Duration(reconnectWindowSecDefault+reconnectBlockSecDefault) * time.Second)
	proxy.reconnectTrackers[userID].lastAttempt = reopened
	proxy.reconnectTrackers[userID].blockedUntil = reopened
	proxy.mu.Unlock()
	require.True(t, proxy.checkAndRecordReconnect(userID),
		"admission must reopen after the window and block expire")
}
