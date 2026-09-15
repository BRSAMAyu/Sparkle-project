package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestRequestContextMiddlewareGeneratesIDs(t *testing.T) {
	r := gin.New()
	r.Use(RequestContextMiddleware())
	r.GET("/ping", func(c *gin.Context) {
		reqID, _ := c.Get("request_id")
		traceID, _ := c.Get("trace_id")
		c.JSON(http.StatusOK, gin.H{
			"request_id": reqID,
			"trace_id":   traceID,
		})
	})

	req := httptest.NewRequest(http.MethodGet, "/ping", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.NotEmpty(t, w.Header().Get("X-Request-ID"))
	assert.NotEmpty(t, w.Header().Get("X-Trace-ID"))
}

func TestRequestContextMiddlewareKeepsIncomingIDs(t *testing.T) {
	r := gin.New()
	r.Use(RequestContextMiddleware())
	r.GET("/ping", func(c *gin.Context) {
		reqID, _ := c.Get("request_id")
		traceID, _ := c.Get("trace_id")
		c.JSON(http.StatusOK, gin.H{
			"request_id": reqID,
			"trace_id":   traceID,
		})
	})

	req := httptest.NewRequest(http.MethodGet, "/ping", nil)
	req.Header.Set("X-Request-ID", "req-123")
	req.Header.Set("X-Trace-ID", "trace-456")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "req-123", w.Header().Get("X-Request-ID"))
	assert.Equal(t, "trace-456", w.Header().Get("X-Trace-ID"))
}
