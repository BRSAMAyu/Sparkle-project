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

func (h *SignalHub) Send(userID string, payload interface{}) {
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
