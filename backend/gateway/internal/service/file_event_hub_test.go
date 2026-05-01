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
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		serverConns = append(serverConns, conn)
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
