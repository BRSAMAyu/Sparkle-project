package handler

import (
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
)

// TestFileEventHandler_HubSendOverlapsRateLimitClose is the write-half
// regression for GW-P0-1: the handler used to write close frames with a bare
// conn.WriteMessage while the Redis subscriber goroutine wrote data frames
// via hub.Send on the same conn — gorilla panics with "concurrent write to
// websocket connection" on that overlap, and the subscriber goroutine has no
// recover, so the panic was process-fatal. Both writes must go through the
// registered wsSafeWriter.
func TestFileEventHandler_HubSendOverlapsRateLimitClose(t *testing.T) {
	hub := service.NewFileEventHub()
	cfg := &config.Config{Environment: "development", AllowedOrigins: []string{"*"}}
	h := NewFileEventHandler(NewWebSocketFactory(cfg), hub, cfg)

	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ws/files", func(c *gin.Context) {
		c.Set("user_id", "file-hub-user")
		h.HandleWebSocket(c)
	})
	ts := httptest.NewServer(r)
	defer ts.Close()

	client, wsResp, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(ts.URL, "http")+"/ws/files", nil)
	require.NoError(t, err)
	defer wsResp.Body.Close()
	defer client.Close()

	require.Eventually(t, func() bool {
		return hub.Count("file-hub-user") == 1
	}, 2*time.Second, 5*time.Millisecond, "connection should be registered in the hub")

	stop := make(chan struct{})
	var wg sync.WaitGroup

	// Redis file_status subscriber stand-in: data-frame writes via hub.Send
	// overlapping the handler's rate-limit close-frame write below.
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			select {
			case <-stop:
				return
			default:
			}
			hub.Send("file-hub-user", map[string]string{"type": "status_update"})
		}
	}()

	// Flood the socket: with the default limiter (1 rps / burst 1) the second
	// message trips the policy-violation close frame while the hub storm is
	// still writing.
	for i := 0; i < 10; i++ {
		_ = client.WriteMessage(websocket.TextMessage, []byte("x"))
	}

	// Drain until the server closes the connection.
	_ = client.SetReadDeadline(time.Now().Add(3 * time.Second))
	for {
		if _, _, err := client.ReadMessage(); err != nil {
			break
		}
	}

	// Handler must exit and unregister its writer cleanly.
	require.Eventually(t, func() bool {
		return hub.Count("file-hub-user") == 0
	}, 3*time.Second, 10*time.Millisecond, "connection should be unregistered after the close frame")

	close(stop)
	wg.Wait()
	assert.Equal(t, 0, hub.Count("file-hub-user"))
}
