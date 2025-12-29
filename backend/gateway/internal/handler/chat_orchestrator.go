package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
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
	"github.com/sparkle/gateway/internal/service"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
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
	Message   string `json:"message"`
	SessionID string `json:"session_id"`
	Nickname  string `json:"nickname,omitempty"`
	ExtraContext map[string]interface{} `json:"extra_context,omitempty"`
}

// Reset clears the input for reuse
func (c *chatInput) Reset() {
	c.Message = ""
	c.SessionID = ""
	c.Nickname = ""
	c.ExtraContext = nil
}

// jsonResponsePool reuses response maps
var jsonResponsePool = sync.Pool{
	New: func() interface{} {
		return make(map[string]interface{}, 8)
	},
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
	agentClient *agent.Client
	queries     *db.Queries
	chatHistory *service.ChatHistoryService
	quota       *service.QuotaService
	semantic    *service.SemanticCacheService
	billing     *service.CostCalculator
	wsFactory   *WebSocketFactory
	userContext *service.UserContextService
}

func NewChatOrchestrator(ac *agent.Client, q *db.Queries, ch *service.ChatHistoryService, qs *service.QuotaService, sc *service.SemanticCacheService, bc *service.CostCalculator, wsFactory *WebSocketFactory, uc *service.UserContextService) *ChatOrchestrator {
	return &ChatOrchestrator{
		agentClient: ac,
		queries:     q,
		chatHistory: ch,
		quota:       qs,
		semantic:    sc,
		billing:     bc,
		wsFactory:   wsFactory,
		userContext: uc,
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
		conn.Close()
		return
	}

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

		// First, check message type
		msgMap := make(map[string]interface{})
		if err := json.Unmarshal(msg, &msgMap); err != nil {
			log.Printf("Failed to parse message: %v", err)
			conn.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
			continue
		}

		msgType, ok := msgMap["type"].(string)
		if !ok {
			msgType = "message" // Default to chat message
		}

		// Route based on message type
		switch msgType {
		case "action_feedback":
			h.handleActionFeedback(msgMap, userID)
			continue

		case "focus_completed":
			h.handleFocusCompleted(msgMap, userID)
			continue

		case "message", "":
			// Continue with normal chat message handling
		default:
			log.Printf("Unknown message type: %s", msgType)
			conn.WriteJSON(gin.H{"type": "error", "message": "Unknown message type"})
			continue
		}

		// P1: Get input from pool instead of allocating new struct
		input := chatInputPool.Get().(*chatInput)

		// Parse JSON input
		if err := json.Unmarshal(msg, input); err != nil {
			log.Printf("Failed to parse message: %v", err)
			conn.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
			input.Reset()
			chatInputPool.Put(input)
			continue
		}

		if input.Message == "" {
			conn.WriteJSON(gin.H{"type": "error", "message": "Empty message"})
			input.Reset()
			chatInputPool.Put(input)
			continue
		}

		// Start a new span for this message processing
		ctx, span := tracer.Start(c.Request.Context(), "HandleMessage")
		span.SetAttributes(
			attribute.String("user_id", userID),
			attribute.String("session_id", input.SessionID),
		)

		// Sanitize Input (Security Hygiene) - reuse global sanitizer
		input.Message = sanitizer.Sanitize(input.Message)

		// Persist user message to Redis history for context pruning
		if input.SessionID != "" {
			sessionID := input.SessionID
			go h.saveMessage(userID, sessionID, "user", input.Message)
		}

		// Canonicalize Input (Semantic Cache Prep)
		_ = h.semantic.Canonicalize(input.Message)
		// TODO: Use canonicalized input for semantic search or caching in future

		startTime := time.Now()

		// P0: Fetch user context (pending tasks, active plans, focus stats, recent progress)
		userContextJSON := ""
		if h.userContext != nil {
			contextData, err := h.userContext.GetUserContextData(ctx, uuid.MustParse(userID))
			if err != nil {
				log.Printf("Failed to fetch user context: %v", err)
				// Non-fatal: continue with empty context
			} else {
				userContextJSON = contextData
			}
		}

		// Build ChatRequest
		req := &agentv1.ChatRequest{
			RequestId: fmt.Sprintf("req_%s", uuid.New().String()),
			UserId:    userID,
			SessionId: input.SessionID,
			Input: &agentv1.ChatRequest_Message{
				Message: input.Message,
			},
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
		// Use the new span context
		stream, err := h.agentClient.StreamChat(ctx, req)
		if err != nil {
			log.Printf("Failed to call StreamChat: %v", err)
			conn.WriteJSON(gin.H{"type": "error", "message": "AI Service Unavailable"})
			span.End()
			continue
		}

		// P1: Get string builder from pool for efficient text accumulation
		textBuilder := stringBuilderPool.Get().(*strings.Builder)
		textBuilder.Reset()

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
				conn.WriteJSON(gin.H{"type": "error", "message": "Stream interrupted"})
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

			// Convert protobuf response to JSON-friendly map
			jsonResp := convertResponseToJSON(resp)

			// Forward to WebSocket client
			if err := conn.WriteJSON(jsonResp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				stringBuilderPool.Put(textBuilder)
				input.Reset()
				chatInputPool.Put(input)
				span.End()
				return
			}
		}
		fullText = textBuilder.String()
		stringBuilderPool.Put(textBuilder)

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

		// Send final metadata
		conn.WriteJSON(gin.H{
			"type": "meta",
			"meta": meta,
		})

		// Persist completed message to database (async)
		if fullText != "" && input.SessionID != "" {
			// Capture values for goroutine before returning input to pool
			sessionID := input.SessionID
			go h.saveMessage(userID, sessionID, "assistant", fullText)

			// Also decrement quota (async)
			go func() {
				if _, err := h.quota.DecrQuota(context.Background(), userID); err != nil {
					log.Printf("Failed to decrement quota: %v", err)
				}
			}()
		}

		// P1: Return input to pool for reuse
		input.Reset()
		chatInputPool.Put(input)
		span.End()
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
				"id":          c.Id,
				"title":       c.Title,
				"content":     c.Content,
				"source_type": c.SourceType,
				"score":       c.Score,
				"url":         c.Url,
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
			"tool_name":    tool.ToolName,
			"success":      tool.Success,
			"data":         data,
			"error_message": tool.ErrorMessage,
			"suggestion":    tool.Suggestion,
			"widget_type":   tool.WidgetType,
			"widget_data":   widgetData,
			"tool_call_id":  tool.ToolCallId,
		}
	}

	if resp.FinishReason != agentv1.FinishReason_NULL {
		result["finish_reason"] = resp.FinishReason.String()
	}

	return result
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

