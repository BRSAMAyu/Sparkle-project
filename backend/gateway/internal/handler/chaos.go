package handler

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/service"
)

type ChaosHandler struct {
	chatHistory *service.ChatHistoryService
}

func NewChaosHandler(ch *service.ChatHistoryService) *ChaosHandler {
	return &ChaosHandler{
		chatHistory: ch,
	}
}

func (h *ChaosHandler) SetThreshold(c *gin.Context) {
	// Simple Security check
	if c.GetHeader("X-Admin-Secret") != "sparkle_2025" {
		c.JSON(http.StatusForbidden, gin.H{"error": "Unauthorized"})
		return
	}

	var req struct {
		Target string `json:"target"` // "queue_persist"
		Value  int64  `json:"value"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if req.Target == "queue_persist" {
		h.chatHistory.SetBreakerThreshold(req.Value)
		
		qLen, _ := h.chatHistory.GetQueueLength(c.Request.Context())

		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
			"msg":    fmt.Sprintf("Threshold updated to %d", req.Value),
			"details": gin.H{
				"current_queue": qLen,
				"new_threshold": req.Value,
				"breaker_tripped": qLen >= req.Value,
			},
		})
	} else {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Unknown target"})
	}
}

func (h *ChaosHandler) GetStatus(c *gin.Context) {
	qLen, _ := h.chatHistory.GetQueueLength(c.Request.Context())
	threshold := h.chatHistory.GetBreakerThreshold()

	c.JSON(http.StatusOK, gin.H{
		"queue_length": qLen,
		"threshold":    threshold,
		"is_tripped":   qLen >= threshold,
	})
}