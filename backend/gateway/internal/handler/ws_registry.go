package handler

import (
	"context"
	"sync"

	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/service"
)

// ConnectionRegistry centralizes WebSocket connection lifecycle management.
type ConnectionRegistry struct {
	mu          sync.RWMutex
	connections map[string]*websocket.Conn
	signalHub   *service.SignalHub
	chatHistory *service.ChatHistoryService
}

func NewConnectionRegistry(signalHub *service.SignalHub, chatHistory *service.ChatHistoryService) *ConnectionRegistry {
	return &ConnectionRegistry{
		connections: make(map[string]*websocket.Conn),
		signalHub:   signalHub,
		chatHistory: chatHistory,
	}
}

func (r *ConnectionRegistry) Register(userID string, conn *websocket.Conn) {
	r.mu.Lock()
	if existing, ok := r.connections[userID]; ok && existing != conn {
		_ = existing.Close()
	}
	r.connections[userID] = conn
	r.mu.Unlock()

	if r.signalHub != nil {
		r.signalHub.Register(userID, conn)
	}
	if r.chatHistory != nil {
		go func() {
			ctx := context.Background()
			_ = r.chatHistory.PublishConnectionEvent(ctx, userID, "connected")
		}()
	}
}

func (r *ConnectionRegistry) Unregister(userID string, conn *websocket.Conn) {
	r.mu.Lock()
	// Only remove if the stored connection is the same one being unregistered.
	// Guard against the reconnect race: Register replaces and closes the old conn;
	// the old goroutine's deferred Unregister must not evict the replacement.
	if r.connections[userID] != conn {
		r.mu.Unlock()
		return
	}
	delete(r.connections, userID)
	r.mu.Unlock()

	if r.signalHub != nil && conn != nil {
		r.signalHub.Unregister(userID, conn)
	}
	if r.chatHistory != nil {
		go func() {
			ctx := context.Background()
			_ = r.chatHistory.PublishConnectionEvent(ctx, userID, "disconnected")
		}()
	}
}

func (r *ConnectionRegistry) Get(userID string) (*websocket.Conn, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	conn, ok := r.connections[userID]
	return conn, ok
}
