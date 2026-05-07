package handler

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"regexp"
	"net/url"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
	"go.uber.org/zap"
)

// wsDefaultMaxMessageBytes is the fallback when WSMaxMessageBytes is not
// configured or set to a non-positive value.  All handlers share this
// default so behaviour is consistent across WebSocket endpoints.
const wsDefaultMaxMessageBytes int64 = 256 * 1024 // 256 KB

// Reconnect rate-limit constants
const (
	reconnectMaxAttemptsDefault = 10  // default max reconnect attempts per window
	reconnectWindowSecDefault   = 30  // default sliding window in seconds (configurable via WSReconnectWindowSeconds)
	reconnectBlockSecDefault    = 300 // default block duration after exceeding limit
	reconnectCleanupSec         = 300 // cleanup interval for expired trackers
)

type reconnectTracker struct {
	attemptCount int
	lastAttempt  time.Time
	blockedUntil time.Time
}

// WebSocketProxy 专门处理 WebSocket 连接代理
// 因为 httputil.ReverseProxy 在某些情况下无法正确处理 WebSocket 升级
//
// Known limitation (G-03): Connection tracking (activeByUser) is local to this
// process. When multiple gateway instances sit behind a load balancer, per-user
// limits are enforced per-instance, not globally. For single-instance
// deployments this is sufficient. A Redis-backed atomic counter would be needed
// for multi-instance enforcement — tracked as future work.
type WebSocketProxy struct {
	pythonBackendURL  string
	upgrader          *websocket.Upgrader
	logger            *zap.Logger
	config            *config.Config
	dedupService      *service.MessageDedupService
	mu                sync.Mutex
	activeByUser      map[string]int
	reconnectTrackers map[string]*reconnectTracker
	liveConnections   map[*websocket.Conn]*proxyConnectionPair
	wg                sync.WaitGroup
	draining          atomic.Bool
}

type proxyConnectionPair struct {
	clientConn  *websocket.Conn
	backendConn *websocket.Conn
}

// NewWebSocketProxy 创建新的 WebSocket 代理
func NewWebSocketProxy(backendURL string, logger *zap.Logger, cfg *config.Config, dedupService *service.MessageDedupService) *WebSocketProxy {
	proxy := &WebSocketProxy{
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
		logger:            logger,
		config:            cfg,
		dedupService:      dedupService,
		activeByUser:      make(map[string]int),
		reconnectTrackers: make(map[string]*reconnectTracker),
		liveConnections:   make(map[*websocket.Conn]*proxyConnectionPair),
	}
	proxy.startReconnectTrackerCleanup()
	return proxy
}

// HandleCommunityWS 代理群聊 WebSocket 连接
// 路由: GET /api/v1/community/groups/:group_id/ws
func (p *WebSocketProxy) HandleCommunityWS(c *gin.Context) {
	if p.IsDraining() {
		c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": "Server shutting down"})
		return
	}
	groupID := c.Param("group_id")
	userID := c.GetString("user_id")

	// Validate groupID is a UUID to prevent path traversal
	if !isValidUUID(groupID) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid group ID format"})
		return
	}

	// Security: Require authenticated user from middleware
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
		return
	}

	p.logger.Info("Group WS connection request",
		zap.String("user_id_hash", hashUserIDForLog(userID)),
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
	if p.IsDraining() {
		c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": "Server shutting down"})
		return
	}
	userID := c.GetString("user_id")

	// Security: Require authenticated user from middleware
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
		return
	}

	p.logger.Info("Personal WS connection request",
		zap.String("user_id_hash", hashUserIDForLog(userID)))

	token := c.GetString("auth_token")
	if token == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing token"})
		return
	}

	backendURL := p.personalBackendURL()

	// P0-1: Forward session_id for reconnect context restoration
	if sessionID := c.Query("session_id"); sessionID != "" {
		if !p.checkReconnectAllowed(userID) {
			p.logger.Warn("WS reconnect rate limit exceeded",
				zap.String("user_id_hash", hashUserIDForLog(userID)),
				zap.String("session_id", sessionID))
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "Reconnect rate limit exceeded. Please wait before retrying.",
				"retry_after": p.reconnectBlockRemaining(userID),
			})
			return
		}
		p.recordReconnectAttempt(userID)
		backendURL = backendURL + "?session_id=" + url.QueryEscape(sessionID)
		p.logger.Info("WS reconnect with session_id",
			zap.String("user_id_hash", hashUserIDForLog(userID)),
			zap.String("session_id", sessionID))
	}

	p.proxyWebSocket(c.Writer, c.Request, backendURL, token, userID, "personal", "")
}

