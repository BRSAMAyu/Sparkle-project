package service

import (
	"context"
	"encoding/json"
	"sync"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/metrics"
)

// captureHubWriter records hub deliveries for assertions.
type captureHubWriter struct {
	mu     sync.Mutex
	writes []map[string]interface{}
	closed bool
}

func (w *captureHubWriter) WriteJSON(payload interface{}) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if raw, err := json.Marshal(payload); err == nil {
		var m map[string]interface{}
		if json.Unmarshal(raw, &m) == nil {
			w.writes = append(w.writes, m)
		}
	}
	return nil
}

func (w *captureHubWriter) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.closed = true
	return nil
}

func (w *captureHubWriter) count() int {
	w.mu.Lock()
	defer w.mu.Unlock()
	return len(w.writes)
}

// TestFileEventSubscriberRunWithRestartRecovers pins the R2-GW-3 fix: a
// terminal subscriber failure (Redis down at subscribe time) must not end the
// subscriber's life. RunWithRestart backs off, restarts, increments
// sparkle_file_event_subscriber_restarts_total, and resumes delivering
// file_status events to the hub once Redis is reachable again.
func TestFileEventSubscriberRunWithRestartRecovers(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{
		Addr:        mr.Addr(),
		MaxRetries:  -1,
		DialTimeout: 100 * time.Millisecond,
		ReadTimeout: 500 * time.Millisecond,
	})
	t.Cleanup(func() { _ = rdb.Close() })

	hub := NewFileEventHub()
	writer := &captureHubWriter{}
	hub.Register("user-restart", writer)
	t.Cleanup(func() { hub.Unregister("user-restart", writer) })

	sub := NewFileEventSubscriber(rdb, hub, zap.NewNop())

	restartsBefore := metrics.FileEventSubscriberRestartsValue()

	// Phase 1: Redis fault — every subscribe attempt fails fast.
	mr.Close()

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		sub.RunWithRestart(ctx)
	}()

	// The restart loop must have counted at least one restart while Redis
	// stayed down.
	require.Eventually(t, func() bool {
		return metrics.FileEventSubscriberRestartsValue() > restartsBefore
	}, 5*time.Second, 50*time.Millisecond,
		"terminal subscriber failures must increment the restart counter")

	// Phase 2: Redis restored — the loop must recover and resume delivery.
	// Keep publishing: messages sent before the restart loop resubscribes are
	// legitimately lost (pubsub is live-only), so at least one publish must
	// land after resubscription.
	require.NoError(t, mr.Restart())
	payload, err := json.Marshal(map[string]interface{}{
		"type":     "file_status",
		"file_id":  "file-1",
		"user_id":  "user-restart",
		"status":   "processed",
		"progress": 100,
	})
	require.NoError(t, err)
	require.Eventually(t, func() bool {
		_ = rdb.Publish(context.Background(), "file_status", payload).Err()
		return writer.count() > 0
	}, 10*time.Second, 100*time.Millisecond,
		"subscriber must resume delivering file_status events after restart")

	cancel()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("RunWithRestart must return after context cancellation")
	}
}
