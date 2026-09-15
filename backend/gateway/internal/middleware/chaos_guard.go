package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
)

// ChaosGuardMiddleware blocks chaos endpoints unless explicitly enabled.
func ChaosGuardMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		if !cfg.ChaosEnabled {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "chaos is disabled"})
			return
		}
		if cfg.IsProduction() && !cfg.ChaosAllowProd {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "chaos is disabled in production"})
			return
		}
		c.Next()
	}
}