// proxyWebSocket 实现双向 WebSocket 代理
func (p *WebSocketProxy) proxyWebSocket(w http.ResponseWriter, r *http.Request, backendURL, authToken, userID, connType, resourceID string) {
	if p.IsDraining() {
		http.Error(w, "Server shutting down", http.StatusServiceUnavailable)
		return
	}
	if !p.registerConnection(userID) {
		if p.IsDraining() {
			http.Error(w, "Server shutting down", http.StatusServiceUnavailable)
			return
		}
		http.Error(w, "Too many websocket connections", http.StatusTooManyRequests)
		return
	}
	defer p.unregisterConnection(userID)
	p.wg.Add(1)
	defer p.wg.Done()

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
	if p.IsDraining() {
		_ = backendConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "server shutting down"),
			time.Now().Add(time.Second),
		)
		_ = backendConn.Close()
		_ = clientConn.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseTryAgainLater, "server shutting down"),
			time.Now().Add(time.Second),
		)
		return
	}
	p.registerLiveConnection(clientConn, backendConn)
	defer p.unregisterLiveConnection(clientConn)

	readLimit := int64(0)
	if p.config != nil {
		readLimit = p.config.WSMaxMessageBytes
	}
	if readLimit <= 0 {
		readLimit = wsDefaultMaxMessageBytes
	}
	pongWaitSeconds := 0
	pingIntervalSeconds := 0
	writeWaitSeconds := 0
	if p.config != nil {
		pongWaitSeconds = p.config.WSPongWaitSeconds
		pingIntervalSeconds = p.config.WSPingIntervalSeconds
		writeWaitSeconds = p.config.WSWriteWaitSeconds
	}
	pongWait := time.Duration(pongWaitSeconds) * time.Second
	if pongWait <= 0 {
		pongWait = 90 * time.Second
	}
	pingInterval := time.Duration(pingIntervalSeconds) * time.Second
	if pingInterval <= 0 || pingInterval >= pongWait {
		pingInterval = pongWait / 2
	}
	writeWait := time.Duration(writeWaitSeconds) * time.Second
	if writeWait <= 0 {
		writeWait = 10 * time.Second
	}
	clientConn.SetReadLimit(readLimit)
	backendConn.SetReadLimit(readLimit)
	msgLimiter := newWSMessageRateLimiter(p.config)
	_ = clientConn.SetReadDeadline(time.Now().Add(pongWait))
	_ = backendConn.SetReadDeadline(time.Now().Add(pongWait))
	clientConn.SetPongHandler(func(string) error {
		return clientConn.SetReadDeadline(time.Now().Add(pongWait))
	})
	backendConn.SetPongHandler(func(string) error {
		return backendConn.SetReadDeadline(time.Now().Add(pongWait))
	})

	p.logger.Info("WebSocket proxy connection established",
		zap.String("user_id_hash", hashUserIDForLog(userID)),
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
	sendErr := func(err error) {
		select {
		case errChan <- err:
		default:
			p.logger.Debug("WebSocket proxy error channel full",
				zap.String("user_id_hash", hashUserIDForLog(userID)),
				zap.Error(err))
		}
	}
	var closeOnce sync.Once
	closeConnections := func(code int, reason string) {
		closeOnce.Do(func() {
			closeMessage := websocket.FormatCloseMessage(code, reason)
			_ = writeMessage(&clientWriteMu, clientConn, websocket.CloseMessage, closeMessage)
			_ = writeMessage(&backendWriteMu, backendConn, websocket.CloseMessage, closeMessage)
			_ = clientConn.Close()
			_ = backendConn.Close()
		})
	}
	recoverProxyGoroutine := func(name string) {
		if r := recover(); r != nil {
			err := fmt.Errorf("%s panic: %v", name, r)
			p.logger.Error("WebSocket proxy goroutine panic recovered",
				zap.String("goroutine", name),
				zap.String("user_id_hash", hashUserIDForLog(userID)),
				zap.String("conn_type", connType),
				zap.Any("panic", r),
				zap.Stack("stack"))
			closeConnections(websocket.CloseInternalServerErr, "internal websocket error")
			sendErr(err)
			signalDone()
		}
	}

	// 客户端 -> 后端
	go func() {
		defer recoverProxyGoroutine("client_to_backend")
		defer signalDone()
		for {
			messageType, data, err := clientConn.ReadMessage()
			if err != nil {
				var closeErr *websocket.CloseError
				if errors.As(err, &closeErr) {
					closeConnections(closeErr.Code, closeErr.Text)
				} else if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					p.logger.Warn("Client read error",
						zap.String("user_id_hash", hashUserIDForLog(userID)),
						zap.Error(err))
				}
				sendErr(err)
				return
			}
			// Reject oversized messages
			if len(data) > int(readLimit) {
				p.logger.Warn("Dropping oversized client message",
					zap.String("user_id_hash", hashUserIDForLog(userID)),
					zap.Int("size", len(data)),
					zap.Int("max", int(readLimit)))
				continue
			}
			if !msgLimiter.Allow() {
				_ = writeMessage(&clientWriteMu, clientConn, websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, defaultWSRateLimitMessage))
				sendErr(nil)
				return
			}
			// Only allow text and binary message types
			if messageType != websocket.TextMessage && messageType != websocket.BinaryMessage {
				continue
			}
			if messageType == websocket.TextMessage {
				data = sanitizeCommunityWSTextPayload(data)

				// P2-29: Server-side message deduplication via content hash
				if p.dedupService != nil && len(data) > 0 {
					hash := sha256.Sum256(data)
					dedupKey := hex.EncodeToString(hash[:])
					isDup, err := p.dedupService.CheckAndMark(context.Background(), userID, dedupKey)
					if err != nil {
						p.logger.Debug("Dedup check failed, forwarding anyway",
							zap.String("user_id_hash", hashUserIDForLog(userID)),
							zap.Error(err))
					} else if isDup {
						p.logger.Debug("Dropping duplicate WebSocket message",
							zap.String("user_id_hash", hashUserIDForLog(userID)),
							zap.Int("size", len(data)))
						continue
					}
				}
			}
			if err := writeMessage(&backendWriteMu, backendConn, messageType, data); err != nil {
				p.logger.Warn("Backend write error",
					zap.String("user_id_hash", hashUserIDForLog(userID)),
					zap.Error(err))
				sendErr(err)
				return
			}
		}
	}()

	// 后端 -> 客户端
	go func() {
		defer recoverProxyGoroutine("backend_to_client")
		defer signalDone()
		for {
			messageType, data, err := backendConn.ReadMessage()
			if err != nil {
				var closeErr *websocket.CloseError
				if errors.As(err, &closeErr) {
					closeConnections(closeErr.Code, closeErr.Text)
				} else if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					p.logger.Warn("Backend read error",
						zap.String("user_id_hash", hashUserIDForLog(userID)),
						zap.Error(err))
				}
				sendErr(err)
				return
			}
			// G-04: Validate backend message size before forwarding to client
			if len(data) > int(readLimit) {
				p.logger.Warn("Backend message exceeds limit, dropping",
					zap.String("user_id_hash", hashUserIDForLog(userID)),
					zap.Int("size", len(data)),
					zap.Int64("limit", readLimit))
				continue
			}
			if err := writeMessage(&clientWriteMu, clientConn, messageType, data); err != nil {
				p.logger.Warn("Client write error",
					zap.String("user_id_hash", hashUserIDForLog(userID)),
					zap.Error(err))
				sendErr(err)
				return
			}
		}
	}()

	go func() {
		defer recoverProxyGoroutine("proxy_ping")
		ticker := time.NewTicker(pingInterval)
		defer ticker.Stop()
		for {
			select {
			case <-done:
				return
			case <-ticker.C:
				if err := writeMessage(&clientWriteMu, clientConn, websocket.PingMessage, nil); err != nil {
					sendErr(err)
					signalDone()
					return
				}
				if err := writeMessage(&backendWriteMu, backendConn, websocket.PingMessage, nil); err != nil {
					sendErr(err)
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
				zap.String("user_id_hash", hashUserIDForLog(userID)),
				zap.Error(err))
		}
	default:
	}

	p.logger.Info("WebSocket proxy connection closed",
		zap.String("user_id_hash", hashUserIDForLog(userID)),
		zap.String("conn_type", connType))
}

