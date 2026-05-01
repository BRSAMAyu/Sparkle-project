/*
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
*/

package handler

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/microcosm-cc/bluemonday"
	pbws "github.com/sparkle/gateway/gen/ws"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/galaxy"
	"github.com/sparkle/gateway/internal/i18n"
	"github.com/sparkle/gateway/internal/metrics"
	"github.com/sparkle/gateway/internal/service"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"golang.org/x/time/rate"
)

// P1 Optimization: Object pools to reduce GC pressure in high-concurrency scenarios

// chatInputPool reuses input message structs
var chatInputPool = sync.Pool{
	New: func() interface{} {
		return &chatInput{}
	},
}

// chatInput represents a WebSocket chat message input
type chatInput struct {
	Message            string                 `json:"message"`
	SessionID          string                 `json:"session_id"`
	RequestID          string                 `json:"request_id,omitempty"`
	Nickname           string                 `json:"nickname,omitempty"`
	FileIds            []string               `json:"file_ids,omitempty"`
	IncludeReferences  bool                   `json:"include_references,omitempty"`
	ActiveTools        []string               `json:"active_tools,omitempty"`
	ExtraContext       map[string]interface{} `json:"extra_context,omitempty"`
	ChatMode           string                 `json:"chat_mode,omitempty"`
	UseDocumentContext *bool                  `json:"use_document_context,omitempty"`
	DocumentFilter     []string               `json:"document_filter,omitempty"`
	// Tool result fields — populated when the client sends back a tool execution result.
	ToolCallID     string `json:"tool_call_id,omitempty"`
	ToolName       string `json:"tool_name,omitempty"`
	ToolResultJSON string `json:"tool_result_json,omitempty"`
	ToolIsError    bool   `json:"tool_is_error,omitempty"`
	ToolErrorMsg   string `json:"tool_error_message,omitempty"`
	IsToolResult   bool   `json:"-"` // internal flag
}

type wsMode int

const (
	wsModeLegacy wsMode = iota
	wsModeEnvelope
)

const (
	maxTraceparentLen = 512
	maxTracestateLen  = 2048
)

type wsEnvelopeIn struct {
	Traceparent string                     `json:"traceparent,omitempty"`
	Tracestate  string                     `json:"tracestate,omitempty"`
	MessageID   string                     `json:"message_id,omitempty"`
	RequestID   string                     `json:"request_id,omitempty"`
	ClientTS    int64                      `json:"client_ts,omitempty"`
	Payload     map[string]json.RawMessage `json:"payload,omitempty"`
	Raw         map[string]json.RawMessage `json:"-"`
}

type wsEnvelopeOut struct {
	Traceparent string                     `json:"traceparent,omitempty"`
	Tracestate  string                     `json:"tracestate,omitempty"`
	MessageID   string                     `json:"message_id,omitempty"`
	RequestID   string                     `json:"request_id,omitempty"`
	Payload     map[string]json.RawMessage `json:"payload,omitempty"`
}

// Reset clears the input for reuse
func (c *chatInput) Reset() {
	c.Message = ""
	c.SessionID = ""
	c.RequestID = ""
	c.Nickname = ""
	c.FileIds = nil
	c.IncludeReferences = false
	c.ActiveTools = nil
	c.ExtraContext = nil
	c.ChatMode = ""
	c.UseDocumentContext = nil
	c.DocumentFilter = nil
	c.ToolCallID = ""
	c.ToolName = ""
	c.ToolResultJSON = ""
	c.ToolIsError = false
	c.ToolErrorMsg = ""
	c.IsToolResult = false
}

// stringBuilderPool reuses string builders for text accumulation
var stringBuilderPool = sync.Pool{
	New: func() interface{} {
		return &strings.Builder{}
	},
}

// sanitizerPool reuses bluemonday policies (they are thread-safe once created)
var sanitizer = bluemonday.UGCPolicy()

