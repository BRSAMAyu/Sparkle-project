package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

func TestInternalAPIKey_ValidKey(t *testing.T) {
	cfg := &config.Config{InternalAPIKey: "secret-key-123"}
	r := gin.New()
	r.Use(InternalAPIKeyMiddleware(cfg))
	// route-tier: internal
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	req.Header.Set("X-Internal-API-Key", "secret-key-123")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestInternalAPIKey_InvalidKey(t *testing.T) {
	cfg := &config.Config{InternalAPIKey: "secret-key-123"}
	r := gin.New()
	r.Use(InternalAPIKeyMiddleware(cfg))
	// route-tier: internal
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	req.Header.Set("X-Internal-API-Key", "wrong-key")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestInternalAPIKey_MissingKey(t *testing.T) {
	cfg := &config.Config{InternalAPIKey: "secret-key-123"}
	r := gin.New()
	r.Use(InternalAPIKeyMiddleware(cfg))
	// route-tier: internal
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestInternalAPIKey_NotConfigured(t *testing.T) {
	cfg := &config.Config{InternalAPIKey: ""}
	r := gin.New()
	r.Use(InternalAPIKeyMiddleware(cfg))
	// route-tier: internal
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestInternalAPIKey_TimingAttackResistant(t *testing.T) {
	cfg := &config.Config{InternalAPIKey: "secret-key-123"}
	r := gin.New()
	r.Use(InternalAPIKeyMiddleware(cfg))
	// route-tier: internal
	r.GET("/internal/test", func(c *gin.Context) { c.Status(200) })

	// Even a partial prefix match should fail
	req := httptest.NewRequest(http.MethodGet, "/internal/test", nil)
	req.Header.Set("X-Internal-API-Key", "secret-key")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}
