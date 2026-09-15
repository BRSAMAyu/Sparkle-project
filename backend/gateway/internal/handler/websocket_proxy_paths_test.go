package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
)

func TestWebSocketProxyURLValidationAndSanitization(t *testing.T) {
	proxy := NewWebSocketProxy("https://backend.local/base", zap.NewNop(), &config.Config{}, nil)

	tests := []struct {
		name string
		raw  string
		want string
	}{
		{name: "http becomes ws", raw: "http://backend.local/ws", want: "ws://backend.local/ws"},
		{name: "https becomes wss", raw: "https://backend.local/ws", want: "wss://backend.local/ws"},
		{name: "ws remains ws", raw: "ws://backend.local/ws", want: "ws://backend.local/ws"},
		{name: "missing scheme defaults ws", raw: "backend.local/ws", want: "ws://backend.local/ws"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := proxy.toWebSocketURL(tt.raw)
			require.NoError(t, err)
			require.Equal(t, tt.want, got)
		})
	}

	_, err := proxy.toWebSocketURL("http://%zz")
	require.Error(t, err)

	require.True(t, isValidUUID("11111111-2222-3333-4444-555555555555"))
	require.False(t, isValidUUID("../not-a-uuid"))

	raw := []byte(`{"message":"<script>alert(1)</script>hello","items":["<b>ok</b>",{"nested":"<img src=x onerror=alert(1)>"}]}`)
	clean := string(sanitizeCommunityWSTextPayload(raw))
	require.NotContains(t, clean, "<script>")
	require.NotContains(t, clean, "onerror")
	require.Contains(t, clean, "hello")

	plain := string(sanitizeCommunityWSTextPayload([]byte(`<script>bad()</script>safe`)))
	require.NotContains(t, plain, "<script>")
	require.Contains(t, plain, "safe")
}

func TestWebSocketProxyReconnectTrackerLifecycle(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{}, nil)
	userID := "user-reconnect"

	require.True(t, proxy.checkReconnectAllowed(userID))
	for i := 0; i < reconnectMaxAttemptsDefault; i++ {
		proxy.recordReconnectAttempt(userID)
	}

	require.False(t, proxy.checkReconnectAllowed(userID))
	require.Greater(t, proxy.reconnectBlockRemaining(userID), 0)

	proxy.mu.Lock()
	proxy.reconnectTrackers[userID].lastAttempt = time.Now().Add(-2 * time.Duration(reconnectWindowSecDefault) * time.Second)
	proxy.reconnectTrackers[userID].blockedUntil = time.Now().Add(-time.Second)
	proxy.mu.Unlock()

	proxy.cleanupExpiredReconnectTrackers()
	require.Empty(t, proxy.reconnectTrackers)
	require.Zero(t, proxy.reconnectBlockRemaining(userID))
	require.NoError(t, proxy.Close())
}

func TestWebSocketProxyHTTPGuards(t *testing.T) {
	gin.SetMode(gin.TestMode)
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{}, nil)

	router := gin.New()
	router.GET("/groups/:group_id/ws", func(c *gin.Context) {
		if c.Query("user") != "" {
			c.Set("user_id", c.Query("user"))
		}
		if c.Query("token") != "" {
			c.Set("auth_token", c.Query("token"))
		}
		proxy.HandleCommunityWS(c)
	})
	router.GET("/personal", func(c *gin.Context) {
		if c.Query("user") != "" {
			c.Set("user_id", c.Query("user"))
		}
		if c.Query("token") != "" {
			c.Set("auth_token", c.Query("token"))
		}
		proxy.HandlePersonalWS(c)
	})

	tests := []struct {
		name string
		path string
		want int
	}{
		{name: "community rejects invalid uuid before auth", path: "/groups/not-a-uuid/ws", want: http.StatusBadRequest},
		{name: "community requires auth", path: "/groups/11111111-2222-3333-4444-555555555555/ws", want: http.StatusUnauthorized},
		{name: "community requires token", path: "/groups/11111111-2222-3333-4444-555555555555/ws?user=user-1", want: http.StatusUnauthorized},
		{name: "personal requires auth", path: "/personal", want: http.StatusUnauthorized},
		{name: "personal requires token", path: "/personal?user=user-1", want: http.StatusUnauthorized},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodGet, tt.path, nil)
			router.ServeHTTP(w, req)
			require.Equal(t, tt.want, w.Code)
		})
	}

	userID := "blocked-user"
	proxy.reconnectTrackers[userID] = &reconnectTracker{
		attemptCount: reconnectMaxAttemptsDefault,
		lastAttempt:  time.Now(),
		blockedUntil: time.Now().Add(time.Minute),
	}
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/personal?user="+userID+"&token=token&session_id="+strings.Repeat("a", 4), nil)
	router.ServeHTTP(w, req)
	require.Equal(t, http.StatusTooManyRequests, w.Code)

	proxy.StartDraining()
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/personal?user=user-1&token=token", nil)
	router.ServeHTTP(w, req)
	require.Equal(t, http.StatusServiceUnavailable, w.Code)
}
