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

func TestConnectionRegistryAllowsMultipleConnectionsPerUser(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil, 0)
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