// 🔧 P1-2: 消息长度限制（防止OOM和滥用）
const maxMessageLength = 4000

// maxToolResultLength limits tool_result_json to prevent oversized payloads.
const maxToolResultLength = 10 * 1024 // 10 KB

// defaultMaxConcurrentStreams is the fallback when StreamMaxConcurrent is not set.
const defaultMaxConcurrentStreams = 200

func streamSemaphoreSize(cfg *config.Config) int {
	if cfg != nil && cfg.StreamMaxConcurrent > 0 {
		return cfg.StreamMaxConcurrent
	}
	return defaultMaxConcurrentStreams
}

type ChatOrchestrator struct {
	agentClient  *agent.Client
	galaxyClient *galaxy.Client
	queries      *db.Queries
	chatHistory  *service.ChatHistoryService
	quota        *service.QuotaService
	semantic     *service.SemanticCacheService
	billing      *service.CostCalculator
	wsFactory    *WebSocketFactory
	cfg          *config.Config
	userContext  *service.UserContextService
	taskCommand  *service.TaskCommandService
	backendURL   string
	signalHub    *service.SignalHub
	httpClient   *http.Client
	wsRegistry   *ConnectionRegistry
	// streamSem limits concurrent gRPC StreamChat calls.
	streamSem chan struct{}
	draining  atomic.Bool
}

func NewChatOrchestrator(ac *agent.Client, gc *galaxy.Client, q *db.Queries, ch *service.ChatHistoryService, qs *service.QuotaService, sc *service.SemanticCacheService, bc *service.CostCalculator, wsFactory *WebSocketFactory, cfg *config.Config, uc *service.UserContextService, tc *service.TaskCommandService, backendURL string, signalHub *service.SignalHub) *ChatOrchestrator {
	return &ChatOrchestrator{
		agentClient:  ac,
		galaxyClient: gc,
		queries:      q,
		chatHistory:  ch,
		quota:        qs,
		semantic:     sc,
		billing:      bc,
		wsFactory:    wsFactory,
		cfg:          cfg,
		userContext:  uc,
		taskCommand:  tc,
		backendURL:   strings.TrimRight(backendURL, "/"),
		signalHub:    signalHub,
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
		},
		wsRegistry: NewConnectionRegistry(signalHub, ch, cfg.WSGlobalMaxConnections, cfg.WSMaxConnections),
		streamSem:  make(chan struct{}, streamSemaphoreSize(cfg)),
	}
}

