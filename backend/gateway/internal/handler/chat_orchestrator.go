package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/microcosm-cc/bluemonday"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/galaxy"
	"github.com/sparkle/gateway/internal/service"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/types/known/structpb"
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
}

// stringBuilderPool reuses string builders for text accumulation
var stringBuilderPool = sync.Pool{
	New: func() interface{} {
		return &strings.Builder{}
	},
}

// sanitizerPool reuses bluemonday policies (they are thread-safe once created)
var sanitizer = bluemonday.UGCPolicy()

type ChatOrchestrator struct {
	agentClient  *agent.Client
	galaxyClient *galaxy.Client
	queries      *db.Queries
	chatHistory  *service.ChatHistoryService
	quota        *service.QuotaService
	semantic     *service.SemanticCacheService
	billing      *service.CostCalculator
	wsFactory    *WebSocketFactory
	userContext  *service.UserContextService
	taskCommand  *service.TaskCommandService
	backendURL   string
	httpClient   *http.Client
}

func NewChatOrchestrator(ac *agent.Client, gc *galaxy.Client, q *db.Queries, ch *service.ChatHistoryService, qs *service.QuotaService, sc *service.SemanticCacheService, bc *service.CostCalculator, wsFactory *WebSocketFactory, uc *service.UserContextService, tc *service.TaskCommandService, backendURL string) *ChatOrchestrator {
	return &ChatOrchestrator{
		agentClient:  ac,
		galaxyClient: gc,
		queries:      q,
		chatHistory:  ch,
		quota:        qs,
		semantic:     sc,
		billing:      bc,
		wsFactory:    wsFactory,
		userContext:  uc,
		taskCommand:  tc,
		backendURL:   strings.TrimRight(backendURL, "/"),
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

func (h *ChatOrchestrator) HandleWebSocket(c *gin.Context) {
	// Use WebSocketFactory for secure origin checking
	var upgrader websocket.Upgrader
	if h.wsFactory != nil {
		upgrader = h.wsFactory.CreateUpgrader()
	} else {
		// Fallback to development upgrader (for backward compatibility)
		upgrader = DefaultUpgrader()
		log.Printf("[WARNING] Using development WebSocket upgrader - configure WebSocketFactory for production")
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("Failed to upgrade WS: %v", err)
		return
	}
	defer conn.Close()

	// Require authenticated user_id from context (must be set by AuthMiddleware)
	userID := c.GetString("user_id")
	if userID == "" {
		log.Printf("WebSocket rejected: missing authentication")
		conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseUnsupportedData, "Authentication required"))
		_ = conn.Close() // Explicitly close rejected connection
		return
	}
	authToken := c.GetString("auth_token")

	log.Printf("WebSocket connected for user: %s", userID)

	tracer := otel.Tracer("chat-orchestrator")

	// Message handling loop: each WebSocket message triggers a new StreamChat call
	for {
		// Read message from WebSocket client
		_, msg, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
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
				case "action_feedback":
					h.handleActionFeedback(conn, msgMap, userID)
					return false
				case "intervention_feedback":
					h.handleInterventionFeedback(conn, msgMap, userID, authToken)
					return false
				case "focus_completed":
					h.handleFocusCompleted(msgMap, userID)
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

				ctx, span := tracer.Start(c.Request.Context(), "HandleMessage")
				span.SetAttributes(
					attribute.String("user_id", userID),
					attribute.String("session_id", input.SessionID),
				)
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
				return h.handleChatMessage(msgCtx, responder, userID, input, envelope.RequestID)
			case "action_feedback":
				msgMap, err := decodePayloadMap(envelope.Payload["action_feedback"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid action_feedback payload", false)
					return false
				}
				h.handleActionFeedbackWithResponder(responder, msgMap, userID)
				return false
			case "focus_completed":
				msgMap, err := decodePayloadMap(envelope.Payload["focus_completed"])
				if err != nil {
					responder.SendError("invalid_argument", "Invalid focus_completed payload", false)
					return false
				}
				h.handleFocusCompleted(msgMap, userID)
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

// convertResponseToJSON converts protobuf ChatResponse to JSON-serializable map
func convertResponseToJSON(resp *agentv1.ChatResponse) map[string]interface{} {
	result := map[string]interface{}{
		"response_id": resp.ResponseId,
		"created_at":  resp.CreatedAt,
		"request_id":  resp.RequestId,
	}

	// Handle oneof content field
	switch content := resp.Content.(type) {
	case *agentv1.ChatResponse_Delta:
		result["type"] = "delta"
		result["delta"] = content.Delta
	case *agentv1.ChatResponse_ToolCall:
		result["type"] = "tool_call"
		result["tool_call"] = map[string]interface{}{
			"id":        content.ToolCall.Id,
			"name":      content.ToolCall.Name,
			"arguments": content.ToolCall.Arguments,
		}
	case *agentv1.ChatResponse_StatusUpdate:
		result["type"] = "status_update"
		result["status"] = map[string]interface{}{
			"state":   content.StatusUpdate.State.String(),
			"details": content.StatusUpdate.Details,
		}
	case *agentv1.ChatResponse_FullText:
		result["type"] = "full_text"
		result["full_text"] = content.FullText
	case *agentv1.ChatResponse_Error:
		result["type"] = "error"
		result["error"] = map[string]interface{}{
			"code":      content.Error.Code,
			"message":   content.Error.Message,
			"retryable": content.Error.Retryable,
		}
	case *agentv1.ChatResponse_Usage:
		result["type"] = "usage"
		result["usage"] = map[string]interface{}{
			"prompt_tokens":     content.Usage.PromptTokens,
			"completion_tokens": content.Usage.CompletionTokens,
			"total_tokens":      content.Usage.TotalTokens,
		}
	case *agentv1.ChatResponse_Citations:
		result["type"] = "citations"
		citations := make([]map[string]interface{}, len(content.Citations.Citations))
		for i, c := range content.Citations.Citations {
			citations[i] = map[string]interface{}{
				"id":            c.Id,
				"title":         c.Title,
				"content":       c.Content,
				"source_type":   c.SourceType,
				"score":         c.Score,
				"url":           c.Url,
				"file_id":       c.FileId,
				"page_number":   c.PageNumber,
				"chunk_index":   c.ChunkIndex,
				"section_title": c.SectionTitle,
			}
		}
		result["citations"] = citations
	case *agentv1.ChatResponse_ToolResult:
		result["type"] = "tool_result"
		tool := content.ToolResult
		data := map[string]interface{}{}
		if tool.Data != nil {
			data = tool.Data.AsMap()
		}
		widgetData := map[string]interface{}{}
		if tool.WidgetData != nil {
			widgetData = tool.WidgetData.AsMap()
		}
		result["tool_result"] = map[string]interface{}{
			"tool_name":     tool.ToolName,
			"success":       tool.Success,
			"data":          data,
			"error_message": tool.ErrorMessage,
			"suggestion":    tool.Suggestion,
			"widget_type":   tool.WidgetType,
			"widget_data":   widgetData,
			"tool_call_id":  tool.ToolCallId,
		}
	case *agentv1.ChatResponse_Intervention:
		result["type"] = "intervention"
		payload := content.Intervention
		req := payload.GetRequest()
		intervention := map[string]interface{}{}
		if req != nil {
			reason := map[string]interface{}{}
			if req.Reason != nil {
				evidence := make([]map[string]interface{}, 0, len(req.Reason.EvidenceRefs))
				for _, ref := range req.Reason.EvidenceRefs {
					evidence = append(evidence, map[string]interface{}{
						"type":           ref.Type,
						"id":             ref.Id,
						"schema_version": ref.SchemaVersion,
						"user_deleted":   ref.UserDeleted,
					})
				}
				reason = map[string]interface{}{
					"trigger_event_id": req.Reason.TriggerEventId,
					"explanation_text": req.Reason.ExplanationText,
					"confidence":       req.Reason.Confidence,
					"evidence_refs":    evidence,
					"decision_trace":   req.Reason.DecisionTrace,
				}
			}
			contentMap := map[string]interface{}{}
			if req.Content != nil {
				contentMap = req.Content.AsMap()
			}
			cooldown := map[string]interface{}{}
			if req.OnReject != nil {
				cooldown = map[string]interface{}{
					"policy":   req.OnReject.Policy,
					"until_ms": req.OnReject.UntilMs,
				}
			}
			intervention = map[string]interface{}{
				"id":              req.Id,
				"dedupe_key":      req.DedupeKey,
				"topic":           req.Topic,
				"created_at_ms":   req.CreatedAtMs,
				"expires_at_ms":   req.ExpiresAtMs,
				"is_retractable":  req.IsRetractable,
				"supersedes_id":   req.SupersedesId,
				"schema_version":  req.SchemaVersion,
				"policy_version":  req.PolicyVersion,
				"model_version":   req.ModelVersion,
				"reason":          reason,
				"level":           req.Level.String(),
				"on_reject":       cooldown,
				"content":         contentMap,
			}
		}
		result["intervention"] = intervention
	}

	if resp.FinishReason != agentv1.FinishReason_NULL {
		result["finish_reason"] = resp.FinishReason.String()
	}

	return result
}

type envelopeResponder struct {
	conn     *websocket.Conn
	envelope *wsEnvelopeIn
	ctx      context.Context
}

func newEnvelopeResponder(conn *websocket.Conn, env *wsEnvelopeIn, ctx context.Context) *envelopeResponder {
	return &envelopeResponder{
		conn:     conn,
		envelope: env,
		ctx:      ctx,
	}
}

func (r *envelopeResponder) SendAck() {
	traceparent := traceparentFromContext(r.ctx)
	payload := map[string]json.RawMessage{}
	ack := map[string]interface{}{
		"request_id": r.envelope.RequestID,
		"server_ts":  time.Now().UnixMilli(),
		"traceparent": traceparent,
	}
	raw, err := json.Marshal(ack)
	if err != nil {
		log.Printf("Failed to encode ack: %v", err)
		return
	}
	payload["ack"] = raw
	if err := r.writeEnvelope(payload, traceparent); err != nil {
		log.Printf("Failed to send ack: %v", err)
	}
}

func (r *envelopeResponder) SendError(code, message string, retryable bool) {
	payload := map[string]json.RawMessage{}
	errBody := map[string]interface{}{
		"code":      code,
		"message":   message,
		"retryable": retryable,
	}
	raw, err := json.Marshal(errBody)
	if err != nil {
		log.Printf("Failed to encode error: %v", err)
		return
	}
	payload["error"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send error: %v", err)
	}
}

func (r *envelopeResponder) SendActionStatus(actionID, status string, data map[string]interface{}) {
	payload := map[string]json.RawMessage{}
	statusMsg := map[string]interface{}{
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	raw, err := json.Marshal(statusMsg)
	if err != nil {
		log.Printf("Failed to encode action status: %v", err)
		return
	}
	payload["action_status"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send action status: %v", err)
	}
}

func (r *envelopeResponder) SendInterventionAck(requestID, status, message string) {
	payload := map[string]json.RawMessage{}
	ack := map[string]interface{}{
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		ack["message"] = message
	}
	raw, err := json.Marshal(ack)
	if err != nil {
		log.Printf("Failed to encode intervention ack: %v", err)
		return
	}
	payload["intervention_feedback_ack"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send intervention ack: %v", err)
	}
}

func (r *envelopeResponder) SendUpdateNodeMasteryAck(nodeID, version string, success bool) {
	payload := map[string]json.RawMessage{}
	body := map[string]interface{}{
		"node_id":   nodeID,
		"version":   version,
		"success":   success,
		"timestamp": time.Now().Unix(),
	}
	raw, err := json.Marshal(body)
	if err != nil {
		log.Printf("Failed to encode mastery ack: %v", err)
		return
	}
	payload["ack_update_node_mastery"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send mastery ack: %v", err)
	}
}

func (r *envelopeResponder) SendUpdateNodeError(nodeID, version, message string) {
	payload := map[string]json.RawMessage{}
	body := map[string]interface{}{
		"nodeId":  nodeID,
		"version": version,
		"error":   message,
	}
	raw, err := json.Marshal(body)
	if err != nil {
		log.Printf("Failed to encode mastery error: %v", err)
		return
	}
	payload["error_update_node_mastery"] = raw
	if err := r.writeEnvelope(payload, traceparentFromContext(r.ctx)); err != nil {
		log.Printf("Failed to send mastery error: %v", err)
	}
}

func (r *envelopeResponder) SendChatResponse(resp *agentv1.ChatResponse) error {
	raw, err := protojson.Marshal(resp)
	if err != nil {
		return err
	}
	payload := map[string]json.RawMessage{
		"chat_response": raw,
	}
	return r.writeEnvelope(payload, traceparentFromContext(r.ctx))
}

func (r *envelopeResponder) SendMeta(meta map[string]interface{}) error {
	raw, err := json.Marshal(meta)
	if err != nil {
		return err
	}
	payload := map[string]json.RawMessage{
		"meta": raw,
	}
	return r.writeEnvelope(payload, traceparentFromContext(r.ctx))
}

func (r *envelopeResponder) writeEnvelope(payload map[string]json.RawMessage, traceparent string) error {
	envOut := wsEnvelopeOut{
		Traceparent: traceparent,
		MessageID:   r.envelope.MessageID,
		RequestID:   r.envelope.RequestID,
		Payload:     payload,
	}
	data, err := json.Marshal(envOut)
	if err != nil {
		return err
	}
	return r.conn.WriteMessage(websocket.TextMessage, data)
}

func parseEnvelopeJSON(msg []byte) (*wsEnvelopeIn, bool) {
	raw := map[string]json.RawMessage{}
	if err := json.Unmarshal(msg, &raw); err != nil {
		return nil, false
	}
	payloadRaw, ok := raw["payload"]
	if !ok {
		return nil, false
	}
	payload := map[string]json.RawMessage{}
	if err := json.Unmarshal(payloadRaw, &payload); err != nil {
		return nil, false
	}
	if len(payload) == 0 {
		return nil, false
	}
	env := &wsEnvelopeIn{}
	if err := json.Unmarshal(msg, env); err != nil {
		return nil, false
	}
	env.Payload = payload
	env.Raw = raw
	return env, true
}

func envelopePayloadType(payload map[string]json.RawMessage) string {
	switch {
	case payload["chat_request"] != nil:
		return "chat_request"
	case payload["action_feedback"] != nil:
		return "action_feedback"
	case payload["focus_completed"] != nil:
		return "focus_completed"
	case payload["update_node_mastery"] != nil:
		return "update_node_mastery"
	case payload["intervention_feedback"] != nil:
		return "intervention_feedback"
	default:
		return ""
	}
}

func decodePayloadMap(raw json.RawMessage) (map[string]interface{}, error) {
	msgMap := make(map[string]interface{})
	if err := json.Unmarshal(raw, &msgMap); err != nil {
		return nil, err
	}
	return msgMap, nil
}

func decodeChatRequestEnvelope(raw json.RawMessage, input *chatInput) error {
	var req agentv1.ChatRequest
	if err := protojson.Unmarshal(raw, &req); err != nil {
		return err
	}
	switch content := req.GetInput().(type) {
	case *agentv1.ChatRequest_Message:
		input.Message = content.Message
	default:
		return fmt.Errorf("unsupported chat_request input")
	}
	input.SessionID = req.GetSessionId()
	input.Nickname = req.GetUserProfile().GetNickname()
	input.FileIds = req.GetFileIds()
	input.IncludeReferences = req.GetIncludeReferences()
	if extra := req.GetExtraContext(); extra != nil {
		input.ExtraContext = extra.AsMap()
	}
	return nil
}

func extractTraceContextFromEnvelope(ctx context.Context, env *wsEnvelopeIn) context.Context {
	if env.Traceparent == "" {
		return ctx
	}
	if len(env.Traceparent) > maxTraceparentLen || len(env.Tracestate) > maxTracestateLen {
		return ctx
	}
	carrier := propagation.MapCarrier{
		"traceparent": env.Traceparent,
	}
	if env.Tracestate != "" {
		carrier["tracestate"] = env.Tracestate
	}
	return otel.GetTextMapPropagator().Extract(ctx, carrier)
}

func traceparentFromContext(ctx context.Context) string {
	carrier := propagation.MapCarrier{}
	otel.GetTextMapPropagator().Inject(ctx, carrier)
	return carrier["traceparent"]
}

func generateMessageID() string {
	id := uuid.New()
	return "msg_" + strings.ReplaceAll(id.String(), "-", "")
}

func generateRequestID() string {
	id := uuid.New()
	return "req_" + strings.ReplaceAll(id.String(), "-", "")
}

func (h *ChatOrchestrator) handleChatMessage(ctx context.Context, responder interface{}, userID string, input *chatInput, requestID string) bool {
	span := trace.SpanFromContext(ctx)
	span.SetAttributes(
		attribute.String("session_id", input.SessionID),
	)

	// Sanitize Input (Security Hygiene) - reuse global sanitizer
	input.Message = sanitizer.Sanitize(input.Message)

	// Persist user message to Redis history for context pruning
	if input.SessionID != "" {
		sessionID := input.SessionID
		message := input.Message
		go h.saveMessage(userID, sessionID, "user", message)
	}

	// Canonicalize Input (Semantic Cache Prep)
	_ = h.semantic.Canonicalize(input.Message)
	// TODO: Use canonicalized input for semantic search or caching in future

	startTime := time.Now()

	// P0: Fetch user context (pending tasks, active plans, focus stats, recent progress)
	userContextJSON := ""
	var contextFetchLatency time.Duration
	if h.userContext != nil {
		contextFetchStart := time.Now()
		contextData, err := h.userContext.GetUserContextData(ctx, uuid.MustParse(userID))
		contextFetchLatency = time.Since(contextFetchStart)

		if err != nil {
			log.Printf("[CONTEXT] Failed to fetch user context for user=%s, latency=%dms, error=%v",
				userID, contextFetchLatency.Milliseconds(), err)
			// Non-fatal: continue with empty context
		} else {
			userContextJSON = contextData
			// P0.4: Enhanced logging for context injection validation
			var contextMap map[string]interface{}
			if jsonErr := json.Unmarshal([]byte(userContextJSON), &contextMap); jsonErr == nil {
				pendingTasksCount := 0
				activePlansCount := 0
				focusMinutes := 0
				recentProgressCount := 0

				if tasks, ok := contextMap["pending_tasks"].([]interface{}); ok {
					pendingTasksCount = len(tasks)
				}
				if plans, ok := contextMap["active_plans"].([]interface{}); ok {
					activePlansCount = len(plans)
				}
				if stats, ok := contextMap["focus_stats"].(map[string]interface{}); ok {
					if mins, ok := stats["total_minutes_today"].(float64); ok {
						focusMinutes = int(mins)
					}
				}
				if progress, ok := contextMap["recent_progress"].([]interface{}); ok {
					recentProgressCount = len(progress)
				}

				log.Printf("[CONTEXT] User=%s, PendingTasks=%d, ActivePlans=%d, FocusMinutes=%dm, RecentProgress=%d, Size=%dB, Latency=%dms",
					userID, pendingTasksCount, activePlansCount, focusMinutes, recentProgressCount,
					len(userContextJSON), contextFetchLatency.Milliseconds())
			} else {
				log.Printf("[CONTEXT] User=%s, Size=%dB, Latency=%dms (JSON parse error: %v)",
					userID, len(userContextJSON), contextFetchLatency.Milliseconds(), jsonErr)
			}
		}
	}

	reqID := requestID
	if reqID == "" {
		reqID = fmt.Sprintf("req_%s", uuid.New().String())
	}

	// Build ChatRequest
	req := &agentv1.ChatRequest{
		RequestId: reqID,
		UserId:    userID,
		SessionId: input.SessionID,
		Input: &agentv1.ChatRequest_Message{
			Message: input.Message,
		},
		FileIds:           input.FileIds,
		IncludeReferences: input.IncludeReferences,
		UserProfile: &agentv1.UserProfile{
			Nickname:     input.Nickname,
			Timezone:     "Asia/Shanghai",
			Language:     "zh-CN",
			ExtraContext: userContextJSON, // P0: Inject user context here
		},
	}
	if input.ExtraContext != nil {
		if extra, err := structpb.NewStruct(input.ExtraContext); err == nil {
			req.ExtraContext = extra
		}
	}

	// Call Python Agent via gRPC (server-side streaming)
	stream, err := h.agentClient.StreamChat(ctx, req)
	if err != nil {
		log.Printf("Failed to call StreamChat: %v", err)
		switch r := responder.(type) {
		case *envelopeResponder:
			r.SendError("unavailable", "AI Service Unavailable", true)
		default:
			conn := responder.(*websocket.Conn)
			conn.WriteJSON(gin.H{"type": "error", "message": "AI Service Unavailable"})
		}
		return false
	}

	// P1: Get string builder from pool for efficient text accumulation
	textBuilder := stringBuilderPool.Get().(*strings.Builder)
	textBuilder.Reset()
	defer func() {
		textBuilder.Reset()
		stringBuilderPool.Put(textBuilder)
	}()

	// Receive and forward streaming responses
	var fullText string
	for {
		resp, err := stream.Recv()
		if err == io.EOF {
			// Stream ended normally
			break
		}
		if err != nil {
			log.Printf("Stream recv error: %v", err)
			switch r := responder.(type) {
			case *envelopeResponder:
				r.SendError("aborted", "Stream interrupted", true)
			default:
				conn := responder.(*websocket.Conn)
				conn.WriteJSON(gin.H{"type": "error", "message": "Stream interrupted"})
			}
			break
		}

		// Accumulate full text for persistence using pooled builder
		if delta := resp.GetDelta(); delta != "" {
			textBuilder.WriteString(delta)
		}
		if ft := resp.GetFullText(); ft != "" {
			textBuilder.Reset()
			textBuilder.WriteString(ft)
		}

		switch r := responder.(type) {
		case *envelopeResponder:
			if err := r.SendChatResponse(resp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				return true
			}
		default:
			conn := responder.(*websocket.Conn)
			// Convert protobuf response to JSON-friendly map
			jsonResp := convertResponseToJSON(resp)
			// Forward to WebSocket client
			if err := conn.WriteJSON(jsonResp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				return true
			}
		}
	}
	fullText = textBuilder.String()

	// Add metadata for the final state
	latency := time.Since(startTime).Milliseconds()
	qLen, _ := h.chatHistory.GetQueueLength(ctx)
	threshold := h.chatHistory.GetBreakerThreshold()

	meta := map[string]interface{}{
		"latency_ms":     latency,
		"is_cache_hit":   false, // Set to true if semantic cache hit (to be implemented)
		"cost_saved":     0.0,
		"breaker_status": "closed",
	}
	if qLen >= threshold {
		meta["breaker_status"] = "open"
	}

	switch r := responder.(type) {
	case *envelopeResponder:
		_ = r.SendMeta(meta)
	default:
		conn := responder.(*websocket.Conn)
		// Send final metadata
		conn.WriteJSON(gin.H{
			"type": "meta",
			"meta": meta,
		})
	}

	// Persist completed message to database (async)
	if fullText != "" && input.SessionID != "" {
		// Capture values for goroutine before returning input to pool
		sessionID := input.SessionID
		result := fullText
		go h.saveMessage(userID, sessionID, "assistant", result)

		// Also decrement quota (async)
		go func(uid string) {
			if _, err := h.quota.DecrQuota(context.Background(), uid); err != nil {
				log.Printf("Failed to decrement quota: %v", err)
			}
		}(userID)
	}

	return false
}

type actionStatusSender interface {
	SendActionStatus(actionID, status string, data map[string]interface{})
}

type updateNodeResponder interface {
	SendUpdateNodeError(nodeID, version, message string)
	SendUpdateNodeMasteryAck(nodeID, version string, success bool)
}

type interventionResponder interface {
	SendInterventionAck(requestID, status, message string)
}

// saveMessage persists a chat message to the database
func (h *ChatOrchestrator) saveMessage(userID, sessionID, role, content string) {
	payload := map[string]string{
		"session_id": sessionID,
		"user_id":    userID,
		"role":       role,
		"content":    content,
		"timestamp":  fmt.Sprintf("%d", time.Now().Unix()),
	}
	data, _ := json.Marshal(payload)

	ctx := context.Background()
	// Use the new reliable double-write mechanism
	if err := h.chatHistory.SaveMessage(ctx, sessionID, data); err != nil {
		log.Printf("Failed to save chat message: %v", err)
	}
}

type legacyActionStatusSender struct {
	conn *websocket.Conn
}

func (s legacyActionStatusSender) SendActionStatus(actionID, status string, data map[string]interface{}) {
	statusMsg := map[string]interface{}{
		"type":      "action_status",
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}
	for k, v := range data {
		statusMsg[k] = v
	}
	if err := s.conn.WriteJSON(statusMsg); err != nil {
		log.Printf("Failed to send action status: %v", err)
	} else {
		log.Printf("✅ Action status sent: status=%s, action_id=%s", status, actionID)
	}
}

type legacyUpdateNodeResponder struct {
	conn *websocket.Conn
}

func (s legacyUpdateNodeResponder) SendUpdateNodeError(nodeID, version, message string) {
	s.conn.WriteJSON(map[string]interface{}{
		"type": "error_update_node_mastery",
		"payload": map[string]interface{}{
			"nodeId":  nodeID,
			"version": version,
			"error":   message,
		},
	})
}

func (s legacyUpdateNodeResponder) SendUpdateNodeMasteryAck(nodeID, version string, success bool) {
	s.conn.WriteJSON(map[string]interface{}{
		"type": "ack_update_node_mastery",
		"payload": map[string]interface{}{
			"node_id":   nodeID,
			"version":   version,
			"success":   success,
			"timestamp": time.Now().Unix(),
		},
	})
}

type legacyInterventionResponder struct {
	conn *websocket.Conn
}

func (s legacyInterventionResponder) SendInterventionAck(requestID, status, message string) {
	payload := map[string]interface{}{
		"type":       "intervention_feedback_ack",
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		payload["message"] = message
	}
	if err := s.conn.WriteJSON(payload); err != nil {
		log.Printf("Failed to send intervention feedback ack: %v", err)
	}
}

func (h *ChatOrchestrator) handleActionFeedbackWithResponder(sender actionStatusSender, msgMap map[string]interface{}, userID string) {
	action, ok := msgMap["action"].(string)
	if !ok {
		log.Printf("Invalid action feedback: missing action field")
		return
	}

	toolResultID, ok := msgMap["tool_result_id"].(string)
	if !ok {
		log.Printf("Invalid action feedback: missing tool_result_id field")
		return
	}

	widgetType, ok := msgMap["widget_type"].(string)
	if !ok {
		log.Printf("Invalid action feedback: missing widget_type field")
		return
	}

	log.Printf("Action feedback from user %s: action=%s, widget_type=%s, tool_result_id=%s",
		userID, action, widgetType, toolResultID)

	// Parse user ID
	userUUID, err := uuid.Parse(userID)
	if err != nil {
		log.Printf("Invalid user ID in action feedback: %v", err)
		return
	}

	// Route feedback to appropriate service handler
	switch widgetType {
	case "task_list", "create_task":
		if action == "confirm" {
			// Handle task list confirmation (tasks were created)
			log.Printf("Task list creation confirmed for user %s, tool_result_id=%s", userID, toolResultID)

			// [P0.1 FIX]: Call TaskCommand to confirm tasks in database
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()

			err := h.taskCommand.ConfirmGeneratedTasks(ctx, userUUID, toolResultID)
			if err != nil {
				log.Printf("❌ Failed to confirm tasks for user %s: %v", userID, err)
				sender.SendActionStatus(toolResultID, "failed", map[string]interface{}{
					"message": "确认失败，请重试",
				})
				return
			}

			// Send confirmation status back to client
			sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
				"message":     "任务已确认",
				"widget_type": widgetType,
			})
		} else if action == "dismiss" {
			// Handle task list dismissal (user rejected generated tasks)
			log.Printf("Task list creation dismissed by user %s", userID)

			// TODO: In future, could mark tasks as rejected in DB
			// For now, just send status update
			sender.SendActionStatus(toolResultID, "dismissed", map[string]interface{}{
				"message":     "任务已忽略",
				"widget_type": widgetType,
			})
		}

	case "plan_card", "create_plan":
		if action == "confirm" {
			// Handle plan confirmation
			log.Printf("Plan creation confirmed for user %s", userID)

			sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
				"message":     "计划已确认",
				"widget_type": widgetType,
			})
		} else if action == "dismiss" {
			log.Printf("Plan creation dismissed by user %s", userID)

			sender.SendActionStatus(toolResultID, "dismissed", map[string]interface{}{
				"message":     "计划已忽略",
				"widget_type": widgetType,
			})
		}

	case "focus_card":
		if action == "confirm" {
			// Handle focus session start confirmation
			log.Printf("Focus session start confirmed for user %s", userID)

			sender.SendActionStatus(toolResultID, "confirmed", map[string]interface{}{
				"message":     "专注已开始",
				"widget_type": widgetType,
			})
		} else if action == "dismiss" {
			log.Printf("Focus session dismissed by user %s", userID)

			sender.SendActionStatus(toolResultID, "dismissed", map[string]interface{}{
				"message":     "专注已取消",
				"widget_type": widgetType,
			})
		}

	default:
		log.Printf("Unknown widget type in action feedback: %s", widgetType)
	}
}

