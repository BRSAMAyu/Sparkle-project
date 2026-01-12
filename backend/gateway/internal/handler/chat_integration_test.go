package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// MockChatOrchestrator mocks the downstream gRPC service or internal logic
type MockChatOrchestrator struct {
	mock.Mock
}

func (m *MockChatOrchestrator) HandleStream(conn *websocket.Conn, userID string) {
	m.Called(conn, userID)
	// Simulate simple echo or processing
	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			break
		}
		conn.WriteJSON(map[string]string{"type": "echo", "content": "ack"})
	}
}

func TestWebSocketLifecycle(t *testing.T) {
	// 1. Setup Gin Router
	gin.SetMode(gin.TestMode)
	r := gin.New()

	// Mock middleware to inject user ID
	r.Use(func(c *gin.Context) {
		token := c.Query("token")
		if token == "valid-token" {
			c.Set("userID", "user-123")
		}
		c.Next()
	})

	// Setup WebSocket endpoint
	r.GET("/ws/chat", func(c *gin.Context) {
		userID, exists := c.Get("userID")
		if !exists {
			c.AbortWithStatus(401)
			return
		}

		upgrader := websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		}

		conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		// Simple echo loop for testing
		for {
			mt, msg, err := conn.ReadMessage()
			if err != nil {
				break
			}
			// Respond
			conn.WriteMessage(mt, msg)
		}

		// In real app, we would call: orchestrator.HandleStream(conn, userID.(string))
		_ = userID
	})

	// 2. Create Test Server
	ts := httptest.NewServer(r)
	defer ts.Close()

	// Convert http URL to ws URL
	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	t.Run("Connection Authentication Failed", func(t *testing.T) {
		_, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
		assert.Error(t, err) // Should fail 401
	})

	t.Run("Connection Success & Message Flow", func(t *testing.T) {
		// Connect with valid token
		conn, resp, err := websocket.DefaultDialer.Dial(wsURL+"?token=valid-token", nil)
		assert.NoError(t, err)
		assert.Equal(t, 101, resp.StatusCode)
		defer conn.Close()

		// Send Message
		err = conn.WriteJSON(map[string]string{"content": "hello"})
		assert.NoError(t, err)

		// Receive Message
		var msg map[string]string
		err = conn.ReadJSON(&msg)
		assert.NoError(t, err)
		assert.Equal(t, "hello", msg["content"])

		// Test Reconnection (Simulate by closing and dialing again)
		conn.Close()
		time.Sleep(10 * time.Millisecond)

		conn2, _, err := websocket.DefaultDialer.Dial(wsURL+"?token=valid-token", nil)
		assert.NoError(t, err)
		conn2.Close()
	})
}
