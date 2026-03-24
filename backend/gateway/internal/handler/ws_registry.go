package handler

import (
	"context"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/service"
)

// ConnectionRegistry centralizes WebSocket connection lifecycle management.
type ConnectionRegistry struct {
	mu          sync.RWMutex
	connections map[string]*connectionEntry
	signalHub   *service.SignalHub
	chatHistory *service.ChatHistoryService
}

type connectionEntry struct {
	conn   *websocket.Conn
	writer service.JSONWriteCloser
}

func NewConnectionRegistry(signalHub *service.SignalHub, chatHistory *service.ChatHistoryService) *ConnectionRegistry {
	return &ConnectionRegistry{
		connections: make(map[string]*connectionEntry),
		signalHub:   signalHub,
		chatHistory: chatHistory,
	}
}

func (r *ConnectionRegistry) Register(userID string, conn *websocket.Conn, writer service.JSONWriteCloser) {
	r.mu.Lock()
	if existing, ok := r.connections[userID]; ok && existing.conn != conn {
		_ = existing.conn.Close()
	}
	r.connections[userID] = &connectionEntry{conn: conn, writer: writer}
	r.mu.Unlock()

	if r.signalHub != nil && writer != nil {
		r.signalHub.Register(userID, writer)
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
	entry := r.connections[userID]
	if entry == nil || entry.conn != conn {
		r.mu.Unlock()
		return
	}
	delete(r.connections, userID)
	r.mu.Unlock()

	if r.signalHub != nil && entry.writer != nil {
		r.signalHub.Unregister(userID, entry.writer)
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
	entry, ok := r.connections[userID]
	if !ok || entry == nil {
		return nil, false
	}
	return entry.conn, true
}

func (r *ConnectionRegistry) GetWriter(userID string) (service.JSONWriteCloser, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	entry, ok := r.connections[userID]
	if !ok || entry == nil || entry.writer == nil {
		return nil, false
	}
	return entry.writer, true
}

// Count returns the number of active connections.
func (r *ConnectionRegistry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.connections)
}

// DrainAll sends a CloseGoingAway frame to every connection and closes it.
// It blocks until all connections are closed or the timeout expires.
func (r *ConnectionRegistry) DrainAll(timeout time.Duration) {
	r.mu.Lock()
	snapshot := make(map[string]*websocket.Conn, len(r.connections))
	for k, v := range r.connections {
		if v != nil && v.conn != nil {
			snapshot[k] = v.conn
		}
	}
	r.mu.Unlock()

	deadline := time.Now().Add(timeout)
	for userID, conn := range snapshot {
		remaining := time.Until(deadline)
		if remaining <= 0 {
			_ = conn.Close()
			continue
		}
		_ = conn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseGoingAway, "server shutting down"),
			deadline,
		)
		_ = conn.Close()
		r.mu.Lock()
		delete(r.connections, userID)
		r.mu.Unlock()
	}
}
