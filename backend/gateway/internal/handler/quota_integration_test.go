package handler

import (
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/service"
	"github.com/stretchr/testify/assert"
)

// TestChatOrchestrator_QuotaIntegration verifies that the WebSocket handler
// correctly interacts with the QuotaService (ReserveRequest).
func TestChatOrchestrator_QuotaIntegration(t *testing.T) {
	// 1. Setup Miniredis & QuotaService
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	defer rdb.Close()

	quotaSvc := service.NewQuotaService(rdb)
	historySvc := service.NewChatHistoryService(rdb)

	// 2. Setup ChatOrchestrator with mostly nil dependencies
	// We only care about the Quota check which happens EARLY in the flow.
	orchestrator := NewChatOrchestrator(
		nil,        // agentClient
		nil,        // galaxyClient
		nil,        // queries
		historySvc, // Mock/Nil history
		quotaSvc,
		&service.SemanticCacheService{}, // Mock/Nil semantic
		nil,                             // cost
		nil,                             // wsFactory
		nil,                             // userContext
		nil,                             // taskCommand
		"http://mock-backend",
		nil, // signalHub
	)

	// 3. Setup Gin & WebSocket
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/ws/chat", func(c *gin.Context) {
		// Mock Auth
		c.Set("user_id", "user_quota_test")
		c.Set("auth_token", "mock_token")
		orchestrator.HandleWebSocket(c)
	})

	ts := httptest.NewServer(r)
	defer ts.Close()
	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	t.Run("Quota Exhausted -> Immediate Error", func(t *testing.T) {
		// Ensure user has 0 quota
		s.Set("user:quota:user_quota_test", "0")

		// Connect
		conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
		assert.NoError(t, err)
		defer conn.Close()

		// Send Message
		err = conn.WriteJSON(map[string]interface{}{
			"message":    "Hello",
			"session_id": "sess_1",
		})
		assert.NoError(t, err)

		// Expect Error Message
		var resp map[string]interface{}
		err = conn.ReadJSON(&resp)
		assert.NoError(t, err)

		// Verify it's a quota error
		assert.Equal(t, "error", resp["type"])
		assert.Equal(t, "Quota exhausted", resp["message"])
	})

	t.Run("Quota Sufficient -> Proceeds (and fails at next step)", func(t *testing.T) {
		// Ensure user has quota
		s.Set("user:quota:user_quota_test", "10")

		// Connect
		conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
		assert.NoError(t, err)
		defer conn.Close()

		// Send Message
		err = conn.WriteJSON(map[string]interface{}{
			"message":    "Hello",
			"session_id": "sess_2",
		})
		assert.NoError(t, err)

		// Expect Error Message (Service Unavailable) because agentClient is nil
		// This proves it PASSED the quota check and tried to call StreamChat
		var resp map[string]interface{}
		err = conn.ReadJSON(&resp)
		assert.NoError(t, err)

		assert.Equal(t, "error", resp["type"])
		assert.Equal(t, "AI Service Unavailable", resp["message"])

		// Verify quota WAS decremented
		val, _ := s.Get("user:quota:user_quota_test")
		assert.Equal(t, "9", val)
	})
}
