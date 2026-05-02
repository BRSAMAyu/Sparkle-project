package handler

import (
	"context"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/service"
)

type GroupChatHandler struct {
	groupChat groupChatService
}

type groupChatService interface {
	CheckGroupMembership(ctx context.Context, userID, groupID pgtype.UUID) (bool, error)
	GetGroupMessages(ctx context.Context, groupID pgtype.UUID, limit, offset int32) ([]service.GroupChatMessage, error)
}

func NewGroupChatHandler(groupChat groupChatService) *GroupChatHandler {
	return &GroupChatHandler{groupChat: groupChat}
}

func (h *GroupChatHandler) GetMessages(c *gin.Context) {
	// Extract authenticated user_id from context (set by AuthMiddleware)
	userIDStr, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing user ID in context"})
		return
	}

	var userID pgtype.UUID
	if err := userID.Scan(userIDStr.(string)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid user ID in context"})
		return
	}

	groupIDStr := c.Param("group_id")
	var groupID pgtype.UUID
	if err := groupID.Scan(groupIDStr); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid group ID"})
		return
	}

	// Check if user is a member of the group
	isMember, err := h.groupChat.CheckGroupMembership(c.Request.Context(), userID, groupID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to verify group membership"})
		return
	}

	if !isMember {
		c.JSON(http.StatusForbidden, gin.H{"error": "You are not a member of this group"})
		return
	}

	limitStr := c.DefaultQuery("limit", "50")
	limit, _ := strconv.Atoi(limitStr)
	offsetStr := c.DefaultQuery("offset", "0")
	offset, _ := strconv.Atoi(offsetStr)

	messages, err := h.groupChat.GetGroupMessages(c.Request.Context(), groupID, int32(limit), int32(offset))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch messages"})
		return
	}

	// Transform to JSON
	var result []map[string]interface{}
	for _, msg := range messages {
		var sender map[string]interface{}
		if msg.SenderID.Valid {
			sender = map[string]interface{}{
				"id":         msg.SenderID,
				"username":   msg.SenderUsername.String,
				"nickname":   msg.SenderNickname.String,
				"avatar_url": msg.SenderAvatarURL.String,
			}
		}

		var quotedMessage map[string]interface{}
		if msg.ReplyID.Valid {
			var replySender map[string]interface{}
			replySender = map[string]interface{}{
				"username": msg.ReplySenderUsername.String,
				"nickname": msg.ReplySenderNickname.String,
			}

			quotedMessage = map[string]interface{}{
				"id":           msg.ReplyID,
				"content":      msg.ReplyContent.String,
				"message_type": msg.ReplyType,
				"sender":       replySender,
			}
		}

		m := map[string]interface{}{
			"id":             msg.ID,
			"group_id":       msg.GroupID,
			"sender":         sender,
			"message_type":   msg.MessageType,
			"content":        msg.Content.String,
			"reply_to_id":    msg.ReplyToID,
			"created_at":     msg.CreatedAt.Time,
			"updated_at":     msg.UpdatedAt.Time,
			"quoted_message": quotedMessage,
		}
		result = append(result, m)
	}

	c.JSON(http.StatusOK, result)
}
