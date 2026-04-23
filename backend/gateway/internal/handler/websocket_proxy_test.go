package handler

import (
	"net/http/httptest"
	"testing"

	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
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

func TestWebSocketProxyBackendURLsDoNotCarryTokens(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{})

	require.Equal(t, "http://backend.local/api/v1/community/groups/group-1/ws", proxy.communityBackendURL("group-1"))
	require.Equal(t, "http://backend.local/api/v1/community/ws/connect", proxy.personalBackendURL())
	require.NotContains(t, proxy.communityBackendURL("group-1"), "token=")
	require.NotContains(t, proxy.personalBackendURL(), "token=")
}

func TestWebSocketProxyConnectionLimitPerUser(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{WSMaxConnections: 1})

	require.True(t, proxy.registerConnection("user-1"))
	require.False(t, proxy.registerConnection("user-1"))
	require.True(t, proxy.registerConnection("user-2"))

	proxy.unregisterConnection("user-1")
	require.True(t, proxy.registerConnection("user-1"))
}
