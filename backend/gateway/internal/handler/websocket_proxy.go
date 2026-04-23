package handler

import (
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/config"
	"go.uber.org/zap"
)

// WebSocketProxy 专门处理 WebSocket 连接代理
// 因为 httputil.ReverseProxy 在某些情况下无法正确处理 WebSocket 升级
type WebSocketProxy struct {
	pythonBackendURL string
	upgrader         *websocket.Upgrader
	logger           *zap.Logger
	config           *config.Config
	mu               sync.Mutex
	activeByUser     map[string]int
}

// NewWebSocketProxy 创建新的 WebSocket 代理
func NewWebSocketProxy(backendURL string, logger *zap.Logger, cfg *config.Config) *WebSocketProxy {
	return &WebSocketProxy{
		pythonBackendURL: backendURL,
		upgrader: &websocket.Upgrader{
			HandshakeTimeout: 10 * time.Second,
			ReadBufferSize:   4096,
			WriteBufferSize:  4096,
			// Use secure origin checking based on config
			CheckOrigin: func(r *http.Request) bool {
				origin := r.Header.Get("Origin")
				// Allow connections without origin header (same-origin requests)
				if origin == "" {
					return true
				}
				allowed := cfg.IsOriginAllowed(origin)
				if !allowed {
					logger.Warn("WebSocket proxy rejected connection from unauthorized origin",
						zap.String("origin", origin))
				}
				return allowed
			},
		},
		logger:       logger,
		config:       cfg,
		activeByUser: make(map[string]int),
	}
}

// HandleCommunityWS 代理群聊 WebSocket 连接
// 路由: GET /api/v1/community/groups/:group_id/ws
func (p *WebSocketProxy) HandleCommunityWS(c *gin.Context) {
	groupID := c.Param("group_id")
	userID := c.GetString("user_id")

	// Security: Require authenticated user from middleware
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
		return
	}

	p.logger.Info("Group WS connection request",
		zap.String("user_id", userID),
		zap.String("group_id", groupID))

	// 构造后端 WebSocket URL
	backendURL := p.communityBackendURL(groupID)

	token := c.GetString("auth_token")
	if token == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing token"})
		return
	}

	// 双向代理 WebSocket 连接
	p.proxyWebSocket(c.Writer, c.Request, backendURL, token, userID, "group", groupID)
}

// HandlePersonalWS 代理个人 WebSocket 连接
// 路由: GET /api/v1/community/ws/connect
func (p *WebSocketProxy) HandlePersonalWS(c *gin.Context) {
	userID := c.GetString("user_id")

	// Security: Require authenticated user from middleware
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
		return
	}

	p.logger.Info("Personal WS connection request",
		zap.String("user_id", userID))

	token := c.GetString("auth_token")
	if token == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing token"})
		return
	}

	backendURL := p.personalBackendURL()

	p.proxyWebSocket(c.Writer, c.Request, backendURL, token, userID, "personal", "")
}

