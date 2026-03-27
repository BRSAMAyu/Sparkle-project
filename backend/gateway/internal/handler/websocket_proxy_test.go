package handler

import (
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestBuildBackendWebSocketHeaders_ForwardsAuthAndProxyHeaders(t *testing.T) {
	req := httptest.NewRequest("GET", "http://gateway.local/api/v1/community/ws/connect", nil)
	req.Header.Set("Origin", "https://app.sparkle.local")
	req.Header.Set("X-Forwarded-For", "10.0.0.8")
	req.Header.Set("X-Real-IP", "10.0.0.8")

	headers := buildBackendWebSocketHeaders(req, "token-123")

	require.Equal(t, "Bearer token-123", headers.Get("Authorization"))
	require.Equal(t, "https://app.sparkle.local", headers.Get("Origin"))
	require.Equal(t, "10.0.0.8", headers.Get("X-Forwarded-For"))
	require.Equal(t, "10.0.0.8", headers.Get("X-Real-IP"))
}

func TestBuildBackendWebSocketHeaders_SkipsEmptyValues(t *testing.T) {
	req := httptest.NewRequest("GET", "http://gateway.local/api/v1/community/ws/connect", nil)

	headers := buildBackendWebSocketHeaders(req, "")

	require.Empty(t, headers.Get("Authorization"))
	require.Empty(t, headers.Get("Origin"))
	require.Empty(t, headers.Get("X-Forwarded-For"))
	require.Empty(t, headers.Get("X-Real-IP"))
}
