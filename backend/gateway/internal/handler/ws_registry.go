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
	connections map[string]map[*websocket.Conn]*connectionEntry
	signalHub   *service.SignalHub
	chatHistory *service.ChatHistoryService
	maxActive   int
}

type connectionEntry struct {
	conn   *websocket.Conn
	writer service.JSONWriteCloser
}

func NewConnectionRegistry(signalHub *service.SignalHub, chatHistory *service.ChatHistoryService, maxActive int) *ConnectionRegistry {
	return &ConnectionRegistry{
		connections: make(map[string]map[*websocket.Conn]*connectionEntry),
		signalHub:   signalHub,
		chatHistory: chatHistory,
		maxActive:   maxActive,
	}
}

func (r *ConnectionRegistry) Register(userID string, conn *websocket.Conn, writer service.JSONWriteCloser) bool {
	r.mu.Lock()
	if r.maxActive > 0 {
		totalActive := 0
		for _, entries := range r.connections {
			totalActive += len(entries)
		}
		if totalActive >= r.maxActive {
			r.mu.Unlock()
			return false
		}
	}
	if r.connections[userID] == nil {
		r.connections[userID] = make(map[*websocket.Conn]*connectionEntry)
	}
	r.connections[userID][conn] = &connectionEntry{conn: conn, writer: writer}
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
	return true
}

func (r *ConnectionRegistry) Unregister(userID string, conn *websocket.Conn) {
	r.mu.Lock()
	userEntries := r.connections[userID]
	if userEntries == nil {
		r.mu.Unlock()
		return
	}
	entry := userEntries[conn]
	if entry == nil {
		r.mu.Unlock()
		return
	}
	delete(userEntries, conn)
	if len(userEntries) == 0 {
		delete(r.connections, userID)
	}
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
	entries, ok := r.connections[userID]
	if !ok || len(entries) == 0 {
		return nil, false
	}
	for conn := range entries {
		return conn, true
	}
	return nil, false
}

func (r *ConnectionRegistry) GetWriter(userID string) (service.JSONWriteCloser, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	entries, ok := r.connections[userID]
	if !ok || len(entries) == 0 {
		return nil, false
	}
	for _, entry := range entries {
		if entry != nil && entry.writer != nil {
			return entry.writer, true
		}
	}
	return nil, false
}

// Count returns the number of active connections.
func (r *ConnectionRegistry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	total := 0
	for _, entries := range r.connections {
		total += len(entries)
	}
	return total
}

// DrainAll sends a CloseGoingAway frame to every connection and closes it.
// It blocks until all connections are closed or the timeout expires.
func (r *ConnectionRegistry) DrainAll(timeout time.Duration) {
	r.mu.Lock()
	snapshot := make(map[string][]*websocket.Conn, len(r.connections))
	for userID, entries := range r.connections {
		for _, entry := range entries {
			if entry != nil && entry.conn != nil {
				snapshot[userID] = append(snapshot[userID], entry.conn)
			}
		}
	}
	r.mu.Unlock()

	deadline := time.Now().Add(timeout)
	for userID, conns := range snapshot {
		for _, conn := range conns {
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
		}
		r.mu.Lock()
		delete(r.connections, userID)
		r.mu.Unlock()
	}
}