// handleActionFeedback processes action confirmation/dismissal feedback from user
func (h *ChatOrchestrator) handleActionFeedback(msgMap map[string]interface{}, userID string) {
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

	// Route feedback to appropriate service handler
	switch widgetType {
	case "task_list":
		if action == "confirm" {
			// Handle task list confirmation (tasks were created)
			log.Printf("Task list creation confirmed for user %s", userID)
			// TODO: Update task status or trigger post-creation logic
		} else if action == "dismiss" {
			// Handle task list dismissal (user rejected generated tasks)
			log.Printf("Task list creation dismissed by user %s", userID)
			// TODO: Log dismissal or cleanup tasks
		}

	case "plan_card":
		if action == "confirm" {
			// Handle plan confirmation
			log.Printf("Plan creation confirmed for user %s", userID)
			// TODO: Update plan status
		} else if action == "dismiss" {
			log.Printf("Plan creation dismissed by user %s", userID)
			// TODO: Archive plan or log dismissal
		}

	case "focus_card":
		if action == "confirm" {
			// Handle focus session start confirmation
			log.Printf("Focus session start confirmed for user %s", userID)
			// TODO: Start focus session in database
		} else if action == "dismiss" {
			log.Printf("Focus session dismissed by user %s", userID)
		}

	default:
		log.Printf("Unknown widget type in action feedback: %s", widgetType)
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
