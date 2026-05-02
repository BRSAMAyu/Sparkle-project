package handler

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
	"golang.org/x/time/rate"
)

type FileEventHandler struct {
	wsFactory *WebSocketFactory
	hub       *service.FileEventHub
	cfg       *config.Config
}

func NewFileEventHandler(wsFactory *WebSocketFactory, hub *service.FileEventHub, cfg *config.Config) *FileEventHandler {
	return &FileEventHandler{
		wsFactory: wsFactory,
		hub:       hub,
		cfg:       cfg,
	}
}

func (h *FileEventHandler) HandleWebSocket(c *gin.Context) {
	var upgrader websocket.Upgrader
	if h.wsFactory != nil {
		upgrader = h.wsFactory.CreateUpgrader()
	} else {
		if !isDevelopmentEnv() {
			log.Printf("[ERROR] WebSocketFactory missing in non-development environment")
			c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "WebSocket configuration error"})
			return
		}
		upgrader = DefaultUpgrader()
	}
	if selected := selectWebSocketSubprotocol(c.Request); selected != "" {
		upgrader.Subprotocols = []string{selected}
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("Failed to upgrade file WS: %v", err)
		return
	}
	defer conn.Close()

	userID := c.GetString("user_id")
	if userID == "" {
		metrics.WSConnectionError.WithLabelValues("/ws/files", "unknown", "missing_user").Inc()
		_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseUnsupportedData, "Authentication required"))
		return
	}
	authMethod := c.GetString("ws_auth_method")
	if authMethod == "" {
		authMethod = "unknown"
	}
	metrics.WSConnectionSuccess.WithLabelValues("/ws/files", authMethod).Inc()

	maxConns := 0
	if h.cfg != nil {
		maxConns = h.cfg.WSMaxConnections
	}
	if maxConns > 0 && h.hub.Count(userID) >= maxConns {
		metrics.WSConnectionError.WithLabelValues("/ws/files", authMethod, "connection_limit").Inc()
		_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Too many connections"))
		return
	}
	h.hub.Register(userID, conn)
	defer h.hub.Unregister(userID, conn)

	readLimit := int64(0)
	msgRate := 0.0
	msgBurst := 0
	if h.cfg != nil {
		readLimit = h.cfg.WSMaxMessageBytes
		msgRate = h.cfg.WSMessageRateRPS
		msgBurst = h.cfg.WSMessageRateBurst
	}
	if readLimit <= 0 {
		readLimit = wsDefaultMaxMessageBytes
	}
	conn.SetReadLimit(readLimit)
	if msgRate <= 0 {
		msgRate = 1
	}
	if msgBurst <= 0 {
		msgBurst = 1
	}
	msgLimiter := rate.NewLimiter(rate.Limit(msgRate), msgBurst)

	for {
		if _, _, err := conn.ReadMessage(); err != nil {
			break
		}
		if !msgLimiter.Allow() {
			_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message rate limit exceeded"))
			break
		}
	}
}