func (h *ChatOrchestrator) HandleWebSocket(c *gin.Context) {
	if h.IsDraining() {
		c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": "Server shutting down"})
		return
	}

	// Use WebSocketFactory for secure origin checking
	var upgrader websocket.Upgrader
	if h.wsFactory != nil {
		upgrader = h.wsFactory.CreateUpgrader()
	} else {
		if !isDevelopmentEnv() {
			log.Printf("[ERROR] WebSocketFactory missing in non-development environment")
			c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "WebSocket configuration error"})
			return
		}
		// Fallback to development upgrader (for backward compatibility)
		upgrader = DefaultUpgrader()
		log.Printf("[WARNING] Using development WebSocket upgrader - configure WebSocketFactory for production")
	}
	if selected := selectWebSocketSubprotocol(c.Request); selected != "" {
		upgrader.Subprotocols = []string{selected}
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("Failed to upgrade WS: %v", err)
		return
	}

	// --- WebSocket lifecycle: deadlines, ping/pong, idle timeout ---
	pongWait := 90 * time.Second
	pingInterval := 30 * time.Second
	writeWait := 60 * time.Second
	idleTimeout := 5 * time.Minute
	if h.cfg != nil {
		if h.cfg.WSPongWaitSeconds > 0 {
			pongWait = time.Duration(h.cfg.WSPongWaitSeconds) * time.Second
		}
		if h.cfg.WSPingIntervalSeconds > 0 {
			pingInterval = time.Duration(h.cfg.WSPingIntervalSeconds) * time.Second
		}
		if h.cfg.WSWriteWaitSeconds > 0 {
			writeWait = time.Duration(h.cfg.WSWriteWaitSeconds) * time.Second
		}
		if h.cfg.WSIdleTimeoutSeconds > 0 {
			idleTimeout = time.Duration(h.cfg.WSIdleTimeoutSeconds) * time.Second
		}
	}
	if writeWait < 60*time.Second {
		writeWait = 60 * time.Second
	}
	writer := newWSSafeWriter(conn, writeWait)
	defer func() {
		_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
		_ = conn.Close()
	}()
	if h.IsDraining() {
		writeServerDrainingClose(writer, conn)
		return
	}

	_ = conn.SetReadDeadline(time.Now().Add(pongWait))
	conn.SetPongHandler(func(string) error {
		return conn.SetReadDeadline(time.Now().Add(pongWait))
	})

	// Ping ticker goroutine
	pingTicker := time.NewTicker(pingInterval)
	pingDone := make(chan struct{})
	go func() {
		defer pingTicker.Stop()
		for {
			select {
			case <-pingTicker.C:
				if err := writer.WriteControl(websocket.PingMessage, nil); err != nil {
					return
				}
			case <-pingDone:
				return
			}
		}
	}()
	defer close(pingDone)

	// Idle timer — close connection if no messages for idleTimeout.
	// connDone prevents the goroutine from touching conn after the handler exits.
	idleTimer := time.NewTimer(idleTimeout)
	defer idleTimer.Stop()
	connDone := make(chan struct{})
	defer close(connDone)
	go func() {
		select {
		case <-idleTimer.C:
			log.Printf("WebSocket idle timeout for connection, closing")
			_ = writer.WriteControl(
				websocket.CloseMessage,
				websocket.FormatCloseMessage(websocket.CloseGoingAway, "idle timeout"),
			)
			_ = conn.Close()
		case <-connDone:
			return
		}
	}()

	// Require authenticated user_id from context (must be set by AuthMiddleware)
	userID := c.GetString("user_id")
	if userID == "" {
		log.Printf("WebSocket rejected: missing authentication")
		_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseUnsupportedData, "Authentication required"))
		_ = conn.Close() // Explicitly close rejected connection
		return
	}
	authToken := c.GetString("auth_token")
	_ = authToken

	log.Printf("WebSocket connected for user: %s", userID)
	// P0-1: Log reconnect context if session_id provided via query param
	if reconnectSID := c.Query("session_id"); reconnectSID != "" {
		log.Printf("WebSocket reconnect for user: %s with session_id: %s", userID, reconnectSID)
	}
	authMethod := c.GetString("ws_auth_method")
	if authMethod == "" {
		authMethod = "unknown"
	}
	metrics.WSConnectionSuccess.WithLabelValues("/ws/chat", authMethod).Inc()
	if !h.registerConnection(userID, conn, writer) {
		if h.IsDraining() {
			metrics.WSConnectionError.WithLabelValues("/ws/chat", authMethod, "draining").Inc()
			writeServerDrainingClose(writer, conn)
			return
		}
		metrics.WSConnectionError.WithLabelValues("/ws/chat", authMethod, "connection_limit").Inc()
		writeConnectionLimitClose(writer, conn)
		return
	}
	defer h.unregisterConnection(userID, conn)

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

	tracer := otel.Tracer("chat-orchestrator")

	// Message handling loop: each WebSocket message triggers a new StreamChat call
	for {
		// Read message from WebSocket client
		msgType, msg, err := conn.ReadMessage()
		if err != nil {
			if errors.Is(err, websocket.ErrReadLimit) {
				_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message too large"))
			}
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		// Reset idle timer on each received message
		if !idleTimer.Stop() {
			select {
			case <-idleTimer.C:
			default:
			}
		}
		idleTimer.Reset(idleTimeout)

		if !msgLimiter.Allow() {
			_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message rate limit exceeded"))
			break
		}

		// P2: Support Binary Protobuf Protocol
		if msgType == websocket.BinaryMessage {
			h.handleProtobufMessage(writer, msg, userID, tracer, c.Request.Context())
			continue
		}

		shouldClose := func() bool {
			mode := wsModeLegacy
			var envelope *wsEnvelopeIn
			if env, ok := parseEnvelopeJSON(msg); ok {
				mode = wsModeEnvelope
				envelope = env
			}

			if mode == wsModeLegacy {
				// First, check message type (legacy JSON)
				msgMap := make(map[string]interface{})
				if err := json.Unmarshal(msg, &msgMap); err != nil {
					log.Printf("Failed to parse message: %v", err)
					_ = writer.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
					return false
				}

				msgType, ok := msgMap["type"].(string)
				if !ok {
					msgType = "message" // Default to chat message
				}

				// Route based on message type
				switch msgType {
				case "ping":
					_ = writer.WriteJSON(gin.H{"type": "pong"})
					return false
				case "action_feedback":
					h.handleActionFeedback(c.Request.Context(), writer, msgMap, userID, authToken)
					return false
				case "intervention_feedback":
					h.handleInterventionFeedback(writer, msgMap, userID, authToken)
					return false
				case "response_feedback":
					h.handleResponseFeedback(writer, msgMap, userID, c.Request.Context())
					return false
				case "plan_review_feedback":
					h.handlePlanReviewFeedback(writer, msgMap, userID, c.Request.Context())
					return false
				case "focus_completed":
					h.handleFocusCompleted(msgMap, userID, authToken)
					return false
				case "tool_result":
					// Legacy JSON routing for tool results
					toolInput := chatInputPool.Get().(*chatInput)
					toolInput.Reset()
					toolInput.IsToolResult = true
					toolInput.ToolCallID, _ = msgMap["tool_call_id"].(string)
					toolInput.ToolName, _ = msgMap["tool_name"].(string)
					toolInput.ToolResultJSON, _ = msgMap["result_json"].(string)
					toolInput.ToolIsError, _ = msgMap["is_error"].(bool)
					toolInput.ToolErrorMsg, _ = msgMap["error_message"].(string)
					toolInput.SessionID, _ = msgMap["session_id"].(string)
					toolInput.RequestID, _ = msgMap["request_id"].(string)

					if len(toolInput.ToolResultJSON) > maxToolResultLength {
						_ = writer.WriteJSON(gin.H{"type": "error", "message": "Tool result too large"})
						toolInput.Reset()
						chatInputPool.Put(toolInput)
						return false
					}

					return func() bool {
						defer func() {
							toolInput.Reset()
							chatInputPool.Put(toolInput)
						}()
						msgCtx := c.Request.Context()
						ctx2, span2 := tracer.Start(msgCtx, "HandleToolResult")
						span2.SetAttributes(
							attribute.String("user_id", userID),
							attribute.String("tool_call_id", toolInput.ToolCallID),
							attribute.String("tool_name", toolInput.ToolName),
						)
						defer span2.End()
						return h.handleChatMessage(ctx2, writer, userID, toolInput, toolInput.RequestID)
					}()
				case "update_node_mastery":
					h.handleUpdateNodeMastery(writer, msgMap, userID, c.Request.Context())
					return false
				case "message", "":
					// Continue with normal chat message handling
				default:
					log.Printf("Unknown message type: %s", msgType)
					_ = writer.WriteJSON(gin.H{"type": "error", "message": "Unknown message type"})
					return false
				}

				// P1: Get input from pool instead of allocating new struct
				input := chatInputPool.Get().(*chatInput)
				input.Reset()
				defer func() {
					input.Reset()
					chatInputPool.Put(input)
				}()

				traceIDFromClient, _ := msgMap["trace_id"].(string)

				// Parse JSON input
				if err := json.Unmarshal(msg, input); err != nil {
					log.Printf("Failed to parse message: %v", err)
					_ = writer.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
					return false
				}

				if input.Message == "" {
					_ = writer.WriteJSON(gin.H{"type": "error", "message": "Empty message"})
					return false
				}

				// 🔧 P1-2: 消息长度检查
				if len(input.Message) > maxMessageLength {
					_ = writer.WriteJSON(gin.H{
						"type":    "error",
						"message": i18n.T(c.Request.Context(), "chat.message_length_exceeded", map[string]string{"max_length": fmt.Sprintf("%d", maxMessageLength)}),
					})
					return false
				}

				// 🔧 P1-2: XSS 过滤
				input.Message = sanitizer.Sanitize(input.Message)

				msgCtx := c.Request.Context()
				if traceIDFromClient != "" {
					msgCtx = agent.WithTraceID(msgCtx, traceIDFromClient)
				}
				ctx, span := tracer.Start(msgCtx, "HandleMessage")
				span.SetAttributes(
					attribute.String("user_id", userID),
					attribute.String("session_id", input.SessionID),
				)
				if traceIDFromClient != "" {
					span.SetAttributes(attribute.String("trace_id", traceIDFromClient))
				}
				defer span.End()

				return h.handleChatMessage(ctx, writer, userID, input, input.RequestID)
			}

			if envelope.MessageID == "" {
				envelope.MessageID = generateMessageID()
			}
			if envelope.RequestID == "" {
				envelope.RequestID = generateRequestID()
			}

			msgCtx := extractTraceContextFromEnvelope(c.Request.Context(), envelope)
			msgCtx, span := tracer.Start(msgCtx, "HandleMessage")
			span.SetAttributes(
				attribute.String("user_id", userID),
				attribute.String("message_id", envelope.MessageID),
				attribute.String("request_id", envelope.RequestID),
			)
			defer span.End()

			responder := newEnvelopeResponder(writer, envelope, msgCtx)
			responder.SendAck()

			switch payloadType := envelopePayloadType(envelope.Payload); payloadType {
			case "chat_request":
				input := chatInputPool.Get().(*chatInput)
				input.Reset()
				defer func() {
					input.Reset()
					chatInputPool.Put(input)
				}()

				if err := decodeChatRequestEnvelope(envelope.Payload["chat_request"], input); err != nil {
					responder.SendError("invalid_argument", "Invalid chat_request payload", false)
					return false
				}

				// 🔧 P1-2: 消息长度检查
				if len(input.Message) > maxMessageLength {
					responder.SendError("invalid_argument",
						i18n.T(msgCtx, "chat.message_length_exceeded", map[string]string{"max_length": fmt.Sprintf("%d", maxMessageLength)}), false)
					return false
				}

				return h.handleChatMessage(msgCtx, responder, userID, input, envelope.RequestID)
			case "tool_result":
				// Envelope routing for tool results (e.g. OpenClaw execution results)
				toolInput := chatInputPool.Get().(*chatInput)
				toolInput.Reset()
				defer func() {
					toolInput.Reset()
					chatInputPool.Put(toolInput)
				}()

				// Decode tool result from envelope payload
				msgMap, mapErr := decodePayloadMap(envelope.Payload["tool_result"])
				if mapErr != nil {
					responder.SendError("invalid_argument", "Invalid tool_result payload", false)
					return false
				}
				toolInput.IsToolResult = true
				toolInput.ToolCallID, _ = msgMap["tool_call_id"].(string)
				toolInput.ToolName, _ = msgMap["tool_name"].(string)
				toolInput.ToolResultJSON, _ = msgMap["result_json"].(string)
				toolInput.ToolIsError, _ = msgMap["is_error"].(bool)
				toolInput.ToolErrorMsg, _ = msgMap["error_message"].(string)
				toolInput.SessionID, _ = msgMap["session_id"].(string)

				if len(toolInput.ToolResultJSON) > maxToolResultLength {
					responder.SendError("invalid_argument", "Tool result too large", false)
					return false
				}

				span.SetAttributes(
					attribute.String("tool_call_id", toolInput.ToolCallID),
					attribute.String("tool_name", toolInput.ToolName),
				)
				return h.handleChatMessage(msgCtx, responder, userID, toolInput, envelope.RequestID)
			case "action_feedback":
				msgMap, err := decodePayloadMap(envelope.Payload["action_feedback"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid action_feedback payload", false)
					return false
				}
				h.handleActionFeedbackWithResponder(msgCtx, responder, msgMap, userID, authToken)
				return false
			case "focus_completed":
				msgMap, err := decodePayloadMap(envelope.Payload["focus_completed"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid focus_completed payload", false)
					return false
				}
				h.handleFocusCompleted(msgMap, userID, authToken)
				return false
			case "update_node_mastery":
				msgMap, err := decodePayloadMap(envelope.Payload["update_node_mastery"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid update_node_mastery payload", false)
					return false
				}
				h.handleUpdateNodeMasteryWithResponder(msgCtx, responder, msgMap, userID)
				return false
			case "intervention_feedback":
				msgMap, err := decodePayloadMap(envelope.Payload["intervention_feedback"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid intervention_feedback payload", false)
					return false
				}
				h.handleInterventionFeedbackWithResponder(responder, msgMap, userID, authToken)
				return false
			case "response_feedback":
				msgMap, err := decodePayloadMap(envelope.Payload["response_feedback"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid response_feedback payload", false)
					return false
				}
				h.handleResponseFeedbackWithResponder(msgCtx, responder, msgMap, userID)
				return false
			case "plan_review_feedback":
				msgMap, err := decodePayloadMap(envelope.Payload["plan_review_feedback"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid plan_review_feedback payload", false)
					return false
				}
				h.handlePlanReviewFeedbackWithResponder(msgCtx, responder, msgMap, userID)
				return false
			default:
				responder.SendError("invalid_argument", "Unknown payload type", false)
				return false
			}
		}()
		if shouldClose {
			return
		}
	}

	log.Printf("WebSocket disconnected for user: %s", userID)
}

// PushIntervention sends an intervention push message to all active WebSocket connections for a user.
func (h *ChatOrchestrator) PushIntervention(userID string, intervention *pbws.InterventionPushMessage) error {
	if h.wsRegistry == nil {
		return fmt.Errorf("no active WebSocket connection for user %s", userID)
	}

	message := map[string]interface{}{
		"type":            "intervention_push",
		"intervention_id": intervention.InterventionId,
		"level":           intervention.Level,
		"content": map[string]interface{}{
			"rendered_message":  intervention.Content.GetRenderedMessage(),
			"intent_type":       intervention.Content.GetIntentType(),
			"template_id":       intervention.Content.GetTemplateId(),
			"scaffolding_level": intervention.Content.GetScaffoldingLevel(),
			"context_variables": intervention.Content.GetContextVariables(),
		},
		"actions":    convertInterventionActions(intervention.Actions),
		"expires_at": intervention.ExpiresAt,
	}

	sent, failed := h.wsRegistry.BroadcastToUser(userID, message)
	for _, conn := range failed {
		h.unregisterConnection(userID, conn)
	}
	if sent == 0 {
		return fmt.Errorf("no active WebSocket connection for user %s", userID)
	}
	return nil
}

func convertInterventionActions(actions []*pbws.InterventionAction) []map[string]interface{} {
	result := make([]map[string]interface{}, len(actions))
	for i, action := range actions {
		result[i] = map[string]interface{}{
			"id":    action.Id,
			"label": action.Label,
			"type":  action.Type,
		}
	}
	return result
}
