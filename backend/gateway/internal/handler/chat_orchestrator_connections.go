package handler

import "github.com/gorilla/websocket"

func (h *ChatOrchestrator) registerConnection(userID string, conn *websocket.Conn, writer *wsSafeWriter) {
	if h.wsRegistry != nil {
		h.wsRegistry.Register(userID, conn, writer)
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

func (h *ChatOrchestrator) getConnectionWriter(userID string) (*wsSafeWriter, bool) {
	if h.wsRegistry == nil {
		return nil, false
	}
	writer, ok := h.wsRegistry.GetWriter(userID)
	if !ok {
		return nil, false
	}
	wsWriter, ok := writer.(*wsSafeWriter)
	return wsWriter, ok
}

// Registry returns the underlying connection registry for shutdown draining.
func (h *ChatOrchestrator) Registry() *ConnectionRegistry {
	return h.wsRegistry
}
