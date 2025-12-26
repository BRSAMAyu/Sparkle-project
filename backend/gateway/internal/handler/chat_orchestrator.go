package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all for dev
	},
}

type ChatOrchestrator struct {
	agentClient *agent.Client
	queries     *db.Queries
	chatHistory *service.ChatHistoryService
	quota       *service.QuotaService
	semantic    *service.SemanticCacheService
}

func NewChatOrchestrator(ac *agent.Client, q *db.Queries, ch *service.ChatHistoryService, qs *service.QuotaService, sc *service.SemanticCacheService) *ChatOrchestrator {
	return &ChatOrchestrator{
		agentClient: ac,
		queries:     q,
		chatHistory: ch,
		quota:       qs,
		semantic:    sc,
	}
}

func (h *ChatOrchestrator) HandleWebSocket(c *gin.Context) {
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("Failed to upgrade WS: %v", err)
		return
	}
	defer conn.Close()

	userID := c.GetString("user_id") // Assumes middleware set this
	if userID == "" {
		// Fallback for dev/demo if no auth middleware yet
		userID = c.Query("user_id")
		if userID == "" {
			userID = "anonymous"
		}
	}

	log.Printf("WebSocket connected for user: %s", userID)

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

		var input struct {
			Message   string `json:"message"`
			SessionID string `json:"session_id"`
			Nickname  string `json:"nickname,omitempty"`
		}

		// Parse JSON input
		if err := json.Unmarshal(msg, &input); err != nil {
			log.Printf("Failed to parse message: %v", err)
			conn.WriteJSON(gin.H{"type": "error", "message": "Invalid JSON format"})
			continue
		}

		if input.Message == "" {
			conn.WriteJSON(gin.H{"type": "error", "message": "Empty message"})
			continue
		}

		// Canonicalize Input (Semantic Cache Prep)
		_ = h.semantic.Canonicalize(input.Message)
		// TODO: Use canonicalized input for semantic search or caching in future

		// Build ChatRequest
		req := &agentv1.ChatRequest{
			RequestId: fmt.Sprintf("req_%s", uuid.New().String()),
			UserId:    userID,
			SessionId: input.SessionID,
			Input: &agentv1.ChatRequest_Message{
				Message: input.Message,
			},
			UserProfile: &agentv1.UserProfile{
				Nickname: input.Nickname,
				Timezone: "Asia/Shanghai",
				Language: "zh-CN",
			},
		}

		// Call Python Agent via gRPC (server-side streaming)
		stream, err := h.agentClient.StreamChat(c.Request.Context(), req)
		if err != nil {
			log.Printf("Failed to call StreamChat: %v", err)
			conn.WriteJSON(gin.H{"type": "error", "message": "AI Service Unavailable"})
			continue
		}

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

			// Accumulate full text for persistence
			if resp.GetDelta() != "" {
				fullText += resp.GetDelta()
			}
			if resp.GetFullText() != "" {
				fullText = resp.GetFullText()
			}

			// Convert protobuf response to JSON-friendly map
			jsonResp := convertResponseToJSON(resp)

			// Forward to WebSocket client
			if err := conn.WriteJSON(jsonResp); err != nil {
				log.Printf("Failed to write to WebSocket: %v", err)
				return
			}
		}

		// Persist completed message to database (async)
		if fullText != "" && input.SessionID != "" {
			go h.saveMessage(userID, input.SessionID, "assistant", fullText)

			// Also decrement quota (async)
			go func() {
				if _, err := h.quota.DecrQuota(context.Background(), userID); err != nil {
					log.Printf("Failed to decrement quota: %v", err)
				}
			}()
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