func (p *WebSocketProxy) registerConnection(userID string) bool {
	if p.IsDraining() {
		return false
	}
	metrics.WSConnectionsActive.Inc()

	maxConns := p.config.WSMaxConnections
	if maxConns <= 0 {
		return true
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	if p.activeByUser[userID] >= maxConns {
		metrics.WSConnectionsActive.Dec()
		return false
	}
	p.activeByUser[userID]++
	return true
}

func (p *WebSocketProxy) unregisterConnection(userID string) {
	metrics.WSConnectionsActive.Dec()

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

func (p *WebSocketProxy) registerLiveConnection(clientConn, backendConn *websocket.Conn) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.liveConnections[clientConn] = &proxyConnectionPair{
		clientConn:  clientConn,
		backendConn: backendConn,
	}
}

func (p *WebSocketProxy) unregisterLiveConnection(clientConn *websocket.Conn) {
	p.mu.Lock()
	defer p.mu.Unlock()
	delete(p.liveConnections, clientConn)
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

func hashUserIDForLog(userID string) string {
	sum := sha256.Sum256([]byte(userID))
	return hex.EncodeToString(sum[:])[:12]
}

var uuidPattern = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

func isValidUUID(s string) bool {
	return uuidPattern.MatchString(s)
}

func sanitizeCommunityWSTextPayload(data []byte) []byte {
	var payload interface{}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := decoder.Decode(&payload); err != nil {
		return []byte(sanitizer.Sanitize(string(data)))
	}
	sanitized, err := json.Marshal(sanitizeCommunityWSJSONValue(payload))
	if err != nil {
		return []byte(sanitizer.Sanitize(string(data)))
	}
	return sanitized
}

func sanitizeCommunityWSJSONValue(value interface{}) interface{} {
	switch v := value.(type) {
	case string:
		return sanitizer.Sanitize(v)
	case []interface{}:
		for i, item := range v {
			v[i] = sanitizeCommunityWSJSONValue(item)
		}
		return v
	case map[string]interface{}:
		for key, item := range v {
			v[key] = sanitizeCommunityWSJSONValue(item)
		}
		return v
	default:
		return v
	}
}

// Close gracefully shuts down the WebSocket proxy by draining connections
// and waiting for in-flight goroutines to finish (up to 5 seconds).
func (p *WebSocketProxy) Close() error {
	p.StartDraining()
	done := make(chan struct{})
	go func() {
		p.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
		return nil
	case <-time.After(5 * time.Second):
		return nil
	}
}

func (p *WebSocketProxy) StartDraining() {
	p.draining.Store(true)
}

func (p *WebSocketProxy) IsDraining() bool {
	return p.draining.Load()
}

// --- Reconnect rate-limit helpers ---

func (p *WebSocketProxy) checkReconnectAllowed(userID string) bool {
	p.mu.Lock()
	defer p.mu.Unlock()

	tracker := p.reconnectTrackers[userID]
	if tracker == nil {
		return true
	}
	if time.Now().Before(tracker.blockedUntil) {
		return false
	}
	windowSec := reconnectWindowSecDefault
	if p.config != nil && p.config.WSReconnectWindowSeconds > 0 {
		windowSec = p.config.WSReconnectWindowSeconds
	}
	window := time.Duration(windowSec) * time.Second
	if time.Since(tracker.lastAttempt) > window {
		tracker.attemptCount = 0
		return true
	}
	maxAttempts := reconnectMaxAttemptsDefault
	if p.config != nil && p.config.WSReconnectMaxAttempts > 0 {
		maxAttempts = p.config.WSReconnectMaxAttempts
	}
	return tracker.attemptCount < maxAttempts
}

func (p *WebSocketProxy) recordReconnectAttempt(userID string) {
	p.mu.Lock()
	defer p.mu.Unlock()

	tracker := p.reconnectTrackers[userID]
	if tracker == nil {
		tracker = &reconnectTracker{}
		p.reconnectTrackers[userID] = tracker
	}
	tracker.attemptCount++
	tracker.lastAttempt = time.Now()

	maxAttempts := reconnectMaxAttemptsDefault
	if p.config != nil && p.config.WSReconnectMaxAttempts > 0 {
		maxAttempts = p.config.WSReconnectMaxAttempts
	}
	blockSec := reconnectBlockSecDefault
	if p.config != nil && p.config.WSReconnectBlockSeconds > 0 {
		blockSec = p.config.WSReconnectBlockSeconds
	}

	if tracker.attemptCount >= maxAttempts {
		tracker.blockedUntil = time.Now().Add(time.Duration(blockSec) * time.Second)
	}
}

func (p *WebSocketProxy) reconnectBlockRemaining(userID string) int {
	p.mu.Lock()
	defer p.mu.Unlock()

	tracker := p.reconnectTrackers[userID]
	if tracker == nil || time.Now().After(tracker.blockedUntil) {
		return 0
	}
	return int(time.Until(tracker.blockedUntil).Seconds())
}

func (p *WebSocketProxy) startReconnectTrackerCleanup() {
	go func() {
		defer func() {
			if r := recover(); r != nil {
				p.logger.Error("WebSocket reconnect tracker cleanup panic recovered",
					zap.Any("panic", r),
					zap.Stack("stack"))
			}
		}()
		ticker := time.NewTicker(time.Duration(reconnectCleanupSec) * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			p.cleanupExpiredReconnectTrackers()
		}
	}()
}

func (p *WebSocketProxy) cleanupExpiredReconnectTrackers() {
	p.mu.Lock()
	defer p.mu.Unlock()

	windowSec := reconnectWindowSecDefault
	if p.config != nil && p.config.WSReconnectWindowSeconds > 0 {
		windowSec = p.config.WSReconnectWindowSeconds
	}
	cutoff := time.Now().Add(-time.Duration(windowSec) * time.Second)
	for userID, tracker := range p.reconnectTrackers {
		if tracker.lastAttempt.Before(cutoff) && time.Now().After(tracker.blockedUntil) {
			delete(p.reconnectTrackers, userID)
		}
	}
}
