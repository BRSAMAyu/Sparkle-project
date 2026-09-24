// Core: infra
// Phase: sense
// Stage: v1 网关基座
//
// 文件事件订阅与推送.

package handler

import (
	"log"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"golang.org/x/time/rate"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
)

type FileEventHandler struct {
	wsFactory *WebSocketFactory
	hub       *service.FileEventHub
	cfg       *config.Config
	// draining stops new upgrades during graceful shutdown; live conns are
	// tracked in drainConns so shutdown can close them with a proper close
	// frame (wt275: /ws/files used to be killed abrupt — http.Server.Shutdown
	// ignores hijacked sockets).
	draining   atomic.Bool
	drainConns *wsConnDrainGroup
}

func NewFileEventHandler(wsFactory *WebSocketFactory, hub *service.FileEventHub, cfg *config.Config) *FileEventHandler {
	return &FileEventHandler{
		wsFactory:  wsFactory,
		hub:        hub,
		cfg:        cfg,
		drainConns: newWSConnDrainGroup(),
	}
}

// StartDraining stops admitting new /ws/files upgrades.
func (h *FileEventHandler) StartDraining() {
	h.draining.Store(true)
	h.drainConns.StartDraining()
}

// IsDraining reports whether the endpoint stopped admitting upgrades.
func (h *FileEventHandler) IsDraining() bool {
	return h.draining.Load()
}

// DrainConnections closes every live /ws/files WebSocket with a CloseGoingAway
// frame and waits (bounded by timeout) for the handler goroutines to unwind.
// It satisfies the graceful-shutdown drainer contract wired in cmd/server.
func (h *FileEventHandler) DrainConnections(timeout time.Duration) {
	h.drainConns.DrainAll(timeout)
}

func (h *FileEventHandler) HandleWebSocket(c *gin.Context) {
	if h.IsDraining() {
		c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": "Server shutting down"})
		return
	}
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

	// Track the upgraded conn for graceful-shutdown drain (see drainConns).
	untrack, ok := h.drainConns.startTracking(conn)
	if !ok {
		_ = conn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "server shutting down"),
			time.Now().Add(time.Second),
		)
		return
	}
	defer untrack()

	// GW-P0-1: serialize all writes (hub.Send from the Redis subscriber
	// goroutine + local close frames) through one wsSafeWriter — gorilla
	// panics on concurrent writers to the same conn, and the subscriber
	// goroutine has no recover.
	writeWait := 10 * time.Second
	if h.cfg != nil && h.cfg.WSWriteWaitSeconds > 0 {
		writeWait = time.Duration(h.cfg.WSWriteWaitSeconds) * time.Second
	}
	writer := newWSSafeWriter(conn, writeWait)

	userID := c.GetString("user_id")
	if userID == "" {
		metrics.WSConnectionError.WithLabelValues("/ws/files", "unknown", "missing_user").Inc()
		_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseUnsupportedData, "Authentication required"))
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
		_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Too many connections"))
		return
	}
	h.hub.Register(userID, writer)
	defer h.hub.Unregister(userID, writer)

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
			_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message rate limit exceeded"))
			break
		}
	}
}
