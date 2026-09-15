package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
)

func CORSMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		if origin != "" {
			if cfg.IsOriginAllowed(origin) {
				c.Header("Access-Control-Allow-Origin", origin)
				c.Header("Access-Control-Allow-Credentials", "true")
				c.Header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Requested-With, X-Request-ID, X-Trace-ID, Accept, Accept-Language")
				c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
				c.Header("Access-Control-Expose-Headers", "X-Request-ID, X-Trace-ID, X-RateLimit-Limit, X-RateLimit-Remaining")
				c.Header("Access-Control-Max-Age", "86400")
			}
			// Always set Vary: Origin to prevent caching a per-origin response
			// and serving it to a different origin (CORS security best practice).
			c.Header("Vary", "Origin")
		}

		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
