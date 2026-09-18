package handler

import (
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
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

// TestWebSocketProxyTerminalUpstreamRejectionsPassThrough covers M-3: terminal
// upstream handshake rejections (engine auth 401/403, missing route 404) must
// reach the client with the upstream status and a non-retryable marker instead
// of a flat 502 that clients blind-retry (15 consecutive 502s during the
// macOS-round engine restore storm).
func TestWebSocketProxyTerminalUpstreamRejectionsPassThrough(t *testing.T) {
	cases := []struct {
		name           string
		upstreamStatus int
	}{
		{name: "403 auth rejection", upstreamStatus: http.StatusForbidden},
		{name: "401 auth rejection", upstreamStatus: http.StatusUnauthorized},
		{name: "404 missing route", upstreamStatus: http.StatusNotFound},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				http.Error(w, "denied", tc.upstreamStatus)
			}))
			defer backend.Close()

			proxy := NewWebSocketProxy(backend.URL, zap.NewNop(), &config.Config{}, nil)
			gateway := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				proxy.proxyWebSocket(w, r, backend.URL, "token-123", "user-1", "personal", "")
			}))
			defer gateway.Close()

			conn, resp, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(gateway.URL), nil)
			require.Error(t, err)
			require.Nil(t, conn)
			require.NotNil(t, resp)
			require.Equal(t, tc.upstreamStatus, resp.StatusCode)

			body, readErr := io.ReadAll(resp.Body)
			require.NoError(t, readErr)
			require.Contains(t, string(body), "websocket_upstream_rejected")
			require.Contains(t, string(body), `"retryable":false`)
		})
	}
}

// TestWebSocketProxyUpstreamUnreachableStays502 keeps the correct mapping for
// a genuinely transient failure: nothing listening on the upstream port.
func TestWebSocketProxyUpstreamUnreachableStays502(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	addr := listener.Addr().String()
	require.NoError(t, listener.Close()) // port now closed → connection refused

	proxy := NewWebSocketProxy("http://"+addr, zap.NewNop(), &config.Config{}, nil)
	gateway := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		proxy.proxyWebSocket(w, r, "http://"+addr, "token-123", "user-1", "personal", "")
	}))
	defer gateway.Close()

	conn, resp, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(gateway.URL), nil)
	require.Error(t, err)
	require.Nil(t, conn)
	require.NotNil(t, resp)
	require.Equal(t, http.StatusBadGateway, resp.StatusCode)
}

// TestWebSocketProxyHandshakeTimeoutMapsTo504 verifies that a silent upstream
// (accepts TCP, never completes the handshake — e.g. a frozen engine event
// loop) fails fast via the configured dial timeout and surfaces as 504.
func TestWebSocketProxyHandshakeTimeoutMapsTo504(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	defer listener.Close()
	go func() {
		for {
			c, err := listener.Accept()
			if err != nil {
				return
			}
			// Hold the connection open without speaking (frozen backend).
			go func(c net.Conn) {
				defer c.Close()
				time.Sleep(5 * time.Second)
			}(c)
		}
	}()

	proxy := NewWebSocketProxy("http://"+listener.Addr().String(), zap.NewNop(), &config.Config{
		WSBackendDialTimeoutSeconds: 1,
	}, nil)
	gateway := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		proxy.proxyWebSocket(w, r, "http://"+listener.Addr().String(), "token-123", "user-1", "personal", "")
	}))
	defer gateway.Close()

	conn, resp, err := websocket.DefaultDialer.Dial(toWebSocketTestURL(gateway.URL), nil)
	require.Error(t, err)
	require.Nil(t, conn)
	require.NotNil(t, resp)
	require.Equal(t, http.StatusGatewayTimeout, resp.StatusCode)
}

func TestWebSocketProxyBackendDialTimeoutDefault(t *testing.T) {
	proxy := NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{}, nil)
	require.Equal(t, 10*time.Second, proxy.backendDialTimeout())

	proxy = NewWebSocketProxy("http://backend.local", zap.NewNop(), &config.Config{WSBackendDialTimeoutSeconds: 3}, nil)
	require.Equal(t, 3*time.Second, proxy.backendDialTimeout())
}
