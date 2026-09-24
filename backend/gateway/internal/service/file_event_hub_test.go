package service

import (
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ============================================================
// FileEventHub Tests (using real WebSocket connections)
// ============================================================

func TestNewFileEventHub(t *testing.T) {
	hub := NewFileEventHub()
	assert.NotNil(t, hub)
	assert.NotNil(t, hub.connections)
	assert.Equal(t, 0, len(hub.connections))
}

func TestFileEventHub_CountEmpty(t *testing.T) {
	hub := NewFileEventHub()
	assert.Equal(t, 0, hub.Count("nonexistent"))
}

func TestFileEventHub_SendToNoConnections(t *testing.T) {
	hub := NewFileEventHub()
	// Should not panic when sending to nonexistent user
	assert.NotPanics(t, func() {
		hub.Send("nonexistent", map[string]string{"type": "test"})
	})
}

func TestFileEventHub_UnregisterNonexistent(t *testing.T) {
	hub := NewFileEventHub()
	// Should not panic when unregistering nonexistent user
	assert.NotPanics(t, func() {
		hub.Unregister("nonexistent", nil)
	})
}

func TestFileEventHub_FullIntegration(t *testing.T) {
	hub := NewFileEventHub()
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

	var serverConns []*websocket.Conn
	var serverConnsMu sync.Mutex
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		serverConnsMu.Lock()
		serverConns = append(serverConns, conn)
		serverConnsMu.Unlock()
		hub.Register("test-user", conn)
	}))
	defer server.Close()

	wsURL := "ws" + server.URL[4:] + "/ws"

	// Connect two clients
	client1, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer client1.Close()

	client2, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)
	defer client2.Close()

	// Wait for registration
	time.Sleep(50 * time.Millisecond)

	assert.Equal(t, 2, hub.Count("test-user"))

	// Send a message
	hub.Send("test-user", map[string]string{"type": "status_update"})

	// Both clients should receive the message
	client1.SetReadDeadline(time.Now().Add(time.Second))
	_, msg1, err := client1.ReadMessage()
	assert.NoError(t, err)
	assert.Contains(t, string(msg1), "status_update")

	client2.SetReadDeadline(time.Now().Add(time.Second))
	_, msg2, err := client2.ReadMessage()
	assert.NoError(t, err)
	assert.Contains(t, string(msg2), "status_update")
}

func TestFileEventHub_UnregisterRemovesConnection(t *testing.T) {
	hub := NewFileEventHub()
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

	var serverConn *websocket.Conn
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		serverConn = conn
		hub.Register("user-a", conn)
	}))
	defer server.Close()

	wsURL := "ws" + server.URL[4:] + "/ws"

	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)

	time.Sleep(50 * time.Millisecond)
	assert.Equal(t, 1, hub.Count("user-a"))

	// Unregister from server side
	hub.Unregister("user-a", serverConn)
	assert.Equal(t, 0, hub.Count("user-a"))

	client.Close()
}

func TestFileEventHub_ConcurrentAccess(t *testing.T) {
	hub := NewFileEventHub()
	var wg sync.WaitGroup

	// Concurrent Count calls on empty hub
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			hub.Count("user-1")
		}()
	}
	wg.Wait()
}

func TestFileEventHub_SendRemovesBadConnections(t *testing.T) {
	hub := NewFileEventHub()
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

	var serverConn *websocket.Conn
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		serverConn = conn
		hub.Register("user-b", conn)
	}))
	defer server.Close()

	wsURL := "ws" + server.URL[4:] + "/ws"
	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	require.NoError(t, err)

	time.Sleep(50 * time.Millisecond)
	assert.Equal(t, 1, hub.Count("user-b"))

	// Close the client so the server-side write will fail
	client.Close()
	time.Sleep(100 * time.Millisecond)

	// Close the server-side conn directly to simulate a broken connection
	// This makes WriteJSON fail on the next Send
	if serverConn != nil {
		serverConn.Close()
	}

	// Send to user — server-side conn should be cleaned up because WriteJSON fails
	hub.Send("user-b", map[string]string{"type": "test"})
	time.Sleep(100 * time.Millisecond)

	assert.Equal(t, 0, hub.Count("user-b"))
}

// TestFileEventHub_SendWhileRegisterUnregister_ConcurrentStress is the
// regression test for GW-P0-1: Send used to iterate the shared connections
// map outside the read lock while Register/Unregister mutated it, which
// trips the Go runtime's unrecoverable "concurrent map iteration and map
// write" fatal as soon as a subscriber Send overlaps a client
// disconnect/reconnect. The test replays exactly that overlap; with the
// pre-fix code this test process dies with a runtime fatal, with the
// snapshot fix it completes cleanly.
func TestFileEventHub_SendWhileRegisterUnregister_ConcurrentStress(t *testing.T) {
	hub := NewFileEventHub()
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

	const numConns = 64
	registered := make(chan struct{}, numConns)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		hub.Register("stress-user", conn)
		registered <- struct{}{}
	}))
	defer server.Close()

	wsURL := "ws" + server.URL[4:] + "/ws"
	clients := make([]*websocket.Conn, 0, numConns)
	defer func() {
		for _, c := range clients {
			_ = c.Close()
		}
	}()
	for i := 0; i < numConns; i++ {
		client, wsResp, err := websocket.DefaultDialer.Dial(wsURL, nil)
		require.NoError(t, err)
		defer wsResp.Body.Close()
		clients = append(clients, client)
	}
	for i := 0; i < numConns; i++ {
		select {
		case <-registered:
		case <-time.After(2 * time.Second):
			t.Fatal("timed out waiting for hub registrations")
		}
	}
	assert.Equal(t, numConns, hub.Count("stress-user"))

	stop := make(chan struct{})
	var wg sync.WaitGroup

	// Simulates /ws/files handler goroutines: disconnect + reconnect churn
	// mutating the shared map.
	for g := 0; g < 4; g++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				select {
				case <-stop:
					return
				default:
				}
				for _, c := range clients {
					hub.Unregister("stress-user", c)
					hub.Register("stress-user", c)
				}
			}
		}()
	}

	// Simulates the Redis file_status subscriber goroutine (exactly one in
	// production): hub.Send per event. Concurrent per-conn write
	// serialization is covered separately at the handler level, where the
	// wsSafeWriter is registered.
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			select {
			case <-stop:
				return
			default:
			}
			hub.Send("stress-user", map[string]string{"type": "stress"})
		}
	}()

	time.Sleep(1500 * time.Millisecond)
	close(stop)
	wg.Wait()
}
