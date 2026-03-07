package handler

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/service"
)

type ChatHistoryHandler struct {
	chatHistory *service.ChatHistoryService
}

func NewChatHistoryHandler(chatHistory *service.ChatHistoryService) *ChatHistoryHandler {
	return &ChatHistoryHandler{chatHistory: chatHistory}
}

func (h *ChatHistoryHandler) GetRecentSessions(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing user ID in context"})
		return
	}

	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	sessions, err := h.chatHistory.GetRecentSessions(c.Request.Context(), userID, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch recent sessions"})
		return
	}

	c.JSON(http.StatusOK, sessions)
}

func (h *ChatHistoryHandler) GetConversationHistory(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing user ID in context"})
		return
	}

	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	sessionID := c.Param("conversation_id")

	messages, err := h.chatHistory.GetMessages(c.Request.Context(), userID, sessionID, limit, offset)
	if err != nil {
		if err.Error() == "forbidden" {
			c.JSON(http.StatusForbidden, gin.H{"error": "Forbidden"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch conversation history"})
		return
	}

	result := make([]gin.H, 0, len(messages))
	for _, msg := range messages {
		createdAt := time.Now().UTC().Format(time.RFC3339)
		if ts, err := strconv.ParseInt(msg.Timestamp, 10, 64); err == nil {
			createdAt = time.Unix(ts, 0).UTC().Format(time.RFC3339)
		}
		result = append(result, gin.H{
			"id":              msg.Timestamp + ":" + msg.Role,
			"conversation_id": msg.SessionID,
			"role":            msg.Role,
			"content":         msg.Content,
			"created_at":      createdAt,
			"user_id":         msg.UserID,
		})
	}
	c.JSON(http.StatusOK, result)
}
