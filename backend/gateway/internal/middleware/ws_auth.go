package middleware

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
)

var wsTicketGetDel = redis.NewScript(`
local val = redis.call("GET", KEYS[1])
if val then
	redis.call("DEL", KEYS[1])
end
return val
`)

const wsTicketKeyPrefix = "ws:ticket:"

type wsTicketPayload struct {
	UserID string `json:"user_id"`
	Token  string `json:"token"`
}

func WsAuthMiddleware(cfg *config.Config, rdb *redis.Client) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Debug logging for real device testing
		log.Printf("[WsAuth] Request to %s from %s, Origin: %s, Upgrade: %s",
			c.Request.URL.Path, c.ClientIP(), c.GetHeader("Origin"), c.GetHeader("Upgrade"))

		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			if strings.HasPrefix(authHeader, "Bearer ") {
				tokenString := strings.TrimPrefix(authHeader, "Bearer ")
				userID, isAdmin, err := validateJWT(cfg, rdb, tokenString)
				if err != nil {
					log.Printf("[WsAuth] JWT header validation failed: %v", err)
					metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "jwt_header", "invalid_token").Inc()
					abortWithAPIError(c, http.StatusUnauthorized, "invalid_or_expired_token", "Invalid or expired token")
					return
				}
				log.Printf("[WsAuth] JWT header validation success for user: %s", userID)
				c.Set("user_id", userID)
				c.Set("is_admin", isAdmin)
				c.Set("auth_token", tokenString)
				c.Set("ws_auth_method", "jwt_header")
				c.Next()
				return
			}
		}

		// Support JWT token via query param (for clients that can't send custom headers, like Flutter)
		if cfg.AllowWsQueryToken {
			if queryToken := c.Query("token"); queryToken != "" {
				log.Printf("[WsAuth] Attempting JWT query validation, AllowWsQueryToken=%v (token omitted from log)", cfg.AllowWsQueryToken)
				userID, isAdmin, err := validateJWT(cfg, rdb, queryToken)
				if err != nil {
					log.Printf("[WsAuth] JWT query validation failed: %v", err)
					metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "jwt_query", "invalid_token").Inc()
					abortWithAPIError(c, http.StatusUnauthorized, "invalid_or_expired_token", "Invalid or expired token")
					return
				}
				log.Printf("[WsAuth] JWT query validation success for user: %s", userID)
				c.Set("user_id", userID)
				c.Set("is_admin", isAdmin)
				c.Set("auth_token", queryToken)
				c.Set("ws_auth_method", "jwt_query")
				c.Next()
				return
			}
		}

		ticket := extractWSTicket(c, cfg.AllowWsQueryToken)
		if ticket == "" {
			metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "unknown", "missing_credentials").Inc()
			abortWithAPIError(c, http.StatusUnauthorized, "authorization_token_required", "Authorization token required")
			return
		}

		key := fmt.Sprintf("%s%s", wsTicketKeyPrefix, ticket)
		ctx, cancel := context.WithTimeout(c.Request.Context(), 500*time.Millisecond)
		defer cancel()

		val, err := wsTicketGetDel.Run(ctx, rdb, []string{key}).Result()
		if err != nil || val == nil {
			metrics.WSTicketConsumeFailure.WithLabelValues("invalid_or_expired").Inc()
			metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "ticket", "invalid_or_expired").Inc()
			abortWithAPIError(c, http.StatusUnauthorized, "invalid_or_expired_ticket", "Invalid or expired ticket")
			return
		}

		valStr, ok := val.(string)
		if !ok || valStr == "" {
			metrics.WSTicketConsumeFailure.WithLabelValues("invalid_payload").Inc()
			metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "ticket", "invalid_payload").Inc()
			abortWithAPIError(c, http.StatusUnauthorized, "invalid_ticket_payload", "Invalid ticket payload")
			return
		}
		payload := wsTicketPayload{UserID: valStr}
		trimmed := strings.TrimSpace(valStr)
		if strings.HasPrefix(trimmed, "{") {
			if err := json.Unmarshal([]byte(trimmed), &payload); err != nil {
				metrics.WSTicketConsumeFailure.WithLabelValues("invalid_payload").Inc()
				metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "ticket", "invalid_payload").Inc()
				abortWithAPIError(c, http.StatusUnauthorized, "invalid_ticket_payload", "Invalid ticket payload")
				return
			}
		}
		userID := payload.UserID
		if userID == "" {
			metrics.WSTicketConsumeFailure.WithLabelValues("invalid_payload").Inc()
			metrics.WSConnectionError.WithLabelValues(wsEndpointLabel(c), "ticket", "invalid_payload").Inc()
			abortWithAPIError(c, http.StatusUnauthorized, "invalid_ticket_payload", "Invalid ticket payload")
			return
		}

		metrics.WSTicketConsumeSuccess.Inc()
		c.Set("user_id", userID)
		c.Set("is_admin", false)
		if payload.Token != "" {
			c.Set("auth_token", payload.Token)
		}
		c.Set("ws_auth_method", "ticket")
		c.Next()
	}
}

func wsEndpointLabel(c *gin.Context) string {
	if path := c.FullPath(); path != "" {
		return path
	}
	return c.Request.URL.Path
}

func extractWSTicket(c *gin.Context, allowQuery bool) string {
	protocolHeader := c.GetHeader("Sec-WebSocket-Protocol")
	if protocolHeader != "" {
		for _, part := range strings.Split(protocolHeader, ",") {
			candidate := strings.TrimSpace(part)
			lower := strings.ToLower(candidate)
			if strings.HasPrefix(lower, "ticket=") {
				return strings.TrimSpace(candidate[7:])
			}
			if strings.HasPrefix(lower, "ticket:") {
				return strings.TrimSpace(candidate[7:])
			}
			if strings.HasPrefix(lower, "ws-ticket=") {
				return strings.TrimSpace(candidate[10:])
			}
			if strings.HasPrefix(lower, "ws-ticket:") {
				return strings.TrimSpace(candidate[10:])
			}
		}
	}

	if allowQuery {
		if cfgTicket := c.Query("ticket"); cfgTicket != "" {
			return cfgTicket
		}
	}

	return ""
}
