package handler

import (
	"context"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/service"
)

// ConnectionRegistry centralizes WebSocket connection lifecycle management.
//
// Invariant: for every live connection, the entry exists in BOTH
// r.connections and r.signalHub simultaneously.  Unregister removes from
// both under a single write-lock so no observer can see a "registry-deleted
// but hub-still-present" intermediate state.
type ConnectionRegistry struct {
	mu          sync.RWMutex
	connections map[string]map[*websocket.Conn]*connectionEntry
	signalHub   *service.SignalHub
	chatHistory *service.ChatHistoryService
	maxActive   int
	maxPerUser  int

	// wg tracks in-flight publish goroutines so DrainAll can wait for them.
	wg sync.WaitGroup
}

type connectionEntry struct {
	conn   *websocket.Conn
	writer service.JSONWriteCloser
	// alive is false once the entry has been logically unregistered.
	// BroadcastToUser checks this flag after snapshotting to avoid writing
	// to a connection that lost its race with Unregister.
	alive bool
}

func NewConnectionRegistry(signalHub *service.SignalHub, chatHistory *service.ChatHistoryService, maxActive, maxPerUser int) *ConnectionRegistry {
	return &ConnectionRegistry{
		connections: make(map[string]map[*websocket.Conn]*connectionEntry),
		signalHub:   signalHub,
		chatHistory: chatHistory,
		maxActive:   maxActive,
		maxPerUser:  maxPerUser,
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
	if r.maxPerUser > 0 {
		if len(r.connections[userID]) >= r.maxPerUser {
			r.mu.Unlock()
			return false
		}
	}
	if r.connections[userID] == nil {
		r.connections[userID] = make(map[*websocket.Conn]*connectionEntry)
	}
	r.connections[userID][conn] = &connectionEntry{conn: conn, writer: writer, alive: true}

	// Register in SignalHub inside the same lock boundary so the two
	// stores are always consistent.
	if r.signalHub != nil && writer != nil {
		r.signalHub.Register(userID, writer)
	}
	r.mu.Unlock()

	if r.chatHistory != nil {
		r.wg.Add(1)
		go func() {
			defer r.wg.Done()
			ctx := context.Background()
			_ = r.chatHistory.PublishConnectionEvent(ctx, userID, "connected")
		}()
	}
	return true
}

// Unregister is idempotent: calling it twice for the same connection is safe.
// It removes the entry from both r.connections and r.signalHub under a single
// write-lock, guaranteeing no intermediate state where the registry has
// deleted the entry but the hub still holds it.
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
	if !entry.alive {
		// Already unregistered — idempotent no-op.
		r.mu.Unlock()
		return
	}
	entry.alive = false
	delete(userEntries, conn)
	if len(userEntries) == 0 {
		delete(r.connections, userID)
	}

	// SignalHub removal inside the same lock to prevent inconsistency.
	if r.signalHub != nil && entry.writer != nil {
		r.signalHub.Unregister(userID, entry.writer)
	}
	r.mu.Unlock()

	// chatHistory publish is fire-and-forget but tracked by WaitGroup.
	if r.chatHistory != nil {
		r.wg.Add(1)
		go func() {
			defer r.wg.Done()
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

// BroadcastToUser sends a JSON message to all alive connections for a user.
// Returns the number of connections that received the message and a list of
// connections that failed (so callers can unregister them via idempotent Unregister).
func (r *ConnectionRegistry) BroadcastToUser(userID string, v interface{}) (int, []*websocket.Conn) {
	r.mu.RLock()
	entries, ok := r.connections[userID]
	if !ok || len(entries) == 0 {
		r.mu.RUnlock()
		return 0, nil
	}
	// Snapshot writers under read lock.  Only snapshot alive entries.
	type writerEntry struct {
		writer service.JSONWriteCloser
		conn   *websocket.Conn
		alive  *bool
	}
	var writers []writerEntry
	for conn, entry := range entries {
		if entry != nil && entry.writer != nil && entry.alive {
			writers = append(writers, writerEntry{writer: entry.writer, conn: conn, alive: &entry.alive})
		}
	}
	r.mu.RUnlock()

	sent := 0
	var failed []*websocket.Conn
	for _, w := range writers {
		// Re-check liveness: the entry may have been unregistered between
		// the snapshot and this write attempt.
		r.mu.RLock()
		stillAlive := *w.alive
		r.mu.RUnlock()
		if !stillAlive {
			continue
		}
		if err := w.writer.WriteJSON(v); err != nil {
			failed = append(failed, w.conn)
		} else {
			sent++
		}
	}
	return sent, failed
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

// DrainAll sends a CloseGoingAway frame to every connection, closes it,
// cleans up SignalHub, and waits for in-flight publish goroutines.
// It covers the full lifecycle: registry → SignalHub → chatHistory goroutines.
func (r *ConnectionRegistry) DrainAll(timeout time.Duration) {
	r.mu.Lock()
	snapshot := make(map[string][]*websocket.Conn, len(r.connections))
	for userID, entries := range r.connections {
		for _, entry := range entries {
			if entry != nil && entry.conn != nil {
				entry.alive = false
				snapshot[userID] = append(snapshot[userID], entry.conn)
			}
		}
	}
	// Clear registry and SignalHub atomically.
	r.connections = make(map[string]map[*websocket.Conn]*connectionEntry)
	if r.signalHub != nil {
		r.signalHub.RemoveAll()
	}
	r.mu.Unlock()

	deadline := time.Now().Add(timeout)
	for _, conns := range snapshot {
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
	}

	// Wait for in-flight chatHistory publish goroutines to finish.
	done := make(chan struct{})
	go func() {
		r.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(timeout):
		// Goroutines timed out; they'll eventually finish on their own.
	}
}

// ProxyDrainAll drains the WebSocketProxy's independent activeByUser tracking.
// Called by the proxy during shutdown so that DrainAll covers both tracking systems.
func (p *WebSocketProxy) ProxyDrainAll() {
	p.mu.Lock()
	p.activeByUser = make(map[string]int)
	p.reconnectTrackers = make(map[string]*reconnectTracker)
	p.mu.Unlock()
}
