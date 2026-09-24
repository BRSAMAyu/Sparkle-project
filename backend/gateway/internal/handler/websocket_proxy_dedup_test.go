package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
)

// TestWebSocketProxyDedupTimeoutForwardsMessage pins GW-P3-4: the per-message
// dedup Redis round-trip is bounded by wsDedupCheckTimeout. When Redis stalls
// (slowed miniredis), the message must be forwarded anyway after the deadline
// instead of freezing the client→backend pump for the whole Redis stall.
func TestWebSocketProxyDedupTimeoutForwardsMessage(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	// Stall every Redis command for 2s, honoring ctx cancellation: the
	// bounded dedup ctx aborts at wsDedupCheckTimeout (200ms); the old
	// detached context.Background() would sit through the full 2s stall.
	rdb.AddHook(slowRedisHook{delay: 2 * time.Second})
	t.Cleanup(func() { _ = rdb.Close() })
	dedup := service.NewMessageDedupService(rdb)

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{CheckOrigin: func(*http.Request) bool { return true }}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		for {
			mt, data, err := conn.ReadMessage()
			if err != nil {
				return
			}
			if err := conn.WriteMessage(mt, data); err != nil { // echo
				return
			}
		}
	}))
	defer backend.Close()

	proxy := NewWebSocketProxy(backend.URL, zap.NewNop(), &config.Config{
		WSWriteWaitSeconds: 2,
	}, dedup)
	gateway := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		proxy.proxyWebSocket(w, r, backend.URL, "token-123", "user-dedup-timeout", "personal", "")
	}))
	defer gateway.Close()

	conn, wsResp, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(gateway.URL), nil)
	require.NoError(t, err)
	defer wsResp.Body.Close()
	defer conn.Close()

	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"dedup-timeout-probe"}`)))

	// Echo must arrive well below the 2s Redis slowdown: the dedup check
	// aborts at wsDedupCheckTimeout (200ms) and the message is forwarded.
	_ = conn.SetReadDeadline(time.Now().Add(1500 * time.Millisecond))
	start := time.Now()
	_, data, err := conn.ReadMessage()
	require.NoError(t, err, "message must be forwarded despite the stalled dedup backend")
	require.Contains(t, string(data), "dedup-timeout-probe")
	t.Logf("echo latency with stalled dedup: %v", time.Since(start))
}

// slowRedisHook delays every Redis command, aborting early when its context
// is cancelled (ctx-aware stall, replacing miniredis's missing SetSlowdown).
type slowRedisHook struct {
	delay time.Duration
}

func (h slowRedisHook) DialHook(next redis.DialHook) redis.DialHook { return next }

func (h slowRedisHook) ProcessHook(next redis.ProcessHook) redis.ProcessHook {
	return func(ctx context.Context, cmd redis.Cmder) error {
		select {
		case <-time.After(h.delay):
			return next(ctx, cmd)
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func (h slowRedisHook) ProcessPipelineHook(next redis.ProcessPipelineHook) redis.ProcessPipelineHook {
	return next
}
