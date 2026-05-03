package handler

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Regression test for ISSUE-20260504-1430-C6:
// Server must emit message_nack (structured NACK with error_code) instead of
// ad-hoc {"type": "error", "message": "..."} so Flutter NackEvent parser
// (websocket_chat_service_v2.dart:853-872) can provide canRetry semantics.

func TestMessageNackEmittedForInvalidJSON(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		Environment:            "development",
		WSIdleTimeoutSeconds:   5,
		WSPingIntervalSeconds:  10,
		WSPongWaitSeconds:      10,
		WSGlobalMaxConnections: 10,
		WSMaxConnections:       10,
		StreamMaxConcurrent:    2,
		WSMaxMessageBytes:      65536,
		WSMessageRateRPS:       10,
		WSMessageRateBurst:     10,
	}
	orchestrator := newLifecycleTestOrchestrator(cfg)

	router := gin.New()
	router.GET("/ws/chat", func(c *gin.Context) {
		c.Set("user_id", "nack-test-user")
		orchestrator.HandleWebSocket(c)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(server.URL, "http")+"/ws/chat", nil)
	require.NoError(t, err)
	defer conn.Close()

	// Send invalid JSON (unquoted garbage)
	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`{this is not valid json`)))

	conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	_, msg, err := conn.ReadMessage()
	require.NoError(t, err)

	var parsed map[string]interface{}
	require.NoError(t, json.Unmarshal(msg, &parsed))

	assert.Equal(t, "message_nack", parsed["type"], "invalid JSON should emit message_nack, not error")
	assert.Equal(t, "invalid_json", parsed["error_code"])
	assert.Equal(t, true, parsed["permanent"])
	assert.NotEmpty(t, parsed["error_message"])
	assert.NotEmpty(t, parsed["message_id"], "message_id must be non-empty for Flutter NackEvent parser")
}

func TestMessageNackEmittedForEmptyMessage(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		Environment:            "development",
		WSIdleTimeoutSeconds:   5,
		WSPingIntervalSeconds:  10,
		WSPongWaitSeconds:      10,
		WSGlobalMaxConnections: 10,
		WSMaxConnections:       10,
		StreamMaxConcurrent:    2,
		WSMaxMessageBytes:      65536,
		WSMessageRateRPS:       10,
		WSMessageRateBurst:     10,
	}
	orchestrator := newLifecycleTestOrchestrator(cfg)

	router := gin.New()
	router.GET("/ws/chat", func(c *gin.Context) {
		c.Set("user_id", "nack-test-user")
		orchestrator.HandleWebSocket(c)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(server.URL, "http")+"/ws/chat", nil)
	require.NoError(t, err)
	defer conn.Close()

	// Send valid JSON with empty message
	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"message","message":"","request_id":"req-123"}`)))

	conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	_, msg, err := conn.ReadMessage()
	require.NoError(t, err)

	var parsed map[string]interface{}
	require.NoError(t, json.Unmarshal(msg, &parsed))

	assert.Equal(t, "message_nack", parsed["type"], "empty message should emit message_nack")
	assert.Equal(t, "empty_message", parsed["error_code"])
	assert.Equal(t, true, parsed["permanent"])
	assert.Equal(t, "req-123", parsed["message_id"], "message_id must match request_id for Flutter NackEvent")
}

func TestMessageNackForUnknownMessageTypeIsPermanent(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		Environment:            "development",
		WSIdleTimeoutSeconds:   5,
		WSPingIntervalSeconds:  10,
		WSPongWaitSeconds:      10,
		WSGlobalMaxConnections: 10,
		WSMaxConnections:       10,
		StreamMaxConcurrent:    2,
		WSMaxMessageBytes:      65536,
		WSMessageRateRPS:       10,
		WSMessageRateBurst:     10,
	}
	orchestrator := newLifecycleTestOrchestrator(cfg)

	router := gin.New()
	router.GET("/ws/chat", func(c *gin.Context) {
		c.Set("user_id", "quota-test-user")
		orchestrator.HandleWebSocket(c)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(server.URL, "http")+"/ws/chat", nil)
	require.NoError(t, err)
	defer conn.Close()

	// Send unknown type to trigger fallback path
	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"nonexistent","message":"hi","request_id":"req-999"}`)))

	conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	_, msg, err := conn.ReadMessage()
	require.NoError(t, err)

	var parsed map[string]interface{}
	require.NoError(t, json.Unmarshal(msg, &parsed))

	assert.Equal(t, "message_nack", parsed["type"], "unknown message type should emit message_nack")
	assert.Equal(t, "unknown_message_type", parsed["error_code"])
	assert.Equal(t, true, parsed["permanent"])
	assert.NotEmpty(t, parsed["message_id"], "message_id must be non-empty for Flutter NackEvent parser")
}

// Verify no legacy {"type":"error"} remains in websocket output.
func TestNoLegacyErrorTypeInNackPaths(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cfg := &config.Config{
		Environment:            "development",
		WSIdleTimeoutSeconds:   5,
		WSPingIntervalSeconds:  10,
		WSPongWaitSeconds:      10,
		WSGlobalMaxConnections: 10,
		WSMaxConnections:       10,
		StreamMaxConcurrent:    2,
		WSMaxMessageBytes:      65536,
		WSMessageRateRPS:       10,
		WSMessageRateBurst:     10,
	}
	orchestrator := newLifecycleTestOrchestrator(cfg)

	router := gin.New()
	router.GET("/ws/chat", func(c *gin.Context) {
		c.Set("user_id", "no-legacy-test")
		orchestrator.HandleWebSocket(c)
	})
	server := httptest.NewServer(router)
	defer server.Close()

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(server.URL, "http")+"/ws/chat", nil)
	require.NoError(t, err)
	defer conn.Close()

	// Send invalid JSON to trigger error path
	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`%%%%%`)))

	conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	_, msg, err := conn.ReadMessage()
	require.NoError(t, err)

	var parsed map[string]interface{}
	require.NoError(t, json.Unmarshal(msg, &parsed))

	assert.NotEqual(t, "error", parsed["type"], "legacy error type must not appear")
	assert.Equal(t, "message_nack", parsed["type"])
	assert.NotEmpty(t, parsed["message_id"], "message_id must be non-empty for Flutter NackEvent parser")
}

// Ensure newLifecycleTestOrchestrator is available (from chat_orchestrator_test.go or helpers).
// If missing, this test compiles: refer to chat_orchestrator_helpers_test.go for the factory.
var _ = context.Background
var _ = agentv1.ChatRequest{}
