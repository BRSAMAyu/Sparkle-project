package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestIsLongRunningRoute(t *testing.T) {
	tests := []struct {
		path string
		want bool
	}{
		{path: "/api/v1/stt/transcribe", want: true},
		{path: "/api/v1/capsules/generate", want: true},
		{path: "/api/v1/capsules/generate/batch", want: true},
		{path: "/api/v1/theater/predictions/generate", want: true},
		{path: "/api/v1/theater/predictions/what-if", want: true},
		{path: "/api/v1/learning-paths/node-1/full-plan", want: true},
		{path: "/api/v1/plans/123/generate-tasks", want: true},
		// SSE-EXEMPT: streaming / long-transfer exemptions.
		{path: "/api/v1/galaxy/events", want: true},
		{path: "/api/v1/chat/stream", want: true},
		{path: "/api/v1/simulation/run/stream", want: true},
		{path: "/api/v1/simulation/sessions/abc-123/continue/stream", want: true},
		{path: "/api/v1/background-tasks/stream/events", want: true},
		{path: "/api/v1/users/me/export", want: true},
		{path: "/api/v1/tts/synthesize", want: true},
		// Non-exempt controls: near-miss siblings must keep the 30s guard.
		{path: "/api/v1/plans/123", want: false},
		{path: "/api/v1/chat/sessions", want: false},
		{path: "/api/v1/chat", want: false},
		{path: "/api/v1/simulation/run", want: false},
		{path: "/api/v1/simulation/sessions/abc-123/continue", want: false},
		{path: "/api/v1/background-tasks/stream", want: false},
		{path: "/api/v1/background-tasks", want: false},
		{path: "/api/v1/users/export", want: false},
		{path: "/api/v1/users", want: false},
		{path: "/api/v1/tts/voices", want: false},
		{path: "/api/v1/galaxy", want: false},
		{path: "/api/v1/galaxy/graph", want: false},
		{path: "/api/v1/health", want: false},
	}

	for _, tc := range tests {
		assert.Equal(t, tc.want, isLongRunningRoute(tc.path), "isLongRunningRoute(%q)", tc.path)
	}
}

// TestTimeout_ExemptStreamingRoutesNoDeadline asserts, per SSE-EXEMPT exempt
// route, that a handler running longer than the configured timeout still
// completes and that its request context carries no deadline — the regression
// signature of the +30.0s deterministic EOF cut observed on galaxy SSE
// (v3-output/SSE-HB-VERIFY).
func TestTimeout_ExemptStreamingRoutesNoDeadline(t *testing.T) {
	exemptPaths := []string{
		"/api/v1/galaxy/events",
		"/api/v1/chat/stream",
		"/api/v1/simulation/run/stream",
		"/api/v1/simulation/sessions/abc-123/continue/stream",
		"/api/v1/background-tasks/stream/events",
		"/api/v1/users/me/export",
		"/api/v1/tts/synthesize",
		// Pre-existing exemptions stay pinned too.
		"/api/v1/stt/transcribe",
		"/api/v1/capsules/generate",
		"/api/v1/theater/predictions/generate",
		"/api/v1/learning-paths/node-1/full-plan",
		"/api/v1/plans/123/generate-tasks",
	}

	for _, path := range exemptPaths {
		t.Run(path, func(t *testing.T) {
			var hasDeadline bool
			var completed bool

			r := gin.New()
			r.Use(TimeoutMiddleware(50 * time.Millisecond))
			r.Any(path, func(c *gin.Context) {
				_, hasDeadline = c.Request.Context().Deadline()
				// Outlive the timeout: an exempt route must not be cut.
				time.Sleep(120 * time.Millisecond)
				completed = true
				c.Status(http.StatusOK)
			})

			req := httptest.NewRequest(http.MethodGet, path, nil)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code, "exempt route must not be cut by the timeout")
			assert.True(t, completed, "handler must run to completion past the timeout")
			assert.False(t, hasDeadline, "exempt route context must not carry a deadline")
		})
	}
}

func TestTimeout_NormalRequest(t *testing.T) {
	r := gin.New()
	r.Use(TimeoutMiddleware(5 * time.Second))
	// route-tier: internal
	r.GET("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestTimeout_ZeroTimeout(t *testing.T) {
	r := gin.New()
	r.Use(TimeoutMiddleware(0))
	// route-tier: internal
	r.GET("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestTimeout_NegativeTimeout(t *testing.T) {
	r := gin.New()
	r.Use(TimeoutMiddleware(-1 * time.Second))
	// route-tier: internal
	r.GET("/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestTimeout_LongRunningRouteSkipped(t *testing.T) {
	r := gin.New()
	r.Use(TimeoutMiddleware(1 * time.Nanosecond))
	// route-tier: internal
	r.GET("/api/v1/stt/transcribe", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/api/v1/stt/transcribe", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestTimeout_SetsContextDeadline(t *testing.T) {
	timeout := 100 * time.Millisecond
	var hasDeadline bool

	r := gin.New()
	r.Use(TimeoutMiddleware(timeout))
	// route-tier: internal
	r.GET("/test", func(c *gin.Context) {
		_, hasDeadline = c.Request.Context().Deadline()
		c.Status(200)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.True(t, hasDeadline, "context should have deadline set")
}

// TestTimeout_NonExemptRouteStillEnforced pins the red line: ordinary APIs
// keep their total-timeout protection (SSE-EXEMPT must be zero-change for
// them). The request context of a non-exempt route is cancelled at the
// deadline even though the handler is still running.
func TestTimeout_NonExemptRouteStillEnforced(t *testing.T) {
	r := gin.New()
	r.Use(TimeoutMiddleware(50 * time.Millisecond))
	// route-tier: internal
	r.GET("/api/v1/chat/sessions", func(c *gin.Context) {
		select {
		case <-c.Request.Context().Done():
			c.JSON(http.StatusGatewayTimeout, gin.H{"error": "deadline exceeded"})
			return
		case <-time.After(300 * time.Millisecond):
			c.Status(http.StatusOK)
		}
	})

	req := httptest.NewRequest(http.MethodGet, "/api/v1/chat/sessions", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusGatewayTimeout, w.Code, "non-exempt slow request must hit the deadline")
}
