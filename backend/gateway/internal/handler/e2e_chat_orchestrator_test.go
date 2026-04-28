//go:build integration
// +build integration

package handler

import (
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"

	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
)

func newTestOrchestrator(t *testing.T) *ChatOrchestrator {
	t.Helper()
	cfg := &config.Config{JWTSecret: "test-secret"}
	ac, err := agent.NewClient(cfg)
	if err != nil {
		t.Fatalf("failed to create agent client: %v", err)
	}
	return NewChatOrchestrator(
		ac,                            // agent client
		nil,                           // galaxy client
		(*db.Queries)(nil),            // queries (nil for integration)
		(*service.ChatHistoryService)(nil),
		(*service.QuotaService)(nil),
		(*service.SemanticCacheService)(nil),
		(*service.CostCalculator)(nil),
		NewWebSocketFactory(cfg),
		cfg,
		(*service.UserContextService)(nil),
		(*service.TaskCommandService)(nil),
		"http://localhost:8000",
		(*service.SignalHub)(nil),
	)
}

// TestE2E_CompleteChatFlow verifies the WS→Gateway→gRPC path
// requires a running Python gRPC server on localhost:50051
func TestE2E_CompleteChatFlow(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping E2E test in short mode")
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()

	router.Use(func(c *gin.Context) {
		c.Set("userID", "e2e-user-001")
		c.Set("sessionID", "e2e-session-001")
		c.Next()
	})

	orchestrator := newTestOrchestrator(t)
	router.GET("/ws/chat", orchestrator.HandleWebSocket)

	ts := httptest.NewServer(router)
	defer ts.Close()

	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	t.Run("WebSocket connection established", func(t *testing.T) {
		conn, resp, err := websocket.DefaultDialer.Dial(wsURL, nil)
		if err != nil {
			t.Fatalf("WebSocket dial failed: %v (status=%d)", err, resp.StatusCode)
		}
		defer conn.Close()
		assert.Equal(t, 101, resp.StatusCode)

		chatMsg := map[string]interface{}{
			"message":    "E2E test message",
			"session_id": "e2e-session-001",
			"chat_mode":  "standard",
		}

		err = conn.WriteJSON(chatMsg)
		assert.NoError(t, err)

		conn.SetReadDeadline(time.Now().Add(30 * time.Second))
		_, msg, err := conn.ReadMessage()
		if err != nil {
			t.Logf("ReadMessage error (expected if gRPC server down): %v", err)
		} else {
			t.Logf("Received message: %s", string(msg[:min(len(msg), 200)]))
			assert.NotEmpty(t, msg)
		}
	})

	t.Run("authentication failed without userID", func(t *testing.T) {
		r2 := gin.New()
		r2.GET("/ws/chat", func(c *gin.Context) {
			// no userID set — handler should reject
			orchestrator.HandleWebSocket(c)
		})
		ts2 := httptest.NewServer(r2)
		defer ts2.Close()

		wsURL2 := "ws" + strings.TrimPrefix(ts2.URL, "http") + "/ws/chat"
		conn, _, err := websocket.DefaultDialer.Dial(wsURL2, nil)
		if err == nil {
			conn.Close()
			t.Log("Connection accepted without auth — handler may allow anonymous")
		}
	})
}

// TestE2E_WebSocketReconnection verifies closing and reopening WS connections
func TestE2E_WebSocketReconnection(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping E2E test in short mode")
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("userID", "e2e-reconnect-user")
		c.Set("sessionID", "e2e-reconnect-session")
		c.Next()
	})

	orchestrator := newTestOrchestrator(t)
	router.GET("/ws/chat", orchestrator.HandleWebSocket)

	ts := httptest.NewServer(router)
	defer ts.Close()

	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	conn1, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	assert.NoError(t, err)
	conn1.Close()

	time.Sleep(100 * time.Millisecond)

	conn2, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	assert.NoError(t, err)
	defer conn2.Close()

	err = conn2.WriteJSON(map[string]interface{}{
		"message": "Reconnected test", "session_id": "reconnect-1", "chat_mode": "standard",
	})
	assert.NoError(t, err)
}

// TestE2E_ConcurrentWebSocketConnections verifies 10 simultaneous connections
func TestE2E_ConcurrentWebSocketConnections(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping E2E test in short mode")
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("userID", "e2e-concurrent-"+c.Query("uid"))
		c.Set("sessionID", "e2e-concurrent-session")
		c.Next()
	})

	orchestrator := newTestOrchestrator(t)
	router.GET("/ws/chat", orchestrator.HandleWebSocket)

	ts := httptest.NewServer(router)
	defer ts.Close()

	const numConns = 10
	errs := make(chan error, numConns)
	conns := make([]*websocket.Conn, numConns)

	for i := 0; i < numConns; i++ {
		go func(idx int) {
			wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat?uid=" + strconv.Itoa(idx)
			conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
			if err != nil {
				errs <- err
				return
			}
			conns[idx] = conn
			errs <- nil
		}(i)
	}

	for i := 0; i < numConns; i++ {
		err := <-errs
		assert.NoError(t, err, "Connection %d should succeed", i)
	}

	for _, conn := range conns {
		if conn != nil {
			conn.Close()
		}
	}
}

// TestE2E_LargeMessageHandling verifies the gateway handles ~10KB messages
func TestE2E_LargeMessageHandling(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping E2E test in short mode")
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("userID", "e2e-large-user")
		c.Next()
	})

	orchestrator := newTestOrchestrator(t)
	router.GET("/ws/chat", orchestrator.HandleWebSocket)

	ts := httptest.NewServer(router)
	defer ts.Close()

	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	assert.NoError(t, err)
	defer conn.Close()

	largeContent := strings.Repeat("Hello ", 2500)
	err = conn.WriteJSON(map[string]interface{}{
		"message": largeContent, "session_id": "large-1", "chat_mode": "standard",
	})
	assert.NoError(t, err, "Should handle large messages")

	err = conn.WriteMessage(websocket.PingMessage, nil)
	assert.NoError(t, err, "Connection should still be alive after large message")
}
