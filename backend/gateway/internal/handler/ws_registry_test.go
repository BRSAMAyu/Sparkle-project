package handler

import (
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/service"
)

type testRegistryWriter struct {
	writes int
}

func (w *testRegistryWriter) WriteJSON(payload interface{}) error {
	w.writes++
	return nil
}

func (w *testRegistryWriter) Close() error {
	return nil
}

func TestConnectionRegistryRegisterGetUnregister(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 0, 0)
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

func TestConnectionRegistryAllowsMultipleConnectionsPerUser(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 0, 0)
	connA := &websocket.Conn{}
	connB := &websocket.Conn{}

	registry.Register("user-1", connA, nil)
	registry.Register("user-1", connB, nil)

	if got := registry.Count(); got != 2 {
		t.Fatalf("expected 2 active connections, got %d", got)
	}

	registry.Unregister("user-1", connA)
	if got := registry.Count(); got != 1 {
		t.Fatalf("expected 1 active connection after unregistering connA, got %d", got)
	}

	got, ok := registry.Get("user-1")
	if !ok {
		t.Fatal("connB should still be registered")
	}
	if got != connB {
		t.Fatal("expected connB to remain active")
	}

	registry.Unregister("user-1", connB)
	if _, ok := registry.Get("user-1"); ok {
		t.Fatal("expected all user-1 connections to be unregistered")
	}
}

func TestConnectionRegistryPerUserLimit(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 100, 2)
	connA := &websocket.Conn{}
	connB := &websocket.Conn{}
	connC := &websocket.Conn{}

	if !registry.Register("user-1", connA, nil) {
		t.Fatal("first connection should be accepted")
	}
	if !registry.Register("user-1", connB, nil) {
		t.Fatal("second connection should be accepted")
	}
	if registry.Register("user-1", connC, nil) {
		t.Fatal("third connection should be rejected (per-user limit=2)")
	}

	// Other user is not affected by user-1's limit
	if !registry.Register("user-2", connC, nil) {
		t.Fatal("user-2 connection should be accepted")
	}

	// After unregistering one, user-1 can connect again
	registry.Unregister("user-1", connA)
	if !registry.Register("user-1", connC, nil) {
		t.Fatal("user-1 should be able to connect after unregistering one")
	}
}

func TestConnectionRegistryUnregisterIsIdempotent(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 0, 0)
	conn := &websocket.Conn{}

	registry.Register("user-1", conn, nil)
	registry.Unregister("user-1", conn)
	registry.Unregister("user-1", conn)

	if got := registry.Count(); got != 0 {
		t.Fatalf("expected count 0 after idempotent unregister, got %d", got)
	}
}

func TestConnectionRegistryDrainAllClearsSignalHub(t *testing.T) {
	hub := service.NewSignalHub()
	registry := NewConnectionRegistry(hub, nil, 0, 0)
	var conn *websocket.Conn
	writer := &testRegistryWriter{}

	if !registry.Register("user-1", conn, writer) {
		t.Fatal("register should succeed")
	}

	registry.DrainAll(10 * time.Millisecond)
	hub.Send("user-1", map[string]string{"type": "probe"})

	if got := registry.Count(); got != 0 {
		t.Fatalf("expected registry count 0 after drain, got %d", got)
	}
	if writer.writes != 0 {
		t.Fatalf("expected drained SignalHub to have 0 writes, got %d", writer.writes)
	}
}
