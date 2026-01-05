package service

import (
	"sync"

	"github.com/gorilla/websocket"
)

type FileEventHub struct {
	mu          sync.RWMutex
	connections map[string]map[*websocket.Conn]struct{}
}

func NewFileEventHub() *FileEventHub {
	return &FileEventHub{
		connections: make(map[string]map[*websocket.Conn]struct{}),
	}
}

func (h *FileEventHub) Register(userID string, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.connections[userID] == nil {
		h.connections[userID] = make(map[*websocket.Conn]struct{})
	}
	h.connections[userID][conn] = struct{}{}
}

func (h *FileEventHub) Unregister(userID string, conn *websocket.Conn) {
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
	h.mu.RLock()
	userConns := h.connections[userID]
	h.mu.RUnlock()

	for conn := range userConns {
		if err := conn.WriteJSON(payload); err != nil {
			h.Unregister(userID, conn)
			_ = conn.Close()
		}
	}
}
