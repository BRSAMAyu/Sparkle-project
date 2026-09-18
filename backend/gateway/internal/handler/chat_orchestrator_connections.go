package handler

import (
	"github.com/gorilla/websocket"
)

type wsReadResult struct {
	messageType int
	message     []byte
	err         error
}

// readWSMessages pumps websocket reads into a channel. onReadError, when
// non-nil, is invoked from the pump goroutine the moment a read fails —
// before the error result is handed to the consumer — so callers can cancel
// any in-flight upstream work even while they are blocked consuming a gRPC
// stream instead of reading from the channel (GW-P1-2).
func readWSMessages(conn *websocket.Conn, connDone <-chan struct{}, onReadError func(error)) <-chan wsReadResult {
	readResults := make(chan wsReadResult)
	go func() {
		defer close(readResults)
		for {
			messageType, message, err := conn.ReadMessage()
			if err != nil && onReadError != nil {
				onReadError(err)
			}
			select {
			case readResults <- wsReadResult{
				messageType: messageType,
				message:     message,
				err:         err,
			}:
			case <-connDone:
				return
			}
			if err != nil {
				return
			}
		}
	}()
	return readResults
}

func (h *ChatOrchestrator) registerConnection(userID string, conn *websocket.Conn, writer *wsSafeWriter) bool {
	if h.IsDraining() {
		return false
	}
	if h.wsRegistry != nil {
		return h.wsRegistry.Register(userID, conn, writer)
	}
	return true
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

func (h *ChatOrchestrator) StartDraining() {
	h.draining.Store(true)
}

func (h *ChatOrchestrator) IsDraining() bool {
	return h.draining.Load()
}

func writeConnectionLimitClose(writer *wsSafeWriter, _ *websocket.Conn) {
	_ = writer.WriteControl(
		websocket.CloseMessage,
		websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Too many connections"),
	)
	_ = writer.Close()
}

func writeServerDrainingClose(writer *wsSafeWriter, _ *websocket.Conn) {
	_ = writer.WriteControl(
		websocket.CloseMessage,
		websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "server shutting down"),
	)
	_ = writer.Close()
}
