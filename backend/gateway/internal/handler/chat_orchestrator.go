package handler

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/microcosm-cc/bluemonday"
	pbws "github.com/sparkle/gateway/gen/ws"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/galaxy"
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
	Message           string                 `json:"message"`
	SessionID         string                 `json:"session_id"`
	Nickname          string                 `json:"nickname,omitempty"`
	FileIds           []string               `json:"file_ids,omitempty"`
	IncludeReferences bool                   `json:"include_references,omitempty"`
	ExtraContext      map[string]interface{} `json:"extra_context,omitempty"`
	ChatMode          string                 `json:"chat_mode,omitempty"`
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
	c.Nickname = ""
	c.FileIds = nil
	c.IncludeReferences = false
	c.ExtraContext = nil
	c.ChatMode = ""
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
		wsRegistry: NewConnectionRegistry(signalHub, ch),
	}
}

func (h *ChatOrchestrator) HandleWebSocket(c *gin.Context) {
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
	defer func() {
		_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
		_ = conn.Close()
	}()

	// Require authenticated user_id from context (must be set by AuthMiddleware)
	userID := c.GetString("user_id")
	if userID == "" {
		// Fallback: Try query parameter (for Guest mode or WebSocket upgrade requests where headers might be stripped)
		userID = c.Query("user_id")
	}

	if userID == "" {
		log.Printf("WebSocket rejected: missing authentication")
		conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseUnsupportedData, "Authentication required"))
		_ = conn.Close() // Explicitly close rejected connection
		return
	}
	authToken := c.GetString("auth_token")
	if authToken == "" {
		authToken = c.Query("token")
	}

	log.Printf("WebSocket connected for user: %s", userID)
	authMethod := c.GetString("ws_auth_method")
	if authMethod == "" {
		authMethod = "unknown"
	}
	metrics.WSConnectionSuccess.WithLabelValues("/ws/chat", authMethod).Inc()
	h.registerConnection(userID, conn)
	defer h.unregisterConnection(userID, conn)

	readLimit := int64(0)
	msgRate := 0.0
	msgBurst := 0
	if h.cfg != nil {
		readLimit = h.cfg.WSMaxMessageBytes
		msgRate = h.cfg.WSMessageRateRPS
		msgBurst = h.cfg.WSMessageRateBurst
	}
	if readLimit > 0 {
		conn.SetReadLimit(readLimit)
	}
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
				_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message too large"))
			}
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		if !msgLimiter.Allow() {
			_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message rate limit exceeded"))
			break
		}

		// P2: Support Binary Protobuf Protocol
		if msgType == websocket.BinaryMessage {
			h.handleProtobufMessage(conn, msg, userID, tracer, c.Request.Context())
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
					conn.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
					return false
				}

				msgType, ok := msgMap["type"].(string)
				if !ok {
					msgType = "message" // Default to chat message
				}

				// Route based on message type
				switch msgType {
				case "ping":
					conn.WriteJSON(gin.H{"type": "pong"})
					return false
				case "action_feedback":
					h.handleActionFeedback(conn, msgMap, userID, authToken)
					return false
				case "intervention_feedback":
					h.handleInterventionFeedback(conn, msgMap, userID, authToken)
					return false
				case "response_feedback":
					h.handleResponseFeedback(conn, msgMap, userID, c.Request.Context())
					return false
				case "plan_review_feedback":
					h.handlePlanReviewFeedback(conn, msgMap, userID, c.Request.Context())
					return false
				case "focus_completed":
					h.handleFocusCompleted(msgMap, userID, authToken)
					return false
				case "update_node_mastery":
					h.handleUpdateNodeMastery(conn, msgMap, userID)
					return false
				case "message", "":
					// Continue with normal chat message handling
				default:
					log.Printf("Unknown message type: %s", msgType)
					conn.WriteJSON(gin.H{"type": "error", "message": "Unknown message type"})
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
					conn.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
					return false
				}

				if input.Message == "" {
					conn.WriteJSON(gin.H{"type": "error", "message": "Empty message"})
					return false
				}

				// 🔧 P1-2: 消息长度检查
				if len(input.Message) > maxMessageLength {
					conn.WriteJSON(gin.H{
						"type":    "error",
						"message": fmt.Sprintf("消息长度超过 %d 字符限制", maxMessageLength),
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

				return h.handleChatMessage(ctx, conn, userID, input, "")
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

			responder := newEnvelopeResponder(conn, envelope, msgCtx)
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
						fmt.Sprintf("消息长度超过 %d 字符限制", maxMessageLength), false)
					return false
				}

				return h.handleChatMessage(msgCtx, responder, userID, input, envelope.RequestID)
			case "action_feedback":
				msgMap, err := decodePayloadMap(envelope.Payload["action_feedback"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid action_feedback payload", false)
					return false
				}
				h.handleActionFeedbackWithResponder(responder, msgMap, userID, authToken)
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
				h.handleUpdateNodeMasteryWithResponder(responder, msgMap, userID)
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

// PushIntervention sends an intervention push message to a connected WebSocket client.
func (h *ChatOrchestrator) PushIntervention(userID string, intervention *pbws.InterventionPushMessage) error {
	conn, exists := h.getConnection(userID)
	if !exists {
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

	if err := conn.WriteJSON(message); err != nil {
		h.unregisterConnection(userID, conn)
		return fmt.Errorf("failed to send intervention: %w", err)
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
