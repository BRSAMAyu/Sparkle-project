package middleware

import (
	"context"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// TimeoutMiddleware wraps each request with a context deadline.
// If the downstream handler respects the context, in-flight work will be
// cancelled when the deadline expires. The middleware also returns 503 if
// the context was cancelled due to timeout.
func TimeoutMiddleware(timeout time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		if timeout <= 0 {
			c.Next()
			return
		}
		if isLongRunningRoute(c.Request.URL.Path) {
			c.Next()
			return
		}

		ctx, cancel := context.WithTimeout(c.Request.Context(), timeout)
		defer cancel()

		c.Request = c.Request.WithContext(ctx)
		c.Next()

		// If the context timed out and no response was written yet, return 503
		if ctx.Err() == context.DeadlineExceeded && !c.Writer.Written() {
			c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{
				"error":   "request timeout",
				"message": "The request took too long to process",
			})
		}
	}
}

func isLongRunningRoute(path string) bool {
	if strings.HasPrefix(path, "/api/v1/learning-paths/") {
		return true
	}
	return strings.HasPrefix(path, "/api/v1/plans/") && strings.HasSuffix(path, "/generate-tasks")
}
