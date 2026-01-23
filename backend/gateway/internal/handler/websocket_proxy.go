package handler

import (
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"go.uber.org/zap"
	"net/http"
	"time"
)

// WebSocketProxy 专门处理 WebSocket 连接代理
// 因为 httputil.ReverseProxy 在某些情况下无法正确处理 WebSocket 升级
type WebSocketProxy struct {
	pythonBackendURL string
	upgrader         *websocket.Upgrader
	logger           *zap.Logger
}

// NewWebSocketProxy 创建新的 WebSocket 代理
func NewWebSocketProxy(backendURL string, logger *zap.Logger) *WebSocketProxy {
	return &WebSocketProxy{
		pythonBackendURL: backendURL,
		upgrader: &websocket.Upgrader{
			HandshakeTimeout: 10 * time.Second,
			ReadBufferSize:   4096,
			WriteBufferSize:  4096,
			// 生产环境需要验证 Origin
			CheckOrigin: func(r *http.Request) bool {
				return true
			},
		},
		logger: logger,
	}
}

// HandleCommunityWS 代理群聊 WebSocket 连接
// 路由: GET /api/v1/community/groups/:group_id/ws
func (p *WebSocketProxy) HandleCommunityWS(c *gin.Context) {
	groupID := c.Param("group_id")
	userID := c.GetString("user_id")

	p.logger.Info("Group WS connection request",
		zap.String("user_id", userID),
		zap.String("group_id", groupID))

	// 构造后端 WebSocket URL
	backendURL := p.pythonBackendURL + "/api/v1/community/groups/" + groupID + "/ws"

	// 从原始请求获取 token
	token := c.Query("token")
	if token == "" {
		authHeader := c.GetHeader("Authorization")
		if len(authHeader) > 7 && authHeader[:7] == "Bearer " {
			token = authHeader[7:]
		}
	}

	if token == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing token"})
		return
	}

	backendURL += "?token=" + token

	// 双向代理 WebSocket 连接
	p.proxyWebSocket(c.Writer, c.Request, backendURL, userID, "group", groupID)
}

// HandlePersonalWS 代理个人 WebSocket 连接
// 路由: GET /api/v1/community/ws/connect
func (p *WebSocketProxy) HandlePersonalWS(c *gin.Context) {
	userID := c.GetString("user_id")

	p.logger.Info("Personal WS connection request",
		zap.String("user_id", userID))

	token := c.Query("token")
	if token == "" {
		authHeader := c.GetHeader("Authorization")
		if len(authHeader) > 7 && authHeader[:7] == "Bearer " {
			token = authHeader[7:]
		}
	}

	if token == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing token"})
		return
	}

	backendURL := p.pythonBackendURL + "/api/v1/community/ws/connect?token=" + token

	p.proxyWebSocket(c.Writer, c.Request, backendURL, userID, "personal", "")
}

// proxyWebSocket 实现双向 WebSocket 代理
func (p *WebSocketProxy) proxyWebSocket(w http.ResponseWriter, r *http.Request, backendURL string, userID, connType, resourceID string) {
	// 连接到后端
	backendConn, _, err := websocket.DefaultDialer.Dial(backendURL, nil)
	if err != nil {
		p.logger.Error("Failed to dial backend",
			zap.String("backend_url", backendURL),
			zap.Error(err))
		http.Error(w, "Failed to connect to backend", http.StatusBadGateway)
		return
	}
	defer backendConn.Close()

	// 升级前端连接
	clientConn, err := p.upgrader.Upgrade(w, r, nil)
	if err != nil {
		p.logger.Error("Failed to upgrade client connection",
			zap.Error(err))
		return
	}
	defer clientConn.Close()

	p.logger.Info("WebSocket proxy connection established",
		zap.String("user_id", userID),
		zap.String("conn_type", connType),
		zap.String("resource_id", resourceID))

	// 双向转发
	done := make(chan struct{})
	errChan := make(chan error, 2)

	// 客户端 -> 后端
	go func() {
		defer close(done)
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
			if err := backendConn.WriteMessage(messageType, data); err != nil {
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
		defer close(done)
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
			if err := clientConn.WriteMessage(messageType, data); err != nil {
				p.logger.Warn("Client write error",
					zap.String("user_id", userID),
					zap.Error(err))
				errChan <- err
				return
			}
		}
	}()

	// 等待任一方向关闭
	<-done

	p.logger.Info("WebSocket proxy connection closed",
		zap.String("user_id", userID),
		zap.String("conn_type", connType))
}

// Close closes the WebSocket proxy (currently a no-op but kept for interface compatibility)
func (p *WebSocketProxy) Close() error {
	return nil
}
