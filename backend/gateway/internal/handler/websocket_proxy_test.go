package handler

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gorilla/websocket"
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
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{}, nil)

	require.Equal(t, "http://backend.local/api/v1/community/groups/group-1/ws", proxy.communityBackendURL("group-1"))
	require.Equal(t, "http://backend.local/api/v1/community/ws/connect", proxy.personalBackendURL())
	require.NotContains(t, proxy.communityBackendURL("group-1"), "token=")
	require.NotContains(t, proxy.personalBackendURL(), "token=")
}

func TestWebSocketProxyConnectionLimitPerUser(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{WSMaxConnections: 1}, nil)

	require.True(t, proxy.registerConnection("user-1"))
	require.False(t, proxy.registerConnection("user-1"))
	require.True(t, proxy.registerConnection("user-2"))

	proxy.unregisterConnection("user-1")
	require.True(t, proxy.registerConnection("user-1"))
}

func TestWebSocketProxyRejectsNewConnectionsWhileDraining(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{WSMaxConnections: 1}, nil)

	proxy.StartDraining()

	require.False(t, proxy.registerConnection("user-1"))
	require.True(t, proxy.IsDraining())
}

func TestWebSocketProxyDrainAllResetsTracking(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{WSMaxConnections: 2}, nil)
	clientConn := &websocket.Conn{}
	backendConn := &websocket.Conn{}

	proxy.activeByUser["user-1"] = 1
	proxy.reconnectTrackers["user-1"] = &reconnectTracker{attemptCount: 1}
	proxy.liveConnections[clientConn] = &proxyConnectionPair{
		clientConn:  nil,
		backendConn: nil,
	}
	proxy.wg.Add(1)
	go func() {
		defer proxy.wg.Done()
		time.Sleep(10 * time.Millisecond)
	}()

	proxy.ProxyDrainAll(100 * time.Millisecond)

	require.Empty(t, proxy.activeByUser)
	require.Empty(t, proxy.reconnectTrackers)
	require.Empty(t, proxy.liveConnections)
	require.True(t, proxy.IsDraining())
	require.NotNil(t, backendConn)
}

func TestWebSocketProxyRejectsPerConnectionRateLimit(t *testing.T) {
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

	proxy := NewWebSocketProxy(backend.URL, zap.NewNop(), &config.Config{
		WSMessageRateRPS:   0.001,
		WSMessageRateBurst: 1,
		WSWriteWaitSeconds: 1,
	}, nil)
	gateway := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		proxy.proxyWebSocket(w, r, backend.URL, "token-123", "user-1", "personal", "")
	}))
	defer gateway.Close()

	conn, _, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(gateway.URL), nil)
	require.NoError(t, err)
	defer conn.Close()

	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"ping"}`)))
	require.NoError(t, conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"ping"}`)))
	_ = conn.SetReadDeadline(time.Now().Add(time.Second))
	_, _, err = conn.ReadMessage()
	require.Error(t, err)
	require.True(t, websocket.IsCloseError(err, websocket.ClosePolicyViolation), "expected close policy violation, got %v", err)
}
