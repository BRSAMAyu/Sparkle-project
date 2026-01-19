package handler

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
)

const wsTicketKeyPrefix = "ws:ticket:"

type WSTicketHandler struct {
	cfg *config.Config
	rdb *redis.Client
}

func NewWSTicketHandler(cfg *config.Config, rdb *redis.Client) *WSTicketHandler {
	return &WSTicketHandler{cfg: cfg, rdb: rdb}
}

func (h *WSTicketHandler) Issue(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "missing user context"})
		return
	}

	ticket := uuid.NewString()
	key := fmt.Sprintf("%s%s", wsTicketKeyPrefix, ticket)
	ttl := time.Duration(h.cfg.WSTicketTTLSeconds) * time.Second

	ctx, cancel := context.WithTimeout(c.Request.Context(), 500*time.Millisecond)
	defer cancel()

	if err := h.rdb.Set(ctx, key, userID, ttl).Err(); err != nil {
		metrics.WSTicketIssueErrors.Inc()
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to issue ticket"})
		return
	}

	metrics.WSTicketIssued.Inc()
	c.JSON(http.StatusOK, gin.H{
		"ticket":      ticket,
		"expires_in":  h.cfg.WSTicketTTLSeconds,
		"token_type":  "ws_ticket",
	})
}
