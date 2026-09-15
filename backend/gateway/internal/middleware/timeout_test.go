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
		{path: "/api/v1/plans/123", want: false},
		{path: "/api/v1/chat/sessions", want: false},
		{path: "/api/v1/users", want: false},
		{path: "/api/v1/health", want: false},
	}

	for _, tc := range tests {
		assert.Equal(t, tc.want, isLongRunningRoute(tc.path), "isLongRunningRoute(%q)", tc.path)
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
