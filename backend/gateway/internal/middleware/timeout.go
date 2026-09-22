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

// isLongRunningRoute reports whether a route must live outside any
// total-request deadline. SSE streams and streamed downloads are governed by
// the upstream stream lifetime, not by how long the request has been running:
// heartbeats reset idle timers but can never reset a total deadline, so a
// non-exempt stream is deterministically cut at the deadline (observed as
// +30.0s EOF on 23/23 galaxy SSE connections, see v3-output/SSE-HB-VERIFY).
// NetworkResilienceMiddleware consults this same list so a stream never
// carries a second, hidden 30s ceiling from the resilience layer.
func isLongRunningRoute(path string) bool {
	// WebSocket routes are intentionally not listed here. They are registered
	// outside the /api/v1 timeout middleware in setupRouter; after an upgrade,
	// the HTTP connection is hijacked and request timeout deadlines should not
	// govern the long-lived stream.
	if strings.HasPrefix(path, "/api/v1/learning-paths/") {
		return true
	}
	if path == "/api/v1/stt/transcribe" {
		return true
	}
	// SSE-EXEMPT: streaming and long-transfer endpoints (audit 2026-09-22).
	if path == "/api/v1/galaxy/events" {
		// Galaxy real-time update SSE stream (galaxy_handler ProxyToBackend).
		return true
	}
	if path == "/api/v1/chat/stream" {
		// REST chat SSE stream (engine chat.py /stream; mobile chatStream).
		return true
	}
	if strings.HasPrefix(path, "/api/v1/simulation/") && strings.HasSuffix(path, "/stream") {
		// Simulation SSE streams: POST /simulation/run/stream and
		// POST /simulation/sessions/{id}/continue/stream.
		return true
	}
	if path == "/api/v1/background-tasks/stream/events" {
		// Background-task update SSE stream (mobile task monitor).
		return true
	}
	if path == "/api/v1/users/me/export" {
		// Full-account data export: engine streams a ZIP body of unbounded size.
		return true
	}
	if path == "/api/v1/tts/synthesize" {
		// Generative TTS: engine upstream budget (QWEN_TTS_REQUEST_TIMEOUT_
		// SECONDS=60) exceeds the gateway default 30s, so the deadline would
		// cut synthesis the engine itself still considers in-flight.
		return true
	}
	if path == "/api/v1/capsules/generate" || path == "/api/v1/capsules/generate/batch" {
		return true
	}
	if path == "/api/v1/theater/predictions/generate" || path == "/api/v1/theater/predictions/what-if" {
		return true
	}
	return strings.HasPrefix(path, "/api/v1/plans/") && strings.HasSuffix(path, "/generate-tasks")
}
