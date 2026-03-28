package handler

import (
	"testing"

	"github.com/gorilla/websocket"
)

func TestConnectionRegistryRegisterGetUnregister(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 0)
	conn := &websocket.Conn{}

	registry.Register("user-1", conn, nil)
	got, ok := registry.Get("user-1")
	if !ok {
		t.Fatalf("expected connection to be registered")
	}
	if got != conn {
		t.Fatalf("expected stored connection to match")
	}

	registry.Unregister("user-1", conn)
	if _, ok := registry.Get("user-1"); ok {
		t.Fatalf("expected connection to be unregistered")
	}
}

// TestConnectionRegistryUnregisterGuardsAgainstReconnectRace verifies that
// Unregister is a no-op when the stored connection has already been replaced
// by a newer one (the reconnect race).
func TestConnectionRegistryUnregisterGuardsAgainstReconnectRace(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 0)
	connA := &websocket.Conn{}
	connB := &websocket.Conn{}

	// Simulate: connA registered, then replaced by connB directly in the map
	// (bypassing Register to avoid calling Close on a zero-value Conn).
	registry.mu.Lock()
	registry.connections["user-1"] = &connectionEntry{conn: connA}
	registry.mu.Unlock()

	registry.mu.Lock()
	registry.connections["user-1"] = &connectionEntry{conn: connB}
	registry.mu.Unlock()

	// connA's goroutine fires its deferred Unregister — must NOT evict connB.
	registry.Unregister("user-1", connA)

	got, ok := registry.Get("user-1")
	if !ok {
		t.Fatal("connB should still be registered after stale Unregister(connA)")
	}
	if got != connB {
		t.Fatal("expected connB to remain; got a different connection")
	}

	// connB's goroutine fires its deferred Unregister — must remove the entry.
	registry.Unregister("user-1", connB)
	if _, ok := registry.Get("user-1"); ok {
		t.Fatal("connB should be unregistered")
	}
}
