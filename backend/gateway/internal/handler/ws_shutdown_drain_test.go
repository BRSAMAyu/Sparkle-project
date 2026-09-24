// wt275-audit-golifecycle: regression tests for the graceful-shutdown drain of
// the single-conn WS endpoints (/ws/stt, /ws/files). Before this card both
// endpoints were killed abrupt at process exit — http.Server.Shutdown ignores
// hijacked sockets — so clients saw an abnormal 1006 close instead of 1001.
package handler

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/service"
)

// startTrackedWSServer upgrades every request, tracks the server-side conn in
// the drain group, and holds the socket open until the test side closes or
// drains it.
func startTrackedWSServer(t *testing.T, g *wsConnDrainGroup) *websocket.Conn {
	t.Helper()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		up := websocket.Upgrader{}
		conn, err := up.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		untrack, ok := g.startTracking(conn)
		if !ok {
			return
		}
		defer untrack()
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	}))
	t.Cleanup(server.Close)

	url := "ws" + strings.TrimPrefix(server.URL, "http")
	conn, _, err := websocket.DefaultDialer.Dial(url, nil)
	require.NoError(t, err)
	t.Cleanup(func() { _ = conn.Close() })
	return conn
}

func TestWSConnDrainGroupSendsCloseGoingAwayAndReleases(t *testing.T) {
	g := newWSConnDrainGroup()
	clientConn := startTrackedWSServer(t, g)

	closeSeen := make(chan int, 1)
	clientConn.SetCloseHandler(func(code int, text string) error {
		closeSeen <- code
		return nil
	})
	// Pump reads so the close handler fires.
	go func() {
		for {
			if _, _, err := clientConn.ReadMessage(); err != nil {
				return
			}
		}
	}()

	g.DrainAll(2 * time.Second)

	select {
	case code := <-closeSeen:
		require.Equal(t, websocket.CloseGoingAway, code)
	case <-time.After(2 * time.Second):
		t.Fatalf("client did not observe CloseGoingAway frame on drain")
	}
}

func TestWSConnDrainGroupRejectsTrackingWhileDraining(t *testing.T) {
	g := newWSConnDrainGroup()
	g.StartDraining()
	untrack, ok := g.startTracking(&websocket.Conn{})
	require.False(t, ok)
	require.Nil(t, untrack)
	// DrainAll on an empty group must return promptly.
	g.DrainAll(50 * time.Millisecond)
}

func TestSTTHandlerRejectsUpgradeWhileDraining(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewSTTHandler(
		"ws://backend.local/api/v1/stt/stream",
		zap.NewNop(),
		&config.Config{Environment: "production"},
	)
	h.StartDraining()
	require.True(t, h.IsDraining())

	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	ctx.Request = httptest.NewRequest("GET", "/ws/stt", nil)
	h.HandleWebSocket(ctx)
	require.Equal(t, http.StatusServiceUnavailable, recorder.Code)
}

func TestFileEventHandlerRejectsWhileDrainingAndDrains(t *testing.T) {
	gin.SetMode(gin.TestMode)
	h := NewFileEventHandler(nil, service.NewFileEventHub(), &config.Config{})
	require.False(t, h.IsDraining())
	h.StartDraining()
	require.True(t, h.IsDraining())

	recorder := httptest.NewRecorder()
	ctx, _ := gin.CreateTestContext(recorder)
	ctx.Request = httptest.NewRequest("GET", "/ws/files", nil)
	h.HandleWebSocket(ctx)
	require.Equal(t, http.StatusServiceUnavailable, recorder.Code)

	// Drain on the empty group returns well within the budget.
	start := time.Now()
	h.DrainConnections(200 * time.Millisecond)
	require.Less(t, time.Since(start), time.Second)
}
