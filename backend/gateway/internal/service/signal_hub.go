package service

import (
	"sync"
)

type JSONWriteCloser interface {
	WriteJSON(payload interface{}) error
	Close() error
}

type SignalHub struct {
	mu          sync.RWMutex
	connections map[string]map[JSONWriteCloser]struct{}
}

func NewSignalHub() *SignalHub {
	return &SignalHub{
		connections: make(map[string]map[JSONWriteCloser]struct{}),
	}
}

func (h *SignalHub) Register(userID string, conn JSONWriteCloser) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.connections[userID] == nil {
		h.connections[userID] = make(map[JSONWriteCloser]struct{})
	}
	h.connections[userID][conn] = struct{}{}
}

func (h *SignalHub) Unregister(userID string, conn JSONWriteCloser) {
	h.mu.Lock()
	defer h.mu.Unlock()

	userConns := h.connections[userID]
	if userConns == nil {
		return
	}
	delete(userConns, conn)
	if len(userConns) == 0 {
		delete(h.connections, userID)
	}
}

// RemoveAll clears every entry. Used during shutdown so DrainAll can
// atomically reset the hub alongside the connection registry.
func (h *SignalHub) RemoveAll() {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.connections = make(map[string]map[JSONWriteCloser]struct{})
}

func (h *SignalHub) Send(userID string, payload interface{}) {
	// R2-GW-5: snapshot the connection set under RLock and write outside any
	// hub-level lock — the previous hub-wide sendMu made one slow connection
	// (chat writeWait floors at 60s) stall widget pushes for EVERY user
	// (head-of-line blocking) and pile up /internal/signals/push handlers.
	// This matches the FileEventHub snapshot pattern; per-connection write
	// serialization is the connection's own contract (production registers
	// wsSafeWriter, which locks internally).
	h.mu.RLock()
	userConns := h.connections[userID]
	conns := make([]JSONWriteCloser, 0, len(userConns))
	for conn := range userConns {
		conns = append(conns, conn)
	}
	h.mu.RUnlock()

	for _, conn := range conns {
		if err := conn.WriteJSON(payload); err != nil {
			h.Unregister(userID, conn)
			_ = conn.Close()
		}
	}
}
