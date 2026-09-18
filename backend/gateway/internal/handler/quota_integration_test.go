package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
)

// TestChatOrchestrator_QuotaIntegration verifies that the WebSocket handler
// relies on token-usage quota only and does not require a preinitialized request quota counter.
//
// F5 root-cause fix of the old baseline red: the factory ran with
// Environment=prod and the dial sent no Origin (and "*" is explicitly ignored
// for production in IsOriginAllowed), so the upgrade was always 403 and the
// deferred conn.Close() dereferenced a nil conn. The factory now uses the
// exact httptest origin and the dial sends it explicitly; dial failures abort
// the test via require instead of panicking later.
func TestChatOrchestrator_QuotaIntegration(t *testing.T) {
	// NOTE: no os.Setenv("ENVIRONMENT", ...) here — the quota gate reads the
	// global handlerConfig (nil in tests → non-development → enforced), and
	// mutating the process env only leaked into unrelated test cases.

	// 1. Setup Miniredis & QuotaService
	s := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	defer rdb.Close()

	quotaSvc := service.NewQuotaService(rdb)
	historySvc := service.NewChatHistoryService(rdb)
	t.Cleanup(historySvc.Stop)

	// 2. Setup Gin & WebSocket server first so the exact origin is known —
	// production factories must whitelist precise origins (wildcards are
	// rejected in production by design).
	gin.SetMode(gin.TestMode)
	r := gin.New()
	ts := httptest.NewServer(r)
	defer ts.Close()
	origin := "http://" + ts.Listener.Addr().String()

	wsFactory := NewWebSocketFactory(&config.Config{
		Environment:    "prod",
		AllowedOrigins: []string{origin},
	})
	cfg := &config.Config{
		Environment:    "prod",
		AllowedOrigins: []string{origin},
	}

	// 3. Setup ChatOrchestrator with mostly nil dependencies
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

	r.GET("/ws/chat", func(c *gin.Context) {
		// Mock Auth
		c.Set("user_id", "user_quota_test")
		c.Set("auth_token", "mock_token")
		orchestrator.HandleWebSocket(c)
	})

	wsURL := "ws" + strings.TrimPrefix(ts.URL, "http") + "/ws/chat"

	t.Run("Request quota counter is not required for first request", func(t *testing.T) {
		// Connect with the exact whitelisted origin (browser-style handshake)
		conn, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{
			"Origin": []string{origin},
		})
		require.NoError(t, err, "upgrade with the whitelisted origin must succeed")
		if resp != nil {
			defer resp.Body.Close()
		}
		defer conn.Close()

		// Send Message
		err = conn.WriteJSON(map[string]interface{}{
			"message":    "Hello",
			"session_id": "sess_2",
		})
		require.NoError(t, err)

		// First expect the accepted ACK from sendLegacyAcceptedAck.
		// Then a message_nack when agentClient is nil.
		// Seeing the nack proves it passed quota admission and attempted the agent call.
		var respFrame map[string]interface{}
		err = conn.ReadJSON(&respFrame)
		require.NoError(t, err)
		require.Equal(t, "ack", respFrame["type"])

		for i := 0; i < 3 && respFrame["type"] != "message_nack"; i++ {
			err = conn.ReadJSON(&respFrame)
			assert.NoError(t, err)
		}
		require.Equal(t, "message_nack", respFrame["type"])
		require.Equal(t, "AI Service Unavailable", respFrame["error_message"])

		assert.False(t, s.Exists("user:quota:user_quota_test"))
	})
}
