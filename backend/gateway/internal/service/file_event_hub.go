package service

import (
	"sync"
)

// FileEventHub mirrors SignalHub's writer abstraction (JSONWriteCloser from
// signal_hub.go): callers register a serialized writer such as the handler
// package's wsSafeWriter instead of the raw *websocket.Conn, so hub writes
// and handler close-frame writes never write the conn concurrently.
// *websocket.Conn satisfies JSONWriteCloser directly.

type FileEventHub struct {
	mu          sync.RWMutex
	connections map[string]map[JSONWriteCloser]struct{}
}

func NewFileEventHub() *FileEventHub {
	return &FileEventHub{
		connections: make(map[string]map[JSONWriteCloser]struct{}),
	}
}

func (h *FileEventHub) Register(userID string, conn JSONWriteCloser) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.connections[userID] == nil {
		h.connections[userID] = make(map[JSONWriteCloser]struct{})
	}
	h.connections[userID][conn] = struct{}{}
}

func (h *FileEventHub) Count(userID string) int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	return len(h.connections[userID])
}

func (h *FileEventHub) Unregister(userID string, conn JSONWriteCloser) {
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

func (h *FileEventHub) Send(userID string, payload interface{}) {
	// GW-P0-1: snapshot the connection set under the read lock. Iterating the
	// shared map after RUnlock raced Register/Unregister deletes and tripped
	// the runtime's unrecoverable "concurrent map iteration and map write"
	// fatal, crashing the whole gateway on every /ws/files disconnect while
	// the Redis subscriber was mid-Send.
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
