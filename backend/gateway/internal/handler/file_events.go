package handler

import (
	"log"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/service"
)

type FileEventHandler struct {
	wsFactory *WebSocketFactory
	hub       *service.FileEventHub
}

func NewFileEventHandler(wsFactory *WebSocketFactory, hub *service.FileEventHub) *FileEventHandler {
	return &FileEventHandler{
		wsFactory: wsFactory,
		hub:       hub,
	}
}

func (h *FileEventHandler) HandleWebSocket(c *gin.Context) {
	var upgrader websocket.Upgrader
	if h.wsFactory != nil {
		upgrader = h.wsFactory.CreateUpgrader()
	} else {
		upgrader = DefaultUpgrader()
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("Failed to upgrade file WS: %v", err)
		return
	}
	defer conn.Close()

	userID := c.GetString("user_id")
	if userID == "" {
		_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseUnsupportedData, "Authentication required"))
		return
	}

	h.hub.Register(userID, conn)
	defer h.hub.Unregister(userID, conn)

	for {
		if _, _, err := conn.ReadMessage(); err != nil {
			break
		}
	}
}
