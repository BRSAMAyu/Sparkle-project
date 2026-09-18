package middleware

import (
	"crypto/subtle"
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/metrics"
)

// InternalAPIKeyMiddleware validates internal service calls using X-Internal-API-Key header.
func InternalAPIKeyMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		if cfg.InternalAPIKey == "" {
			metrics.KeyAuthFailures.WithLabelValues("internal_api_key", "not_configured").Inc()
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "internal api key not configured"})
			return
		}

		provided := c.GetHeader("X-Internal-API-Key")
		if provided == "" || subtle.ConstantTimeCompare([]byte(provided), []byte(cfg.InternalAPIKey)) != 1 {
			// GW-P3/R2-GW-9: rejected before rate limiting — count explicitly.
			reason := "invalid"
			if provided == "" {
				reason = "missing"
			}
			metrics.KeyAuthFailures.WithLabelValues("internal_api_key", reason).Inc()
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid internal api key"})
			return
		}

		c.Next()
	}
}
