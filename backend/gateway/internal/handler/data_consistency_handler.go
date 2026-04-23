package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
)

// DataConsistencyHandler provides endpoints for data consistency verification
type DataConsistencyHandler struct {
	chatHistory *service.ChatHistoryService
	queries     *db.Queries
	redis       *redis.Client
}

// NewDataConsistencyHandler creates a new data consistency handler
func NewDataConsistencyHandler(
	chatHistory *service.ChatHistoryService,
	queries *db.Queries,
	redis *redis.Client,
) *DataConsistencyHandler {
	return &DataConsistencyHandler{
		chatHistory: chatHistory,
		queries:     queries,
		redis:       redis,
	}
}

// RegisterRoutes registers data consistency check routes
func (h *DataConsistencyHandler) RegisterRoutes(api *gin.RouterGroup, authMiddleware gin.HandlerFunc) {
	// Check message in Redis cache
	api.GET("/chat/cache/check", authMiddleware, h.checkCache)
	// Check message in database
	api.GET("/chat/db/check", authMiddleware, h.checkDatabase)
}

// checkCache checks if a message exists in Redis cache
func (h *DataConsistencyHandler) checkCache(c *gin.Context) {
	messageID := c.Query("message_id")
	conversationID := c.Query("conversation_id")

	if messageID == "" || conversationID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "message_id and conversation_id are required",
		})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	// Check Redis cache
	cacheKey := "chat:history:" + conversationID
	result, err := h.redis.LRange(ctx, cacheKey, 0, -1).Result()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}

	// Search for the message
	var foundMessage map[string]interface{}
	for _, msg := range result {
		var msgData map[string]interface{}
		if err := json.Unmarshal([]byte(msg), &msgData); err != nil {
			continue
		}

		if msgID, ok := msgData["id"].(string); ok && msgID == messageID {
			foundMessage = msgData
			break
		}
	}

	if foundMessage == nil {
		c.JSON(http.StatusOK, gin.H{
			"exists": false,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"exists":  true,
		"message": foundMessage,
	})
}

// checkDatabase checks if a message exists in the database
func (h *DataConsistencyHandler) checkDatabase(c *gin.Context) {
	messageIDStr := c.Query("message_id")
	conversationIDStr := c.Query("conversation_id")

	if messageIDStr == "" || conversationIDStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "message_id and conversation_id are required",
		})
		return
	}

	// Parse UUIDs
	messageID, err := uuid.Parse(messageIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid message_id format",
		})
		return
	}

	conversationID, err := uuid.Parse(conversationIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid conversation_id format",
		})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	// Convert uuid.UUID to pgtype.UUID
	var pgMessageID pgtype.UUID
	copy(pgMessageID.Bytes[:], messageID[:])
	pgMessageID.Valid = true

	var pgSessionID pgtype.UUID
	copy(pgSessionID.Bytes[:], conversationID[:])
	pgSessionID.Valid = true

	// Query database
	message, err := h.queries.GetMessageByID(ctx, db.GetMessageByIDParams{
		ID:        pgMessageID,
		SessionID: pgSessionID,
	})
	if err != nil {
		// Message not found
		c.JSON(http.StatusOK, gin.H{
			"exists": false,
		})
		return
	}

	// Convert to map for response
	messageData := map[string]interface{}{
		"id":              message.ID.String(),
		"conversation_id": message.SessionID.String(),
		"role":            message.Role,
		"content":         message.Content,
		"timestamp":       message.CreatedAt.Time.Format(time.RFC3339),
	}

	c.JSON(http.StatusOK, gin.H{
		"exists":  true,
		"message": messageData,
	})
}
