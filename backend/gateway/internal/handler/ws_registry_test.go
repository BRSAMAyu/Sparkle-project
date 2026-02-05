package handler

import (
	"testing"

	"github.com/gorilla/websocket"
)

func TestConnectionRegistryRegisterGetUnregister(t *testing.T) {
	registry := NewConnectionRegistry(nil, nil)
	conn := &websocket.Conn{}

	registry.Register("user-1", conn)
	got, ok := registry.Get("user-1")
	if !ok {
		t.Fatalf("expected connection to be registered")
	}
	if got != conn {
		t.Fatalf("expected stored connection to match")
	}

	registry.Unregister("user-1")
	if _, ok := registry.Get("user-1"); ok {
		t.Fatalf("expected connection to be unregistered")
	}
}
