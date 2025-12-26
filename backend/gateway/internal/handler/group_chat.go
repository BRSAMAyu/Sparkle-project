package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/db"
)

type GroupChatHandler struct {
	queries *db.Queries
}

func NewGroupChatHandler(queries *db.Queries) *GroupChatHandler {
	return &GroupChatHandler{queries: queries}
}

func (h *GroupChatHandler) GetMessages(c *gin.Context) {
	groupIDStr := c.Param("group_id")
	var groupID pgtype.UUID
	if err := groupID.Scan(groupIDStr); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid group ID"})
		return
	}

	limitStr := c.DefaultQuery("limit", "50")
	limit, _ := strconv.Atoi(limitStr)
	offsetStr := c.DefaultQuery("offset", "0")
	offset, _ := strconv.Atoi(offsetStr)

	messages, err := h.queries.GetGroupMessages(c.Request.Context(), db.GetGroupMessagesParams{
		GroupID: groupID,
		Limit:   int32(limit),
		Offset:  int32(offset),
	})
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
				"avatar_url": msg.SenderAvatarUrl.String,
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
				"message_type": msg.ReplyType.Messagetype,
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
