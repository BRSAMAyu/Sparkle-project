package handler

import (
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
	"github.com/stretchr/testify/assert"
)

// TestChatOrchestrator_QuotaIntegration verifies that the WebSocket handler
// relies on token-usage quota only and does not require a preinitialized request quota counter.
func TestChatOrchestrator_QuotaIntegration(t *testing.T) {
	// Force production environment to enable quota checks
	os.Setenv("ENVIRONMENT", "prod")
	defer os.Unsetenv("ENVIRONMENT")

	// 1. Setup Miniredis & QuotaService
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	defer rdb.Close()

	quotaSvc := service.NewQuotaService(rdb)
	historySvc := service.NewChatHistoryService(rdb)
	wsFactory := NewWebSocketFactory(&config.Config{
		Environment:    "prod",
		AllowedOrigins: []string{"*"},
	})
	cfg := &config.Config{
		Environment:    "prod",
		AllowedOrigins: []string{"*"},
	}

	// 2. Setup ChatOrchestrator with mostly nil dependencies
	// We only care about the Quota check which happens EARLY in the flow.
	orchestrator := NewChatOrchestrator(
		nil,        // agentClient
		nil,        // galaxyClient
		nil,        // userIdentity
		historySvc, // Mock/Nil history
		quotaSvc,
		nil, // Semantic cache (nil to avoid panic in SearchExact)
		nil, // cost
		wsFactory,
		cfg,
		nil, // userContext
		nil, // taskCommand
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

	t.Run("Request quota counter is not required for first request", func(t *testing.T) {
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

		assert.False(t, s.Exists("user:quota:user_quota_test"))
	})
}
