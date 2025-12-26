package handler

import (
	"encoding/json"
	"io"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/sparkle/gateway/internal/agent"
	"github.com/sparkle/gateway/internal/db"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all for dev
	},
}

type ChatOrchestrator struct {
	agentClient *agent.Client
	queries     *db.Queries
}

func NewChatOrchestrator(ac *agent.Client, q *db.Queries) *ChatOrchestrator {
	return &ChatOrchestrator{
		agentClient: ac,
		queries:     q,
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

	// Connect to Python Agent
	// Note: In production, stream should be created per session or reused carefully
	stream, err := h.agentClient.StreamChat(c.Request.Context(), userID)
	if err != nil {
		log.Printf("Failed to connect to agent: %v", err)
		conn.WriteJSON(gin.H{"type": "system_error", "payload": "AI Service Unavailable"})
		return
	}

	// Channel to signal read pump to stop
	done := make(chan struct{})

	// Read Pump (Client -> Gateway -> Agent)
	go func() {
		defer close(done)
		for {
			_, msg, err := conn.ReadMessage()
			if err != nil {
				return
			}

			var input struct {
				Message   string `json:"message"`
				SessionID string `json:"sessionId"`
			}

			// Try to parse as JSON, otherwise treat as raw string if needed,
			// but best to enforce JSON protocol
			if err := json.Unmarshal(msg, &input); err == nil {
				req := &agentv1.ChatRequest{
					UserId:    userID,
					SessionId: input.SessionID,
					Input: &agentv1.ChatRequest_Message{
						Message: input.Message,
					},
				}
				if err := stream.Send(req); err != nil {
					log.Printf("Failed to send to agent: %v", err)
					return
				}
			}
		}
	}()

	// Write Pump (Agent -> Gateway -> Client)
	for {
		resp, err := stream.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Printf("Stream recv error: %v", err)
			conn.WriteJSON(gin.H{"type": "system_error", "payload": "Stream interrupted"})
			break
		}

		// Persist if finished (Simple example)
		if resp.FinishReason != agentv1.FinishReason_NULL && resp.GetFullText() != "" {
			// Save to DB asynchronously
			// In a real implementation, you'd extract the session ID from context or response
			go func(text string) {
				// ctx := context.Background()
				// h.queries.CreateChatMessage(ctx, db.CreateChatMessageParams{
				// 	SessionID: ...
				// 	UserID: userID,
				// 	Role: "assistant",
				// 	Content: text,
				// })
			}(resp.GetFullText())
		}

		// Forward to Client
		if err := conn.WriteJSON(resp); err != nil {
			break
		}
	}
	<-done
}
