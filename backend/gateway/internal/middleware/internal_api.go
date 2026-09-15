package middleware

import (
	"crypto/subtle"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
)

// InternalAPIKeyMiddleware validates internal service calls using X-Internal-API-Key header.
func InternalAPIKeyMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		if cfg.InternalAPIKey == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "internal api key not configured"})
			return
		}

		provided := c.GetHeader("X-Internal-API-Key")
		if provided == "" || subtle.ConstantTimeCompare([]byte(provided), []byte(cfg.InternalAPIKey)) != 1 {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid internal api key"})
			return
		}

		c.Next()
	}
}