// proxyWebSocket 实现双向 WebSocket 代理
func (p *WebSocketProxy) proxyWebSocket(w http.ResponseWriter, r *http.Request, backendURL, authToken, userID, connType, resourceID string) {
	if !p.registerConnection(userID) {
		http.Error(w, "Too many websocket connections", http.StatusTooManyRequests)
		return
	}
	defer p.unregisterConnection(userID)

	backendWSURL, err := p.toWebSocketURL(backendURL)
	if err != nil {
		p.logger.Error("Failed to normalize backend websocket URL",
			zap.String("backend_url", backendURL),
			zap.Error(err))
		http.Error(w, "Invalid backend websocket URL", http.StatusBadGateway)
		return
	}

	// 连接到后端，并透传认证/子协议，避免网关后的 Python WS 鉴权失配。
	dialer := *websocket.DefaultDialer
	if subprotocols := websocket.Subprotocols(r); len(subprotocols) > 0 {
		dialer.Subprotocols = subprotocols
	}
	backendConn, _, err := dialer.Dial(backendWSURL, buildBackendWebSocketHeaders(r, authToken))
	if err != nil {
		p.logger.Error("Failed to dial backend",
			zap.String("backend_url", backendWSURL),
			zap.Error(err))
		http.Error(w, "Failed to connect to backend", http.StatusBadGateway)
		return
	}
	defer backendConn.Close()

	// 升级前端连接，并回显后端确认的子协议，保持客户端/后端握手一致。
	upgradeHeaders := http.Header{}
	if selectedSubprotocol := backendConn.Subprotocol(); selectedSubprotocol != "" {
		upgradeHeaders.Set("Sec-WebSocket-Protocol", selectedSubprotocol)
	}
	clientConn, err := p.upgrader.Upgrade(w, r, upgradeHeaders)
	if err != nil {
		p.logger.Error("Failed to upgrade client connection",
			zap.Error(err))
		return
	}
	defer clientConn.Close()

	readLimit := p.config.WSMaxMessageBytes
	if readLimit <= 0 {
		readLimit = 1 << 20
	}
	pongWait := time.Duration(p.config.WSPongWaitSeconds) * time.Second
	if pongWait <= 0 {
		pongWait = 90 * time.Second
	}
	pingInterval := time.Duration(p.config.WSPingIntervalSeconds) * time.Second
	if pingInterval <= 0 || pingInterval >= pongWait {
		pingInterval = pongWait / 2
	}
	writeWait := time.Duration(p.config.WSWriteWaitSeconds) * time.Second
	if writeWait <= 0 {
		writeWait = 10 * time.Second
	}
	clientConn.SetReadLimit(readLimit)
	backendConn.SetReadLimit(readLimit)
	_ = clientConn.SetReadDeadline(time.Now().Add(pongWait))
	_ = backendConn.SetReadDeadline(time.Now().Add(pongWait))
	clientConn.SetPongHandler(func(string) error {
		return clientConn.SetReadDeadline(time.Now().Add(pongWait))
	})
	backendConn.SetPongHandler(func(string) error {
		return backendConn.SetReadDeadline(time.Now().Add(pongWait))
	})

	p.logger.Info("WebSocket proxy connection established",
		zap.String("user_id", userID),
		zap.String("conn_type", connType),
		zap.String("resource_id", resourceID))

	// 双向转发
	done := make(chan struct{})
	var doneOnce sync.Once
	errChan := make(chan error, 3)
	signalDone := func() {
		doneOnce.Do(func() {
			close(done)
		})
	}
	var clientWriteMu sync.Mutex
	var backendWriteMu sync.Mutex
	writeMessage := func(mu *sync.Mutex, conn *websocket.Conn, messageType int, data []byte) error {
		mu.Lock()
		defer mu.Unlock()
		_ = conn.SetWriteDeadline(time.Now().Add(writeWait))
		return conn.WriteMessage(messageType, data)
	}

	// 客户端 -> 后端
	go func() {
		defer signalDone()
		for {
			messageType, data, err := clientConn.ReadMessage()
			if err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					p.logger.Warn("Client read error",
						zap.String("user_id", userID),
						zap.Error(err))
				}
				errChan <- err
				return
			}
			if err := writeMessage(&backendWriteMu, backendConn, messageType, data); err != nil {
				p.logger.Warn("Backend write error",
					zap.String("user_id", userID),
					zap.Error(err))
				errChan <- err
				return
			}
		}
	}()

	// 后端 -> 客户端
	go func() {
		defer signalDone()
		for {
			messageType, data, err := backendConn.ReadMessage()
			if err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					p.logger.Warn("Backend read error",
						zap.String("user_id", userID),
						zap.Error(err))
				}
				errChan <- err
				return
			}
			if err := writeMessage(&clientWriteMu, clientConn, messageType, data); err != nil {
				p.logger.Warn("Client write error",
					zap.String("user_id", userID),
					zap.Error(err))
				errChan <- err
				return
			}
		}
	}()

	go func() {
		ticker := time.NewTicker(pingInterval)
		defer ticker.Stop()
		for {
			select {
			case <-done:
				return
			case <-ticker.C:
				if err := writeMessage(&clientWriteMu, clientConn, websocket.PingMessage, nil); err != nil {
					errChan <- err
					signalDone()
					return
				}
				if err := writeMessage(&backendWriteMu, backendConn, websocket.PingMessage, nil); err != nil {
					errChan <- err
					signalDone()
					return
				}
			}
		}
	}()

	// 等待任一方向关闭
	<-done
	select {
	case err := <-errChan:
		if err != nil && !websocket.IsCloseError(err, websocket.CloseNormalClosure) {
			p.logger.Debug("WebSocket proxy closed with terminal error",
				zap.String("user_id", userID),
				zap.Error(err))
		}
	default:
	}

	p.logger.Info("WebSocket proxy connection closed",
		zap.String("user_id", userID),
		zap.String("conn_type", connType))
}

func (p *WebSocketProxy) registerConnection(userID string) bool {
	maxConns := p.config.WSMaxConnections
	if maxConns <= 0 {
		return true
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	if p.activeByUser[userID] >= maxConns {
		return false
	}
	p.activeByUser[userID]++
	return true
}

func (p *WebSocketProxy) unregisterConnection(userID string) {
	maxConns := p.config.WSMaxConnections
	if maxConns <= 0 {
		return
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	if p.activeByUser[userID] <= 1 {
		delete(p.activeByUser, userID)
		return
	}
	p.activeByUser[userID]--
}

func (p *WebSocketProxy) communityBackendURL(groupID string) string {
	return p.pythonBackendURL + "/api/v1/community/groups/" + groupID + "/ws"
}

func (p *WebSocketProxy) personalBackendURL() string {
	return p.pythonBackendURL + "/api/v1/community/ws/connect"
}

func (p *WebSocketProxy) toWebSocketURL(rawURL string) (string, error) {
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return "", err
	}

	switch parsed.Scheme {
	case "http":
		parsed.Scheme = "ws"
	case "https":
		parsed.Scheme = "wss"
	case "ws", "wss":
	default:
		parsed.Scheme = "ws"
	}

	return parsed.String(), nil
}

func buildBackendWebSocketHeaders(r *http.Request, authToken string) http.Header {
	headers := http.Header{}
	if authToken != "" {
		headers.Set("Authorization", "Bearer "+authToken)
	}
	if origin := r.Header.Get("Origin"); origin != "" {
		headers.Set("Origin", origin)
	}
	if forwardedFor := r.Header.Get("X-Forwarded-For"); forwardedFor != "" {
		headers.Set("X-Forwarded-For", forwardedFor)
	}
	if realIP := r.Header.Get("X-Real-IP"); realIP != "" {
		headers.Set("X-Real-IP", realIP)
	}
	return headers
}

// Close closes the WebSocket proxy (currently a no-op but kept for interface compatibility)
func (p *WebSocketProxy) Close() error {
	return nil
}
