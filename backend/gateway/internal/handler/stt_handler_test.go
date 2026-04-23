package handler

import (
	"net/http/httptest"
	"testing"

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