func (h *ChatOrchestrator) handleUpdateNodeMasteryWithResponder(responder updateNodeResponder, msgMap map[string]interface{}, userID string) {
	payload, ok := msgMap["payload"].(map[string]interface{})
	if !ok {
		log.Printf("Invalid update_node_mastery: missing payload")
		return
	}

	nodeID, _ := payload["nodeId"].(string)
	mastery := int32(0)
	if v, ok := payload["mastery"].(float64); ok {
		mastery = int32(v)
	}
	versionStr, _ := payload["version"].(string)

	if nodeID == "" || versionStr == "" {
		log.Printf("Invalid update_node_mastery: missing fields")
		responder.SendUpdateNodeError(nodeID, versionStr, "Invalid payload")
		return
	}

	// Support flexible ISO8601 parsing (Dart toIso8601String format)
	var version time.Time
	var err error

	// Try multiple formats to be safe
	formats := []string{
		time.RFC3339Nano,
		"2006-01-02T15:04:05.999999999Z",
		"2006-01-02T15:04:05.999999",
		time.RFC3339,
	}

	for _, f := range formats {
		version, err = time.Parse(f, versionStr)
		if err == nil {
			break
		}
	}

	if err != nil {
		log.Printf("Invalid version format: %s", versionStr)
		responder.SendUpdateNodeError(nodeID, versionStr, "Invalid timestamp format")
		return
	}

	log.Printf("Received mastery update for user %s, node %s, mastery %d, version %s", userID, nodeID, mastery, versionStr)

	// Call Python Backend via gRPC
	if h.galaxyClient == nil {
		log.Printf("Galaxy gRPC client not initialized")
		responder.SendUpdateNodeError(nodeID, versionStr, "Internal service error")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	resp, err := h.galaxyClient.UpdateNodeMastery(ctx, userID, nodeID, mastery, version, "offline_sync")

	if err != nil {
		log.Printf("gRPC mastery update failed: %v", err)
		responder.SendUpdateNodeError(nodeID, versionStr, "Sync service unavailable")
		return
	}

	if resp.Success {
		responder.SendUpdateNodeMasteryAck(nodeID, versionStr, true)
	} else {
		responder.SendUpdateNodeError(nodeID, versionStr, resp.Reason)
	}
}

func (h *ChatOrchestrator) handleInterventionFeedbackWithResponder(responder interventionResponder, msgMap map[string]interface{}, userID, authToken string) {
	requestID, ok := msgMap["request_id"].(string)
	if !ok || requestID == "" {
		log.Printf("Invalid intervention_feedback: missing request_id")
		responder.SendInterventionAck("", "failed", "missing request_id")
		return
	}

	feedbackType, ok := msgMap["feedback_type"].(string)
	if !ok || feedbackType == "" {
		log.Printf("Invalid intervention_feedback: missing feedback_type")
		responder.SendInterventionAck(requestID, "failed", "missing feedback_type")
		return
	}

	metadata := map[string]interface{}{}
	if raw, ok := msgMap["metadata"].(map[string]interface{}); ok {
		metadata = raw
	}

	if h.backendURL == "" || authToken == "" {
		log.Printf("Intervention feedback rejected: backendURL or auth token missing")
		responder.SendInterventionAck(requestID, "failed", "backend unavailable")
		return
	}

	payload := map[string]interface{}{
		"feedback_type": feedbackType,
		"metadata":      metadata,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Failed to marshal intervention feedback: %v", err)
		responder.SendInterventionAck(requestID, "failed", "invalid payload")
		return
	}

	endpoint := fmt.Sprintf("%s/api/v1/interventions/requests/%s/feedback", h.backendURL, requestID)
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		log.Printf("Failed to build intervention feedback request: %v", err)
		responder.SendInterventionAck(requestID, "failed", "request error")
		return
	}
	req.Header.Set("Authorization", "Bearer "+authToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.httpClient.Do(req)
	if err != nil {
		log.Printf("Failed to send intervention feedback: %v", err)
		responder.SendInterventionAck(requestID, "failed", "network error")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		log.Printf("Intervention feedback rejected: status=%d", resp.StatusCode)
		responder.SendInterventionAck(requestID, "failed", "backend rejected")
		return
	}

	responder.SendInterventionAck(requestID, "ok", "")
}

// handleActionFeedback processes action confirmation/dismissal feedback from user
func (h *ChatOrchestrator) handleActionFeedback(conn *websocket.Conn, msgMap map[string]interface{}, userID string) {
	h.handleActionFeedbackWithResponder(legacyActionStatusSender{conn: conn}, msgMap, userID)
}

// sendActionStatus sends action confirmation/dismissal status back to the client via WebSocket
func (h *ChatOrchestrator) sendActionStatus(conn *websocket.Conn, actionID, status string, data map[string]interface{}) {
	// Build status message
	statusMsg := map[string]interface{}{
		"type":      "action_status",
		"action_id": actionID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}

	// Merge additional data
	for k, v := range data {
		statusMsg[k] = v
	}

	// Send message to client
	if err := conn.WriteJSON(statusMsg); err != nil {
		log.Printf("Failed to send action status: %v", err)
	} else {
		log.Printf("✅ Action status sent: status=%s, action_id=%s", status, actionID)
	}
}

func (h *ChatOrchestrator) handleInterventionFeedback(conn *websocket.Conn, msgMap map[string]interface{}, userID, authToken string) {
	h.handleInterventionFeedbackWithResponder(legacyInterventionResponder{conn: conn}, msgMap, userID, authToken)
}

func (h *ChatOrchestrator) sendInterventionAck(conn *websocket.Conn, requestID, status, message string) {
	payload := map[string]interface{}{
		"type":       "intervention_feedback_ack",
		"request_id": requestID,
		"status":     status,
		"timestamp":  time.Now().Unix(),
	}
	if message != "" {
		payload["message"] = message
	}
	if err := conn.WriteJSON(payload); err != nil {
		log.Printf("Failed to send intervention feedback ack: %v", err)
	}
}

// handleFocusCompleted processes focus session completion events
func (h *ChatOrchestrator) handleFocusCompleted(msgMap map[string]interface{}, userID string) {
	sessionID, ok := msgMap["session_id"].(string)
	if !ok {
		log.Printf("Invalid focus_completed event: missing session_id field")
		return
	}

	actualDuration, ok := msgMap["actual_duration"].(float64)
	if !ok {
		log.Printf("Invalid focus_completed event: missing actual_duration field")
		return
	}

	var completedTaskIDs []string
	if tasks, ok := msgMap["tasks_completed"].([]interface{}); ok {
		for _, t := range tasks {
			if taskID, ok := t.(string); ok {
				completedTaskIDs = append(completedTaskIDs, taskID)
			}
		}
	}

	log.Printf("Focus session completed: user=%s, session_id=%s, duration=%d minutes, completed_tasks=%d",
		userID, sessionID, int(actualDuration), len(completedTaskIDs))

	// TODO: Update focus session status to completed
	// TODO: Update associated task statuses to completed
	// TODO: Record metrics for focus session
}

// handleUpdateNodeMastery forwards mastery updates to Python backend via gRPC and sends ACK
func (h *ChatOrchestrator) handleUpdateNodeMastery(conn *websocket.Conn, msgMap map[string]interface{}, userID string) {
	h.handleUpdateNodeMasteryWithResponder(legacyUpdateNodeResponder{conn: conn}, msgMap, userID)
}

func (h *ChatOrchestrator) sendError(conn *websocket.Conn, opType, nodeID, version, message string) {
	conn.WriteJSON(map[string]interface{}{
		"type": fmt.Sprintf("error_%s", opType),
		"payload": map[string]interface{}{
			"nodeId":  nodeID,
			"version": version,
			"error":   message,
		},
	})
}
