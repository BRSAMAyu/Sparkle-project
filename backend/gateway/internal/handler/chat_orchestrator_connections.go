package handler

import "github.com/gorilla/websocket"

func (h *ChatOrchestrator) registerConnection(userID string, conn *websocket.Conn) {
	if h.wsRegistry != nil {
		h.wsRegistry.Register(userID, conn)
	}
}

func (h *ChatOrchestrator) unregisterConnection(userID string, conn *websocket.Conn) {
	if h.wsRegistry != nil {
		h.wsRegistry.Unregister(userID, conn)
	}
}

func (h *ChatOrchestrator) getConnection(userID string) (*websocket.Conn, bool) {
	if h.wsRegistry == nil {
		return nil, false
	}
	return h.wsRegistry.Get(userID)
}

// Registry returns the underlying connection registry for shutdown draining.
func (h *ChatOrchestrator) Registry() *ConnectionRegistry {
	return h.wsRegistry
}
