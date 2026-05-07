package handler

import (
	"log"
	"net/http"
	"strings"

	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/config"
)

// P3: WebSocket upgrader factory with configurable origin checking
// Provides secure WebSocket connections with environment-aware origin validation

// WebSocketFactory creates configured WebSocket upgraders
type WebSocketFactory struct {
	config *config.Config
}

// NewWebSocketFactory creates a new WebSocket factory with the given config
func NewWebSocketFactory(cfg *config.Config) *WebSocketFactory {
	return &WebSocketFactory{config: cfg}
}

// CreateUpgrader creates a WebSocket upgrader with proper origin checking
func (f *WebSocketFactory) CreateUpgrader() websocket.Upgrader {
	return websocket.Upgrader{
		ReadBufferSize:    4096,
		WriteBufferSize:   4096,
		EnableCompression: true,
		CheckOrigin:       f.checkOrigin,
	}
}

// checkOrigin validates the WebSocket connection origin
func (f *WebSocketFactory) checkOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")

	// Allow connections without origin header (same-origin requests)
	if origin == "" {
		return true
	}

	allowed := f.config.IsOriginAllowed(origin)
	if !allowed {
		log.Printf("[WebSocket] Rejected connection from unauthorized origin: %s", origin)
	}
	return allowed
}

// DefaultUpgrader returns a development-mode upgrader that allows all origins
// This should only be used for local development
func DefaultUpgrader() websocket.Upgrader {
	return websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
		CheckOrigin: func(r *http.Request) bool {
			return true // DEV ONLY: Allow all origins
		},
	}
}

func isDevelopmentEnv() bool {
	if cfg := handlerConfig.Load(); cfg != nil {
		return cfg.IsDevelopment()
	}
	return false
}

func selectWebSocketSubprotocol(r *http.Request) string {
	header := r.Header.Get("Sec-WebSocket-Protocol")
	if header == "" {
		return ""
	}

	parts := strings.Split(header, ",")
	for _, part := range parts {
		candidate := strings.TrimSpace(part)
		lower := strings.ToLower(candidate)
		if strings.HasPrefix(lower, "ticket=") ||
			strings.HasPrefix(lower, "ticket:") ||
			strings.HasPrefix(lower, "ws-ticket=") ||
			strings.HasPrefix(lower, "ws-ticket:") ||
			strings.HasPrefix(lower, "bearer ") ||
			strings.HasPrefix(lower, "token=") ||
			strings.HasPrefix(lower, "token:") {
			return candidate
		}
	}

	if len(parts) > 0 {
		return strings.TrimSpace(parts[0])
	}
	return ""
}
