package handler

import (
	"encoding/json"
	"io"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/config"
	"go.uber.org/zap"
)

// STTHandler proxies WebSocket connections from Flutter to Python STT service
type STTHandler struct {
	pythonSTTUrl string
	upgrader     websocket.Upgrader
	logger       *zap.Logger
	config       *config.Config
}

// NewSTTHandler creates a new STT handler
func NewSTTHandler(pythonSTTUrl string, logger *zap.Logger, cfg *config.Config) *STTHandler {
	return &STTHandler{
		pythonSTTUrl: pythonSTTUrl,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				origin := r.Header.Get("Origin")
				if origin == "" {
					return true
				}
				allowed := cfg.IsOriginAllowed(origin)
				if !allowed {
					logger.Warn("STT WebSocket rejected connection from unauthorized origin",
						zap.String("origin", origin))
				}
				return allowed
			},
			HandshakeTimeout: 10 * time.Second,
			ReadBufferSize:   4096,
			WriteBufferSize:  4096,
		},
		logger: logger,
		config: cfg,
	}
}

// HandleWebSocket proxies Flutter WebSocket connections to Python STT service
func (h *STTHandler) HandleWebSocket(c *gin.Context) {
	// Debug logging for real device testing
	origin := c.GetHeader("Origin")
	h.logger.Info("STT WebSocket upgrade attempt",
		zap.String("origin", origin),
		zap.String("client_ip", c.ClientIP()),
		zap.String("upgrade_header", c.GetHeader("Upgrade")),
		zap.String("connection_header", c.GetHeader("Connection")))

	// 1. Upgrade HTTP to WebSocket
	clientConn, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		h.logger.Error("Failed to upgrade WebSocket connection",
			zap.Error(err),
			zap.String("origin", origin),
			zap.String("client_ip", c.ClientIP()))
		return
	}
	writeWait := 10 * time.Second
	if h.config != nil && h.config.WSWriteWaitSeconds > 0 {
		writeWait = time.Duration(h.config.WSWriteWaitSeconds) * time.Second
	}
	clientWriter := newWSSafeWriter(clientConn, writeWait)
	defer clientWriter.Close()
	readLimit := int64(0)
	if h.config != nil {
		readLimit = h.config.WSMaxMessageBytes
	}
	if readLimit <= 0 {
		readLimit = wsDefaultMaxMessageBytes
	}
	clientConn.SetReadLimit(readLimit)
	msgLimiter := newWSMessageRateLimiter(h.config)

	// Extract user_id from context (set by auth middleware)
	userID := c.GetString("user_id")
	if userID == "" {
		h.logger.Warn("No user_id in context for STT WebSocket")
		_ = clientWriter.WriteJSON(map[string]string{
			"type":    "error",
			"content": "Unauthorized: No user context",
		})
		return
	}

	h.logger.Info("STT WebSocket connected", zap.String("user_id", userID))

	// 2. Connect to Python STT service with Bearer token from Authorization header or query param
	pythonHeaders := make(map[string][]string)
	authToken := c.GetString("auth_token")
	if authToken != "" {
		pythonHeaders["Authorization"] = []string{"Bearer " + authToken}
	}

	pythonConn, _, err := websocket.DefaultDialer.Dial(h.pythonSTTUrl, pythonHeaders)
	if err != nil {
		h.logger.Error("Failed to connect to Python STT service", zap.Error(err))
		_ = clientWriter.WriteJSON(map[string]string{
			"type":    "error",
			"content": "STT service unavailable",
		})
		return
	}
	defer pythonConn.Close()

	h.logger.Info("Connected to Python STT service",
		zap.String("user_id", userID),
		zap.String("python_url", h.pythonSTTUrl))

	// 3. Bidirectional forwarding using channels
	errChan := make(chan error, 2)
	done := make(chan struct{})
	var closeOnce sync.Once
	closeDone := func() {
		closeOnce.Do(func() {
			close(done)
		})
	}
	var pythonWriteMu sync.Mutex
	writePython := func(messageType int, data []byte) error {
		pythonWriteMu.Lock()
		defer pythonWriteMu.Unlock()
		_ = pythonConn.SetWriteDeadline(time.Now().Add(writeWait))
		return pythonConn.WriteMessage(messageType, data)
	}

	// Client -> Python (forward audio data)
	go func() {
		defer closeDone()
		for {
			select {
			case <-done:
				return
			default:
				messageType, data, err := clientConn.ReadMessage()
				if err != nil {
					if io.EOF == err || websocket.IsCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
						errChan <- nil
					} else {
						errChan <- err
					}
					return
				}

				if !msgLimiter.Allow() {
					_ = clientWriter.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, defaultWSRateLimitMessage))
					errChan <- nil
					return
				}
				if messageType != websocket.TextMessage && messageType != websocket.BinaryMessage {
					continue
				}
				// Forward binary audio data or control messages to Python
				if err := writePython(messageType, data); err != nil {
					errChan <- err
					return
				}
			}
		}
	}()

	// Python -> Client (forward transcription results)
	go func() {
		defer closeDone()
		for {
			select {
			case <-done:
				return
			default:
				messageType, data, err := pythonConn.ReadMessage()
				if err != nil {
					if io.EOF == err || websocket.IsCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
						errChan <- nil
					} else {
						errChan <- err
					}
					return
				}

				// Forward transcription results to client
				if err := clientWriter.WriteMessage(messageType, data); err != nil {
					errChan <- err
					return
				}
			}
		}
	}()

	// Wait for error or completion
	err = <-errChan
	if err != nil {
		h.logger.Error("STT WebSocket proxy error",
			zap.String("user_id", userID),
			zap.Error(err))
	}

	// Send STOP signal to Python before closing
	_ = writePython(websocket.TextMessage, []byte("STOP"))

	h.logger.Info("STT WebSocket disconnected", zap.String("user_id", userID))
}

// STTMessage represents a message sent over the STT WebSocket
type STTMessage struct {
	Type    string `json:"type"`    // "transcription", "status", "error"
	Content string `json:"content"` // message content
	Text    string `json:"text"`    // transcribed text (for type="transcription")
	IsFinal bool   `json:"is_final"`
}

// SendSTTMessage sends a JSON message to the WebSocket connection
func SendSTTMessage(conn *websocket.Conn, msg STTMessage) error {
	return conn.WriteJSON(msg)
}

// ParseSTTMessage parses a JSON message from the WebSocket connection
func ParseSTTMessage(data []byte) (*STTMessage, error) {
	var msg STTMessage
	if err := json.Unmarshal(data, &msg); err != nil {
		return nil, err
	}
	return &msg, nil
}
