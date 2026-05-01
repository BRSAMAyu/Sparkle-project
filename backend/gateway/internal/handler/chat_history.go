package handler

import (
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/service"
)

type ChatHistoryMessageDTO struct {
	ID                   string                   `json:"id"`
	UserID               string                   `json:"user_id"`
	ConversationID       string                   `json:"conversation_id"`
	SessionID            string                   `json:"session_id"`
	TaskID               string                   `json:"task_id"`
	Role                 string                   `json:"role"`
	Content              string                   `json:"content"`
	CreatedAt            string                   `json:"created_at"`
	Widgets              []map[string]interface{} `json:"widgets"`
	ToolResults          []map[string]interface{} `json:"tool_results"`
	HasErrors            bool                     `json:"has_errors"`
	Errors               []map[string]interface{} `json:"errors"`
	RequiresConfirmation bool                     `json:"requires_confirmation"`
	ConfirmationData     map[string]interface{}   `json:"confirmation_data"`
	ReasoningSteps       []map[string]interface{} `json:"reasoning_steps"`
	ReasoningSummary     string                   `json:"reasoning_summary"`
	IsReasoningComplete  bool                     `json:"is_reasoning_complete"`
	Meta                 map[string]interface{}   `json:"meta"`
	AgentCollaboration   map[string]interface{}   `json:"agentCollaboration"`
}

type ChatHistoryHandler struct {
	chatHistory *service.ChatHistoryService
}

type ConversationSettingsPatchRequest struct {
	UseDocumentContext *bool     `json:"use_document_context"`
	DocumentFilter     *[]string `json:"document_filter"`
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
		if errors.Is(err, service.ErrChatHistoryForbidden()) {
			c.JSON(http.StatusForbidden, gin.H{"error": "Forbidden"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch conversation history"})
		return
	}

	result := make([]ChatHistoryMessageDTO, 0, len(messages))
	for _, msg := range messages {
		createdAt := time.Now().UTC().Format(time.RFC3339)
		if ts, err := strconv.ParseInt(msg.Timestamp, 10, 64); err == nil {
			createdAt = time.Unix(ts, 0).UTC().Format(time.RFC3339)
		}
		// Use message ID if available, otherwise fallback to timestamp:role (for backwards compatibility)
		msgID := msg.ID
		if msgID == "" {
			msgID = msg.Timestamp + ":" + msg.Role
		}
		result = append(result, ChatHistoryMessageDTO{
			ID:                   msgID,
			UserID:               msg.UserID,
			ConversationID:       msg.SessionID,
			SessionID:            msg.SessionID,
			TaskID:               msg.TaskID,
			Role:                 msg.Role,
			Content:              msg.Content,
			CreatedAt:            createdAt,
			Widgets:              msg.Widgets,
			ToolResults:          msg.ToolResults,
			HasErrors:            msg.HasErrors,
			Errors:               msg.Errors,
			RequiresConfirmation: msg.RequiresConfirmation,
			ConfirmationData:     msg.ConfirmationData,
			ReasoningSteps:       msg.ReasoningSteps,
			ReasoningSummary:     msg.ReasoningSummary,
			IsReasoningComplete:  msg.IsReasoningComplete,
			Meta:                 msg.Meta,
			AgentCollaboration:   msg.AgentCollaboration,
		})
	}
	c.JSON(http.StatusOK, result)
}

func (h *ChatHistoryHandler) PatchConversationSettings(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing user ID in context"})
		return
	}
	sessionID := c.Param("conversation_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Missing conversation_id"})
		return
	}

	var payload ConversationSettingsPatchRequest
	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}
	if payload.UseDocumentContext == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "use_document_context is required"})
		return
	}

	documentFilter := []string{}
	if payload.DocumentFilter != nil {
		documentFilter = *payload.DocumentFilter
	} else if stored, ok, err := h.chatHistory.GetConversationSettings(c.Request.Context(), userID, sessionID); err == nil && ok && stored != nil {
		documentFilter = stored.DocumentFilter
	} else if err != nil {
		if errors.Is(err, service.ErrChatHistoryForbidden()) {
			c.JSON(http.StatusForbidden, gin.H{"error": "Forbidden"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load conversation settings"})
		return
	}

	settings, err := h.chatHistory.UpdateConversationSettings(
		c.Request.Context(),
		userID,
		sessionID,
		service.ConversationSettings{
			UseDocumentContext: *payload.UseDocumentContext,
			DocumentFilter:     documentFilter,
		},
	)
	if err != nil {
		if errors.Is(err, service.ErrChatHistoryForbidden()) {
			c.JSON(http.StatusForbidden, gin.H{"error": "Forbidden"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update conversation settings"})
		return
	}

	c.JSON(http.StatusOK, settings)
}
