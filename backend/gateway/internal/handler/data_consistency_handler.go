package handler

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sparkle/gateway/internal/service"
)

// DataConsistencyHandler provides endpoints for data consistency verification
type DataConsistencyHandler struct {
	consistency dataConsistencyService
}

type dataConsistencyService interface {
	CheckCache(ctx context.Context, messageID, conversationID string) (service.CacheMessageResult, error)
	CheckDatabase(ctx context.Context, messageID, conversationID uuid.UUID) (service.DatabaseMessageResult, error)
}

// NewDataConsistencyHandler creates a new data consistency handler
func NewDataConsistencyHandler(consistency dataConsistencyService) *DataConsistencyHandler {
	return &DataConsistencyHandler{
		consistency: consistency,
	}
}

// RegisterRoutes registers data consistency check routes
func (h *DataConsistencyHandler) RegisterRoutes(api *gin.RouterGroup, authMiddleware gin.HandlerFunc) {
	// route-tier: authed
	api.GET("/chat/cache/check", authMiddleware, h.checkCache)
	// route-tier: authed
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

	result, err := h.consistency.CheckCache(ctx, messageID, conversationID)
	if err != nil {
		sanitizeErrorResponse(c, http.StatusInternalServerError, err, "data_consistency.check_cache")
		return
	}

	if !result.Exists {
		c.JSON(http.StatusOK, gin.H{
			"exists": false,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"exists":  true,
		"message": result.Message,
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

	result, err := h.consistency.CheckDatabase(ctx, messageID, conversationID)
	if err != nil {
		sanitizeErrorResponse(c, http.StatusInternalServerError, err, "data_consistency.check_database")
		return
	}

	if !result.Exists {
		c.JSON(http.StatusOK, gin.H{
			"exists": false,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"exists":  true,
		"message": result.Message,
	})
}
