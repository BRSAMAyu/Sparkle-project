package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

func TestSTTHandlerUsesConfiguredOriginAllowlist(t *testing.T) {
	handler := NewSTTHandler(
		"ws://backend.local/api/v1/stt/stream",
		zap.NewNop(),
		&config.Config{
			Environment:    "production",
			AllowedOrigins: []string{"https://app.sparkle.local"},
		},
	)

	allowed := httptest.NewRequest("GET", "http://gateway.local/ws/stt", nil)
	allowed.Header.Set("Origin", "https://app.sparkle.local")
	require.True(t, handler.upgrader.CheckOrigin(allowed))

	denied := httptest.NewRequest("GET", "http://gateway.local/ws/stt", nil)
	denied.Header.Set("Origin", "https://evil.example")
	require.False(t, handler.upgrader.CheckOrigin(denied))
}

func TestSTTHandlerAllowsMissingOriginForSameOriginClients(t *testing.T) {
	handler := NewSTTHandler(
		"ws://backend.local/api/v1/stt/stream",
		zap.NewNop(),
		&config.Config{Environment: "production"},
	)

	req := httptest.NewRequest("GET", "http://gateway.local/ws/stt", nil)
	require.True(t, handler.upgrader.CheckOrigin(req))
}

func TestSTTHandlerDialFailureReturnsSafeError(t *testing.T) {
	gin.SetMode(gin.TestMode)
	handler := NewSTTHandler(
		"ws://127.0.0.1:1/api/v1/stt/stream",
		zap.NewNop(),
		&config.Config{WSWriteWaitSeconds: 1},
	)
	router := gin.New()
	router.GET("/ws/stt", func(c *gin.Context) {
		c.Set("user_id", "user-1")
		handler.HandleWebSocket(c)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	conn, _, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(server.URL)+"/ws/stt", nil)
	require.NoError(t, err)
	defer conn.Close()

	var payload map[string]string
	require.NoError(t, conn.ReadJSON(&payload))
	require.Equal(t, "error", payload["type"])
	require.Equal(t, "STT service unavailable", payload["content"])
	require.NotContains(t, payload["content"], "127.0.0.1")
	require.NotContains(t, payload["content"], "connect:")
}

func TestSTTHandlerRejectsPerConnectionRateLimit(t *testing.T) {
	gin.SetMode(gin.TestMode)
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{CheckOrigin: func(*http.Request) bool { return true }}
		conn, err := upgrader.Upgrade(w, r, nil)
		require.NoError(t, err)
		defer conn.Close()
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	}))
	defer backend.Close()

	handler := NewSTTHandler(
		toWebSocketTestURL(backend.URL),
		zap.NewNop(),
		&config.Config{
			WSMessageRateRPS:   0.001,
			WSMessageRateBurst: 1,
			WSWriteWaitSeconds: 1,
		},
	)
	router := gin.New()
	router.GET("/ws/stt", func(c *gin.Context) {
		c.Set("user_id", "user-1")
		handler.HandleWebSocket(c)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	conn, _, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(server.URL)+"/ws/stt", nil)
	require.NoError(t, err)
	defer conn.Close()

	require.NoError(t, conn.WriteMessage(websocket.BinaryMessage, []byte("audio-1")))
	require.NoError(t, conn.WriteMessage(websocket.BinaryMessage, []byte("audio-2")))
	_ = conn.SetReadDeadline(time.Now().Add(time.Second))
	_, _, err = conn.ReadMessage()
	require.Error(t, err)
	require.True(t, websocket.IsCloseError(err, websocket.ClosePolicyViolation), "expected close policy violation, got %v", err)
}

func toWebSocketTestURL(httpURL string) string {
	return "ws" + strings.TrimPrefix(httpURL, "http")
}
